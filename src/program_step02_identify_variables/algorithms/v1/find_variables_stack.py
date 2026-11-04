"""Algorithm version ``v1``.

Chooses which variables and categories to stack: it finds the biggest
mutually-reinforcing ("interlapping") group of questions and categories.

The algorithm consumes the internal model produced by the adapter layer
(``questions`` and ``categories`` dicts) and has no knowledge of the MDD JSON
report format. It returns: list of variables, list of categories, and extra
debug data.
"""

import re


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


def find_all_combinations(lst,depth):
    if not(depth>0):
        yield []
        return
    for index,node in enumerate(lst):
        for result in find_all_combinations(lst[index+1:],depth-1):
            yield [node] + result


# main fn here
def find_variables_to_stack(dict_questions,dict_categories,config={}):
    category_mode = config.get('category_mode', 'union')
    for _, cat in dict_categories.items():
        cat['w'] = CONFIG_CAT_WGT_START_WITH * find_adjusted_category_priority(cat,config)
    for _, q in dict_questions.items():
        q['w'] = CONFIG_INITIAL_Q_WGT
        if q['flags']['is_assigner']:
            q['w'] = 1 - (1-q['w'])*CONFIG_INCREASE_QWGT_IF_ASSIGNER

    # assign weights
    QCFlags = set()
    QCLog = []
    for attempt in range(0,CONFIG_PROCESS_ITERATIONS):
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

    if category_mode == 'intersection':
        # shared stubs only: the maximal set of categories used by every
        # selected variable (v2-like behaviour).
        shared = None
        for qname in result_variables:
            cats = set(dict_questions[qname]['iterations'])
            shared = cats if shared is None else (shared & cats)
        result_categories = sorted(shared or set())
    else:
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
        'variables': [ v for v in result_variables if not dict_questions[v]['flags']['skip'] ],
        'categories': result_categories,
        'variables_raw': result_variables,
        'variables_metadata': [ dict_questions[qname] for qname in dict.keys(dict_questions) if 'w' in dict_questions[qname] ],
        'comment': result_debug_data,
        'algorithm_ver': config.get('algorithm_ver', 'v1'),
    }
    return result

