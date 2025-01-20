# import os, time, re, sys
from ast import excepthandler
from concurrent.futures import process
import os
from datetime import datetime, timezone
# from dateutil import tz
import argparse
from pathlib import Path
import re
import json



# import pythoncom
import win32com.client



if __name__ == '__main__':
    # run as a program
    import utility_performance_monitor
elif '.' in __name__:
    # package
    from . import utility_performance_monitor
else:
    # included with no parent package
    import utility_performance_monitor



# we'll add "_2",, "_3", and so on, if this name is used
CONFIG_LOOP_NAME_SUGGESTED = 'STKLoop'

CONFIG_ANALYSIS_VALUE_YES = 1
CONFIG_ANALYSIS_VALUE_NO = 0

# code templates
# metadata code templates
CONFIG_METADATA_PAGE_TEMPLATE = 'Metadata(en-US, Question, label)\n{@}\nEnd Metadata'

CONFIG_METADATA_LOOP_OUTERSTKLOOP = """
<<stk_loopname>> -
Loop
{
    <<CATEGORIES>>
}
fields
(
	STK_ID -
	text[..255];
    STK_Iteration -
    categorical [1..1]
    {
        <<CATEGORIES>>
    };
)expand;
"""

# edits code templates

# what code are we generating here
# is something like `.BrandFamiliarity_YN = BrandFamiliarity[cbrand].GV`
# the pattern is `stk_var = original_var`
# sometimes it is not just a top-level variable, we need to iterate over something
# so `iter.GV = unstk_iter.GV`, or something like this
# and "variable_stk_path" and "variable_unstacked_path" are holding the name "iter" and "unstk_iter" here
CONFIG_CODE_LOOP_OUTERSTKLOOP = {
    'variable_stk_path': 'iter_stk.',
    'variable_unstacked_path': '',
    'code': """
dim brand, cbrand, iter_stk

' <<STK_VARIABLE_NAME>>
for each brand in <<STK_VARIABLE_NAME>>.categories
cbrand = ccategorical(brand)
'with <<STK_VARIABLE_NAME>>[cbrand]
set iter_stk = <<STK_VARIABLE_PATH>><<STK_VARIABLE_NAME>>[cbrand]
	
	' STK_ID
	iter_stk.STK_ID = ctext(brand.name)+"_"+ctext(Respondent.ID)
	
	' STK_Iteration
	iter_stk.STK_Iteration = cbrand
	
	' {@}
	
'end with
next
set iter_stk = null
"""
}

CONFIG_CODE_LOOP_UNSTACK_SIMPLE = {
    'variable_stk_path': '<<STK_VARIABLE_PATH>><<STK_VARIABLE_NAME>>.', # not sure we need it, we don't expect that we need to process subfields separately; we need to find some really complicated tests to check it, where we stack at 2 different levels - I can imaging this could happen, let's find some tests and see
    'variable_unstacked_path': '<<UNSTK_VARIABLE_PATH>><<UNSTK_VARIABLE_NAME>>[cbrand].<<UNSTK_VARIABLE_FIELDNAME>>.', # not sure we need it, we don't expect that we need to process subfields separately; we need to find some really complicated tests to check it, where we stack at 2 different levels - I can imaging this could happen, let's find some tests and see
    'code': """
' <<STK_VARIABLE_NAME>>
' from: <<UNSTK_VARIABLE_NAME>>
if containsany( <<UNSTK_VARIABLE_PATH>><<UNSTK_VARIABLE_NAME>>.DefinedCategories(), cbrand ) then
    <<STK_VARIABLE_PATH>><<STK_VARIABLE_NAME>> = <<UNSTK_VARIABLE_PATH>><<UNSTK_VARIABLE_NAME>>[cbrand].<<UNSTK_VARIABLE_FIELDNAME>>
end if
' {@}
"""
}

CONFIG_CODE_LOOP_UNSTACK_OBJECT_LOOP_OR_BLOCK = {
    'variable_stk_path': '<<STK_VARIABLE_PATH>><<STK_VARIABLE_NAME>>.', # we need it
    'variable_unstacked_path': '<<UNSTK_VARIABLE_PATH>><<UNSTK_VARIABLE_NAME>>[cbrand].', # we need it; don't add variable name - it is already generated with recursive code
    'code': """
' <<STK_VARIABLE_NAME>>
' from: <<UNSTK_VARIABLE_NAME>>
' TODO: generate code iterating over all categories and subfields
if containsany( <<UNSTK_VARIABLE_PATH>><<UNSTK_VARIABLE_NAME>>.DefinedCategories(), cbrand ) then
    ' {@}
end if
"""
}

CONFIG_CODE_LOOP = {
    'variable_stk_path': 'iter_stk_<<STK_VARIABLE_NAME>>.', # we certainly need
    'variable_unstacked_path': 'iter_<<UNSTK_VARIABLE_NAME>>.', # we certainly need it
    'code': """
' <<STK_VARIABLE_NAME>>
' from: <<UNSTK_VARIABLE_NAME>>
' process everything within this loop
dim cat_stk_<<STK_VARIABLE_NAME>>, iter_stk_<<STK_VARIABLE_NAME>>, iter_<<UNSTK_VARIABLE_NAME>>
for each cat_stk_<<STK_VARIABLE_NAME>> in <<STK_VARIABLE_PATH>><<STK_VARIABLE_NAME>>.Categories
    set iter_stk_<<STK_VARIABLE_NAME>> = <<STK_VARIABLE_PATH>><<STK_VARIABLE_NAME>>[cat_stk_<<STK_VARIABLE_NAME>>.name]
    set iter_<<UNSTK_VARIABLE_NAME>> = <<UNSTK_VARIABLE_PATH>><<UNSTK_VARIABLE_NAME>>[cat_stk_<<STK_VARIABLE_NAME>>.name]

    ' {@}

next
"""
}

CONFIG_CODE_CATEGORICALYN = {
    'variable_stk_path': '<<STK_VARIABLE_PATH>><<STK_VARIABLE_NAME>>', # we definitely not need it and it will not work, it will break, and that's some good news, we'll see that something is off
    'variable_unstacked_path': '<<UNSTK_VARIABLE_PATH>><<UNSTK_VARIABLE_NAME>>', # we definitely not need it and it will not work, it will break, and that's some good news, we'll see that something is off
    'code': """
' <<STK_VARIABLE_NAME>>
' from: <<UNSTK_VARIABLE_NAME>>
<<STK_VARIABLE_PATH>><<STK_VARIABLE_NAME>> = iif( <<UNSTK_VARIABLE_PATH>><<UNSTK_VARIABLE_NAME>> is null, null, iif( <<UNSTK_VARIABLE_PATH>><<UNSTK_VARIABLE_NAME>>=*cbrand, {Yes}, {No} ) )
' {@}
"""
}




def trim_dots(s):
    return re.sub(r'^\s*?\.','',re.sub(r'\.\s*?$','',s,flags=re.I),flags=re.I)

def linebreaks_remove(s):
    return re.sub(r'(?:\r\n|\r|\n)',' ',s,flags=re.I)

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

def get_mdd_data_questions_from_input_data(inp_mdd_scheme):
    def convert_list_to_dict(data_lst):
        result = {}
        for record in data_lst:
            result[record['name']] = record['value']
        return result
    mdd_data_questions = ([sect for sect in inp_mdd_scheme['sections'] if sect['name']=='fields'])[0]['content']
    mdd_data_questions = [ {**q,'properties':convert_list_to_dict(q['properties'] if 'properties' in q else []),'attributes':convert_list_to_dict(q['attributes'] if 'attributes' in q else [])} for q in mdd_data_questions ]
    return mdd_data_questions

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

# def find_variable_record(fullpathandname,records):
#     def val(s):
#         return not not re.match(r'^(?:\w+\.)*\w+$',s)
#     def norm(name):
#         s = name
#         s = re.sub(r'\[\s*?\{?\s*?(?:\w+|\.\.)?\s*?\}?\s*?\]','',s,flags=re.I)
#         s = re.sub(r'\s','',s,flags=re.I)
#         s = s.lower()
#         if val(s):
#             return s
#         else:
#             raise ValueError('looking for item in records, but name does not follow convention: {s}'.format(s=s))
#     records = [ {**rec,'name_norm': norm(rec['name'])} for rec in records ]
#     name_lookup = norm(fullpathandname)
#     records_matching = [ rec for rec in records if rec['name_norm']==name_lookup ]
#     if len(records_matching)>0:
#         return records_matching[0]
#     else:
#         return None




def generate_updated_metadata_rename(mdmitem_unstk,mdmitem_script,newname,mdmdoc):
    mdmitem_unstk.Name = newname
    return mdmitem_unstk, mdmitem_unstk.Script

def generate_updated_metadata_setlabel(mdmitem_unstk,mdmitem_script,newvalue,mdmdoc):
    newvalue_clean = linebreaks_remove(newvalue) # we don't need multi-line text in stacked variables; it breaks syntax and it is unnecessary
    mdmitem_unstk.Label = newvalue_clean
    return mdmitem_unstk, mdmitem_unstk.Script

def generate_updated_metadata_updateproperties(mdmitem_unstk,mdmitem_script,newvalues_dict,mdmdoc):
    assert not isinstance(newvalues_dict,list)
    for prop_name, prop_value in newvalues_dict.items():
        def sanitize_prop_name(name):
            name = re.sub(r'^\s*(.*?)\s*(?:\(.*?\)\s*?)?\s*?$',lambda m: m[1],name,flags=re.I)
            if re.match(r'^.*?[^\w].*?$',name,flags=re.I):
                # raise ValueError('Invalid Prop Name: {s}'.format(s=name))
                return None
            return name
        propname_clean = sanitize_prop_name(prop_name)
        if propname_clean:
            # if not propname_clean in 
            mdmitem_unstk.Properties[propname_clean] = prop_value
    return mdmitem_unstk, mdmitem_unstk.Script

def generate_updated_metadata_update_all_in_batch(mdmitem_stk,mdmitem_stk_script,updated_metadata_data,mdmdoc):
    if 'label' in updated_metadata_data and updated_metadata_data['label']:
        mdmitem_stk, mdmitem_stk_script = generate_updated_metadata_setlabel(mdmitem_stk,mdmitem_stk_script,updated_metadata_data['label'],mdmdoc)
    if 'properties' in updated_metadata_data and updated_metadata_data['properties']:
        mdmitem_stk, mdmitem_stk_script = generate_updated_metadata_updateproperties(mdmitem_stk,mdmitem_stk_script,updated_metadata_data['properties'],mdmdoc)
    return mdmitem_stk, mdmitem_stk_script

def generate_updated_metadata_stk_categorical(mdmitem_unstk,mdmitem_script,mdmdoc):
    # if mdmitem_unstk.Elements.IsReference:
    #     mdmitem_unstk.Elements.Reference = None
    #     mdmitem_unstk.Elements.ReferenceName = None
    # for mdmelem in mdmitem_unstk.Elements:
    #     mdmitem_unstk.Elements.remove(mdmelem.Name)
    # mdm_elem_new = mdmdoc.CreateElements("","")
    # mdmitem_unstk.Elements = mdm_elem_new
    if mdmitem_unstk.Elements.IsReference:
        # TODO: this is not 100% correct, the regular expression can match the word "categorical" somewhere in label
        # but I cen't find any better solution
        mdmitem_unstk.Script = re.sub(r'^(.*)(\bcategorical\b)(\s*?(?:\{.*?\})?\s*?(?:\w+\s*?(?:\(.*?\))?)?\s*?;?\s*?)$',lambda m: '{a}{b}{c}'.format(a=m[1],b=m[2],c=' { Yes "Yes" };'),mdmitem_unstk.Script,flags=re.I|re.DOTALL)
        # for attempt in range(0,2):
        #     try:
        #         mdm_elem_new = mdmdoc.CreateElements("","")
        #         mdmitem_unstk.Elements = mdm_elem_new
        #     except:
        #         pass
        #     try:
        #         mdmitem_unstk.Elements.ReferenceName = ''
        #     except:
        #         pass
        #     try:
        #         mdmitem_unstk.Elements.IsReference = False
        #     except:
        #         pass
        #     try:
        #         mdmitem_unstk.Elements.Remove(0)
        #     except:
        #         pass
    for mdmelem in mdmitem_unstk.Elements:
        mdmitem_unstk.Elements.remove(mdmelem.Name)
    # clean out responses for "Other" - I think we don't need it in stacked, or should it be configurable?
    for mdmfield in mdmitem_unstk.HelperFields:
        mdmitem_unstk.HelperFields.remove(mdmfield.Name)
    mdmitem_unstk.MinValue = 1
    mdmitem_unstk.MaxValue = 1
    mdmitem_unstk.Elements.Order = 0 # no randomization
    mdmelem = mdmdoc.CreateElement("Yes","Yes")
    mdmelem.Name = "Yes"
    mdmelem.Label = "Yes"
    mdmelem.Type = 0 # mdmlib.ElementTypeConstants.mtCategory
    if CONFIG_ANALYSIS_VALUE_YES is not None:
        # mdmelem.Properties.Item["Value"] = 1 # use this in mrs instead
        mdmelem.Properties['Value'] = CONFIG_ANALYSIS_VALUE_YES
    mdmitem_unstk.Elements.Add(mdmelem)
    mdmelem = mdmdoc.CreateElement("No","No")
    mdmelem.Name = "No"
    mdmelem.Label = "No"
    mdmelem.Type = 0 # mdmlib.ElementTypeConstants.mtCategory
    if CONFIG_ANALYSIS_VALUE_NO is not None:
        mdmelem.Properties['Value'] = CONFIG_ANALYSIS_VALUE_NO
    mdmitem_unstk.Elements.Add(mdmelem)
    return mdmitem_unstk, mdmitem_unstk.Script

def generate_metadata_from_scripts(name,script,attr_dict,mdmroot,isgrid_retry_attempts=None):
    assert not isinstance(attr_dict,list)
    detect_type = None
    variable_is_plain = False
    variable_is_categorical = False
    variable_is_loop = False
    variable_is_grid = False
    variable_is_block = False
    if 'type' in attr_dict:
        variable_is_plain = variable_is_plain or not not re.match(r'^\s*?plain\b',attr_dict['type'],flags=re.I)
        variable_is_categorical = variable_is_categorical or not not re.match(r'^\s*?plain/(?:categorical|multipunch|singlepunch)',attr_dict['type'],flags=re.I)
        variable_is_loop = variable_is_loop or not not re.match(r'^\s*?(?:array|grid|loop)\b',attr_dict['type'],flags=re.I)
        variable_is_block = variable_is_block or not not re.match(r'^\s*?(?:block)\b',attr_dict['type'],flags=re.I)
    if 'is_grid' in attr_dict:
        variable_is_grid = variable_is_grid or not not re.match(r'^\s*?true\b',attr_dict['is_grid'],flags=re.I)
    if variable_is_plain or variable_is_categorical:
        detect_type = 'plain'
    elif variable_is_loop:
        detect_type = 'loop'
    elif variable_is_block:
        detect_type = 'block'
    mdmitem_ref = None
    if detect_type == 'plain':
        mdmitem_ref = mdmroot.CreateVariable(name, name)
    elif detect_type == 'loop':
        if variable_is_grid:
            mdmitem_ref = mdmroot.CreateGrid(name, name)
        else:
            mdmitem_ref = mdmroot.CreateArray(name, name)
    elif detect_type == 'block':
        mdmitem_ref = mdmroot.CreateClass(name, name)
    elif not detect_type:
        raise ValueError('Cat\'t create object: unrecognized type')
    else:
        raise ValueError('Can\'t handle this type of bject: {s}'.format(s=detect_type))
    if not detect_type:
        raise ValueError('Failed to create variable, please check all data in the patch specs')
    # if 'object_type_value' in attr_dict:
    #     mdmitem_ref.ObjectTypeValue = attr_dict['object_type_value']
    if 'data_type' in attr_dict:
        mdmitem_ref.DataType = attr_dict['data_type']
    if 'label' in attr_dict:
        mdmitem_ref.Label = attr_dict['label']
    try:
        mdmitem_ref.Script = script
    except Exception as e:
        if variable_is_grid and ( isgrid_retry_attempts is None or isgrid_retry_attempts<3 ):
            # same manipulations as above
            return generate_metadata_from_scripts(name,script,{**attr_dict,'type':'array','is_grid':'false'},mdmroot,isgrid_retry_attempts=isgrid_retry_attempts+1 if isgrid_retry_attempts is not None else 1)
        else:
            raise e
    return mdmitem_ref

def generate_updated_metadata_clone_excluding_subfields(name,script,attr_dict,mdmroot):
    mdmitem_add = generate_metadata_from_scripts(name,script,attr_dict,mdmroot)
    for f in mdmitem_add.Fields:
        mdmitem_add.Fields.Remove(f.Name)
    return mdmitem_add

def generate_category_metadata(name,label,properties,mdmdoc):
    assert not isinstance(properties,list)
    mdmelem = mdmdoc.CreateElement(name,name)
    mdmelem.Name = name
    mdmelem.Label = label
    mdmelem.Type = 0 # mdmlib.ElementTypeConstants.mtCategory
    for prop_name, prop_value in properties.items():
        # mdmelem.Properties.Item[prop['name']] = prop['value'] # use this in mrs instead
        mdmelem.Properties[prop_name] = prop_value
    return mdmelem.Script

def prepare_syntax_substitutions( d, stk_variable_name='', unstk_variable_name='', unstk_variable_fieldname='' ):
    result = {}
    assert not '.' in stk_variable_name
    assert not '.' in unstk_variable_name
    assert not '.' in unstk_variable_fieldname
    for key in d:
        # first, copy, to ensure we are not modifying the reference, we are moifying the copy
        text = '{s}'.format(s=d[key])
        text = text.replace('<<STK_VARIABLE_NAME>>',stk_variable_name)
        text = text.replace('<<UNSTK_VARIABLE_NAME>>',unstk_variable_name)
        text = text.replace('<<UNSTK_VARIABLE_FIELDNAME>>',unstk_variable_fieldname)
        result[key] = text
    result['stk_variable_name'] = stk_variable_name
    result['unstk_variable_name'] = unstk_variable_name
    result['unstk_variable_fieldname'] = unstk_variable_fieldname
    return result

def generate_recursive_onnextcase_code(mdmitem_stk,mdmitem_ref):
    def recursive(mdmitem_stk,mdmitem_ref,indent,name_part):
        def trim_lines(s):
            if re.match(r'^\s*$',s):
                return ''
            s = re.sub(r'^(?:\s*?\n)*','',s,flags=re.DOTALL)
            s = re.sub(r'(?:\s*?\n)*$','',s,flags=re.DOTALL)
            s = re.sub(r'\n?$','',s,flags=re.DOTALL)
            s = s + '\n'
            return s
        def add_indent(s,indent):
            s = '\n'+re.sub(r'\n?$','',s) # I am adding a line break at the beginning to make wotking with regexs easier
            s = re.sub(r'(\n)',lambda m: '{k}{i}'.format(i=indent,k=m[1]),s)
            s = s[1:] # remove line break at the beginning that we added
            return s
        if mdmitem_stk.ObjectTypeValue==0 or mdmitem_stk.ObjectTypeValue==0:
            # regular, plain variable
            result = ''
            result = result + '\' {t}\n'.format(t=mdmitem_ref.Name)
            result = result + '<<DEST_PATH>><<DEST>> = <<SOURCE_PATH>><<SOURCE>>\n'
            result = result.replace('<<DEST>>',mdmitem_stk.Name).replace('<<SOURCE>>',mdmitem_ref.Name)
            return trim_lines(add_indent(result,indent))
        elif mdmitem_stk.ObjectTypeValue==1 or mdmitem_stk.ObjectTypeValue==2:
            # loop/array/grid
            result = ''
            result = result + 'dim cat_<<n>>\nfor each cat_<<n>> in <<DEST_PATH>><<DEST>>.categories\n'
            for subfield in mdmitem_stk.Fields:
                result_field = recursive(subfield,mdmitem_ref.Fields[subfield.name],indent=indent+'\t',name_part=name_part+'_'+subfield.Name)
                result_field = result_field.replace('<<DEST_PATH>>','<<DEST_PATH>><<DEST>>[cat_<<n>>.name].').replace('<<SOURCE_PATH>>','<<SOURCE_PATH>><<SOURCE>>[cat_<<n>>.name].')
                result = result + result_field
            result = result + 'next\n'
            result = result.replace('<<DEST>>',mdmitem_stk.Name)
            result = result.replace('<<SOURCE>>',mdmitem_ref.Name)
            result = result.replace('<<n>>',name_part)
            return trim_lines(add_indent(result,indent))
        elif mdmitem_stk.ObjectTypeValue==3:
            # block of fields
            result = ''
            result = result + '' # leading code - set loop iterations, etc... nothing for block of fields
            for subfield in mdmitem_stk.Fields:
                result_field = recursive(subfield,mdmitem_ref.Fields[subfield.name],indent=indent+'\t',name_part=name_part+'_'+subfield.Name)
                result_field = result_field.replace('<<DEST_PATH>>','<<DEST_PATH>><<DEST>>.').replace('<<SOURCE_PATH>>','<<SOURCE_PATH>><<SOURCE>>.')
                result = result + result_field
            result = result.replace('<<DEST>>',mdmitem_stk.Name)
            result = result.replace('<<SOURCE>>',mdmitem_ref.Name)
            result = result.replace('<<n>>',name_part)
            result = result + ''  # trailing code - end if, next... nothing for block of fields
            return trim_lines(add_indent(result,indent))
        else:
            raise ValueError('can\'t generate onnextcase codes: unrecognized item type: {t} ( stk var: {stkvar}, unstk var: {unstkvar} )'.format(t=mdmitem_stk.ObjectTypeValue,stkvar=mdmitem_stk.Name,unstkvar=mdmitem_ref.Name))
    result = recursive(mdmitem_stk,mdmitem_ref,indent='',name_part=mdmitem_stk.Name)
    result = result.replace('<<DEST_PATH>>','<<STK_VARIABLE_PATH>>').replace('<<SOURCE_PATH>>','<<UNSTK_VARIABLE_PATH>><<UNSTK_VARIABLE_NAME>>[cbrand].')
    return result




def prepare_variable_records(mdd_data_questions):
    variable_records = {}
    # for rec in variable_specs['variables_metadata']:
    for rec in mdd_data_questions:
        item_name_clean = sanitize_item_name(rec['name'])
        # rec = rec['records_ref']
        variable_records[item_name_clean] = rec
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
    process_type = None
    # variable_is_plain = re.match(r'^\s*?plain\b',variable_attributes_captured_with_mdd_read['type'])
    variable_is_categorical = re.match(r'^\s*?plain/(?:categorical|multipunch|singlepunch)',variable_attributes_captured_with_mdd_read['type'])
    variable_is_loop = re.match(r'^\s*?(?:array|grid|loop)\b',variable_attributes_captured_with_mdd_read['type'])
    # variable_is_block = re.match(r'^\s*?(?:block)\b',variable_attributes_captured_with_mdd_read['type'])
    if variable_is_loop:
        process_type = 'loop'
    elif variable_is_categorical:
        process_type = 'categorical'
    else:
        raise ValueError('Can\'t handle this type of variable: {s}'.format(s=variable_attributes_captured_with_mdd_read['type']))
    return process_type

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

def init_mdd_doc_from_script(script):
    mdmdoc = win32com.client.Dispatch("MDM.Document")
    mdmdoc.IncludeSystemVariables = False
    mdmdoc.Contexts.Base = "Analysis"
    mdmdoc.Contexts.Current = "Analysis"
    mdmdoc.Script = CONFIG_METADATA_PAGE_TEMPLATE.replace('{@}',script)
    return mdmdoc

def prepare_category_scripts(key_categories,mdd_data_categories,mdmdoc):
    cat_stk_data = []
    performance_counter = iter(utility_performance_monitor.PerformanceMonitor(config={
        'total_records': len(key_categories),
        'report_frequency_records_count': 1,
        'report_frequency_timeinterval': 14,
        'report_text_pipein': 'progress processing categories',
    }))
    print_log_processing('categories: trying to find the most frequent label and analysis value for every category')
    for cat_stk_name in [ sanitize_item_name(c) for c in key_categories ]:
        next(performance_counter)
        cat_label_frequency_data = {}
        cat_analysisvalue_frequency_data = {}
        for cat_mdd in mdd_data_categories:
            question_name, category_name = extract_category_name(cat_mdd['name'])
            question_name_clean, category_name_clean = sanitize_item_name(question_name), sanitize_item_name(category_name)
            category_label = cat_mdd['label']
            category_properties_dict = cat_mdd['properties']
            assert not isinstance(category_properties_dict,list)
            category_analysisvalue = None
            for prop_name, prop_value in category_properties_dict.items(): # we need to iterate cause property names are case insensitive; it can be "value" or "Value", or (I've never seen, but it can be) "VaLuE"
                if sanitize_item_name(prop_name)==sanitize_item_name('value'):
                    if prop_value:
                        try:
                            value = int(prop_value)
                            category_analysisvalue = value
                        except:
                            pass
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
    return ',\n'.join([ generate_category_metadata(cat['name'],cat['label'],cat['properties'],mdmdoc) for cat in cat_stk_data ])

def process_metadata_outerloop(name,key_categories,mdd_data_categories,mdmdoc,previously_added):
    print_log_processing('categories')
    categories_scripts = prepare_category_scripts(key_categories,mdd_data_categories,mdmdoc)
    print_log_processing('top level stacking loop')
    result_metadata = CONFIG_METADATA_LOOP_OUTERSTKLOOP.replace('<<stk_loopname>>',name).replace('<<CATEGORIES>>',categories_scripts)
    result_edits = prepare_syntax_substitutions( CONFIG_CODE_LOOP_OUTERSTKLOOP, stk_variable_name=name, unstk_variable_name='', unstk_variable_fieldname='' )
    # add defines
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

def process_metadata_stack_a_loop(mdmitem_stk,field_name_stk,path_stk,mdmitem_unstk,field_name_unstk,path_unstk,variable_record,variable_records,mdmdoc,previously_added):
    mdmitem_stk, mdmitem_stk_script = generate_updated_metadata_update_all_in_batch(mdmitem_stk,mdmitem_stk.Script,variable_record,mdmdoc)
    _, loop_name_unstk = extract_field_name(path_unstk)

    for result_patch_parent in process_metadata_every_parent(path_stk,variable_records,mdmdoc,previously_added):
        yield result_patch_parent

    # done with parent levels, add record for processing the variable that is stacked
    result_metadata = mdmitem_stk.Script
    code_source = ''
    if variable_record['attributes']['object_type_value']==0:
        # it means it's a regular plain variable
        # we can use direct assignment
        code_source = CONFIG_CODE_LOOP_UNSTACK_SIMPLE
    else:
        # it's c complex structure
        # unfortunately, direct assignment "A = B" is not working in dms scripts
        # we need to iterate over fields
        # and I can't use a function, i.e. CopyFrom(A,B)
        # because I can't detect var/loop type in CDSC (case data source component)
        # anyway, doing euristic analysis is not 100% right, it is not the most performance efficient
        # and stacking is sometimes slow, it can take 8 hours, or more, in some projects, i.e. Disney+&Hulu tracker
        # So I have to generate proper code here iterating over all loops and fields
        code_source = {**CONFIG_CODE_LOOP_UNSTACK_OBJECT_LOOP_OR_BLOCK}
        code_source_add = generate_recursive_onnextcase_code(mdmitem_stk,mdmitem_unstk)
        code_source['code'] = re.sub(r'^(.*?)\n\s*?\'\s*?\{@\}[^\n]*?\n(.*?)$',lambda m: '{code_begin}{code_add}{code_end}'.format(code_begin=re.sub(r'\n?$','\n',m[1],flags=re.I|re.DOTALL),code_end=re.sub(r'\n?$','\n',m[2],flags=re.I|re.DOTALL),code_add=re.sub(r'\n?$','\n',code_source_add,flags=re.I|re.DOTALL)),code_source['code'],flags=re.I|re.DOTALL)
    result_edits = prepare_syntax_substitutions( code_source, stk_variable_name=field_name_stk, unstk_variable_name=loop_name_unstk, unstk_variable_fieldname=field_name_unstk )
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

def process_metadata_stack_a_categorical(mdmitem_stk,field_name_stk,path_stk,mdmitem_unstk,field_name_unstk,path_unstk,variable_record,variable_records,mdmdoc,previously_added):
    mdmitem_stk, mdmitem_stk_script = generate_updated_metadata_update_all_in_batch(mdmitem_stk,mdmitem_stk.Script,variable_record,mdmdoc)

    for result_patch_parent in process_metadata_every_parent(path_stk,variable_records,mdmdoc,previously_added):
        yield result_patch_parent

    # done with parent levels, add record for processing the variable that is stacked
    result_metadata = mdmitem_stk.Script
    code_source = CONFIG_CODE_CATEGORICALYN
    result_edits = prepare_syntax_substitutions( code_source, stk_variable_name=field_name_stk, unstk_variable_name=field_name_unstk, unstk_variable_fieldname=field_name_unstk )
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

def process_metadata_every_parent(path_stk,variable_records,mdmdoc,previously_added):
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
            mdmitem = generate_updated_metadata_clone_excluding_subfields(current_item_stk_name,variable_record_unstk['scripting'],variable_record_unstk['attributes'],mdmdoc)
            result_metadata = mdmitem.Script
            code_source = CONFIG_CODE_LOOP
            result_edits = prepare_syntax_substitutions( code_source, stk_variable_name=current_item_stk_name, unstk_variable_name=current_item_stk_name, unstk_variable_fieldname='' )
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



def generate_patch_stk(variable_specs,mdd_data,config):


    # here we have a list of items in the output patch file
    result = []

    # # ops that was already done
    # try:
    #     mdd_data = ([sect for sect in mdd_data['sections'] if sect['name']=='fields'])[0]['content']
    # except:
    #     pass
    mdd_data_questions = [ field for field in mdd_data if detect_item_type_from_mdddata_fields_report(field['name'])=='variable' ]
    mdd_data_categories = [ cat for cat in mdd_data if detect_item_type_from_mdddata_fields_report(cat['name'])=='category' ]

    # helper variable
    # prep dict with variable data stored in variable_specs
    variable_records = prepare_variable_records(mdd_data_questions)

    # here we go, first, we should create the loop
    stk_loopname = choose_loop_name(variable_records,CONFIG_LOOP_NAME_SUGGESTED)

    # prepare mdm item that is used for interaction with all mdm interfaces
    mdmdoc = init_mdd_doc_from_script('')

    # go!

    # 1. add that global loop
    for result_patch in process_metadata_outerloop(name=stk_loopname,key_categories=variable_specs['categories'],mdd_data_categories=mdd_data_categories,mdmdoc=mdmdoc,previously_added=result):
        result.append(result_patch)

    # now process every variable
    performance_counter = iter(utility_performance_monitor.PerformanceMonitor(config={
        'total_records': len(variable_specs['variables']),
        'report_frequency_records_count': 1,
        'report_frequency_timeinterval': 9,
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
            process_type = detect_var_type_by_record(variable_record)
            
            # grab scripts
            if not 'scripting' in variable_record:
                raise ValueError('Input data does not include "scripting" data, please adjust settings that you use to run mdd_read')
            variable_scripts = variable_record['scripting']

            # processed variable is not always a top level variable
            # maybe we need to process every parent and add metadata for them
            # see process_metadata_every_parent within process_metadata_stack_a_loop and process_metadata_stack_a_categorical
            
            # and now manipulations with MDD
            mdmdoc = init_mdd_doc_from_script(variable_scripts)
            mdmitem_unstk = mdmdoc.Fields[field_name] # that's top-level!
            
            if process_type=='loop':
                
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
                        mdmitem_unstk = generate_metadata_from_scripts(field_name_unstk,variable_record_unstk['scripting'],variable_record_unstk['attributes'],mdmdoc)
                        
                        outer_path, _ = extract_field_name(variable_record['name'])
                        full_name_stk = '{loopname}{path}.{field_name}'.format(loopname=stk_loopname,path='.{path}'.format(path=outer_path) if outer_path else '',field_name=mdmitem_loop_field.Name)
                        path_stk, _ = extract_field_name(full_name_stk)
                        
                        mdmitem_stk = generate_metadata_from_scripts(mdmitem_loop_field.Name,mdmitem_loop_field.Script,variable_record_unstk['attributes'],mdmdoc)
                        mdmitem_stk_script = mdmitem_loop_field.Script
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
                            mdmitem_stk, mdmitem_stk_script = generate_updated_metadata_rename(mdmitem_stk,mdmitem_stk_script,field_name_stk,mdmdoc)
                        
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

                        for result_patch in process_metadata_stack_a_loop(mdmitem_stk,mdmitem_stk.Name,path_stk,mdmitem_unstk,field_name_unstk,path_unstk,variable_record_unstk_final,variable_records,mdmdoc,result):
                            result.append(result_patch)

            elif process_type=='categorical':
                
                mdmitem_stk, mdmitem_stk_script = generate_updated_metadata_stk_categorical(mdmitem_unstk,variable_scripts,mdmdoc)
                mdmitem_stk, mdmitem_stk_script = generate_updated_metadata_rename(mdmitem_unstk,variable_scripts,'{part_old}{part_added}'.format(part_old=mdmitem_unstk.Name,part_added='_YN'),mdmdoc)

                full_name_unstk = variable_record['name']
                path_unstk, field_name_unstk = extract_field_name(full_name_unstk)
                full_name_stk = trim_dots('{stk_loopname}.{path_nested}'.format(stk_loopname=stk_loopname,path_nested=trim_dots('{path}.{field_name}'.format(path=path_unstk,field_name=field_name_unstk))))
                path_stk, field_name_stk = extract_field_name(full_name_stk)

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

                for result_patch in process_metadata_stack_a_categorical(mdmitem_stk,mdmitem_stk.Name,path_stk,mdmitem_unstk,field_name_unstk,path_unstk,variable_record_final,variable_records,mdmdoc,result):
                    result.append(result_patch)

            else:
                raise ValueError('Generating updated item metadata: can\'t handle this type, not implemented: {s}'.format(s=process_type))

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

    mdd_data_questions = get_mdd_data_questions_from_input_data(inp_mdd_scheme)

    result = generate_patch_stk(variable_specs,mdd_data_questions,config)
    
    result_json = json.dumps(result, indent=4)

    print('{script_name}: saving as "{fname}"'.format(fname=result_final_fname,script_name=script_name))
    with open(result_final_fname, "w") as outfile:
        outfile.write(result_json)

    time_finish = datetime.now()
    print('{script_name}: finished at {dt} (elapsed {duration})'.format(dt=time_finish,duration=time_finish-time_start,script_name=script_name))



if __name__ == '__main__':
    entry_point({'arglist_strict':True})
