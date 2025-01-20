import re





# import pythoncom
import win32com.client




CONFIG_ANALYSIS_VALUE_YES = 1
CONFIG_ANALYSIS_VALUE_NO = 0



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

CONFIG_METADATA_PAGE_TEMPLATE = 'Metadata(en-US, Question, label)\n{@}\nEnd Metadata'



def init_mdd_doc_from_script(script):
    mdmdoc = win32com.client.Dispatch("MDM.Document")
    mdmdoc.IncludeSystemVariables = False
    mdmdoc.Contexts.Base = "Analysis"
    mdmdoc.Contexts.Current = "Analysis"
    mdmdoc.Script = CONFIG_METADATA_PAGE_TEMPLATE.replace('{@}',script)
    return mdmdoc

def generate_updated_metadata_rename(mdmitem_unstk,mdmitem_script,newname,mdmdoc):
    mdmitem_unstk.Name = newname
    return mdmitem_unstk, mdmitem_unstk.Script

def generate_updated_metadata_setlabel(mdmitem_unstk,mdmitem_script,newvalue,mdmdoc):
    def linebreaks_remove(s):
        return re.sub(r'(?:\r\n|\r|\n)',' ',s,flags=re.I)
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
    return mdmelem







def generate_scripts_outerstkloop( loop_name, mdmcategories ):
    result = CONFIG_METADATA_LOOP_OUTERSTKLOOP
    categories_scripts = ',\n'.join( mdmcat.Script for mdmcat in mdmcategories )
    result = result.replace('<<stk_loopname>>',loop_name)
    result = result.replace('<<CATEGORIES>>',categories_scripts)
    return result

