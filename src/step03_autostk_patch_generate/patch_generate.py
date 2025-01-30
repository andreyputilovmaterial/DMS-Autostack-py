from datetime import datetime, timezone
import argparse
from pathlib import Path
import re
import json




if __name__ == '__main__':
    # run as a program
    import utility_performance_monitor
    import util_produce_code_mdata as metadata_functions
    import util_produce_code_edits as edits_functions
elif '.' in __name__:
    # package
    from . import utility_performance_monitor
    from . import util_produce_code_mdata as metadata_functions
    from . import util_produce_code_edits as edits_functions
else:
    # included with no parent package
    import utility_performance_monitor
    import util_produce_code_mdata as metadata_functions
    import util_produce_code_edits as edits_functions




# we can set it to True of False
# if we set it to True, we'll run additional code
# that brings all shared lists from the original MDD
# to MDMDocument dynamically created
# to generate metadata for newly created items in stacked
# if we set it to True, we can correctly iterate over all categories (elements)
# everywhere and not hit "Unresolved reference" error
# but maybe it is unnecessary
# we don't have to iterate over categories in shared lists
# when updating labels - labels are already defined in a shared lists,
# that's the correct place, we don't have to update anything
# and it seems we don't have to iterate over elements to produce
# a list of categories for edits code - just because such iterating is slow,
# and we already have a list of categories in variable_record from mdd_read
# so maybe we can turn this switch to off (to False)
# and make mdm scripts generation faster,
# because we are re-creating mdmdoc every time we are processing a new item (should we?)
# and adding shared lists adds significant time to generating results
CONFIG_BRING_SHAREDLISTS_TO_NEW_MDMDOC_TO_ADDRESS_CAT_UNRESOLVEDREFERENCES = False



# the name of the loop, will be "STKLoop"
# we don't guarantee that the loop created will have exactly this name,
# if this is name is already used,
# we'll add "_2",, "_3", and so on
# basically, this name is not super important, it can be whatever not already used, because we'll move from this level in STKCreate and we'll not have this loop in final data
CONFIG_LOOP_NAME_SUGGESTED = 'STKLoop'




def trim_dots(s):
    return re.sub(r'^\s*?\.','',re.sub(r'\.\s*?$','',s,flags=re.I),flags=re.I)

def sanitize_item_name(item_name):
    return re.sub(r'\s*$','',re.sub(r'^\s*','',re.sub(r'\s*([\[\{\]\}\.])\s*',lambda m:'{m}'.format(m=m[1]),item_name,flags=re.I))).lower()

def extract_field_name(item_name):
    m = re.match(r'^\s*((?:\w.*?\.)*)(\w+)\s*$',item_name,flags=re.I)
    if m:
        return re.sub(r'\s*\.\s*$','',m[1]),m[2]
    else:
        raise ValueError('Can\'t extract field name from "{s}"'.format(s=item_name))

def extract_parent_name(item_name):
    if item_name=='':
        return '', ''
    m = re.match(r'^\s*(\w+)((?:\.\w*?)*)\s*$',item_name,flags=re.I)
    if m:
        return trim_dots(m[1]), trim_dots(m[2])
    else:
        raise ValueError('Can\'t extract field name from "{s}"'.format(s=item_name))

def extract_category_name(item_name):
    m = re.match(r'^\s*(\w+.*?\w)\.(?:categories|elements)\s*?\[\s*?\{?\s*?(\w+)\s*?\}?\s*?\]\s*$',item_name,flags=re.I)
    if m:
        return trim_dots(m[1]), trim_dots(m[2])
    else:
        raise ValueError('Can\'t extract category name from "{s}"'.format(s=item_name))




def should_skip(variable_record,variable_records):
    def check_val_txt(value_assess,value_compare):
        def trim(s):
            return re.sub(r'^\s*','',re.sub(r'\s*$','',s))
        def sanitize(s):
            s = '{s}'.format(s=s)
            s = trim(s)
            s = s.lower()
            return s
        return sanitize(value_assess)==sanitize(value_compare)
    def check_is_assigner_qta(variable_record,variable_records):
        assigner_found = False
        path, fieldname = extract_field_name(variable_record['name'])
        if re.match(r'^\s*?(qta_)(\w+)\s*?$',fieldname,flags=re.I|re.DOTALL):
            field_name_assigner = re.sub(r'^\s*?(qta_)(\w+)\s*?$',lambda m: '{prefix}{mainpart}'.format(prefix='DV_',mainpart=m[2]),fieldname,flags=re.I|re.DOTALL)
            variable_name_assigner = sanitize_item_name(trim_dots('{path}.{field}'.format(path=path,field=field_name_assigner)))
            if variable_name_assigner in variable_records:
                variable_assigner = variable_records[variable_name_assigner]
                properties = [ p.lower() for p in variable_record['properties'].keys() ] + [ p.lower() for p in variable_assigner['properties'].keys() ]
                if 'assignertext' in properties:
                    assigner_found = True
        return assigner_found
    def check_no_case_data(variable_record,variable_records):
        return ( 'has_case_data' in variable_record['attributes'] and check_val_txt(variable_record['attributes']['has_case_data'],'false') )
    # 1. check if it's a helper assigner var that in fact we don't need
    # I'd prefer to trim it in prepdata, but what can I do here, I'll skip
    if check_is_assigner_qta(variable_record,variable_records):
        return True
    # 2. nocasedata - skip
    if check_no_case_data(variable_record,variable_records):
        return True
    # nothing of the above triggered - return "false" (should not skip)
    return False




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
    #                 if sanitize_item_name(variable_record['name'])==sanitize_item_name(var['name']):
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
    item_name_clean = sanitize_item_name(item_name)
    if re.match(r'^\s*?$',item_name_clean,flags=re.I):
        return 'blank'
    elif re.match(r'^\s*?(\w(?:[\w\[\{\]\}\.]*?\w)?)\.(?:categories|elements)\s*?\[\s*?\{?\s*?(\w+)\s*?\}?\]\s*?$',item_name_clean,flags=re.I):
        return 'category'
    elif re.match(r'^\s*?(\w(?:[\w\[\{\]\}\.]*?\w)?)\s*?$',item_name_clean,flags=re.I):
        return 'variable'
    else:
        raise ValueError('Item name is not recognized, is it a variable or a category: "{s}"'.format(s=item_name))








def prepare_variable_records(mdd_data_records,mdd_data_categories):
    variable_records = {}
    # for rec in variable_specs['variables_metadata']:
    for rec in mdd_data_records:
        question_id_clean = sanitize_item_name(rec['name'])
        variable_records[question_id_clean] = rec
    for rec in mdd_data_records:
        path, _ = extract_field_name(rec['name'])
        if path and not (path==''):
            variable_parent = variable_records[sanitize_item_name(path)]
            if not 'subfields' in variable_parent:
                variable_parent['subfields'] = []
            variable_parent['subfields'].append(rec) # that's a reference, and child item should also be updated, when it receives its own subfields
    for cat_mdd in mdd_data_categories:
        question_name, category_name = extract_category_name(cat_mdd['name'])
        question_id_clean = sanitize_item_name(question_name)
        variable = variable_records[question_id_clean]
        if not 'categories' in variable:
            variable['categories'] = []
        variable['categories'].append({**cat_mdd,'name':category_name}) # that's not a reference, that's a copy; and name is a category name

    return variable_records

def detect_var_type_by_record(variable_record):
    variable_attributes_captured_with_mdd_read = {}
    if not 'attributes' in variable_record:
        raise ValueError('Input data does not include "attributes" data, please adjust settings that you use to run mdd_read')
    else:
        assert isinstance(variable_record,dict)
    variable_attributes_captured_with_mdd_read = {**variable_record['attributes']}
    if not 'type' in variable_attributes_captured_with_mdd_read:
        raise ValueError('Input data must follow certain format and must include "type" within its list of attributes generated with mdd_read')

    # detect variable type - we are doing it from grabbing data from attributes that were written by mdd_read
    variable_type = None
    # variable_is_plain = re.match(r'^\s*?plain\b',variable_attributes_captured_with_mdd_read['type'])
    variable_is_categorical = re.match(r'^\s*?plain/(?:categorical|multipunch|singlepunch)',variable_attributes_captured_with_mdd_read['type'])
    variable_is_loop = re.match(r'^\s*?(?:array|grid|loop)\b',variable_attributes_captured_with_mdd_read['type'])
    # variable_is_block = re.match(r'^\s*?(?:block)\b',variable_attributes_captured_with_mdd_read['type'])
    if variable_is_loop:
        variable_type = 'loop'
    elif variable_is_categorical:
        variable_type = 'categorical'
    else:
        raise ValueError('Can\'t handle this type of variable: {s}'.format(s=variable_attributes_captured_with_mdd_read['type']))
    return variable_type

def should_exclude_field(mdmfield):
    field_exclude = False
    if (mdmfield.DataType if mdmfield.ObjectTypeValue==0 else 4) == 0: # info item, skip, 4 = "object"
        field_exclude = True
    if sanitize_item_name(mdmfield.Name)==sanitize_item_name('NavButtonSelect'):
        field_exclude = True # that stupid field from mf-polar
    return field_exclude

def check_if_improper_name(name):
    is_improper_name = False
    # and there are less common cases but still happening in disney bes
    is_improper_name = is_improper_name or not not re.match(r'^\s*?((?:Top|T|Bottom|B))(\d*)((?:B|Box))\s*?$',name,flags=re.I)
    is_improper_name = is_improper_name or not not re.match(r'^\s*?(?:GV|Rank|Num)\s*?$',name,flags=re.I)
    return is_improper_name

def check_if_field_name_can_be_used_as_final_name(mdmparent,variable_record,variable_records,previously_added):
    result = True
    flag_iim = False
    flag_rpc = False
    potential_item_path, _ = extract_field_name(variable_record['name'])
    patch_chunks_with_top_level_items = [ chunk for chunk in previously_added if chunk['action']=='variable-new' and sanitize_item_name(chunk['position'])=='' ]
    loopname = patch_chunks_with_top_level_items[0]['variable'] # the first item added was the loop
    potential_item_path_stk = trim_dots('{stk_loop}.{path}'.format(stk_loop=loopname,path=potential_item_path))
    for mdmfield in mdmparent.Fields:
        # if that's not field we care about, just skip
        if should_exclude_field(mdmfield):
            continue
        # first I do straightforward check - check if this item exists at parent level
        potential_full_name = sanitize_item_name( trim_dots('{parent_path}.{item}'.format(parent_path=potential_item_path,item=mdmfield.Name)) )
        count_previous_entries = len([ chunk for chunk in previously_added if chunk['action']=='variable-new' and sanitize_item_name(chunk['variable'])==sanitize_item_name(mdmfield.Name) and sanitize_item_name(chunk['position'])==sanitize_item_name(potential_item_path_stk) ])
        already_existing = count_previous_entries>0
        result = result and not already_existing
        # and we'll also check unstk
        already_existing_in_unstk = potential_full_name in variable_records
        result = result and not already_existing_in_unstk
        # also we should not create items named just "GV" so I'll check against some popular field names
        is_improper_name = re.match(r'^\s*?(?:GV|Num|Rank)\s*?$',mdmfield.Name,flags=re.I|re.DOTALL)
        result = result and not is_improper_name
        iim_flags_count = 0
        rpc_flags_count = 0
        if 'overlap' in sanitize_item_name(mdmfield.Name):
            iim_flags_count = iim_flags_count + 1
        if ('iim' in sanitize_item_name(mdmparent.Name) or 'qim' in sanitize_item_name(mdmparent.Name)):
            iim_flags_count = iim_flags_count + 1
        if re.match(r'^\s*?(?:Which)\s*?$',mdmfield.Name,flags=re.I):
            if ('rpc' in sanitize_item_name(mdmparent.Name)):
                rpc_flags_count = rpc_flags_count + 1
            else:
                iim_flags_count = iim_flags_count + 1
        if iim_flags_count>=2:
            flag_iim = True
        if rpc_flags_count>=1:
            flag_rpc = True
    result = result and not flag_iim and not flag_rpc
    return result

def choose_loop_name(variable_records,name_to_start_with):
    stk_loopname = name_to_start_with
    # avoid using name that is already used
    counter = 2
    while sanitize_item_name(stk_loopname) in variable_records:
        stk_loopname = '{base_part}_{knt}'.format(base_part=CONFIG_LOOP_NAME_SUGGESTED,knt=counter)
        counter = counter + 1
    return stk_loopname

def prepare_category_list_stk_list(key_categories,mdd_data_categories,mdmdoc):
    cat_stk_data = []
    performance_counter = iter(utility_performance_monitor.PerformanceMonitor(config={
        'total_records': len(key_categories),
        'report_frequency_records_count': 1,
        'report_frequency_timeinterval': 14,
        'report_text_pipein': 'progress processing categories',
    }))
    print_log_processing('categories: trying to find the most frequent label and analysis value for every category')
    # TODO: this is slow
    # actually, the only project where it takes significant time (~maybe 5-10 minutes) is Gerber 2302101
    # but that's a very bad project with ghost categories, with old categories, with revammp in (I don't remember year) when category names changed
    # in most project, even big trackers, this still takes several seconds
    # so this can be optimized
    # but I am not willing to spend time on this now
    for cat_mdd in mdd_data_categories:
        category_properties_dict = cat_mdd['properties']
        assert not isinstance(category_properties_dict,list)
        category_analysisvalue = None
        for prop_name, prop_value in category_properties_dict.items(): # we need to iterate cause property names are case insensitive; it can be "value" or "Value", or (I've never seen, but it can be) "VaLuE"
            if sanitize_item_name(prop_name)==sanitize_item_name('value'):
                def sanitize_value(value):
                    if not value:
                        return None
                    try:
                        value_float = float(value)
                        value_int = int(round(value_float))
                        is_whole = abs(value_float-value_int)<0.01
                        if is_whole:
                            return value_int
                        else:
                            return None
                    except:
                        return None
                analysis_value = sanitize_value(prop_value)
                if analysis_value:
                    category_analysisvalue = analysis_value
        cat_mdd['property_analysis_value'] = category_analysisvalue
    for cat_stk_name in [ sanitize_item_name(c) for c in key_categories ]:
        next(performance_counter)
        cat_label_frequency_data = {}
        cat_analysisvalue_frequency_data = {}
        for cat_mdd in mdd_data_categories:
            question_name, category_name = extract_category_name(cat_mdd['name'])
            question_name_clean, category_name_clean = sanitize_item_name(question_name), sanitize_item_name(category_name)
            category_label = cat_mdd['label']
            category_analysisvalue = cat_mdd['property_analysis_value']
            if category_name_clean==cat_stk_name:
                cat_label_id = category_label
                if cat_label_id in cat_label_frequency_data:
                    cat_label_frequency_data[cat_label_id]['count'] = cat_label_frequency_data[cat_label_id]['count'] + 1
                    cat_label_frequency_data[cat_label_id]['questions_used'].append(question_name_clean) # why storing this data, I don't use it
                else:
                    cat_label_frequency_data[cat_label_id] = {
                        'name': category_name,
                        'questions_used': [question_name_clean], # why storing this data, I don't use it
                        'label': category_label,
                        'count': 1
                    }
                cat_analysisvalue_id = '{s}'.format(s=category_analysisvalue)
                if category_analysisvalue and category_analysisvalue>0:
                    if cat_analysisvalue_id in cat_analysisvalue_frequency_data:
                        cat_analysisvalue_frequency_data[cat_analysisvalue_id]['count'] = cat_analysisvalue_frequency_data[cat_analysisvalue_id]['count'] + 1
                    else:
                        cat_analysisvalue_frequency_data[cat_analysisvalue_id] = {
                            'count': 1,
                            'value': category_analysisvalue,
                        }
        cat_label_frequency_data = [ cat for _, cat in cat_label_frequency_data.items() ]
        if len(cat_label_frequency_data)==0:
            cat_label_frequency_data = [{
                'name': cat_stk_data,
                'questions_used': [],
                'label': cat_stk_data,
                'count': 0
            }]
        cat_label_frequency_data = sorted(cat_label_frequency_data,key=lambda c: -c['count'])
        cat_label_data = cat_label_frequency_data[0]
        cat_analysisvalue_frequency_data = [ cat for _, cat in cat_analysisvalue_frequency_data.items() ]
        cat_analysisvalue_frequency_data = sorted(cat_analysisvalue_frequency_data,key=lambda c: -c['count'])
        cat_analysisvalue_data = cat_analysisvalue_frequency_data[0]['value'] if len(cat_analysisvalue_frequency_data)>0 else None
        cat_stk_data.append({
            'cat_id': cat_stk_name,
            'name': cat_label_data['name'],
            'label': cat_label_data['label'],
            'questions_used': cat_label_data['questions_used'], # why storing this data, I don't use it
            'properties': { 'Value': cat_analysisvalue_data } if cat_analysisvalue_data else {},
        })
    return [ metadata_functions.generate_category_metadata(cat['name'],cat['label'],cat['properties'],mdmdoc) for cat in cat_stk_data ]





def process_outerloop(name,key_categories,mdd_data_categories,mdmdoc,previously_added):
    print_log_processing('categories')
    mdmcategories = prepare_category_list_stk_list(key_categories,mdd_data_categories,mdmdoc)
    print_log_processing('top level stacking loop')
    result_metadata = metadata_functions.generate_scripts_outerstkloop( name, mdmcategories )
    result_edits = edits_functions.generate_code_outerstkloop_walkthrough( None, None, stk_variable_name=name, unstk_variable_name='', unstk_variable_fieldname='', categories_iterating_over=None )
    # add defines
    assert re.match(r'^\w+$',name,flags=re.I)
    yield {
        'action': 'section-insert-lines',
        'position': '', # top of the script
        'new_lines': '#define STACKINGLOOP "'+name+'"\n'
    }
    result_patch = {
        'action': 'variable-new',
        'variable': name,
        'position': '', # root
        'debug_data': { 'description': 'top level stacking loop' },
        'new_metadata': result_metadata,
        'attributes': { 'object_type_value': 1, 'label': None, 'type': 'array' },
        'new_edits': result_edits,
    }
    yield result_patch

def process_stack_a_loop(mdmitem_stk,field_name_stk,path_stk,mdmitem_unstk,field_name_unstk,path_unstk,variable_record,variable_records,mdmdoc,previously_added):
    mdmitem_stk = metadata_functions.sync_labels_from_mddreport(mdmitem_stk,variable_record)
    mdmitem_stk = metadata_functions.generate_updated_metadata_update_all_in_batch(mdmitem_stk,variable_record,mdmdoc)
    _, loop_name_unstk = extract_field_name(path_unstk)
    loop_variable_unstk = variable_records[sanitize_item_name(path_unstk)]

    for result_patch_parent in process_every_parent(path_stk,variable_records,mdmdoc,previously_added):
        yield result_patch_parent

    # done with parent levels, add record for processing the variable that is stacked
    result_metadata = mdmitem_stk.Script
    result_edits = ''
    if variable_record['attributes']['object_type_value']==0:
        # it means it's a regular plain variable
        # we can use direct assignment
        result_edits = edits_functions.generate_code_loop_unstack_simple( mdmitem_stk, mdmitem_unstk, stk_variable_name=field_name_stk, unstk_variable_name=loop_name_unstk, unstk_variable_fieldname=field_name_unstk, categories_iterating_over=loop_variable_unstk['categories'] )
    else:
        # it's c complex structure
        # unfortunately, direct assignment "A = B" is not working in dms scripts
        # we need to iterate over fields
        # and I can't use a function, i.e. CopyFrom(A,B)
        # because I can't detect var/loop type in CDSC (case data source component)
        # anyway, doing euristic analysis is not 100% right, it is not the most performance efficient
        # and stacking is sometimes slow, it can take 8 hours, or more, in some projects, i.e. Disney+&Hulu tracker
        # So I have to generate proper code here iterating over all loops and fields
        result_edits = edits_functions.generate_code_loop_unstack_structural( mdmitem_stk, mdmitem_unstk, stk_variable_name=field_name_stk, unstk_variable_name=loop_name_unstk, unstk_variable_fieldname=field_name_unstk, categories_iterating_over=loop_variable_unstk['categories'] )
    result_patch = {
        'action': 'variable-new',
        'variable': mdmitem_stk.Name,
        'position': path_stk,
        'debug_data': { 'source_from': variable_record['name'] },
        'new_metadata': result_metadata,
        'attributes': variable_record['attributes'],
        'new_edits': result_edits,
    }
    yield result_patch
    count_entries_stk = len([ chunk for chunk in previously_added if chunk['action']=='variable-new' and sanitize_item_name(chunk['variable'])==sanitize_item_name(field_name_stk) and sanitize_item_name(chunk['position'])==sanitize_item_name(path_stk) ])
    exist_stk = count_entries_stk>0
    duplicate_stk = count_entries_stk>1
    exist_unstk = sanitize_item_name(trim_dots(path_unstk+'.'+field_name_unstk)) in variable_records
    assert exist_stk
    assert not duplicate_stk
    assert exist_unstk

def process_stack_a_categorical(mdmitem_stk,field_name_stk,path_stk,mdmitem_unstk,field_name_unstk,path_unstk,variable_record,variable_records,mdmdoc,previously_added):
    mdmitem_stk = metadata_functions.generate_updated_metadata_update_all_in_batch(mdmitem_stk,variable_record,mdmdoc)

    for result_patch_parent in process_every_parent(path_stk,variable_records,mdmdoc,previously_added):
        yield result_patch_parent

    # done with parent levels, add record for processing the variable that is stacked
    result_metadata = mdmitem_stk.Script
    result_edits = edits_functions.generate_code_unstack_categorical_yn( mdmitem_stk, None, stk_variable_name=field_name_stk, unstk_variable_name=field_name_unstk, unstk_variable_fieldname=field_name_unstk, categories_iterating_over=variable_record['categories'] )
    result_patch = {
        'action': 'variable-new',
        'variable': mdmitem_stk.Name,
        'position': path_stk,
        'debug_data': { 'source_from': variable_record['name'] },
        'new_metadata': result_metadata,
        'attributes': variable_record['attributes'],
        'new_edits': result_edits,
    }
    yield result_patch
    count_entries_stk = len([ chunk for chunk in previously_added if chunk['action']=='variable-new' and sanitize_item_name(chunk['variable'])==sanitize_item_name(field_name_stk) and sanitize_item_name(chunk['position'])==sanitize_item_name(path_stk) ])
    exist_stk = count_entries_stk>0
    duplicate_stk = count_entries_stk>1
    exist_unstk = sanitize_item_name(trim_dots(path_unstk+'.'+field_name_unstk)) in variable_records
    assert exist_stk
    assert not duplicate_stk
    assert exist_unstk

def process_every_parent(path_stk,variable_records,mdmdoc,previously_added):
    full_path_stk = ''
    full_path_unstk = ''
    parent, rest = extract_parent_name(path_stk)
    current_item_stk_name = parent
    current_item_stk_path = full_path_stk
    full_path_stk = trim_dots('{prev}.{added}'.format(prev=full_path_stk,added=parent))
    # full_path_unstk = ... (skip)
    # parent is probably an outer loop, it exists, we should skip it
    # ok, we'll check that it exists
    exist_parent = len([ chunk for chunk in previously_added if chunk['action']=='variable-new' and sanitize_item_name(chunk['variable'])==sanitize_item_name(current_item_stk_name) and sanitize_item_name(chunk['position'])==sanitize_item_name(current_item_stk_path) ])>0
    assert exist_parent
    parent, rest = extract_parent_name(rest)
    while not (parent==''):
        current_item_stk_name = parent
        current_item_stk_path = full_path_stk
        full_path_stk = trim_dots('{prev}.{added}'.format(prev=full_path_stk,added=parent))
        full_path_unstk = trim_dots('{prev}.{added}'.format(prev=full_path_unstk,added=parent))
        exist_parent = len([ chunk for chunk in previously_added if chunk['action']=='variable-new' and sanitize_item_name(chunk['variable'])==sanitize_item_name(current_item_stk_name) and sanitize_item_name(chunk['position'])==sanitize_item_name(current_item_stk_path) ])>0
        if not exist_parent:
            # create it
            variable_record_unstk = variable_records[sanitize_item_name(full_path_unstk)]
            mdmitem = metadata_functions.generate_updated_metadata_clone_excluding_subfields(current_item_stk_name,variable_record_unstk['scripting'],variable_record_unstk['attributes'],mdmdoc)
            mdmitem = metadata_functions.sync_labels_from_mddreport(mdmitem,variable_record_unstk)
            result_metadata = mdmitem.Script
            result_edits = edits_functions.generate_code_loop_walkthrough( mdmitem, None, stk_variable_name=current_item_stk_name, unstk_variable_name=current_item_stk_name, unstk_variable_fieldname='', categories_iterating_over=None )
            result_patch = {
                'action': 'variable-new',
                'variable': current_item_stk_name,
                'position': current_item_stk_path,
                'debug_data': { 'source_from': full_path_unstk },
                'new_metadata': result_metadata,
                'attributes': variable_record_unstk['attributes'],
                'new_edits': result_edits,
            }
            yield result_patch
            parent, rest = extract_parent_name(rest)

def print_log_processing(item):
    print('processing {item}...'.format(item=item))



def generate_patch_stk(variable_specs,mdd_data_records,config):


    # here we have a list of items in the output patch file
    result = []

    # # ops that was already done
    # try:
    #     mdd_data_records = ([sect for sect in mdd_data_records['sections'] if sect['name']=='fields'])[0]['content']
    # except:
    #     pass
    mdd_data_root = [ field for field in mdd_data_records if field['name']=='' ][0]
    mdd_data_questions = [ field for field in mdd_data_records if detect_item_type_from_mdddata_fields_report(field['name'])=='variable' ]
    mdd_data_categories = [ cat for cat in mdd_data_records if detect_item_type_from_mdddata_fields_report(cat['name'])=='category' ]

    # helper variable
    # prep dict with variable data stored in variable_specs
    variable_records = prepare_variable_records(mdd_data_questions,mdd_data_categories)

    # here we go, first, we should create the loop
    stk_loopname = choose_loop_name(variable_records,CONFIG_LOOP_NAME_SUGGESTED)

    # prepare mdm item that is used for interaction with all mdm interfaces
    mdmdoc = metadata_functions.init_mdd_doc_from_item_script('')
    if CONFIG_BRING_SHAREDLISTS_TO_NEW_MDMDOC_TO_ADDRESS_CAT_UNRESOLVEDREFERENCES:
        mdmdoc = metadata_functions.mdmdoc_sync_types_definitions(mdmdoc,metadata_functions.init_mdd_doc_from_script(mdd_data_root['scripting']))

    # go!

    # 1. add that global loop
    for result_patch in process_outerloop(name=stk_loopname,key_categories=variable_specs['categories'],mdd_data_categories=mdd_data_categories,mdmdoc=mdmdoc,previously_added=result):
        result.append(result_patch)

    # now process every variable
    performance_counter = iter(utility_performance_monitor.PerformanceMonitor(config={
        'total_records': len(variable_specs['variables']),
        'report_frequency_records_count': 1,
        'report_frequency_timeinterval': 6, # provide update on progress every 6 seconds (print to console)
        'report_text_pipein': 'progress processing variables',
    }))
    for variable_id in variable_specs['variables']:
        try:
            
            print_log_processing(variable_id)
            next(performance_counter)
            # read variable data from variable_specs
            variable_record = variable_records[sanitize_item_name(variable_id)]
            variable_record_name = variable_record['name']
            field_path, field_name = extract_field_name(variable_record_name)
            variable_type = detect_var_type_by_record(variable_record)

            # detect if we should skip
            if should_skip(variable_record,variable_records):
                continue
            
            # grab scripts
            if not 'scripting' in variable_record:
                raise ValueError('Input data does not include "scripting" data, please adjust settings that you use to run mdd_read')
            variable_scripts = variable_record['scripting']

            # processed variable is not always a top level variable
            # maybe we need to process every parent and add metadata for them
            # see process_every_parent within process_stack_a_loop and process_stack_a_categorical
            
            # and now manipulations with MDD
            mdmdoc = metadata_functions.init_mdd_doc_from_item_script(variable_scripts)
            if CONFIG_BRING_SHAREDLISTS_TO_NEW_MDMDOC_TO_ADDRESS_CAT_UNRESOLVEDREFERENCES:
                mdmdoc = metadata_functions.mdmdoc_sync_types_definitions(mdmdoc,metadata_functions.init_mdd_doc_from_script(mdd_data_root['scripting']))
            mdmitem_unstk = mdmdoc.Fields[field_name] # that's top-level!
            
            if variable_type=='loop':
                
                mdmitem_outer_unstk = mdmitem_unstk
                is_a_single_item_within_loop = False
                fields_include = [ mdmfield.Name for mdmfield in mdmitem_outer_unstk.Fields if not should_exclude_field(mdmfield) ]
                is_a_single_item_within_loop = not ( len(fields_include)>1 )
                can_field_name_be_used_as_final_name = check_if_field_name_can_be_used_as_final_name(mdmitem_outer_unstk,variable_record,variable_records,result)
                for index,mdmitem_loop_field in enumerate(mdmitem_outer_unstk.Fields):
                    if mdmitem_loop_field.Name in fields_include:

                        full_name_unstk = '{path}.{field}'.format(path=variable_record_name,field=mdmitem_loop_field.Name)
                        path_unstk, field_name_unstk = extract_field_name(full_name_unstk)
                        variable_record_unstk = variable_records[sanitize_item_name(full_name_unstk)]
                        if should_skip(variable_record_unstk,variable_records):
                            continue
                        mdmitem_unstk = metadata_functions.generate_metadata_from_scripts(field_name_unstk,variable_record_unstk['scripting'],variable_record_unstk['attributes'],mdmdoc)
                        
                        outer_path, _ = extract_field_name(variable_record['name'])
                        full_name_stk = '{loopname}{path}.{field_name}'.format(loopname=stk_loopname,path='.{path}'.format(path=outer_path) if outer_path else '',field_name=mdmitem_loop_field.Name)
                        path_stk, _ = extract_field_name(full_name_stk)
                        
                        mdmitem_stk = metadata_functions.generate_metadata_from_scripts(mdmitem_loop_field.Name,mdmitem_loop_field.Script,variable_record_unstk['attributes'],mdmdoc)
                        is_improper_name = check_if_improper_name(mdmitem_loop_field.Name)
                        field_name_stk = mdmitem_loop_field.Name
                        if is_a_single_item_within_loop:
                            field_name_stk = mdmitem_outer_unstk.Name
                        elif can_field_name_be_used_as_final_name:
                            if is_improper_name and index==0:
                                field_name_stk = mdmitem_outer_unstk.Name
                            elif not is_improper_name:
                                field_name_stk = mdmitem_stk.Name
                            else:
                                field_name_stk = '{part_parent}_{part_field}'.format(part_parent=mdmitem_outer_unstk.Name,part_field=mdmitem_stk.Name)
                        else:
                            field_name_stk = '{part_parent}_{part_field}'.format(part_parent=mdmitem_outer_unstk.Name,part_field=mdmitem_stk.Name)
                        if not (field_name_stk == mdmitem_stk.Name):
                            mdmitem_stk = metadata_functions.generate_updated_metadata_rename(mdmitem_stk,field_name_stk,mdmdoc)
                        
                        # combine from variable_record_unstk and variable_record
                        # somehow labels disappear when switching from Question context to Analysis context
                        # so I'll reset it back to original value captured by mdd_read
                        # and same with properties
                        # I will also adjust attributes ensuring that object_type_value holds the right type
                        variable_record_unstk_final = {**variable_record_unstk}
                        variable_record_unstk_final['label'] = variable_record_unstk['label'] # read from field
                        if not variable_record_unstk_final['label']:
                            variable_record_unstk_final['label'] = variable_record['label'] # fallback, read from parent loop
                        if not variable_record_unstk_final['label']:
                            variable_record_unstk_final['label'] = mdmitem_stk.Label # fallback, read label from actual item created through scripts
                        variable_record_unstk_final['properties'] = {**variable_record_unstk['properties']}
                        for prop_name, prop_value in variable_record['properties'].items():
                            if not sanitize_item_name(prop_name) in [ sanitize_item_name(m) for m in variable_record_unstk_final['properties'] ]:
                                variable_record_unstk_final['properties'][prop_name] = prop_value
                        variable_record_unstk_final['attributes'] = {**variable_record_unstk['attributes']}
                        variable_record_unstk_final['attributes']['label'] = variable_record_unstk_final['label']
                        variable_record_unstk_final['attributes']['object_type_value'] = mdmitem_unstk.ObjectTypeValue
                        if variable_record_unstk_final['attributes']['object_type_value']==0:
                            variable_record_unstk_final['attributes']['data_type'] = mdmitem_stk.DataType
                        if 'is_grid' in variable_record_unstk_final['attributes']:
                            if variable_record_unstk_final['attributes']['object_type_value']==1 or variable_record_unstk_final['attributes']['object_type_value']==2 or variable_record_unstk_final['attributes']['object_type_value']==3:
                                if mdmitem_stk.Fields.Count>1:
                                    variable_record_unstk_final['attributes']['is_grid'] = 'false'

                        for result_patch in process_stack_a_loop(mdmitem_stk,mdmitem_stk.Name,path_stk,mdmitem_unstk,field_name_unstk,path_unstk,variable_record_unstk_final,variable_records,mdmdoc,result):
                            result.append(result_patch)

            elif variable_type=='categorical':
                
                full_name_unstk = variable_record['name']
                path_unstk, field_name_unstk = extract_field_name(full_name_unstk)
                full_name_stk = trim_dots('{stk_loopname}.{path_nested}'.format(stk_loopname=stk_loopname,path_nested=trim_dots('{path}.{field_name}'.format(path=path_unstk,field_name=field_name_unstk))))
                path_stk, field_name_stk = extract_field_name(full_name_stk)

                mdmitem_stk = metadata_functions.generate_metadata_from_scripts(field_name_unstk,variable_record['scripting'],variable_record['attributes'],mdmdoc)
                mdmitem_stk = metadata_functions.generate_updated_metadata_stk_categorical(mdmitem_stk,mdmdoc)
                mdmitem_stk = metadata_functions.generate_updated_metadata_rename(mdmitem_stk,'{part_old}{part_added}'.format(part_old=mdmitem_unstk.Name,part_added='_YN'),mdmdoc)

                # combine labels, properties, attributes
                # somehow labels disappear when switching from Question context to Analysis context
                # so I'll reset it back to original value captured by mdd_read
                # and same with properties
                # I will also adjust attributes ensuring that object_type_value holds the right type
                variable_record_final = {**variable_record}
                variable_record_final['label'] = variable_record['label'] # read from field
                if not variable_record_final['label']:
                    variable_record_final['label'] = mdmitem_stk.Label # fallback, read label from actual item created through scripts
                variable_record_final['properties'] = {**variable_record['properties']}
                variable_record_final['attributes'] = {**variable_record['attributes']}
                variable_record_final['attributes']['label'] = variable_record_final['label']
                variable_record_final['attributes']['object_type_value'] = mdmitem_unstk.ObjectTypeValue
                if variable_record_final['attributes']['object_type_value']==0:
                    variable_record_final['attributes']['data_type'] = mdmitem_stk.DataType

                for result_patch in process_stack_a_categorical(mdmitem_stk,mdmitem_stk.Name,path_stk,mdmitem_unstk,field_name_unstk,path_unstk,variable_record_final,variable_records,mdmdoc,result):
                    result.append(result_patch)

            else:
                raise ValueError('Generating updated item metadata: can\'t handle this type, not implemented: {s}'.format(s=variable_type))

        except Exception as e:
            print('Failed when processing variable: {s}'.format(s=variable_id))
            raise e
    return result



def entry_point(runscript_config={}):

    time_start = datetime.now()
    script_name = 'mdmautostktoolsap mdd stk generate patch script'

    parser = argparse.ArgumentParser(
        description="MDD: produce patches for stk",
        prog='mdd-autostacking-prepare-patch'
    )
    parser.add_argument(
        '-1',
        '--inp-mdd-scheme',
        type=str,
        help='JSON with fields data from MDD Input File',
        required=True
    )
    parser.add_argument(
        '--var-list',
        help='Provide specs with variables to process',
        type=str,
        required=True
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

    variable_specs = None
    variable_specs_file_name = None
    if args.var_list:
        variable_specs_file_name = Path(args.var_list)
        variable_specs_file_name = '{f}'.format(f=variable_specs_file_name.resolve())
        if not(Path(variable_specs_file_name).is_file()):
            raise FileNotFoundError('file not found: {fname}'.format(fname=variable_specs_file_name))
        with open(variable_specs_file_name) as f_l:
                try:
                    variable_specs = json.load(f_l)
                except json.JSONDecodeError as e:
                    # just a more descriptive message to the end user
                    # can happen if the tool is started two times in parallel and it is writing to the same json simultaneously
                    raise TypeError('MDD Patch: Can\'t read file with variable specs as JSON: {msg}'.format(msg=e))

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
            raise TypeError('Patch: Can\'t read left file as JSON: {msg}'.format(msg=e))
    
    print('{script_name}: script started at {dt}'.format(dt=time_start,script_name=script_name))

    # mdd_data_records = get_mdd_data_records_from_input_data(inp_mdd_scheme,variable_specs)
    mdd_data_records = get_mdd_data_records_from_input_data(inp_mdd_scheme)

    result = generate_patch_stk(variable_specs,mdd_data_records,config)
    
    result_json = json.dumps(result, indent=4)

    print('{script_name}: saving as "{fname}"'.format(fname=result_final_fname,script_name=script_name))
    with open(result_final_fname, "w") as outfile:
        outfile.write(result_json)

    time_finish = datetime.now()
    print('{script_name}: finished at {dt} (elapsed {duration})'.format(dt=time_finish,duration=time_finish-time_start,script_name=script_name))



if __name__ == '__main__':
    entry_point({'arglist_strict':True})
