
import re



if __name__ == '__main__':
    # run as a program
    import util_vars
elif '.' in __name__:
    # package
    from . import util_vars
else:
    # included with no parent package
    import util_vars



# def get_mdd_data_records_from_input_data(inp_mdd_scheme,variable_specs):
def get_mdd_data_records_from_input_data(inp_mdd_scheme):
    def convert_list_to_dict(data_lst):
        result = {}
        for record in data_lst:
            result[record['name']] = record['value']
        return result
    # def update_mdd_data_records_with_iterations_from_variable_specs(mdd_data_records,variable_specs):
    #     for var in variable_specs['variables_metadata']:
    #         if 'iterations' in var:
    #             for variable_record in mdd_data_records:
    #                 if util_vars.sanitize_item_name(variable_record['name'])==util_vars.sanitize_item_name(var['name']):
    #                     variable_record['iterations'] = var['iterations']
    #     return mdd_data_records
    mdd_data_records = ([sect for sect in inp_mdd_scheme['sections'] if sect['name']=='fields'])[0]['content']
    mdd_data_records = [ {**q,'properties':convert_list_to_dict(q['properties'] if 'properties' in q else []),'attributes':convert_list_to_dict(q['attributes'] if 'attributes' in q else [])} for q in mdd_data_records ]
    # now we want to have category list (aka "list of iterations") added to every variable
    # approach A
    # approach A - read it from variable_specs - this is already stored, generated in step02_autostk_var_loop_guesser
    # unfortunately, category names are normalized to lowercase there - not perfectly beautiful
    # mdd_data_records = update_mdd_data_records_with_iterations_from_variable_specs(mdd_data_records,variable_specs)
    # approach B
    # so I'll use another approach B
    return mdd_data_records


def detect_item_type_from_mdddata_fields_report(item_name):
    item_name_clean = util_vars.sanitize_item_name(item_name)
    if re.match(r'^\s*?$',item_name_clean,flags=re.I):
        return 'blank'
    elif re.match(r'^\s*?(\w(?:[\w\[\{\]\}\.]*?\w)?)\.(?:categories|elements)\s*?\[\s*?\{?\s*?(\w+)\s*?\}?\]\s*?$',item_name_clean,flags=re.I):
        return 'category'
    elif re.match(r'^\s*?(\w(?:[\w\[\{\]\}\.]*?\w)?)\s*?$',item_name_clean,flags=re.I):
        return 'variable'
    else:
        raise ValueError('Item name is not recognized, is it a variable or a category: "{s}"'.format(s=item_name))







def prepare_variable_records(mdd_data_records,mdd_data_categories,mdd_data_root):
    variable_records = {}
    # for rec in variable_specs['variables_metadata']:
    for rec in mdd_data_records:
        question_id_clean = util_vars.sanitize_item_name(rec['name'])
        variable_records[question_id_clean] = rec
    for rec in mdd_data_records:
        path, _ = util_vars.extract_field_name(rec['name'])
        if path and not (path==''):
            variable_parent = variable_records[util_vars.sanitize_item_name(path)]
            if not 'subfields' in variable_parent:
                variable_parent['subfields'] = []
            variable_parent['subfields'].append(rec) # that's a reference, and child item should also be updated, when it receives its own subfields
    for cat_mdd in mdd_data_categories:
        question_name, category_name = util_vars.extract_category_name(cat_mdd['name'])
        question_id_clean = util_vars.sanitize_item_name(question_name)
        variable = variable_records[question_id_clean]
        if not 'categories' in variable:
            variable['categories'] = []
        variable['categories'].append({**cat_mdd,'name':category_name}) # that's not a reference, that's a copy; and name is a category name
    variable_records[''] = mdd_data_root
    return variable_records


def prepare_category_records(mdd_data_records,mdd_data_categories,mdd_data_root):
    result = {}
    for cat in mdd_data_categories:
        variable_name, category_name = util_vars.extract_category_name(cat['name'])
        cat['name_variable'] = variable_name
        cat['name_category'] = category_name
        result[util_vars.sanitize_item_name(category_name)] = cat
    return result




