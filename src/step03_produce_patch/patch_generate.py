import re





if __name__ == '__main__':
    # run as a program
    import patch_classes
    import util_vars
    import utility_performance_monitor
    import util_produce_code_mdata as mdata_functions
    import util_produce_code_edits as onc_functions # "onc" stands for "OnNextCase" event
elif '.' in __name__:
    # package
    from . import patch_classes
    from . import util_vars
    from . import utility_performance_monitor
    from . import util_produce_code_mdata as mdata_functions
    from . import util_produce_code_edits as onc_functions # "onc" stands for "OnNextCase" event
else:
    # included with no parent package
    import patch_classes
    import util_vars
    import utility_performance_monitor
    import util_produce_code_mdata as mdata_functions
    import util_produce_code_edits as onc_functions # "onc" stands for "OnNextCase" event






# TODO: (done) pass config to every funtion
# TODO: review "not aaa in bbb" vs "aaa not in bbb"
# TODO: (done) check that "get_list_existing_items" is passed to every function when necessary
# TODO: check that every assert statement has a message
# TODO: print errors to stderr
# TODO: review that file open() is always used with "with"




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
CONFIG_BRING_SHAREDLISTS_TO_NEW_MDMDOC_TO_ADDRESS_CAT_UNRESOLVEDREFERENCES = True



# the name of the loop, will be "STKLoop"
# we don't guarantee that the loop created will have exactly this name,
# if this is name is already used,
# we'll add "_2",, "_3", and so on
# basically, this name is not super important, it can be whatever not already used, because we'll move from this level in STKCreate and we'll not have this loop in final data
CONFIG_LOOP_NAME_SUGGESTED = 'STKLoop'






def print_log_processing(item):
    print('processing {item}...'.format(item=item))


# def filter_metadata_chunk_old_s(variable,position,chunks):
#     return [ chunk for chunk in chunks if chunk['action']=='section/metadata/insert' and ( ( variable is None ) or util_vars.sanitize_item_name(chunk['payload']['variable'])==util_vars.sanitize_item_name(variable) ) and ( ( position is None ) or util_vars.sanitize_item_name(chunk['position'])==util_vars.sanitize_item_name(position) ) ]





def should_exclude_field(mdmfield,mdmsiblings):

    def check_is_info_item(mdmitem):
        data_type = (mdmitem.DataType if mdmitem.ObjectTypeValue==0 else 4) # 0=="info", 4 = "object"
        return data_type==0
    def check_is_assigner_qta(mdmfield,mdmsiblings):
        def get_properties(mdmitem):
            # TODO: should we care about context?
            # I think the default context here is Analysis, that's what we set globally when we create mdmdoc instance
            # "assginertext" (our prop of interest) is probably added in "Question" context
            # but I think (I hope) it will be listed anyway
            # anyway, we probably don't need it at all
            # checlking a loop field if it's an assigner - am I mad?
            result = {}
            for index_prop in range(0,mdmitem.Properties.Count):
               prop_name = mdmitem.Properties.Name(index_prop)
               prop_value = mdmitem.Properties[prop_name]
               result[prop_name] = prop_value
            return result
        assigner_found = False
        fieldname = mdmfield.Name
        if re.match(r'^\s*?(qta_)(\w+)\s*?$',fieldname,flags=re.I|re.DOTALL):
            field_name_assigner = re.sub(r'^\s*?(qta_)(\w+)\s*?$',lambda m: '{prefix}{mainpart}'.format(prefix='DV_',mainpart=m[2]),fieldname,flags=re.I|re.DOTALL)
            variable_name_assigner = field_name_assigner
            if util_vars.sanitize_item_name(variable_name_assigner) in [util_vars.sanitize_item_name(mdmitem.Name) for mdmitem in mdmsiblings if not(mdmitem.Name==mdmfield.Name)]:
                mdmassigner = [mdmitem.Name for mdmitem in mdmsiblings if (util_vars.sanitize_item_name(mdmitem.Name)==util_vars.sanitize_item_name(variable_name_assigner))][0]
                properties = [ p.lower() for p in get_properties(mdmfield).keys() ] + [ p.lower() for p in get_properties(mdmassigner).keys() ]
                if 'assignertext' in properties:
                    assigner_found = True
        return assigner_found
    def check_no_case_data(mdmfield):
        def has_attribute(item,attr):
            return attr.lower() in ['{m}'.format(m=m).lower() for m in dir(item)]
        try:
            if has_attribute(mdmfield,'HasCaseData'):
                if mdmfield.HasCaseData==False:
                    return True
            return False
        except AttributeError:
            return False
    def has_subfields(mdmitem):
        object_type_value = mdmitem.ObjectTypeValue
        # 1 is loop, 2 is grid, 3 is class (block)
        return (object_type_value==1) or (object_type_value==2) or (object_type_value==3)
    
    std_fields_skip = [
        'NavButtonSelect'
    ]

    field_exclude = False
    # 1. skip info items
    field_exclude = field_exclude or check_is_info_item(mdmfield)
    # 2. skip known trash items
    field_exclude = field_exclude or util_vars.sanitize_item_name(mdmfield.Name) in [util_vars.sanitize_item_name(n) for n in std_fields_skip]
    # 3. ??? skip Assigner QTA variables - any chance this is within some loop? I don't think so. That's probably pointless. Assigners are alwasys top level
    field_exclude =  field_exclude or check_is_assigner_qta(mdmfield,mdmsiblings)
    # 4. exclude nocasedata fields
    field_exclude =  field_exclude or check_no_case_data(mdmfield)
    # 5. check recursively
    field_exclude =  field_exclude or ( has_subfields(mdmfield) and len( [ mdmchild for mdmchild in mdmfield.Fields if not should_exclude_field(mdmchild,mdmfield.Fields) ] )==0 )
    return field_exclude

# we detect names that can't be used as final variable name
# i.e. it does not make sense to name a variable "GV" or "TopBox"
def check_if_improper_name(name):
    is_improper_name = False
    # and there are less common cases but still happening in disney bes
    is_improper_name = is_improper_name or not not re.match(r'^\s*?((?:Top|T|Bottom|B))(\d*)((?:B|Box))\s*?$',name,flags=re.I)
    is_improper_name = is_improper_name or not not re.match(r'^\s*?(?:GV|Rank|Num)\s*?$',name,flags=re.I)
    return is_improper_name

def check_if_field_name_can_be_used_as_final_name(mdmparent,variable_record,variable_records,get_list_existing_items,config):
    result = True
    flag_iim = False
    flag_rpc = False
    potential_item_path, _ = util_vars.extract_field_name(variable_record['name'])
    loopname = None
    try:
        loopname = config['loopname'] # the first item added was the loop
    except Exception as e:
        raise Exception('trying to find STKLoop name within added patch chunks and failed to find one: {e}'.format(e=e))
    potential_item_path_stk = util_vars.trim_dots('{stk_loop}.{path}'.format(stk_loop=loopname,path=potential_item_path))
    for mdmfield in mdmparent.Fields:
        # if that's not field we care about, just skip
        if should_exclude_field(mdmfield,mdmparent.Fields):
            continue
        # first I do straightforward check - check if this item exists at parent level
        potential_full_name = util_vars.sanitize_item_name( util_vars.trim_dots('{parent_path}.{item}'.format(parent_path=potential_item_path,item=mdmfield.Name)) )
        already_existing = util_vars.sanitize_item_name(util_vars.trim_dots('{path}.{fieldname}'.format(path=potential_item_path_stk,fieldname=mdmfield.Name))) in get_list_existing_items()
        result = result and not already_existing
        # and we'll also check unstk
        already_existing_in_unstk = potential_full_name in variable_records
        result = result and not already_existing_in_unstk
        # also we should not create items named just "GV" so I'll check against some popular field names
        is_improper_name = re.match(r'^\s*?(?:GV|Num|Rank)\s*?$',mdmfield.Name,flags=re.I|re.DOTALL)
        result = result and not is_improper_name
        iim_flags_count = 0
        rpc_flags_count = 0
        if 'overlap' in util_vars.sanitize_item_name(mdmfield.Name):
            iim_flags_count = iim_flags_count + 1
        if ('iim' in util_vars.sanitize_item_name(mdmparent.Name) or 'qim' in util_vars.sanitize_item_name(mdmparent.Name)):
            iim_flags_count = iim_flags_count + 1
        if re.match(r'^\s*?(?:Which)\s*?$',mdmfield.Name,flags=re.I):
            if ('rpc' in util_vars.sanitize_item_name(mdmparent.Name)):
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
    while util_vars.sanitize_item_name(stk_loopname) in variable_records:
        stk_loopname = '{base_part}_{knt}'.format(base_part=CONFIG_LOOP_NAME_SUGGESTED,knt=counter)
        counter = counter + 1
    return stk_loopname









def generate_stkcategories_metadata(key_categories,category_records,mdmdoc_stk):
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
    for _, cat_mdd in category_records.items():
        category_properties_dict = cat_mdd['properties']
        assert not isinstance(category_properties_dict,list)
        category_analysisvalue = None
        for prop_name, prop_value in category_properties_dict.items(): # we need to iterate cause property names are case insensitive; it can be "value" or "Value", or (I've never seen, but it can be) "VaLuE"
            if util_vars.sanitize_item_name(prop_name)==util_vars.sanitize_item_name('value'):
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
    for cat_stk_name in [ util_vars.sanitize_item_name(c) for c in key_categories ]:
        next(performance_counter)
        cat_label_frequency_data = {}
        cat_analysisvalue_frequency_data = {}
        for _, cat_mdd in category_records.items():
            question_name, category_name = util_vars.extract_category_name(cat_mdd['name'])
            question_name_clean, category_name_clean = util_vars.sanitize_item_name(question_name), util_vars.sanitize_item_name(category_name)
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
    return [ mdata_functions.create_mdmcategory(cat['name'],cat['label'],cat['properties'],mdmdoc_stk) for cat in cat_stk_data ]


def process_outerloop(name,key_categories,category_records,mdmdoc_stk,get_list_existing_items,config):
    print_log_processing('categories')
    mdmcategories = generate_stkcategories_metadata(key_categories,category_records,mdmdoc_stk)
    print_log_processing('top level stacking loop')
    mdmitem_stk = mdata_functions.create_mdmvariable_outerstkloop( name, mdmcategories, mdmdoc_stk )
    result_metadata = mdmitem_stk.Script
    # add defines
    assert re.match(r'^\w+$',name,flags=re.I), 'adding #define STKLoop: STKLoop name does not pass validation ({s})'.format(s=name)
    yield patch_classes.PatchInsert(
        position = patch_classes.Position(0),
        comment = {
            'description': 'comment for tracking when it was done and why',
            'target': '401_PreStack_script',
        },
        payload = {
            "lines": '\'\n\' ***\n\' generated with mdm-autostk-tools-ap\n\' {d}\n\' ***\n\'\n'.format(d=config['datetime'] if 'datetime' in config else 'Date/Not/Passed (TODO:)'),
        },
    )
    yield patch_classes.PatchInsert(
        position = patch_classes.Position(0),
        comment = {
            'description': 'comment for tracking when it was done and why',
            'target': '402_Stack_script',
        },
        payload = {
            "lines": '\'\n\' ***\n\' generated with mdm-autostk-tools-ap\n\' {d}\n\' ***\n\'\n'.format(d=config['datetime'] if 'datetime' in config else 'Date/Not/Passed (TODO:)'),
        },
    )
    yield patch_classes.PatchInsert(
        position = [
            patch_classes.Position(re.compile(r'((?:^|\n)\s*?\'*?\s*?#include[^\n]*?Globals[^\n]*?\.mrs[^\n]*?\s*?\n(?:\s*?\'*?#(?:include|define)[^\n]*?\s*?\n)*)((?:\s*?\n)*)',flags=re.I|re.DOTALL)),
            patch_classes.Position(0),
        ],
        comment = {
            'description': 'global defines, providing stk loop name',
            'target': '401_PreStack_script',
        },
        payload = {
            "lines": '#define STACKINGLOOP "{n}"\n'.format(n=name),
        },
    )
    yield patch_classes.PatchInsert(
        position = [
            patch_classes.Position(re.compile(r'((?:^|\n)\s*?\'*?\s*?#include[^\n]*?Globals[^\n]*?\.mrs[^\n]*?\s*?\n(?:\s*?\'*?#(?:include|define)[^\n]*?\s*?\n)*)((?:\s*?\n)*)',flags=re.I|re.DOTALL)),
            patch_classes.Position(0),
        ],
        comment = {
            'description': 'global defines, providing stk loop name',
            'target': '402_Stack_script',
        },
        payload = {
            "lines": '#define STACKINGLOOP "{n}"\n'.format(n=name),
        },
    )
    yield patch_classes.PatchSectionMetadataInsert(
        position= patch_classes.Position(''), # root
        comment = {
            'description': 'top level stacking loop',
            'target': '401_PreStack_script',
        },
        payload = {
            'variable': name,
            'metadata': result_metadata,
            'attributes': { 'object_type_value': 1, 'label': None, 'type': 'array' },
        },
    )
    for chunk in onc_functions.generate_patches_outerstkloop_walkthrough( None, None, stk_variable_name=name, stk_variable_path='', unstk_variable_name='', config=config ):
        yield chunk
    

def process_stack_a_loop(mdmitem_stk,field_name_stk,path_stk,mdmitem_unstk,field_name_unstk,path_unstk,variable_record,variable_records,mdmdoc_stk,get_list_existing_items,config):
    mdmitem_stk = mdata_functions.sync_labels_and_key_spss_properties_from_mddreport(mdmitem_stk,variable_record)
    mdmitem_stk = mdata_functions.update_mdmvariable_attributes(mdmitem_stk,variable_record)
    _, loop_name_unstk = util_vars.extract_field_name(path_unstk)
    # loop_variable_unstk = variable_records[util_vars.sanitize_item_name(path_unstk)]

    for result_patch_parent in process_every_parent(path_stk,variable_records,mdmdoc_stk,get_list_existing_items,config):
        yield result_patch_parent

    # done with parent levels, add record for processing the variable that is stacked
    result_metadata = mdmitem_stk.Script
    yield patch_classes.PatchSectionMetadataInsert(
        position = patch_classes.Position(path_stk),
        comment = {
            'source_from': variable_record['name'],
            'target': '401_PreStack_script',
        },
        payload = {
            'variable': mdmitem_stk.Name,
            'metadata': result_metadata,
            'attributes': variable_record['attributes'],
        },
    )
    # if variable_record['attributes']['object_type_value']==0:
    if False:
        # # it means it's a regular plain variable
        # # we can use direct assignment
        # for chunk in onc_functions.generate_patches_loop_unstack_simple( mdmitem_stk, mdmitem_unstk, stk_variable_name=field_name_stk, stk_variable_path=path_stk, unstk_variable_name=loop_name_unstk, unstk_variable_fieldname=field_name_unstk, categories_iterating_over=loop_variable_unstk['categories'], config=config ):
        #     yield chunk
        pass
    else:
        # it's c complex structure
        # unfortunately, direct assignment "A = B" is not working in dms scripts
        # we need to iterate over fields
        # and I can't use a function, i.e. CopyFrom(A,B)
        # because I can't detect var/loop type in CDSC (case data source component)
        # anyway, doing euristic analysis is not 100% right, it is not the most performance efficient
        # and stacking is sometimes slow, it can take 8 hours, or more, in some projects, i.e. Disney+&Hulu tracker
        # So I have to generate proper code here iterating over all loops and fields
        for chunk in onc_functions.generate_patches_loop_unstack_structural( mdmitem_stk, mdmitem_unstk, stk_variable_name=field_name_stk, stk_variable_path=path_stk, unstk_variable_name=loop_name_unstk, config=config ):
            yield chunk
        
    count_entries_stk = len( [ item for item in get_list_existing_items() if util_vars.sanitize_item_name(util_vars.trim_dots('{path}.{field_name}'.format(path=path_stk,field_name=field_name_stk)))==util_vars.sanitize_item_name(item) ] )
    exist_stk = count_entries_stk>0
    duplicate_stk = count_entries_stk>1
    exist_unstk = util_vars.sanitize_item_name(util_vars.trim_dots(path_unstk+'.'+field_name_unstk)) in variable_records
    assert exist_stk
    assert not duplicate_stk
    assert exist_unstk

def process_stack_a_categorical(mdmitem_stk,field_name_stk,path_stk,mdmitem_unstk,field_name_unstk,path_unstk,variable_record,variable_records,mdmdoc_stk,get_list_existing_items,config):
    mdmitem_stk = mdata_functions.update_mdmvariable_attributes(mdmitem_stk,variable_record)

    for result_patch_parent in process_every_parent(path_stk,variable_records,mdmdoc_stk,get_list_existing_items,config):
        yield result_patch_parent

    # done with parent levels, add record for processing the variable that is stacked
    result_metadata = mdmitem_stk.Script
    yield patch_classes.PatchSectionMetadataInsert(
        position = patch_classes.Position(path_stk),
        comment = {
            'source_from': variable_record['name'],
            'target': '401_PreStack_script',
        },
        payload = {
            'variable': mdmitem_stk.Name,
            'metadata': result_metadata,
            'attributes': variable_record['attributes'],
        },
    )
    for chunk in onc_functions.generate_patches_unstack_categorical_yn( mdmitem_stk, mdmitem_unstk, stk_variable_name=field_name_stk, stk_variable_path=path_stk, unstk_variable_name=field_name_unstk, config=config ):
        yield chunk
    
    count_entries_stk = len( [ item for item in get_list_existing_items() if util_vars.sanitize_item_name(util_vars.trim_dots('{path}.{field_name}'.format(path=path_stk,field_name=field_name_stk)))==util_vars.sanitize_item_name(item) ] )
    exist_stk = count_entries_stk>0
    duplicate_stk = count_entries_stk>1
    exist_unstk = util_vars.sanitize_item_name(util_vars.trim_dots(path_unstk+'.'+field_name_unstk)) in variable_records
    assert exist_stk
    assert not duplicate_stk
    assert exist_unstk

def process_every_parent(path_stk,variable_records,mdmdoc_stk,get_list_existing_items,config):
    full_path_stk = ''
    full_path_unstk = ''
    parent, rest = util_vars.extract_parent_name(path_stk)
    current_item_stk_name = parent
    current_item_stk_path = full_path_stk
    full_path_stk = util_vars.trim_dots('{prev}.{added}'.format(prev=full_path_stk,added=parent))
    # full_path_unstk = ... (skip)
    # parent is probably an outer loop, it exists, we should skip it
    # ok, we'll check that it exists
    exist_parent = len( [ item for item in get_list_existing_items() if util_vars.sanitize_item_name(util_vars.trim_dots('{path}.{field_name}'.format(path=current_item_stk_path,field_name=current_item_stk_name)))==util_vars.sanitize_item_name(item) ] ) > 0
    assert exist_parent
    parent, rest = util_vars.extract_parent_name(rest)
    while not (parent==''):
        current_item_stk_name = parent
        current_item_stk_path = full_path_stk
        full_path_stk = util_vars.trim_dots('{prev}.{added}'.format(prev=full_path_stk,added=parent))
        full_path_unstk = util_vars.trim_dots('{prev}.{added}'.format(prev=full_path_unstk,added=parent))
        exist_parent = len( [ item for item in get_list_existing_items() if util_vars.sanitize_item_name(util_vars.trim_dots('{path}.{field_name}'.format(path=current_item_stk_path,field_name=current_item_stk_name)))==util_vars.sanitize_item_name(item) ] ) > 0
        if not exist_parent:
            # create it
            variable_record_unstk = variable_records[util_vars.sanitize_item_name(full_path_unstk)]
            mdmitem = mdata_functions.create_mdmvariable_clone_excluding_subfields(current_item_stk_name,variable_record_unstk['scripting'],variable_record_unstk['attributes'],mdmdoc_stk)
            mdmitem = mdata_functions.sync_labels_and_key_spss_properties_from_mddreport(mdmitem,variable_record_unstk)
            result_metadata = mdmitem.Script
            yield patch_classes.PatchSectionMetadataInsert(
                position = patch_classes.Position(current_item_stk_path),
                comment = {
                    'source_from': full_path_unstk,
                    'target': '401_PreStack_script',
                },
                payload = {
                    'variable': current_item_stk_name,
                    'metadata': result_metadata,
                    'attributes': variable_record_unstk['attributes'],
                },
            )
            for chunk in onc_functions.generate_patches_loop_walkthrough( mdmitem, None, stk_variable_name=current_item_stk_name, stk_variable_path=current_item_stk_path, unstk_variable_name=current_item_stk_name, config=config ):
                yield chunk
            parent, rest = util_vars.extract_parent_name(rest)




def generate_patches_stk(variable_specs,variable_records,category_records,config):


    # here we have a list of items in the output patch file
    result_401_402_combined = []

    def get_list_existing_items():
        result = []
        for chunk in result_401_402_combined:
            if chunk['comment']['target']=='401_PreStack_script':
                if chunk['action']==patch_classes.PatchSectionMetadataInsert.action:
                    try:
                        field_name = chunk['payload']['variable']
                        path = None
                        if isinstance(chunk['position'],str):
                            path = chunk['position']
                        elif isinstance(chunk['position'],dict) and ('type' in chunk['position'] and chunk['position']['type']=='address' and 'position' in chunk['position']):
                            path = chunk['position']['position']
                        else:
                            raise Exception('can\'t extract position, patch chunk position format does not follow the pattern')
                        potential_name = util_vars.sanitize_item_name(util_vars.trim_dots('{path}.{field_name}'.format(path=path,field_name=field_name)))
                        result.append(potential_name)
                    except Exception as e:
                        raise Exception('failed when trying to check existing chunks and failed when trying to filter: {e}'.format(e=e)) from e

        return result

    # here we go, first, we should create the loop
    stk_loopname = choose_loop_name(variable_records,CONFIG_LOOP_NAME_SUGGESTED)
    config['loopname'] = stk_loopname

    # prepare mdm item that is used for interaction with all mdm interfaces
    mdmdoc_stk = mdata_functions.create_mdmdoc()
    mdmdoc_unstk = mdata_functions.create_mdmdoc(variable_records['']['scripting'])
    if CONFIG_BRING_SHAREDLISTS_TO_NEW_MDMDOC_TO_ADDRESS_CAT_UNRESOLVEDREFERENCES:
        mdmdoc_stk = mdata_functions.mdmdoc_sync_types_definitions(mdmdoc_stk,mdmdoc_unstk)

    # go!

    # 1. add that global loop
    for result_patch in process_outerloop(name=stk_loopname,key_categories=variable_specs['categories'],category_records=category_records,mdmdoc_stk=mdmdoc_stk,get_list_existing_items=get_list_existing_items,config=config):
        result_401_402_combined.append(result_patch)

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
            variable_record = variable_records[util_vars.sanitize_item_name(variable_id)]
            variable_record_name = variable_record['name']
            variable_type = util_vars.detect_var_type_by_record(variable_record)

            # detect if we should skip
            # if should_skip(variable_record,variable_records):
            #     continue
            # not doing it here anymore - we suppose all fitlering is done in step02_guess_vars
            # if a variable is specced for stacking here - our job is to stack it, not to decide that this should be skipped
            
            # processed variable is not always a top level variable
            # maybe we need to process every parent and add metadata for them
            # see process_every_parent within process_stack_a_loop and process_stack_a_categorical
            
            # and now manipulations with MDD
            mdmitem_unstk = mdmdoc_unstk
            item_name, path_rest = util_vars.extract_parent_name(variable_record['name'])
            path = item_name
            mdmitem_unstk = mdmitem_unstk.Fields[item_name]
            while path_rest:
                item_name, path_rest = util_vars.extract_parent_name(path_rest)
                path = path + '.' + item_name
                try:
                    item_attrs = variable_records[util_vars.sanitize_item_name(path)]['attributes']
                except KeyError as e:
                    raise KeyError('Trying to find unstacked variable matching "{name}": not found ({e})'.format(name=path,e=e))
                item_is_helperfield = 'is_helper_field' in item_attrs and re.match(r'^\s*?true\s*?$',item_attrs['is_helper_field'],flags=re.I|re.DOTALL)
                if not item_is_helperfield:
                    mdmitem_unstk = mdmitem_unstk.Fields[item_name]
                else:
                    mdmitem_unstk = mdmitem_unstk.HelperFields[item_name]
            mdmitem_stk = None # none yet, we'll create it depending on its type, if it should be a stacked loop or y/n categorical

            
            
            if variable_type=='loop':
                
                mdmitem_outer_unstk = mdmitem_unstk
                is_a_single_item_within_loop = False
                fields_include = [ mdmfield.Name for mdmfield in mdmitem_outer_unstk.Fields if not should_exclude_field(mdmfield,mdmitem_outer_unstk.Fields) ]
                is_a_single_item_within_loop = not ( len(fields_include)>1 )
                can_field_name_be_used_as_final_name = check_if_field_name_can_be_used_as_final_name(mdmitem_outer_unstk,variable_record,variable_records,get_list_existing_items,config)
                for index,mdmitem_loop_field in enumerate(mdmitem_outer_unstk.Fields):
                    if mdmitem_loop_field.Name in fields_include:

                        full_name_unstk = '{path}.{field}'.format(path=variable_record_name,field=mdmitem_loop_field.Name)
                        path_unstk, field_name_unstk = util_vars.extract_field_name(full_name_unstk)
                        variable_record_unstk = variable_records[util_vars.sanitize_item_name(full_name_unstk)]
                        mdmitem_inner_unstk = mdmitem_outer_unstk.Fields[field_name_unstk]
                        
                        outer_path, _ = util_vars.extract_field_name(variable_record['name'])
                        full_name_stk = '{loopname}{path}.{field_name}'.format(loopname=stk_loopname,path='.{path}'.format(path=outer_path) if outer_path else '',field_name=mdmitem_loop_field.Name)
                        path_stk, _ = util_vars.extract_field_name(full_name_stk)
                        
                        mdmitem_stk = mdata_functions.create_mdmvariable(mdmitem_loop_field.Name,mdmitem_loop_field.Script,variable_record_unstk['attributes'],mdmdoc_stk)
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
                            mdmitem_stk = mdata_functions.rename_mdmvariable(mdmitem_stk,field_name_stk)
                        
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
                            if not util_vars.sanitize_item_name(prop_name) in [ util_vars.sanitize_item_name(m) for m in variable_record_unstk_final['properties'] ]:
                                variable_record_unstk_final['properties'][prop_name] = prop_value
                        variable_record_unstk_final['attributes'] = {**variable_record_unstk['attributes']}
                        variable_record_unstk_final['attributes']['label'] = variable_record_unstk_final['label']
                        variable_record_unstk_final['attributes']['object_type_value'] = mdmitem_inner_unstk.ObjectTypeValue
                        if variable_record_unstk_final['attributes']['object_type_value']==0:
                            variable_record_unstk_final['attributes']['data_type'] = mdmitem_stk.DataType
                        if 'is_grid' in variable_record_unstk_final['attributes']:
                            if variable_record_unstk_final['attributes']['object_type_value']==1 or variable_record_unstk_final['attributes']['object_type_value']==2 or variable_record_unstk_final['attributes']['object_type_value']==3:
                                if mdmitem_stk.Fields.Count>1:
                                    variable_record_unstk_final['attributes']['is_grid'] = 'false'

                        for result_patch in process_stack_a_loop(mdmitem_stk,mdmitem_stk.Name,path_stk,mdmitem_inner_unstk,field_name_unstk,path_unstk,variable_record_unstk_final,variable_records,mdmdoc_stk,get_list_existing_items,config):
                            result_401_402_combined.append(result_patch)

            elif variable_type=='categorical':
                
                full_name_unstk = variable_record['name']
                path_unstk, field_name_unstk = util_vars.extract_field_name(full_name_unstk)
                full_name_stk = util_vars.trim_dots('{stk_loopname}.{path_nested}'.format(stk_loopname=stk_loopname,path_nested=util_vars.trim_dots('{path}.{field_name}'.format(path=path_unstk,field_name=field_name_unstk))))
                path_stk, field_name_stk = util_vars.extract_field_name(full_name_stk)

                mdmitem_stk = mdata_functions.create_mdmvariable(field_name_unstk,variable_record['scripting'],variable_record['attributes'],mdmdoc_stk)
                mdmitem_stk = mdata_functions.create_mdmvariable_categorical_yn(mdmitem_stk,mdmdoc_stk)
                mdmitem_stk = mdata_functions.rename_mdmvariable(mdmitem_stk,'{part_old}{part_added}'.format(part_old=mdmitem_unstk.Name,part_added='_YN'))

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

                for result_patch in process_stack_a_categorical(mdmitem_stk,mdmitem_stk.Name,path_stk,mdmitem_unstk,field_name_unstk,path_unstk,variable_record_final,variable_records,mdmdoc_stk,get_list_existing_items,config):
                    result_401_402_combined.append(result_patch)

            else:
                raise ValueError('Generating updated item metadata: can\'t handle this type, not implemented: {s}'.format(s=variable_type))

        except Exception as e:
            print('Failed when processing variable: {s}'.format(s=variable_id))
            raise e
    result_401 = []
    result_402 = []
    for chunk in result_401_402_combined:
        assert 'comment' in chunk, 'every chunk in a patch must have target specified, if it\'s "401_PreStack_script" or "402_Stack_script"'
        if chunk['comment']['target']=='401_PreStack_script':
            result_401.append(chunk)
        elif chunk['comment']['target']=='402_Stack_script':
            result_402.append(chunk)
        else:
            raise Exception('every chunk in a patch must have target specified, if it\'s "401_PreStack_script" or "402_Stack_script"')
    return result_401, result_402
