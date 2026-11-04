"""Adapter: turn the flat MDD ``fields`` list into the internal model.

This module is the only place that knows the MDD JSON report shape. It produces
two plain dictionaries consumed by every algorithm version:

    questions : { <lowercase name>: {
                     'name', 'label', 'iterations': [<category lower>...],
                     'record_ref': <raw JSON row> (opaque, for debug output),
                     'flags': {
                         'is_assigner': bool,
                         'skip': bool,   # QTA assigner / no-case-data heuristics
                     },
                 } }
    categories: { <lowercase name>: {
                     'name', 'used': [<question lower>...],
                     'flags': {},       # derivative indicators, empty for now
                 } }

``flags`` are precomputed here so the algorithms never have to look into the raw
MDD JSON. They hold derivative indicators and are kept separate from the
structural fields above; the category ``flags`` dict is a placeholder so future
indicators have a home.
"""

import re

from . import util_var_functions


CONFIG_NUM_CATEGORIES_PICK_DEFAULT = 3


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


def build_model(fields_all):
    dict_questions = {}
    dict_categories = {}

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
                'flags': {},
            }
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
                    'used': [],
                    'flags': {},
                    }
            dict_categories[category_name_lower]['used'].append(variable_name_lower)
        else:
            raise ValueError('Item name is not recognized, is it a variable or a category: "{s}"'.format(s=row['name']))

    # precompute semantic flags so algorithms never look into the raw JSON
    for _, q in dict_questions.items():
        q['flags']['is_assigner'] = var_is_assigner(q['record_ref'])
    for _, q in dict_questions.items():
        q['flags']['skip'] = should_skip(q['record_ref'], dict_questions)

    return dict_questions, dict_categories


def normalize_config(config):
    if 'priority_categories_str' in config:
        config['priority_categories'] = [ util_var_functions.sanitize_item_name(cat) for cat in config['priority_categories_str'].split(',') ]
    if 'num_categories_pick' in config and not not config['num_categories_pick']:
        if config['num_categories_pick'].isnumeric:
            config['num_categories_pick'] = +int(config['num_categories_pick'])
        else:
            raise ValueError('Wrong config option: num_categories_pick must be numeric ({s})'.format(s=config['num_categories_pick']))
    if not 'num_categories_pick' in config or not config['num_categories_pick']:
        config['num_categories_pick'] = CONFIG_NUM_CATEGORIES_PICK_DEFAULT
    return config
