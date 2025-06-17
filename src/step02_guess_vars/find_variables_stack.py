


import re





if __name__ == '__main__':
    # run as a program
    import util_var_functions
elif '.' in __name__:
    # package
    from . import util_var_functions
else:
    # included with no parent package
    import util_var_functions





# this is an algorithmic approach
# to choose the right vars that we stack
# all is done autocatically
# the code here finds the biggest number of categories that produce the biggest cumulative weight projected to biggest number of variables

# the result is: list of variables, list of categories, and additional data that helps us in debugging





CONFIG_NUM_CATEGORIES_PICK = 3
CONFIG_WEIGHT_DECREASE_IF_NOT_PRIORITY = 0.1
CONFIG_INITIAL_Q_WGT = 0.01
CONFIG_CAT_WGT_START_WITH = 0.1
CONFIG_PROCESS_ITERATIONS = 4
# CONFIG_FREQ_CUTOFF_PERCENTILE = 0.65
# CONFIG_FREQ_CUTOFF_NOTLATERTHAN = 0.95
CONFIG_INCREASE_QWGT_IF_ASSIGNER = 0.35

CONFIG_MAX_WARNINGS = 64









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
    elif( ('dv_country' in category['used']) or ('uslocationdata.state' in category['used']) ):
        ratio = .35
    elif( re.match(r'^\s*?(?:_\d+)\s*?$',category['name'],flags=re.DOTALL|re.ASCII|re.I) ):
        ratio = .01
    elif( re.match(r'^\s*?(?:Yes|No)\s*?$',category['name'],flags=re.DOTALL|re.ASCII|re.I) ):
        ratio = .01
    return ratio



def var_is_assigner(variable):
    # TODO: maybe check if it's a plain variable (not loop or grid or block) and check if it's categorical
    # Ahh we should not care about it now,
    # we are only stacking categoricals,
    # so this is not possible that we get something else here
    if 'properties' in variable:
        for prop in variable['properties']:
            if re.match(r'^\s*?assignertext\s*?$',prop['name'],flags=re.I|re.DOTALL):
                return True
    return False





# note: only categorical variables are assessed with this fn
# we don't have to check if it's an info item, or check loops recursively
# so I am checking 2 thigs: if it's QTA_... quota assigner var
# and if it's a "nocasedata" var
def should_skip(variable,variable_records):
    def check_is_assigner_qta(variable,variable_records):
        if re.match(r'(.*?)(\bqta_)(\w+)\s*?$',variable['name'],flags=re.I|re.DOTALL):
            possible_var_name_assigner = re.sub(r'(.*?)(\bqta_)(\w+)\s*?$',lambda m: '{parentpath}{prefix}{mainpart}'.format(prefix='DV_',mainpart=m[3],parentpath=m[1]),variable['name'],flags=re.I|re.DOTALL)
            possible_var_name_assigner_lcase = possible_var_name_assigner.lower()
            if possible_var_name_assigner_lcase in variable_records:
                variable_assigner = variable_records[possible_var_name_assigner_lcase]
                return var_is_assigner(variable) or var_is_assigner(variable_assigner)
        return False
    def check_no_case_data(variable):
        if 'attributes' in variable:
            for attr in variable['attributes']:
                if attr['name']=='has_case_data':
                    if attr['value']==False or re.match(r'^\s*?false\s*?$',attr['value'],flags=re.I|re.DOTALL):
                        return True
        return False
    # 1. check if it's a helper assigner var that in fact we don't need
    # I'd prefer to trim it in prepdata, but what can I do here, I'll skip
    if check_is_assigner_qta(variable,variable_records):
        return True
    # 2. nocasedata - skip
    if check_no_case_data(variable):
        return True
    # nothing of the above triggered - return "false" (should not skip)
    return False




def find_all_combinations(lst,depth):
    if not(depth>0):
        yield []
        return
    for index,node in enumerate(lst):
        for result in find_all_combinations(lst[index+1:],depth-1):
            yield [node] + result




# main fn here
def find_variables_to_stack(fields_all,config={}):
    
    result_debug_data = {}
    dict_questions = {}
    dict_categories = {}

    if 'priority_categories_str' in config:
        config['priority_categories'] = [ util_var_functions.sanitize_item_name(cat) for cat in config['priority_categories_str'].split(',') ]
    if 'num_categories_pick' in config and not not config['num_categories_pick']:
        if config['num_categories_pick'].isnumeric:
            config['num_categories_pick'] = +int(config['num_categories_pick'])
        else:
            raise ValueError('Wrong config option: num_categories_pick must be numeric ({s})'.format(s=config['num_categories_pick']))
    if not 'num_categories_pick' in config or not config['num_categories_pick']:
        config['num_categories_pick'] = CONFIG_NUM_CATEGORIES_PICK
    
    for row in fields_all:
        item_name = util_var_functions.sanitize_item_name(row['name'])
        item_type = util_var_functions.detect_item_type(item_name)
        if item_type=='blank':
            continue
        elif item_type=='variable':
            variable_name = item_name
            variable_name_lcase = variable_name.lower()
            if not variable_name_lcase in dict_questions:
                dict_questions[variable_name_lcase] = {
                'name': '{n}'.format(n=variable_name),
                'iterations': [],
                'record_ref': row,
                'label': row['label'],
            }
            # dict_questions[variable_name_lcase] = {
            #     **dict_questions[variable_name_lcase],
            #     # 'iterations': dict_questions[variable_name_lcase]['iterations']+[],
            # }
        elif item_type=='category':
            variable_name, category_name = util_var_functions.extract_category_name(item_name)
            variable_name_lower = variable_name.lower()
            category_name_lower = category_name.lower()
            if not variable_name_lower in dict_questions:
                raise ValueError('Found a category but did not find a previous record for the variable: "{s}"'.format(s=item_name))
            dict_questions[variable_name_lower]['iterations'].append(category_name_lower)
            if not category_name_lower in dict_categories:
                dict_categories[category_name_lower] = {
                    'name': '{r}'.format(r=category_name),
                    'used': []
                    }
            dict_categories[category_name_lower]['used'].append(variable_name_lower)
        else:
            raise ValueError('Item name is not recognized, is it a variable or a category: "{s}"'.format(s=row['name']))
    
    # # now we are trying to find frequent categories
    # for category_key, category in dict_categories.items():
    #     def calc_adjusted_frequency(category):
    #         ratio = find_adjusted_category_priority(category,config)
    #         return len(category['used']) * ratio
    #     category['adjusted_frequency'] = calc_adjusted_frequency(category)
    # def find_freq_cutoff(frequencies):
    #     frequencies = sorted(frequencies)
    #     list_of_all_possible_freqs = sorted( [ category['adjusted_frequency'] for category_key, category in dict_categories.items() ] )
    #     #print(list(dict_categories.items()))
    #     if len(list_of_all_possible_freqs) == 0:
    #             list_of_all_possible_freqs = [0]
    #     all_possible_freqs_percentile_value = list_of_all_possible_freqs[len(list_of_all_possible_freqs)-1]*CONFIG_FREQ_CUTOFF_PERCENTILE # int("{:.0f}".format(list_of_all_possible_freqs[len(list_of_all_possible_freqs)-1]*.64))
    #     all_possible_freqs_percentile_index = None
    #     for i in range(0,len(list_of_all_possible_freqs)):
    #         if all_possible_freqs_percentile_index is None:
    #             if( (list_of_all_possible_freqs[i]>all_possible_freqs_percentile_value)):
    #                 all_possible_freqs_percentile_index = i
    #                 break
    #             if len(list_of_all_possible_freqs)>10 and i>len(list_of_all_possible_freqs)*CONFIG_FREQ_CUTOFF_NOTLATERTHAN:
    #                 all_possible_freqs_percentile_index = i
    #                 break
    #     all_possible_freqs_percentile_value = list_of_all_possible_freqs[all_possible_freqs_percentile_index]
    #     #print('len(list_of_all_possible_freqs) = {l0}, list_of_all_possible_freqs[0] = {l1}, list_of_all_possible_freqs[max] = {l2}, u_percentile_75 = {l3}'.format(l0=len(list_of_all_possible_freqs),l1=list_of_all_possible_freqs[0],l2=list_of_all_possible_freqs[len(list_of_all_possible_freqs)-1],l3='list_of_all_possible_freqs[{l0}] = {l1}'.format(l0=all_possible_freqs_percentile_index,l1=list_of_all_possible_freqs[all_possible_freqs_percentile_index])))
    #     return all_possible_freqs_percentile_value
    # # TODO: we are calculating this cutoff and ...we are not using it?
    # freq_cutoff_value = find_freq_cutoff([ category['adjusted_frequency'] for _, category in dict_categories.items() ])
    # key_categories = []
    # for category_key, category in dict_categories.items():
    #     # is_key = category['adjusted_frequency'] >= freq_cutoff_value
    #     is_key = category['adjusted_frequency'] > 0
    #     category['is_key'] = is_key
    #     if is_key:
    #         category['w'] = pow(.5,1/category['adjusted_frequency'])
    #         key_categories.append(category_key)
    for _, cat in dict_categories.items():
        cat['w'] = CONFIG_CAT_WGT_START_WITH * find_adjusted_category_priority(cat,config)
    for _, q in dict_questions.items():
        q['w'] = CONFIG_INITIAL_Q_WGT
        if var_is_assigner(q['record_ref']):
            q['w'] = 1 - (1-q['w'])*CONFIG_INCREASE_QWGT_IF_ASSIGNER
    
    # assign weights
    QCFlags = set()
    QCLog = []
    for attempt in range(0,CONFIG_PROCESS_ITERATIONS):
        # for cat_tested in key_categories:
        #     cat = dict_categories[cat_tested]
        #     questions = cat['used']
        #     for 
        #     best_q_biggest_number_of_matches = {
        #         'qname': None,
        #         'score': 0,
        #         'similar': []
        #     }
        #     for q_tested in questions:
        #         questions_similar = set()
        #         for q_compare in questions:
        #             if not (q_compare==q_tested):
        #                 categories_common = set(dict_questions[q_tested]['iterations']) & set(dict_questions[q_compare]['iterations']) - set([cat_tested])
        #                 if len(categories_common)>0:
        #                     questions_similar = questions_similar | set([q_compare])
        #         questions_similar_count = len(questions_similar)
        #         if questions_similar_count>best_q_biggest_number_of_matches['score']:
        #             best_q_biggest_number_of_matches['score'] = questions_similar_count
        #             best_q_biggest_number_of_matches['qname'] = q_tested
        #             best_q_biggest_number_of_matches['similar'] = [ qname for qname in dict.keys(dict_questions) if qname in questions_similar or qname==q_tested ] # I prefer to maintain order, for debugging, that's why converting from set to list with natural order how questions are listed in the qre
        #     if best_q_biggest_number_of_matches['qname']:
        #         for qname in best_q_biggest_number_of_matches['similar']:
        #             q = dict_questions[qname]
        #             q['w'] = 1 - ( 1 - q['w'] ) * ( 1 - cat['w']*.06 )
        #             if not (q['w']>=0 and q['w']<1):
        #                 QCFlags.add('failed-question-weight')
        #                 QCLog.append('WARNING: question weight reached 1 or 0: weight == {w}, attempt == {attempt}, question == {q}, category == {cat}'.format(w=q['w'],attempt=attempt,q=q['name'],cat=cat_tested))
        #     # w = CONFIG_CAT_WGT_START_WITH
        #     # for qname in questions:
        #     #     q = dict_questions[qname]
        #     #     w = 1 - ( 1 - w ) * ( 1 - q['w'] * pow(1.0/len(questions),.5) )
        #     # cat['w'] = w
        #     # if not(cat['w']>=0 and cat['w']<1):
        #     #     QCFlags.add('failed-category-weight')
        #     #     QCLog.append('WARNING: category weight reached 1 or 0: weight == {w}, attempt == {attempt}, category == {cat}'.format(w=cat['w'],attempt=attempt,cat=cat_tested))
        for _, cat_tested in dict_categories.items():
            for q_iter in cat_tested['used']:
                q = dict_questions[q_iter]
                decrease_factor = 0.08
                cat_tested['w'] = 1 - ( 1 - cat_tested['w'] ) * ( 1 - q['w']*decrease_factor )
        for _, q_tested in dict_questions.items():
            if len(q_tested['iterations'])>0:
                cats_clean = [ {**dict_categories[c_iter]} for c_iter in q_tested['iterations'] if 'w' in dict_categories[c_iter] ]
                cats_clean = sorted(cats_clean,key=lambda c: -c['w'])
                decrease_factor = 0.08
                for cat in cats_clean:
                    q_tested['w'] = 1 - ( 1 - q_tested['w'] ) * ( 1 - cat['w']*decrease_factor )
                    decrease_factor = decrease_factor * .6
                    if not (q_tested['w']>=0 and q_tested['w']<1):
                        QCFlags.add('failed-question-weight')
                        QCLog.append('WARNING: question weight reached 1 or 0: weight == {w}, attempt == {attempt}, question == {q}, category == {cat}'.format(w=q_tested['w'],attempt=attempt,q=q_tested['name'],cat=cat_tested))

    def cmp_key_categories_by_weights(e):
        return (-dict_categories[e]['w'],e)
    key_categories = [ c['name'] for _,c in dict_categories.items() ]
    key_categories = sorted(key_categories,key=cmp_key_categories_by_weights)
    # key_categories = sorted(key_categories,key=cmp_key_categories_by_weights)[:config['num_categories_pick']]
    key_categories = [ c for c in key_categories if dict_categories[c]['w']>dict_categories[key_categories[0]]['w']*.1 ]
    key_categories = key_categories[:36]
    # print('Selected categories: {key_categories}'.format(key_categories=key_categories))

    categories_potential_best_choices = [c for c in key_categories]

    combinations = [ { 'elements': c } for c in find_all_combinations(categories_potential_best_choices,config['num_categories_pick']) ]
    for comb_of_categories in combinations:
        questions_where_cats_are_used = []
        for cat in comb_of_categories['elements']:
            for q in dict_categories[cat]['used']:
                if q not in questions_where_cats_are_used:
                    questions_where_cats_are_used.append(q)
        questions_where_cats_are_used = [ { 'name': q } for q in questions_where_cats_are_used ]
        w_total = 0
        for q in questions_where_cats_are_used:
            w_combined = 0
            for cat in comb_of_categories['elements']:
                if q['name'] in dict_categories[cat]['used']:
                    w = 0.8 + 0.2*dict_questions[q['name']]['w']
                    w_combined = w_combined + w * 1.0/(1.0*len(comb_of_categories['elements']))
            w_combined = pow(w_combined,4)
            q['w'] = w_combined
            w_total = w_total + w_combined
        comb_of_categories['w'] = w_total
        comb_of_categories['ref'] = questions_where_cats_are_used
    combinations = sorted( combinations, key=lambda c: -c['w'] )

    key_categories = combinations[0]['elements']
    
    result_variables = []
    stk_questions_combined_list = dict.keys(dict_questions) if len(key_categories)>0 else []
    for item in key_categories:
        # stk_questions_combined_list.extend([ q for q in dict_categories[item]['used'] if not q in stk_questions_combined_list])
        stk_questions_combined_list = [ q for q in stk_questions_combined_list if q in dict_categories[item]['used'] ]
    # print('the following questions will be stacked: {q}'.format(q=[dict_questions[q]['name'] for q in stk_questions_combined_list]))
    for var in [dict_questions[q]['name'] for q in stk_questions_combined_list]:
        result_variables.append('{qname}'.format(qname=var))
    
    # result_categories = []
    result_category_frequencies = {}
    orig_order_index = 0
    for q in result_variables:
        cats_add = dict_questions[q]['iterations']
        # result_categories.extend([catname for catname in cats_add if not catname in result_categories])
        for cat in cats_add:
            if not cat in result_category_frequencies:
                result_category_frequencies[cat] = { 'name': cat, 'count': 1, 'orig_order_index': orig_order_index }
                orig_order_index = orig_order_index + 1
            else:
                result_category_frequencies[cat]['count'] = result_category_frequencies[cat]['count'] + 1
    result_category_frequencies = [ cat for _, cat in result_category_frequencies.items() ]
    result_category_frequencies = sorted(result_category_frequencies,key=lambda c: -c['count']*100+c['orig_order_index']*(1/len(cats_add)) )
    # if not (len(result_category_frequencies)>0):
    #     raise ValueError('Something went wrong, no categories found')
    # I al also trimming category list to only popular entries
    # and excluding None here (should this be configurable)?
    key_cat_cutoff_index = len(result_category_frequencies) - int(len(result_category_frequencies)*(.69))
    key_cutoff_value = result_category_frequencies[key_cat_cutoff_index]['count'] if len(result_category_frequencies)>0 else len(result_variables)
    result_category_frequencies = [ cat for cat in result_category_frequencies if cat['count']>=key_cutoff_value and not re.match(r'\b(?:NoneThese|NoneAbove|None|NoAnswer|NoneOfThese)\b',cat['name'],flags=re.I) ]
    result_category_frequencies = [ cat['name'] for cat in result_category_frequencies ]
    result_categories = result_category_frequencies
    
    result_debug_data = {
        'key_categories': sorted( [ cat for _,cat in dict_categories.items() if 'w' in cat ], key=lambda c: -c['w'] ),
        'categories_potential_best_choices': categories_potential_best_choices,
        'categories_potential_best_choices_detailed': [ { 'name': c, 'weight': dict_categories[c]['w'], 'used_count': len(dict_categories[c]['used']), 'used': dict_categories[c]['used'], } for c in categories_potential_best_choices ],
        'qclog': QCLog,
        'dict_categories': dict_categories,
        'dict_questions': dict_questions,
    }

    for err in QCLog:
        print(err[:CONFIG_MAX_WARNINGS])
        if len(QCLog)>CONFIG_MAX_WARNINGS:
            print('...{n} more warnings not shown'.format(n=len(QCLog)-CONFIG_MAX_WARNINGS))

    result = {
        'variables': [ v for v in result_variables if not should_skip(dict_questions[v]['record_ref'],dict_questions) ],
        'categories': result_categories,
        'variables_raw': result_variables,
        'variables_metadata': [ dict_questions[qname] for qname in dict.keys(dict_questions) if 'w' in dict_questions[qname] ],
        'comment': result_debug_data,
    }
    return result

