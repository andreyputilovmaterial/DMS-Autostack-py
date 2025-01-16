# import os, time, re, sys
import os
from datetime import datetime, timezone
# from dateutil import tz
import argparse
from pathlib import Path
import re
import json





# if __name__ == '__main__':
#     # run as a program
#     import helper_utility_wrappers
# elif '.' in __name__:
#     # package
#     from . import helper_utility_wrappers
# else:
#     # included with no parent package
#     import helper_utility_wrappers



CONFIG_NUM_CATEGORIES_PICK = 3
CONFIG_WEIGHT_DECREASE_IF_NOT_PRIORITY = 0.0000001
CONFIG_INITIAL_Q_WGT = 0.01
CONFIG_CAT_WGT_START_WITH = 0.1
CONFIG_PROCESS_ITERATIONS = 4
CONFIG_FREQ_CUTOFF_PERCENTILE = 0.65
CONFIG_FREQ_CUTOFF_NOTLATERTHAN = 0.95

CONFIG_MAX_WARNINGS = 64




def sanitize_item_name(item_name):
    return re.sub(r'\s*$','',re.sub(r'^\s*','',re.sub(r'\s*([\[\{\]\}\.])\s*',lambda m:'{m}'.format(m=m[1]),item_name,flags=re.I)))

def detect_item_type(item_name):
    item_name_clean = sanitize_item_name(item_name)
    if re.match(r'^\s*?$',item_name_clean,flags=re.I):
        return 'blank'
    elif re.match(r'^\s*?(\w(?:[\w\[\{\]\}\.]*?\w)?)\.(?:categories|elements)\s*?\[\s*?\{?\s*?(\w+)\s*?\}?\]\s*?$',item_name_clean,flags=re.I):
        return 'category'
    elif re.match(r'^\s*?(\w(?:[\w\[\{\]\}\.]*?\w)?)\s*?$',item_name_clean,flags=re.I):
        return 'variable'
    else:
        raise ValueError('Item name is not recognized, is it a variable or a category: "{s}"'.format(s=item_name))

def extract_field_and_category_part(item_name):
    item_name_clean = sanitize_item_name(item_name)
    matches = re.match(r'^\s*?(\w(?:[\w\[\{\]\}\.]*?\w)?)\.(?:categories|elements)\s*?\[\s*?\{?\s*?(\w+)\s*?\}?\]\s*?$',item_name_clean,flags=re.I)
    return matches[1],matches[2]



def find_adjusted_category_priority(category,config):
    ratio = 1
    priority_categories = []
    if config and 'priority_categories' in config and config['priority_categories']:
        priority_categories = [ cat.lower() for cat in (config['priority_categories'] if 'priority_categories' in config else []) ]
    if len(priority_categories)>0:
        if( category['name'].lower() in priority_categories ):
            ratio = 1
        else:
            return CONFIG_WEIGHT_DECREASE_IF_NOT_PRIORITY * find_adjusted_category_priority(category,{**config,'priority_categories':None})
    if( re.match(r'.*?(?:Other|OtherSpec|None|NoneAbove).*?',category['name'],flags=re.DOTALL|re.ASCII|re.I) ):
        ratio = .85
    # elif( re.match(r'^\s*?\b(?:Us)\b\s*?$',category['name'],flags=re.DOTALL|re.ASCII|re.I) ):
    elif( 'dv_country' in category['used'] ):
        ratio = .35
    elif( re.match(r'^\s*?(?:_\d+)\s*?$',category['name'],flags=re.DOTALL|re.ASCII|re.I) ):
        ratio = .01
    elif( re.match(r'^\s*?(?:Yes|No)\s*?$',category['name'],flags=re.DOTALL|re.ASCII|re.I) ):
        ratio = .01
    return ratio



def find_variables_to_stack(fields_all,config={}):
    
    result_variables = []
    result_categories = []
    result_debug_data = {}
    dict_questions = {}
    dict_categories = {}

    if 'priority_categories_str' in config:
        config['priority_categories'] = [ sanitize_item_name(cat) for cat in config['priority_categories_str'].split(',') ]
    if 'num_categories_pick' in config and not not config['num_categories_pick']:
        if config['num_categories_pick'].isnumeric:
            config['num_categories_pick'] = +int(config['num_categories_pick'])
        else:
            raise ValueError('Wrong config option: num_categories_pick must be numeric ({s})'.format(s=config['num_categories_pick']))
    if not 'num_categories_pick' in config or not config['num_categories_pick']:
        config['num_categories_pick'] = CONFIG_NUM_CATEGORIES_PICK
    
    for row in fields_all:
        item_name = sanitize_item_name(row['name'])
        item_type = detect_item_type(item_name)
        if item_type=='blank':
            continue
        elif item_type=='variable':
            field_name = item_name
            field_name_lcase = field_name.lower()
            if not field_name_lcase in dict_questions:
                dict_questions[field_name_lcase] = {
                'name': '{n}'.format(n=field_name),
                'iterations': [],
                'records_ref': row,
                'label': row['label'],
            }
            # dict_questions[field_name_lcase] = {
            #     **dict_questions[field_name_lcase],
            #     # 'iterations': dict_questions[field_name_lcase]['iterations']+[],
            # }
        elif item_type=='category':
            field_name,category_name = extract_field_and_category_part(item_name)
            field_name_lower = field_name.lower()
            category_name_lower = category_name.lower()
            if not field_name_lower in dict_questions:
                raise ValueError('Found a category but did not find a previous record for the variable: "{s}"'.format(s=item_name))
            dict_questions[field_name_lower]['iterations'].append(category_name_lower)
            if not category_name_lower in dict_categories:
                dict_categories[category_name_lower] = {
                    'name': '{r}'.format(r=category_name),
                    'used': []
                    }
            dict_categories[category_name_lower]['used'].append(field_name_lower)
        else:
            raise ValueError('Item name is not recognized, is it a variable or a category: "{s}"'.format(s=row['name']))
    
    # now we are trying to find frequent categories
    for category_key, category in dict_categories.items():
        def calc_adjusted_frequency(category):
            ratio = find_adjusted_category_priority(category,config)
            return len(category['used']) * ratio
        category['adjusted_frequency'] = calc_adjusted_frequency(category)
    def find_freq_cutoff(frequencies):
        frequencies = sorted(frequencies)
        list_of_all_possible_freqs = sorted( [ category['adjusted_frequency'] for category_key, category in dict_categories.items() ] )
        #print(list(dict_categories.items()))
        if len(list_of_all_possible_freqs) == 0:
                list_of_all_possible_freqs = [0]
        all_possible_freqs_percentile_value = list_of_all_possible_freqs[len(list_of_all_possible_freqs)-1]*CONFIG_FREQ_CUTOFF_PERCENTILE # int("{:.0f}".format(list_of_all_possible_freqs[len(list_of_all_possible_freqs)-1]*.64))
        all_possible_freqs_percentile_index = None
        for i in range(0,len(list_of_all_possible_freqs)):
            if all_possible_freqs_percentile_index is None:
                if( (list_of_all_possible_freqs[i]>all_possible_freqs_percentile_value)):
                    all_possible_freqs_percentile_index = i
                    break
                if len(list_of_all_possible_freqs)>10 and i>len(list_of_all_possible_freqs)*CONFIG_FREQ_CUTOFF_NOTLATERTHAN:
                    all_possible_freqs_percentile_index = i
                    break
        all_possible_freqs_percentile_value = list_of_all_possible_freqs[all_possible_freqs_percentile_index]
        #print('len(list_of_all_possible_freqs) = {l0}, list_of_all_possible_freqs[0] = {l1}, list_of_all_possible_freqs[max] = {l2}, u_percentile_75 = {l3}'.format(l0=len(list_of_all_possible_freqs),l1=list_of_all_possible_freqs[0],l2=list_of_all_possible_freqs[len(list_of_all_possible_freqs)-1],l3='list_of_all_possible_freqs[{l0}] = {l1}'.format(l0=all_possible_freqs_percentile_index,l1=list_of_all_possible_freqs[all_possible_freqs_percentile_index])))
        return all_possible_freqs_percentile_value
    freq_cutoff_value = find_freq_cutoff([ category['adjusted_frequency'] for category_key, category in dict_categories.items() ])
    key_categories = []
    for category_key, category in dict_categories.items():
        # is_key = category['adjusted_frequency'] >= freq_cutoff_value
        is_key = category['adjusted_frequency'] > 0
        category['is_key'] = is_key
        if is_key:
            category['w'] = pow(.5,1/category['adjusted_frequency'])
            key_categories.append(category_key)
    for q_key, q in dict_questions.items():
        q['w'] = CONFIG_INITIAL_Q_WGT
    
    # assign weights
    QCFlags = set()
    QCLog = []
    for attempt in range(0,CONFIG_PROCESS_ITERATIONS):
        for cat_tested in key_categories:
            cat = dict_categories[cat_tested]
            questions = cat['used']
            best_q_biggest_number_of_matches = {
                'qname': None,
                'score': 0,
                'similar': []
            }
            for q_tested in questions:
                questions_similar = set()
                for q_compare in questions:
                    if not (q_compare==q_tested):
                        categories_common = set(dict_questions[q_tested]['iterations']) & set(dict_questions[q_compare]['iterations']) - set([cat_tested])
                        if len(categories_common)>0:
                            questions_similar = questions_similar | set([q_compare])
                questions_similar_count = len(questions_similar)
                if questions_similar_count>best_q_biggest_number_of_matches['score']:
                    best_q_biggest_number_of_matches['score'] = questions_similar_count
                    best_q_biggest_number_of_matches['qname'] = q_tested
                    best_q_biggest_number_of_matches['similar'] = [ qname for qname in dict.keys(dict_questions) if qname in questions_similar or qname==q_tested ] # I prefer to maintain order, for debugging, that's why converting from set to list with natural order how questions are listed in the qre
            if best_q_biggest_number_of_matches['qname']:
                for qname in best_q_biggest_number_of_matches['similar']:
                    q = dict_questions[qname]
                    q['w'] = 1 - ( 1 - q['w'] ) * ( 1 - cat['w']*.06 )
                    if not (q['w']>=0 and q['w']<1):
                        QCFlags.add('failed-question-weight')
                        QCLog.append('WARNING: question weight reached 1 or 0: weight == {w}, attempt == {attempt}, question == {q}, category == {cat}'.format(w=q['w'],attempt=attempt,q=q['name'],cat=cat_tested))
            w = CONFIG_CAT_WGT_START_WITH
            for qname in questions:
                q = dict_questions[qname]
                w = 1 - ( 1 - w ) * ( 1 - q['w'] * pow(1.0/len(questions),.5) )
            cat['w'] = w
            if not(cat['w']>=0 and cat['w']<1):
                QCFlags.add('failed-category-weight')
                QCLog.append('WARNING: category weight reached 1 or 0: weight == {w}, attempt == {attempt}, category == {cat}'.format(w=cat['w'],attempt=attempt,cat=cat_tested))

    def cmp_key_categories_by_weights(e):
        return (-dict_categories[e]['w'],e)
    key_categories = sorted(key_categories,key=cmp_key_categories_by_weights)[:config['num_categories_pick']]
    # print('Selected categories: {key_categories}'.format(key_categories=key_categories))
    
    for cat in key_categories:
        result_categories.append('{qname}'.format(qname=cat))
    stk_questions_combined_list = dict.keys(dict_questions) if len(key_categories)>0 else []
    for item in key_categories:
        # stk_questions_combined_list.extend([ q for q in dict_categories[item]['used'] if not q in stk_questions_combined_list])
        stk_questions_combined_list = [ q for q in stk_questions_combined_list if q in dict_categories[item]['used'] ]
    # print('the following questions will be stacked: {q}'.format(q=[dict_questions[q]['name'] for q in stk_questions_combined_list]))
    for cat in [dict_questions[q]['name'] for q in stk_questions_combined_list]:
        result_variables.append('{qname}'.format(qname=cat))
    
    result_debug_data = {
        'key_categories': sorted( [ cat for _,cat in dict_categories.items() if 'w' in cat ], key=lambda c: -c['w'] ),
        'dict_categories': dict_categories,
        'dict_questions': dict_questions,
    }

    for err in QCLog:
        print(err[:CONFIG_MAX_WARNINGS])
        if len(QCLog)>CONFIG_MAX_WARNINGS:
            print('...{n} more warnings not shown'.format(n=len(QCLog)-CONFIG_MAX_WARNINGS))

    result = {
        'variables': result_variables,
        'categories': result_categories,
        'variables_metadata': [ dict_questions[qname] for qname in dict.keys(dict_questions) if 'w' in dict_questions[qname] ],
        'debug_data': result_debug_data,
    }
    return result




def entry_point(runscript_config={}):

    time_start = datetime.now()
    script_name = 'mdmautostktoolsap autostacking suggest-loop-and-variables script'

    parser = argparse.ArgumentParser(
        description="Autostacking: guess which loops and variables to stack on",
        prog='mdd-autostacking-pick-variables'
    )
    parser.add_argument(
        '-1',
        '--inp-mdd-scheme',
        type=str,
        help='JSON with fields data from MDD Input File',
        required=True
    )
    parser.add_argument(
        '--config-priority-categories',
        help='Priority categories: examples of categories that you stack on',
        type=str,
        required=False
    )
    parser.add_argument(
        '--output-filename',
        help='Set preferred output file name, with path',
        type=str,
        required=False
    )
    args = None
    args_rest = None
    if( ('arglist_strict' in runscript_config) and (not runscript_config['arglist_strict']) ):
        args, args_rest = parser.parse_known_args()
    else:
        args = parser.parse_args()
    
    inp_filename = ''
    if args.inp_mdd_scheme:
        inp_filename = Path(args.inp_mdd_scheme)
        inp_filename = '{inp_filename}'.format(inp_filename=inp_filename.resolve())
    else:
        raise FileNotFoundError('Inp source: file not provided; please use --inp-mdd-scheme option')

    config = {}
    if args.config_priority_categories:
        config['priority_categories_str'] = args.config_priority_categories


    # report_part_filename = re.sub( r'\.json\s*?$', '', Path(inp_filename).name )
    result_final_fname = None
    if args.output_filename:
        result_final_fname = Path(args.output_filename)
    else:
        raise FileNotFoundError('Inp source: file not provided; please use --inp-mdd-scheme option')
    

    if not(Path(inp_filename).is_file()):
        raise FileNotFoundError('file not found: {fname}'.format(fname=inp_filename))

    inp_mdd_scheme = None
    with open(inp_filename) as f_l:
        try:
            inp_mdd_scheme = json.load(f_l)
        except json.JSONDecodeError as e:
            # just a more descriptive message to the end user
            # can happen if the tool is started two times in parallel and it is writing to the same json simultaneously
            raise TypeError('Autostacking variable and loop guesser: Can\'t read input file as JSON: {msg}'.format(msg=e))
    
    print('{script_name}: script started at {dt}'.format(dt=time_start,script_name=script_name))

    data = []
    try:
        data = ([sect for sect in inp_mdd_scheme['sections'] if sect['name']=='fields'])[0]['content']
    except:
        pass

    result = find_variables_to_stack(data,config)
    
    result_json = json.dumps(result, indent=4)

    print('{script_name}: saving as "{fname}"'.format(fname=result_final_fname,script_name=script_name))
    with open(result_final_fname, "w") as outfile:
        outfile.write(result_json)

    time_finish = datetime.now()
    print('{script_name}: finished at {dt} (elapsed {duration})'.format(dt=time_finish,duration=time_finish-time_start,script_name=script_name))



if __name__ == '__main__':
    entry_point({'arglist_strict':True})
