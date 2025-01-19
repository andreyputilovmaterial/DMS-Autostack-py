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



# if __name__ == '__main__':
#     # run as a program
#     import helper_utility_wrappers
# elif '.' in __name__:
#     # package
#     from . import helper_utility_wrappers
# else:
#     # included with no parent package
#     import helper_utility_wrappers



# we'll add "_2",, "_3", and so on, if this name is used
CONFIG_LOOP_NAME_SUGGESTED = 'STKLoop'

CONFIG_ANALYSIS_VALUE_YES = 1
CONFIG_ANALYSIS_VALUE_NO = 0

# code templates
# metadata code templates
CONFIG_METADATA_PAGE_TEMPLATE = 'Metadata(en-US, Question, label)\n{@}\nEnd Metadata'

CONFIG_METADATA_LOOP_OUTERSTKLOOP = """
<<LOOPNAME>> -
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

' CopyFrom(dest,source)
' A helper function used to bring values from source to dest
' We use
' CopyFrom( .BrandFamiliarity_GV, BrandFamiliarity[cbrand].GV )
' instead of
' .BrandFamiliarity_GV = BrandFamiliarity[cbrand].GV
' because GV can be a loop/array/grid/block of fields
' and we'll need to iterate over its fields and/or categories
function CopyFrom(dest,source)
	' for categorical source and dest
	'vartype(dest) = 4 (object)
	'vartype(dest.response.value) = 3 (categorical)
	'dest.QuestionDataType = 3
	'DataTypeConstants = {
	'	mtNone: 0,
	'	mtDouble: 1,
	'	mtText: 2,
	'	mtCategorical: 3,
	'	mtObject: 4,
	'	mtDate: 5,
	'	mtDouble: 6,
	'	mtBoolean: 7
	'}
	'VarType constants:
	'	0: None (Val is NULL)
	'	1: Long
	'	2: Text
	'	3: Categorical
	'	4: Object
	'	5: Date
	'	6: Double
	'	7: Boolean
    'if dest.ObjectTypeValue = 0 or dest.ObjectTypeValue = 16 then
    if true then
        ' plain variable, no matter which type it is - categorical/numeric/text/date/etc...
        ' I don't know which code is 16, it's very rare, but once I saw Respondent.Serial had ObjectTypeValue=16
        ' just assign the value
        dest = source
    elseif dest.ObjectTypeValue = 3 then
        ' 3 = block of fields
        dim field_dest
        for each field_dest in dest.Fields
            set source[field_dest.Name] = source[field_dest.QuestionName]
        next
    elseif dest.ObjectTypeValue = 1 or dest.ObjectTypeValue = 2 then
        ' loop/array/grid
        dim cat, subfield, iter_source, iter_dest
        for each cat in dest.categories
            set iter_dest = dest[cat.name]
            for each subfield in iter_dest.Items
                set iter_source = source[cat.name]
                iter_dest[subfield.Name] = iter_source[cat.name]
            next
        next
    else
        debug.echo("unrecognized data type")
        debug.log("unrecognized data type")
        err.raise(-999,"unrecognized data type")
    end if
end function

"""
}

CONFIG_CODE_LOOP_UNSTACK = {
    'variable_stk_path': '<<STK_VARIABLE_PATH>><<STK_VARIABLE_NAME>>.', # not sure we need it, we don't expect that we need to process subfields separately; we need to find some really complicated tests to check it, where we stack at 2 different levels - I can imaging this could happen, let's find some tests and see
    'variable_unstacked_path': '<<UNSTK_VARIABLE_PATH>><<UNSTK_VARIABLE_NAME>>[cbrand].<<UNSTK_VARIABLE_FIELDNAME>>.', # not sure we need it, we don't expect that we need to process subfields separately; we need to find some really complicated tests to check it, where we stack at 2 different levels - I can imaging this could happen, let's find some tests and see
    'code': """
' <<STK_VARIABLE_NAME>>
' from: <<UNSTK_VARIABLE_NAME>>
' <<STK_VARIABLE_PATH>><<STK_VARIABLE_NAME>> = <<UNSTK_VARIABLE_PATH>><<UNSTK_VARIABLE_NAME>>[cbrand].<<UNSTK_VARIABLE_FIELDNAME>>
' It can be a loop/array/grid or a block of fields, so we'll use CopyFrom() instead of direct assignment
CopyFrom( <<STK_VARIABLE_PATH>><<STK_VARIABLE_NAME>>, <<UNSTK_VARIABLE_PATH>><<UNSTK_VARIABLE_NAME>>[cbrand].<<UNSTK_VARIABLE_FIELDNAME>> )
' {@}
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

def check_if_variable_exists_based_on_mdd_read_records(records,fullpathandname):
    def val(s):
        return not not re.match(r'^(?:\w+\.)*\w+$',s)
    def norm(name):
        s = name
        s = re.sub(r'\[\s*?\{?\s*?(?:\w+|\.\.)?\s*?\}?\s*?\]','',s,flags=re.I)
        s = re.sub(r'\s','',s,flags=re.I)
        s = s.lower()
        if val(s):
            return s
        else:
            raise ValueError('looking for item in records, but name does not follow convention: {s}'.format(s=s))
    return norm(fullpathandname) in [ norm(s['name']) for s in records ]



def generate_updated_metadata_rename(mdmitem,mdmitem_script,newname,mdmdoc):
    mdmitem.Name = newname
    return mdmitem, mdmitem.Script

def generate_updated_metadata_setlabel(mdmitem,mdmitem_script,newvalue,mdmdoc):
    mdmitem.Label = newvalue
    return mdmitem, mdmitem.Script

def generate_updated_metadata_updateproperties(mdmitem,mdmitem_script,newvalues_dict,mdmdoc):
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
            mdmitem.Properties[propname_clean] = prop_value
    return mdmitem, mdmitem.Script

def generate_updated_metadata_stk_categorical(mdmitem,mdmitem_script,mdmdoc):
    # if mdmitem.Elements.IsReference:
    #     mdmitem.Elements.Reference = None
    #     mdmitem.Elements.ReferenceName = None
    # for mdmelem in mdmitem.Elements:
    #     mdmitem.Elements.remove(mdmelem.Name)
    # mdm_elem_new = mdmdoc.CreateElements("","")
    # mdmitem.Elements = mdm_elem_new
    if mdmitem.Elements.IsReference:
        # TODO: this is not 100% correct, the regular expression can match the word "categorical" somewhere in label
        # but I cen't find any better solution
        mdmitem.Script = re.sub(r'^(.*)(\bcategorical\b)(\s*?(?:\{.*?\})?\s*?(?:\w+\s*?(?:\(.*?\))?)?\s*?;?\s*?)$',lambda m: '{a}{b}{c}'.format(a=m[1],b=m[2],c=' { Yes "Yes" };'),mdmitem.Script,flags=re.I|re.DOTALL)
        # for attempt in range(0,2):
        #     try:
        #         mdm_elem_new = mdmdoc.CreateElements("","")
        #         mdmitem.Elements = mdm_elem_new
        #     except:
        #         pass
        #     try:
        #         mdmitem.Elements.ReferenceName = ''
        #     except:
        #         pass
        #     try:
        #         mdmitem.Elements.IsReference = False
        #     except:
        #         pass
        #     try:
        #         mdmitem.Elements.Remove(0)
        #     except:
        #         pass
    for mdmelem in mdmitem.Elements:
        mdmitem.Elements.remove(mdmelem.Name)
    # clean out responses for "Other" - I think we don't need it in stacked, or should it be configurable?
    for mdmfield in mdmitem.HelperFields:
        mdmitem.HelperFields.remove(mdmfield.Name)
    mdmitem.MinValue = 1
    mdmitem.MaxValue = 1
    mdmitem.Elements.Order = 0 # no randomization
    mdmelem = mdmdoc.CreateElement("Yes","Yes")
    mdmelem.Name = "Yes"
    mdmelem.Label = "Yes"
    mdmelem.Type = 0 # mdmlib.ElementTypeConstants.mtCategory
    if CONFIG_ANALYSIS_VALUE_YES is not None:
        # mdmelem.Properties.Item["Value"] = 1 # use this in mrs instead
        mdmelem.Properties['Value'] = CONFIG_ANALYSIS_VALUE_YES
    mdmitem.Elements.Add(mdmelem)
    mdmelem = mdmdoc.CreateElement("No","No")
    mdmelem.Name = "No"
    mdmelem.Label = "No"
    mdmelem.Type = 0 # mdmlib.ElementTypeConstants.mtCategory
    if CONFIG_ANALYSIS_VALUE_NO is not None:
        mdmelem.Properties['Value'] = CONFIG_ANALYSIS_VALUE_NO
    mdmitem.Elements.Add(mdmelem)
    return mdmitem, mdmitem.Script

def generate_updated_metadata_clone_excluding_subfields(name,script,attr_list,mdmroot):
    detect_type = None
    variable_is_plain = False
    variable_is_categorical = False
    variable_is_loop = False
    variable_is_grid = False
    variable_is_block = False
    for attr_record in attr_list:
        attr_name = attr_record['name']
        attr_value = attr_record['value']
        if attr_name=='type':
            variable_is_plain = variable_is_plain or not not re.match(r'^\s*?plain\b',attr_value,flags=re.I)
            variable_is_categorical = variable_is_categorical or not not re.match(r'^\s*?plain/(?:categorical|multipunch|singlepunch)',attr_value,flags=re.I)
            variable_is_loop = variable_is_loop or not not re.match(r'^\s*?(?:array|grid|loop)\b',attr_value,flags=re.I)
            variable_is_block = variable_is_block or not not re.match(r'^\s*?(?:block)\b',attr_value,flags=re.I)
        if attr_name=='is_grid':
            variable_is_grid = variable_is_grid or not not re.match(r'^\s*?true\b',attr_value,flags=re.I)
    if variable_is_plain or variable_is_categorical:
        detect_type = 'plain'
    elif variable_is_loop:
        detect_type = 'loop'
    elif variable_is_block:
        detect_type = 'block'
    mdmitem_add = None
    if detect_type == 'plain':
        mdmitem_add = mdmroot.CreateVariable(name, name)
    elif detect_type == 'loop':
        if variable_is_grid:
            mdmitem_add = mdmroot.CreateGrid(name, name)
        else:
            mdmitem_add = mdmroot.CreateArray(name, name)
    elif detect_type == 'block':
        mdmitem_add = mdmroot.CreateClass(name, name)
    elif not detect_type:
        raise ValueError('Cat\'t create object: unrecognized type')
    else:
        raise ValueError('Can\'t handle this type of bject: {s}'.format(s=detect_type))
    if not detect_type:
        raise ValueError('Failed to create variable, please check all data in the patch specs')
    for attr_record in attr_list:
        attr_name = attr_record['name']
        attr_value = attr_record['value']
        # if attr_name=='ObjectTypeValue':
        #     mdmitem_add.ObjectTypeValue = attr_value
        if attr_name=='DataType':
            mdmitem_add.DataType = attr_value
        elif attr_name=='Label':
            mdmitem_add.Label = attr_value if attr_value else ''
        else:
            pass
    mdmitem_add.Script = script
    for f in mdmitem_add.Fields:
        mdmitem_add.Fields.Remove(f.Name)
    return mdmitem_add
    # return mdmitem_add.Script

def generate_category_metadata(name,label,properties,mdmdoc):
    mdmelem = mdmdoc.CreateElement(name,name)
    mdmelem.Name = name
    mdmelem.Label = label
    mdmelem.Type = 0 # mdmlib.ElementTypeConstants.mtCategory
    for prop in properties:
        # mdmelem.Properties.Item[prop['name']] = prop['value'] # use this in mrs instead
        mdmelem.Properties[prop['name']] = prop['value']
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

    def check_if_variable_exists(item_name):
        return check_if_variable_exists_based_on_mdd_read_records(mdd_data_questions,item_name)

    # helper variable
    # prep dict with variable data stored in variable_specs
    variable_records = {}
    # for rec in variable_specs['variables_metadata']:
    for rec in mdd_data_questions:
        item_name_clean = sanitize_item_name(rec['name'])
        # rec = rec['records_ref']
        variable_records[item_name_clean] = rec

    # here we go, first, we should create the loop
    loopname = CONFIG_LOOP_NAME_SUGGESTED
    # avoid using name that is already used
    counter = 2
    while check_if_variable_exists(loopname):
        loopname = '{base_part}_{knt}'.format(base_part=CONFIG_LOOP_NAME_SUGGESTED,knt=counter)
        counter = counter + 1

    categories_scripts = ''
    mdmdoc = win32com.client.Dispatch("MDM.Document")
    mdmdoc.IncludeSystemVariables = False
    mdmdoc.Contexts.Base = "Analysis"
    mdmdoc.Contexts.Current = "Analysis"
    mdmdoc.Script = CONFIG_METADATA_PAGE_TEMPLATE.replace('{@}','')
    cat_stk_data = []
    for cat_stk_name in [ sanitize_item_name(c) for c in variable_specs['categories'] ]:
        cat_label_frequency_data = {}
        cat_analysisvalue_frequency_data = {}
        for cat_mdd in mdd_data_categories:
            question_name, category_name = extract_category_name(cat_mdd['name'])
            question_name_clean, category_name_clean = sanitize_item_name(question_name), sanitize_item_name(category_name)
            category_label = cat_mdd['label']
            category_properties_list = cat_mdd['properties']
            category_analysisvalue = None
            for prop in category_properties_list:
                if sanitize_item_name(prop['name'])==sanitize_item_name('value'):
                    if prop['value']:
                        try:
                            value = int(prop['value'])
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
            'properties': [ { 'name': 'Value', 'value': cat_analysisvalue_data } ] if cat_analysisvalue_data else [],
        })
    categories_scripts = ',\n'.join([ generate_category_metadata(cat['name'],cat['label'],cat['properties'],mdmdoc) for cat in cat_stk_data ])


    result_metadata = CONFIG_METADATA_LOOP_OUTERSTKLOOP.replace('<<LOOPNAME>>',loopname).replace('<<CATEGORIES>>',categories_scripts)
    result_edits = prepare_syntax_substitutions( CONFIG_CODE_LOOP_OUTERSTKLOOP, stk_variable_name=loopname, unstk_variable_name='', unstk_variable_fieldname='' )
    result_patch = {
        'action': 'variable-new',
        'variable': loopname,
        'position': '', # root
        'debug_data': { 'description': 'top level stacking loop' },
        'new_metadata': result_metadata,
        'attributes': { 'ObjectTypeValue': 1, 'Label': None, 'MDMRead_type': 'array' },
        'new_edits': result_edits,
    }
    result.append(result_patch)

    # here we go, process every variable
    # and generate an item in output patch file
    for variable_id in variable_specs['variables']:
        try:
            
            # read variable data from variable_specs
            variable_record = variable_records[sanitize_item_name(variable_id)]
            variable_record_name = variable_record['name']
            variable_name_clean = sanitize_item_name(variable_record_name)
            field_position, field_name = extract_field_name(variable_record_name)
            variable_attributes_captured_with_mdd_read = {}
            if not 'attributes' in variable_record:
                raise ValueError('Input data does not include "attributes" data, please adjust settings that you use to run mdd_read')
            for prop in variable_record['attributes']:
                variable_attributes_captured_with_mdd_read[prop['name']] = prop['value']
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
            
            # and last but not least - we'll operate with the variable in object-oriented way with native tools from IBM
            # that's why we need to load variable metadata as it was stored
            # and we have "scripting" stored for this purpose
            if not 'scripting' in variable_record:
                raise ValueError('Input data does not include "scripting" data, please adjust settings that you use to run mdd_read')
            variable_scripts = variable_record['scripting']

            # please note: we can't just provide updated scripts for the variable
            # it's useless if it's not a top level variable
            # we should provide updated scripts for all its parents
            
            # and now manipulations with MDD
            mdmdoc = win32com.client.Dispatch("MDM.Document")
            mdmdoc.IncludeSystemVariables = False
            mdmdoc.Contexts.Base = "Analysis"
            mdmdoc.Contexts.Current = "Analysis"
            mdmdoc.Script = CONFIG_METADATA_PAGE_TEMPLATE.replace('{@}',variable_scripts)
            mdmitem = mdmdoc.Fields[field_name] # that's top-level!
            
            if process_type=='loop':
                
                mdmloop = mdmitem
                is_a_single_item_within_loop = False
                is_conflicting_name = False
                fields_meaningful = []
                for mdmitem in mdmloop.Fields:
                    meaningless = False
                    if (mdmitem.DataType if mdmitem.ObjectTypeValue==0 else 0) == 0: # info item, skip
                        meaningless = True
                    if sanitize_item_name(mdmitem.Name)==sanitize_item_name('NavButtonSelect'):
                        meaningless = True # that stupid field from mf-polar
                    if not meaningless:
                        fields_meaningful.append(mdmitem.Name)
                is_a_single_item_within_loop = not ( len(fields_meaningful)>1 )
                for mdmitem in mdmloop.Fields:
                    if mdmitem.Name in fields_meaningful:
                        potential_full_name = re.sub(r'^\s*?\.','','{parent_path}.{item}'.format(parent_path=field_position,item=mdmitem.Name),flags=re.I)
                        # first I do straightforward check - check if this item exists at parent level
                        is_conflicting_name = is_conflicting_name or check_if_variable_exists(potential_full_name)
                        # also we should not create items named just "GV" so I'll check against some popular field names
                        is_conflicting_name = is_conflicting_name or sanitize_item_name(mdmitem.Name) in ['gv','rank','num'] or ('overlap' in sanitize_item_name(mdmitem.Name) and ('iim' in sanitize_item_name(mdmloop.Name) or 'qim' in sanitize_item_name(mdmloop.Name)))
                for index,mdmitem in enumerate(mdmloop.Fields):
                    if mdmitem.Name in fields_meaningful:
                        mdmitem_stk = mdmitem
                        mdmitem_name_backup = mdmitem.Name
                        mdmitem_stk_script = mdmitem.Script
                        is_bad_name = False
                        # and there are less common cases but still happening in disney bes
                        is_bad_name = is_bad_name or re.match(r'^\s*?((?:Top|T|Bottom|B))(\d*)((?:B|Box))\s*?$',mdmitem.Name,flags=re.I)
                        name_upd = mdmitem_stk.Name
                        if is_a_single_item_within_loop:
                            name_upd = mdmloop.Name
                        elif is_conflicting_name or is_bad_name:
                            if index==0 and not is_bad_name:
                                name_upd = '{part_parent}'.format(part_parent=mdmloop.Name)
                            else:
                                name_upd = '{part_parent}_{part_field}'.format(part_parent=mdmloop.Name,part_field=mdmitem_stk.Name)
                        if not (name_upd == mdmitem_stk.Name):
                            mdmitem_stk, mdmitem_stk_script = generate_updated_metadata_rename(mdmitem_stk,mdmitem_stk_script,name_upd,mdmdoc)
                        
                        # somehow labels disappear when switching from Question context to Analysis context
                        # so I'll reset it back to original value captured by mdd_read
                        label_overwrite = mdmitem_stk.Label
                        variable_record_stk = variable_record
                        variable_name_stk_clean = '{a}.{b}'.format(a=variable_name_clean,b=sanitize_item_name(mdmitem_name_backup))
                        if variable_name_stk_clean in variable_records:
                            variable_record_stk =  variable_records[variable_name_stk_clean]
                        if variable_record_stk['label']:
                            label_overwrite = variable_record_stk['label']
                        mdmitem_stk, mdmitem_stk_script = generate_updated_metadata_setlabel(mdmitem_stk,mdmitem_stk_script,label_overwrite,mdmdoc)

                        # somehow properties are also lost when  switching from Question context to Analysis context
                        # they are just not displayed in scripts
                        # so I'll bring it back too
                        props = {}
                        for record in variable_record['properties']:
                            props[record['name']] = record['value']
                        mdmitem_stk, mdmitem_stk_script = generate_updated_metadata_updateproperties(mdmitem_stk,mdmitem_stk_script,props,mdmdoc)
                        props = {}
                        variable_record_stk = variable_record
                        variable_name_stk_clean = '{a}.{b}'.format(a=variable_name_clean,b=sanitize_item_name(mdmitem_name_backup))
                        if variable_name_stk_clean in variable_records:
                            variable_record_stk =  variable_records[variable_name_stk_clean]
                        for record in variable_record_stk['properties']:
                            props[record['name']] = record['value']
                        mdmitem_stk, mdmitem_stk_script = generate_updated_metadata_updateproperties(mdmitem_stk,mdmitem_stk_script,props,mdmdoc)

                        # and prepare attributes
                        mdmitem_stk_attributes = {}
                        mdmitem_stk_attributes['ObjectTypeValue'] = mdmitem_stk.ObjectTypeValue
                        if mdmitem_stk_attributes['ObjectTypeValue']==0:
                            mdmitem_stk_attributes['DataType'] = mdmitem_stk.DataType
                        mdmitem_stk.Label = linebreaks_remove(mdmitem_stk.Label)
                        mdmitem_stk_attributes['Label'] = mdmitem_stk.Label
                        variable_record_stk = variable_record
                        variable_name_stk_clean = '{a}.{b}'.format(a=variable_name_clean,b=sanitize_item_name(mdmitem_name_backup))
                        if variable_name_stk_clean in variable_records:
                            variable_record_stk =  variable_records[variable_name_stk_clean]
                        for record in variable_record_stk['attributes']:
                            mdmitem_stk_attributes['MDMRead_'+record['name']] = record['value']

                        field_position_stk = '{loopname}{path_nested}'.format(loopname=loopname,path_nested='.{path_persisted}'.format(path_persisted=field_position) if field_position else '')
                        # check if all parents exist, or add if they do not
                        unstk_variable_full_name = field_name
                        added_item_name = field_position_stk
                        added_item_position = ''
                        parent,added_item_name = extract_parent_name(added_item_name)
                        prev_items_added = [ sanitize_item_name(trim_dots('{path}.{v}'.format(path=r['position'],v=r['variable']))) for r in result if r['action']=='variable-new' ]
                        added_item_fullpath = trim_dots('{p}.{e}'.format(p=added_item_position,e=parent))
                        while not ( parent=='' ):
                            found = sanitize_item_name(added_item_fullpath) in prev_items_added
                            if not found:
                                added_item_possible_matching_lookup_name = sanitize_item_name(added_item_fullpath)
                                added_item_possible_matching_lookup_name_part1, added_item_possible_matching_lookup_name_part2 = extract_parent_name(added_item_possible_matching_lookup_name)
                                if sanitize_item_name(added_item_possible_matching_lookup_name_part1)==sanitize_item_name(loopname):
                                    added_item_possible_matching_lookup_name = added_item_possible_matching_lookup_name_part2
                                added_item_matching_var = variable_records[added_item_possible_matching_lookup_name]
                                mdmitem = generate_updated_metadata_clone_excluding_subfields(parent,added_item_matching_var['scripting'],added_item_matching_var['attributes'],mdmdoc)
                                added_item_attributes = {}
                                added_item_attributes['ObjectTypeValue'] = mdmitem.ObjectTypeValue
                                if added_item_attributes['ObjectTypeValue']==0:
                                    added_item_attributes['DataType'] = mdmitem.DataType
                                mdmitem.Label = linebreaks_remove(mdmitem.Label)
                                added_item_attributes['Label'] = mdmitem.Label
                                for record in added_item_matching_var['attributes']:
                                    added_item_attributes['MDMRead_'+record['name']] = record['value']
                                
                                result_metadata = mdmitem.Script
                                result_edits = prepare_syntax_substitutions( CONFIG_CODE_LOOP, stk_variable_name=parent, unstk_variable_name=parent, unstk_variable_fieldname='GV_Suggested' )
                                unstk_variable_full_name = field_name # result_edits['unstk_variable_name'] + '_' + parent
                                result_patch_parent = {
                                    'action': 'variable-new',
                                    'variable': parent,
                                    'position': added_item_position,
                                    'debug_data': { 'description': 'added as a parent item when processing {v}'.format(v=variable_record_name), 'source_from': '???' },
                                    'new_metadata': result_metadata,
                                    'attributes': added_item_attributes,
                                    'new_edits': result_edits,
                                }
                                result.append(result_patch_parent)
                            added_item_position = added_item_fullpath
                            parent,added_item_name = extract_parent_name(added_item_name)
                            prev_items_added = [ sanitize_item_name(trim_dots('{path}.{v}'.format(path=r['position'],v=r['variable']))) for r in result if r['action']=='variable-new' ]
                            added_item_fullpath = trim_dots('{p}.{e}'.format(p=added_item_position,e=parent))

                        # done with parent levels, add record for processing the variable that is stacked
                        result_metadata = mdmitem_stk.Script
                        result_edits = prepare_syntax_substitutions( CONFIG_CODE_LOOP_UNSTACK, stk_variable_name=mdmitem_stk.Name, unstk_variable_name=unstk_variable_full_name, unstk_variable_fieldname=mdmitem_name_backup )
                        result_patch = {
                            'action': 'variable-new',
                            'variable': mdmitem_stk.Name,
                            'position': field_position_stk,
                            'debug_data': { 'source_from': variable_record_name },
                            'new_metadata': result_metadata,
                            'attributes': mdmitem_stk_attributes,
                            'new_edits': result_edits,
                        }
                        
                        # finally, save and go to next variable
                        result.append(result_patch)

            elif process_type=='categorical':
                
                mdmitem_stk, mdmitem_stk_script = generate_updated_metadata_stk_categorical(mdmitem,variable_scripts,mdmdoc)
                mdmitem_stk, mdmitem_stk_script = generate_updated_metadata_rename(mdmitem,variable_scripts,'{part_old}{part_added}'.format(part_old=mdmitem.Name,part_added='_YN'),mdmdoc)

                field_position_stk = '{loopname}{path_nested}'.format(loopname=loopname,path_nested='.{path_persisted}'.format(path_persisted=field_position) if field_position else '')

                # somehow labels disappear when switching from Question context to Analysis context
                # so I'll reset it back to original value captured by mdd_read
                # label_overwrite = mdmitem_stk.Label
                label_overwrite = mdmitem_stk.Label
                variable_record_stk = variable_record
                if variable_record_stk['label']:
                    label_overwrite = variable_record_stk['label']
                mdmitem_stk, mdmitem_stk_script = generate_updated_metadata_setlabel(mdmitem_stk,mdmitem_stk_script,label_overwrite,mdmdoc)

                # somehow properties are also lost when  switching from Question context to Analysis context
                # they are just not displayed in scripts
                # so I'll bring it back too
                props = {}
                variable_record_stk = variable_record
                for record in variable_record_stk['properties']:
                    props[record['name']] = record['value']
                mdmitem_stk, mdmitem_stk_script = generate_updated_metadata_updateproperties(mdmitem_stk,mdmitem_stk_script,props,mdmdoc)

                # and prepare attributes
                mdmitem_stk_attributes = {}
                mdmitem_stk_attributes['ObjectTypeValue'] = mdmitem_stk.ObjectTypeValue
                if mdmitem_stk_attributes['ObjectTypeValue']==0:
                    mdmitem_stk_attributes['DataType'] = mdmitem_stk.DataType
                mdmitem_stk.Label = linebreaks_remove(mdmitem_stk.Label)
                mdmitem_stk_attributes['Label'] = mdmitem_stk.Label
                variable_record_stk = variable_record
                for record in variable_record_stk['attributes']:
                    mdmitem_stk_attributes['MDMRead_'+record['name']] = record['value']

                # check if all parents exist, or add if they do not
                unstk_variable_full_name = field_name
                added_item_name = field_position_stk
                added_item_position = ''
                parent,added_item_name = extract_parent_name(added_item_name)
                prev_items_added = [ sanitize_item_name(trim_dots('{path}.{v}'.format(path=r['position'],v=r['variable']))) for r in result if r['action']=='variable-new' ]
                added_item_fullpath = trim_dots('{p}.{e}'.format(p=added_item_position,e=parent))
                while not ( parent=='' ):
                    found = sanitize_item_name(added_item_fullpath) in prev_items_added
                    if not found:
                        added_item_possible_matching_lookup_name = sanitize_item_name(added_item_fullpath)
                        added_item_possible_matching_lookup_name_part1, added_item_possible_matching_lookup_name_part2 = extract_parent_name(added_item_possible_matching_lookup_name)
                        if sanitize_item_name(added_item_possible_matching_lookup_name_part1)==sanitize_item_name(loopname):
                            added_item_possible_matching_lookup_name = added_item_possible_matching_lookup_name_part2
                        added_item_matching_var = variable_records[added_item_possible_matching_lookup_name]
                        mdmitem = generate_updated_metadata_clone_excluding_subfields(parent,added_item_matching_var['scripting'],added_item_matching_var['attributes'],mdmdoc)
                        added_item_attributes = {}
                        added_item_attributes['ObjectTypeValue'] = mdmitem.ObjectTypeValue
                        if added_item_attributes['ObjectTypeValue']==0:
                            added_item_attributes['DataType'] = mdmitem.DataType
                        mdmitem.Label = linebreaks_remove(mdmitem.Label)
                        added_item_attributes['Label'] = mdmitem.Label
                        for record in added_item_matching_var['attributes']:
                            added_item_attributes['MDMRead_'+record['name']] = record['value']
                        
                        result_metadata = mdmitem.Script
                        result_edits = prepare_syntax_substitutions( CONFIG_CODE_LOOP, stk_variable_name=parent, unstk_variable_name=parent, unstk_variable_fieldname='GV_Suggested' )
                        unstk_variable_full_name = field_name # result_edits['unstk_variable_name'] + '_' + parent
                        result_patch_parent = {
                            'action': 'variable-new',
                            'variable': parent,
                            'position': added_item_position,
                            'debug_data': { 'description': 'added as a parent item when processing {v}'.format(v=variable_record_name), 'source_from': '???' },
                            'new_metadata': result_metadata,
                            'attributes': added_item_attributes,
                            'new_edits': result_edits,
                        }
                        result.append(result_patch_parent)
                    added_item_position = added_item_fullpath
                    parent,added_item_name = extract_parent_name(added_item_name)
                    prev_items_added = [ sanitize_item_name(trim_dots('{path}.{v}'.format(path=r['position'],v=r['variable']))) for r in result if r['action']=='variable-new' ]
                    added_item_fullpath = trim_dots('{p}.{e}'.format(p=added_item_position,e=parent))

                # done with parent levels, add record for processing the variable that is stacked
                result_metadata = mdmitem_stk.Script
                result_edits = prepare_syntax_substitutions( CONFIG_CODE_CATEGORICALYN, stk_variable_name=mdmitem_stk.Name, unstk_variable_name=unstk_variable_full_name, unstk_variable_fieldname='GV_Suggested' )
                result_patch = {
                    'action': 'variable-new',
                    'variable': mdmitem_stk.Name,
                    'position': field_position_stk,
                    'debug_data': { 'source_from': variable_record_name },
                    'new_metadata': result_metadata,
                    'attributes': mdmitem_stk_attributes,
                    'new_edits': result_edits,
                }
                
                # done, return results
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

    mdd_data_questions = []
    try:
        mdd_data_questions = ([sect for sect in inp_mdd_scheme['sections'] if sect['name']=='fields'])[0]['content']
    except:
        pass

    result = generate_patch_stk(variable_specs,mdd_data_questions,config)
    
    result_json = json.dumps(result, indent=4)

    print('{script_name}: saving as "{fname}"'.format(fname=result_final_fname,script_name=script_name))
    with open(result_final_fname, "w") as outfile:
        outfile.write(result_json)

    time_finish = datetime.now()
    print('{script_name}: finished at {dt} (elapsed {duration})'.format(dt=time_finish,duration=time_finish-time_start,script_name=script_name))



if __name__ == '__main__':
    entry_point({'arglist_strict':True})
