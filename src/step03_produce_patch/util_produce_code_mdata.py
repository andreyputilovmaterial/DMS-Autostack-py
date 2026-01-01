
import re

import sys # for error reporting, to print messages to stderr
import warnings


# import pythoncom
import win32com.client



CONFIG_METADATA_PAGE_TEMPLATE = 'Metadata(en-US, Analysis, label)\n\' ...\nEnd Metadata'

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





CONFIG_ANALYSIS_VALUE_YES = 1
CONFIG_ANALYSIS_VALUE_NO = 0




# we create an MDMDocument from scripts
# and the scripts are expected to contain the outer "Metadata" clause
def create_mdmdoc(script=None):
    if not script:
        script = CONFIG_METADATA_PAGE_TEMPLATE
    mdmdoc = win32com.client.Dispatch("MDM.Document")
    mdmdoc.IncludeSystemVariables = False
    mdmdoc.Contexts.Base = "Analysis"
    mdmdoc.Contexts.Current = "Analysis"
    mdmdoc.Script = script
    return mdmdoc




# and this is a helper fn to update MDMDocument
# and add shared lists from another referenced MDMDocument
# if we don't do it we can possibly get an error of "Unresolved reference" when iterating over categories (over elements)
def mdmdoc_sync_types_definitions(mdmdoc,mdmdoc_ref):
    # I am trying create an shared list
    # but I have no idea how to do it
    # there is no method CreateType
    # it seems a shared list is the same class as Elements
    # so mdmdoc.CreateElements gives as similar object, similar to a shared list, instance of the right interface, with the right .ObjectTypeValue == 5
    # but it is still can't be added as a shared list, it is a "namespace", not shared list
    # I searched all docs in help pages and searched all code samples that are coming with DDL library, there are examples of creating several types of objects but not shared lists
    # so what I am doing is that I am re-attaching the existing object from referenced mdmdoc to target mdmdoc
    # but this object is already a part of a tree, so it has Parent and other references to super fields
    # so I have to detach it from referenced mdm doc, but doing this I am modifying the referenced mdm doc, which is not good
    # so I have to create a copy of referenced mdm doc to have it clear, to have the provided object unmodifyed and have this fn clean
    mdmdoc_ref_clone = create_mdmdoc(mdmdoc_ref.Script)
    for mdmsl_ref in mdmdoc_ref_clone.Types:
        # mdmsl = mdmdoc.CreateType(mdmsl_ref.Name, '')
        # mdmsl = mdmdoc.CreateSharedList(mdmsl_ref.Name, '')
        # mdmsl = mdmdoc.CreateElements(mdmsl_ref.Name, '')
        # mdmsl.Script = re.sub( r'^\s*?.*?\bdefine\b\s*?\n?\s*?\{', '{', mdmsl_ref.Script, flags=re.I|re.DOTALL )
        # mdmdoc.Types.Add(mdmsl)
        mdmdoc_ref_clone.Types.Remove(mdmsl_ref.Name)
        mdmdoc.Types.Add(mdmsl_ref)
    return mdmdoc

def create_mdmvariable(name,script,attr_dict,mdmroot,isgrid_retry_attempts=None):
    assert not isinstance(attr_dict,list)
    detect_type = None
    variable_is_plain = False
    variable_is_categorical = False
    variable_is_loop = False
    variable_is_grid = False
    variable_is_block = False
    if 'type' in attr_dict:
        # in debug, I hate seeing None, I prefer False or True, that's why I have "not not ...""
        # when I see None, it looks like something is wrong, I forgot to initialize a variable, or used the wrong variable name, or some other issues
        variable_is_plain = variable_is_plain or not not re.match(r'^\s*?plain\b',attr_dict['type'],flags=re.I)
        variable_is_categorical = variable_is_categorical or not not re.match(r'^\s*?plain/(?:categorical|multipunch|singlepunch)',attr_dict['type'],flags=re.I)
        variable_is_loop = variable_is_loop or not not re.match(r'^\s*?(?:array|grid|loop)\b',attr_dict['type'],flags=re.I)
        variable_is_block = variable_is_block or not not re.match(r'^\s*?(?:block)\b',attr_dict['type'],flags=re.I)
    if 'object_type_value' in attr_dict:
        variable_is_plain = variable_is_plain or not not re.match(r'^\s*?(?:0)\b',attr_dict['object_type_value'],flags=re.I)
        variable_is_loop = variable_is_loop or not not re.match(r'^\s*?(?:1|2)\b',attr_dict['object_type_value'],flags=re.I)
        variable_is_block = variable_is_block or not not re.match(r'^\s*?(?:3)\b',attr_dict['object_type_value'],flags=re.I)
    if 'data_type' in attr_dict:
        variable_is_categorical = variable_is_categorical or not not re.match(r'^\s*?(?:3)',attr_dict['data_type'],flags=re.I)
    if 'is_grid' in attr_dict:
        # yeah that's text; that's 'True', not True, or 'False', not 'False'
        # that's what we get from mdd_read - everything is in text
        # that tool was initially invented for human-readable outputs, not machine-readable
        # but I am totally okay with having it as text
        # that's even easier to handle it in different environments, when you know you don't have to care about format, you are reading text
        variable_is_grid = variable_is_grid or not not re.match(r'^\s*?true\b',attr_dict['is_grid'],flags=re.I)
    if variable_is_plain or variable_is_categorical:
        detect_type = 'plain'
    elif variable_is_loop:
        detect_type = 'loop'
    elif variable_is_block:
        detect_type = 'block'
    mdmitem = None
    if detect_type == 'plain':
        mdmitem = mdmroot.CreateVariable(name, name)
    elif detect_type == 'loop':
        if variable_is_grid:
            mdmitem = mdmroot.CreateGrid(name, name)
        else:
            mdmitem = mdmroot.CreateArray(name, name)
    elif detect_type == 'block':
        mdmitem = mdmroot.CreateClass(name, name)
    elif not detect_type:
        raise Exception('Cat\'t create object: unrecognized type')
    else:
        raise Exception('Can\'t handle this type of bject: {s}'.format(s=detect_type))
    if not detect_type:
        raise Exception('Failed to create variable, please check all data in the patch specs')
    # if 'object_type_value' in attr_dict:
    #     # we can't set ObjectTypeValue prop here, and we don't have to
    #     # this property should already be of proper type
    #     # if we used the right function to create our object - CreateVariable, CreateGrid, CreateArray...
    #     mdmitem.ObjectTypeValue = attr_dict['object_type_value']
    if 'data_type' in attr_dict:
        mdmitem.DataType = attr_dict['data_type']
    if 'label' in attr_dict:
        mdmitem.Label = attr_dict['label']
    try:
        mdmitem.Script = script
    except Exception as e:
        if variable_is_grid and ( isgrid_retry_attempts is None or isgrid_retry_attempts<3 ):
            # same manipulations as above
            # maybe it failed because we tried to create an object of IGrid interface and it's not compatible, our object is not a grid
            # let's try to unset the "grid" flag and try again
            return create_mdmvariable(name,script,{**attr_dict,'type':'array','is_grid':'false'},mdmroot,isgrid_retry_attempts=isgrid_retry_attempts+1 if isgrid_retry_attempts is not None else 1)
        else:
            raise e
    return mdmitem


def create_mdmvariable_clone_excluding_subfields(name,script,attr_dict,mdmroot):
    mdmitem_add = create_mdmvariable(name,script,attr_dict,mdmroot)
    for f in mdmitem_add.Fields:
        mdmitem_add.Fields.Remove(f.Name)
    return mdmitem_add


def create_mdmvariable_categorical_yn(mdmitem,mdmdoc):
    if mdmitem.Elements.IsReference:
        # if elements (categories) are a reference to something - that's a pain, I can't unset it
        # I tried different approaches
        # I tried setting mdmitem.Elements.Reference, .ReferenceName, .IsReference (I can read all of these but not set)
        # I tried re-creating the Elements with mdmdoc.CreateElements()
        # I tried to set mdmitem.Elements.Script = ...
        # or mdmitem.Categories.Script = ...
        # It all fails
        # I tried to search in help pages, I tried all different keywords, I could not find anything
        # The only solution that worked for me is replacing the whole item Scripts
        # That's what I am doing here updating the list of categories with regex
        # TODO: this is not 100% correct
        # the regular expression can match the word "categorical" somewhere in label...
        # I hape it does not happen, because I have a greedy search (.*), and then the word "categorical" should still follow
        # but I can't be sure
        # or yes, I know when it certainly fails - when there is a categorical field in HelperFields
        # hm, I'll try to delete all HelperFields first
        # but I cen't find any better solution
        for mdmfield in mdmitem.HelperFields:
            mdmitem.HelperFields.remove(mdmfield.Name)
        mdmitem.Script = re.sub(r'^(.*)(\bcategorical\b)(\s*?(?:\{.*?\})?\s*?(?:\w+\s*?(?:\(.*?\))?)?\s*?;?\s*?)$',lambda m: '{a}{b}{c}'.format(a=m[1],b=m[2],c=' { Yes "Yes" };'),mdmitem.Script,flags=re.I|re.DOTALL)
    for mdmelem in mdmitem.Elements:
        mdmitem.Elements.remove(mdmelem.Name)
    # clean out responses for "Other" - I think we don't need it in stacked, or should it be configurable?
    # actually, should not be configurable, we definitely don't need it in YN variables
    for mdmfield in mdmitem.HelperFields:
        mdmitem.HelperFields.remove(mdmfield.Name)
    mdmitem.MinValue = 1
    mdmitem.MaxValue = 1
    mdmitem.Elements.Order = 0 # no randomization
    mdmelem = create_mdmcategory(
        "Yes",
        "Yes",
        ({'Value':CONFIG_ANALYSIS_VALUE_YES} if CONFIG_ANALYSIS_VALUE_YES is not None else {}),
        mdmdoc
    )
    mdmitem.Elements.Add(mdmelem)
    mdmelem = create_mdmcategory(
        "No",
        "No",
        ({'Value':CONFIG_ANALYSIS_VALUE_NO} if CONFIG_ANALYSIS_VALUE_NO is not None else {}),
        mdmdoc
    )
    mdmitem.Elements.Add(mdmelem)
    return mdmitem

def rename_mdmvariable(mdmitem,newname):
    mdmitem.Name = newname
    return mdmitem




def update_mdmvariable_attributes(mdmitem,updated_metadata_data):
    def update_label(mdmitem,newvalue):
        def linebreaks_remove(s):
            return re.sub(r'\s*(?:\r\n|\r|\n)\s*',' ',s,flags=re.I)
        newvalue_clean = linebreaks_remove(newvalue) # we don't need multi-line text in stacked variables; it breaks syntax and it is unnecessary, we also don't need it in tab exports
        mdmitem.Label = newvalue_clean
        return mdmitem
    def update_properties(mdmitem_unstk,newvalues_dict):
        assert not isinstance(newvalues_dict,list)
        for prop_name, prop_value in newvalues_dict.items():
            def sanitize_prop_name(name):
                name = re.sub(r'^\s*(.*?)\s*(?:\(.*?\)\s*?)?\s*?$',lambda m: m[1],name,flags=re.I)
                if re.match(r'^.*?[^\w].*?$',name,flags=re.I):
                    # raise Exception('Invalid Prop Name: {s}'.format(s=name))
                    return None
                return name
            propname_clean = sanitize_prop_name(prop_name)
            if propname_clean:
                # if not propname_clean in 
                mdmitem_unstk.Properties[propname_clean] = prop_value
        return mdmitem_unstk
    if 'label' in updated_metadata_data and updated_metadata_data['label']:
        mdmitem = update_label(mdmitem,updated_metadata_data['label'])
    if 'properties' in updated_metadata_data and updated_metadata_data['properties']:
        mdmitem = update_properties(mdmitem,updated_metadata_data['properties'])
    return mdmitem

def create_mdmcategory(name,label,properties,mdmdoc):
    assert not isinstance(properties,list)
    mdmelem = mdmdoc.CreateElement(name,name)
    mdmelem.Name = name
    mdmelem.Label = label
    mdmelem.Type = 0 # mdmlib.ElementTypeConstants.mtCategory
    for prop_name, prop_value in properties.items():
        # mdmelem.Properties.Item[prop['name']] = prop['value'] # use this in mrs instead
        mdmelem.Properties[prop_name] = prop_value
    return mdmelem


def sync_labels_and_key_spss_properties_from_mddreport(mdmitem,variable_record):
    def sanitize_line_breaks(s):
        return re.sub(r'\s*(?:\r\n|\r|\n)\s*',' ',s,flags=re.I)
    def extract_field_name(item_name):
        m = re.match(r'^\s*((?:\w.*?\.)*)(\w+)\s*$',item_name,flags=re.I)
        if m:
            return re.sub(r'\s*\.\s*$','',m[1]),m[2]
        else:
            raise Exception('Can\'t extract field name from "{s}"'.format(s=item_name))
    def sanitize_item_name(item_name):
        return re.sub(r'\s*$','',re.sub(r'^\s*','',re.sub(r'\s*([\[\{\]\}\.])\s*',lambda m:'{m}'.format(m=m[1]),item_name,flags=re.I))).lower()
    def sanitize_field_name(name):
        _, field_name = extract_field_name(name)
        return sanitize_item_name(field_name)
    def iterate_over_categories(mdmitem):
        for mdmelem in mdmitem.Elements:
            if mdmelem.IsReference:
                # shared list - nothing to update
                pass
            elif mdmelem.Type==0: # 0==mdmlib.ElementTypeConstants.mtCategory
                # category
                yield mdmelem
            elif (mdmelem.Type==1) or (mdmelem.Type==13): # 1==mdmlib.ElementTypeConstants.mtCategoryList
                yield from iterate_over_categories(mdmelem)
            elif (mdmelem.Type==4097) or (re.match(r'^\s*?\d+\s*?$','{s}'.format(s=mdmelem.Name),flags=re.I|re.DOTALL)):
                yield mdmelem
                pass
            else:
                try:
                    yield from iterate_over_categories(mdmelem)
                except:
                    yield mdmelem
    # 1. update item label
    label_upd = sanitize_line_breaks(variable_record['label'])
    if label_upd:
        mdmitem.Label = label_upd
    for prop_name, prop_value in variable_record['properties'].items():
        prop_name_lower = prop_name.lower()
        if prop_name_lower == 'shortname' or prop_name_lower == 'fullname' or 'remove' in prop_name_lower:
            mdmitem.Properties[prop_name] = prop_value
    # 2. update labels for all categories
    try:
        potentially_has_categories_stkver = ( (mdmitem.ObjectTypeValue==0 and mdmitem.DataType==3) or ( mdmitem.ObjectTypeValue==1 or mdmitem.ObjectTypeValue==2 ) )
        has_categories_unstkver = 'categories' in variable_record and len(variable_record['categories'])>0
        if not(potentially_has_categories_stkver==has_categories_unstkver):
            warnings.warn('WARNING: updating labels: could not compare category list and update labels: {name} ({report_name})'.format(name=mdmitem.Name,report_name=variable_record['name']),RuntimeWarning)
        if potentially_has_categories_stkver and has_categories_unstkver:
            for mdmcat in iterate_over_categories(mdmitem):
                matching = [ cat for cat in variable_record['categories'] if sanitize_item_name(mdmcat.Name)==sanitize_item_name(cat['name']) ]
                if len(matching)>0:
                    label_upd = sanitize_line_breaks(matching[0]['label'])
                    if label_upd:
                        mdmcat.Label = label_upd
                    for prop_name, prop_value in matching[0]['properties'].items():
                        prop_name_lower = prop_name.lower()
                        # if prop_name_lower == 'value' or 'remove' in prop_name_lower:
                        if 'logic' in prop_name_lower or 'origin' in prop_name_lower:
                            # skip those
                            pass
                        else:
                            mdmcat.Properties[prop_name] = prop_value
                else:
                    warnings.warn('WARNING: updating labels: no matching category: {name}, variable name: {var_name} ({report_name})'.format(name=mdmcat.Name,var_name=mdmitem.Name,report_name=variable_record['name']),RuntimeWarning)
    except Exception as e:
        print('updating labels: Error: something happened when synchronizing category labels of  {name} ({report_name})'.format(name=mdmitem.Name,report_name=variable_record['name']),file=sys.stderr)
        print(e,file=sys.stderr) # make this non-critical, if something happened during updating labels... it's not an essential part
        pass
    # 3. update labels for all subfields
    try:
        has_subfields_stkver = ( ( mdmitem.ObjectTypeValue==1 or mdmitem.ObjectTypeValue==2 or mdmitem.ObjectTypeValue==3 ) ) and mdmitem.Fields.Count>0
        has_subfields_unstkver = 'subfields' in variable_record and len(variable_record['subfields'])>0
        if has_subfields_stkver and not has_subfields_unstkver:
            warnings.warn('WARNING: updating labels: could not compare subfields list and update labels: {name} ({report_name})'.format(name=mdmitem.Name,report_name=variable_record['name']),RuntimeWarning)
        if has_subfields_stkver and has_subfields_unstkver:
            for mdmfield in mdmitem.Fields:
                matching = [ item for item in variable_record['subfields'] if sanitize_item_name(mdmfield.Name)==sanitize_field_name(item['name']) ]
                if len(matching)>0:
                    subfield_variable_record = matching[0]
                    sync_labels_and_key_spss_properties_from_mddreport(mdmfield,subfield_variable_record)
                else:
                    warnings.warn('WARNING: updating labels: no matching subfield: {name}, variable name: {var_name} ({report_name})'.format(name=mdmfield.Name,var_name=mdmitem.Name,report_name=variable_record['name']),RuntimeWarning)
    except Exception as e:
        print('Error: updating labels: something happened when synchronizing subfield of  {name} ({report_name})'.format(name=mdmitem.Name,report_name=variable_record['name']),file=sys.stderr)
        print(e,file=sys.stderr) # make this non-critical, if something happened during updating labels... it's not an essential part
        pass
    return mdmitem

def create_mdmvariable_outerstkloop( loop_name, mdmcategories, mdmdoc ):
    result_scripts = CONFIG_METADATA_LOOP_OUTERSTKLOOP
    categories_scripts = ',\n'.join( mdmcat.Script for mdmcat in mdmcategories )
    result_scripts = result_scripts.replace('<<stk_loopname>>',loop_name)
    result_scripts = result_scripts.replace('<<CATEGORIES>>',categories_scripts)
    variable_attrs_dict = {
        'type': 'loop',
        'object_type_value': '1',
    }
    mdmvariable = create_mdmvariable(loop_name,result_scripts,variable_attrs_dict,mdmdoc,isgrid_retry_attempts=None)
    return mdmvariable

