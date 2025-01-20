import re



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








def normalize_line_breaks(s):
    return re.sub(r'(?:\r\n|\r|\n)','\n',s,flags=re.DOTALL)

def sanitize_item_name(item_name):
    return re.sub(r'\s*$','',re.sub(r'^\s*','',re.sub(r'\s*([\[\{\]\}\.])\s*',lambda m:'{m}'.format(m=m[1]),item_name,flags=re.I))).lower()

# def extract_field_name(item_name):
#     m = re.match(r'^\s*((?:\w.*?\.)?)(\w+)\s*$',item_name,flags=re.I)
#     if m:
#         return re.sub(r'\s*\.\s*$','',m[1]),m[2]
#     else:
#         raise ValueError('Can\'t extract field name from "{s}"'.format(s=item_name))

def remove_unnecessary_metadata_section_definition(script):
    script = script + '\n'
    script = re.sub(r'^\s*?(\s*?(?:\'[^\n]*?)?\n)*?\s*?Metadata\b\s*?(?:\([^\n]*?\))?\s*?(?:\'[^\n]*?)?\s*?\n','',script,flags=re.I|re.DOTALL)
    script = re.sub(r'\n\s*?End\b\s*?\bMetadata\b\s*?(?:\'[^\n]*?)?\s*?\n(\s*?(?:\'[^\n]*?)?\n)*$','\n',script,flags=re.I|re.DOTALL)
    return script



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



class MDMItemNotFound(Exception):
    """MDM item not found"""
def find_item(path,mdmitem):
    def extract_top_field_name(item_name):
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
        def trim_dots(s):
            return re.sub(r'^\s*?\.','',re.sub(r'\.\s*?$','',s))
        item_name_clean = norm(item_name)
        m = re.match(r'^\s*(\w+)((?:(?:\.\w+)*)?)\s*$',item_name_clean,flags=re.I)
        if m:
            return trim_dots(m[1]), trim_dots(m[2])
        else:
            raise ValueError('Can\'t extract field name from "{s}"'.format(s=item_name))
    if path=='':
        return mdmitem
    path_root, path_rest = extract_top_field_name(path)
    if mdmitem.Fields.Exist(path_root):
        result = mdmitem.Fields[path_root]
        if path_rest:
            return find_item(path_rest,result)
        else:
            return result
    else:
        raise MDMItemNotFound('Item not found: {s}'.format(s=path))





def generate_scripts(mdd_data,patch,config):
    
    def print_log_processing(item):
        print('processing metadata for {item}...'.format(item=item))

    result = ''

    mdmroot = win32com.client.Dispatch("MDM.Document")
    mdmroot.IncludeSystemVariables = False
    mdmroot.Contexts.Base = "Analysis"
    mdmroot.Contexts.Current = "Analysis"
    mdmroot.Script = '{opening_part}{mdata}{closing_part}'.format(opening_part='Metadata(en-us, question, label)\n',closing_part='\nEnd Metadata',mdata='')

    mdd_data = [ field for field in mdd_data if detect_item_type_from_mdddata_fields_report(field['name'])=='variable' or field['name']=='' ]

    mdmref = win32com.client.Dispatch("MDM.Document")
    mdmref.IncludeSystemVariables = False
    mdmref.Contexts.Base = "Analysis"
    mdmref.Contexts.Current = "Analysis"
    mdmref.Script = [f for f in mdd_data if f['name']==''][0]['scripting']

    # warning: we are making updates to mdmroot
    # not a clear function
    def patch_process_update_metadata(chunk):
        action = chunk['action']
        if action=='variable-new':
            if 'new_metadata' in chunk and chunk['new_metadata']:
                print_log_processing('{path}.{field_name}'.format(path=chunk['position'],field_name=chunk['variable']))
                # add code
                try:
                    mdmparent = find_item(chunk['position'],mdmroot)
                except MDMItemNotFound as e:
                    # we should not be doing it here
                    # this code belon
                    # # hm, item does not exist
                    # # maybe because we forgot to bring its parent, we did not do it
                    # # let's check that it has parent
                    # # and try to create one
                    # # and try to find this item again
                    # if '.' in chunk['position']:
                    #     mdmitemcandidate = 
                    # else:
                    #     raise e
                    raise e
                detect_type = None
                variable_is_plain = False
                variable_is_categorical = False
                variable_is_loop = False
                variable_is_grid = False
                variable_is_block = False
                for attr_name, attr_value in chunk['attributes'].items():
                    if attr_name=='type':
                        variable_is_plain = variable_is_plain or not not re.match(r'^\s*?plain\b',attr_value)
                        variable_is_categorical = variable_is_categorical or not not re.match(r'^\s*?plain/(?:categorical|multipunch|singlepunch)',attr_value)
                        variable_is_loop = variable_is_loop or not not re.match(r'^\s*?(?:array|grid|loop)\b',attr_value)
                        variable_is_block = variable_is_block or not not re.match(r'^\s*?(?:block)\b',attr_value)
                    if attr_name=='is_grid':
                        variable_is_grid = variable_is_grid or not not re.match(r'^\s*?true\b',attr_value)
                if variable_is_plain or variable_is_categorical:
                    detect_type = 'plain'
                elif variable_is_loop:
                    detect_type = 'loop'
                elif variable_is_block:
                    detect_type = 'block'
                mdmitem_add = None
                if detect_type == 'plain':
                    mdmitem_add = mdmroot.CreateVariable(chunk['variable'], chunk['variable'])
                elif detect_type == 'loop':
                    if variable_is_grid:
                        mdmitem_add = mdmroot.CreateGrid(chunk['variable'], chunk['variable'])
                    else:
                        mdmitem_add = mdmroot.CreateArray(chunk['variable'], chunk['variable'])
                elif detect_type == 'block':
                    mdmitem_add = mdmroot.CreateClass(chunk['variable'], chunk['variable'])
                elif not detect_type:
                    raise ValueError('Cat\'t create object: unrecognized type')
                else:
                    raise ValueError('Can\'t handle this type of bject: {s}'.format(s=detect_type))
                if not detect_type:
                    raise ValueError('Failed to create variable, please check all data in the patch specs')
                for attr_name, attr_value in chunk['attributes'].items():
                    # if attr_name=='object_type_value':
                    #     mdmitem_add.ObjectTypeValue = attr_value
                    if attr_name=='data_type':
                        mdmitem_add.DataType = attr_value
                    elif attr_name=='Label':
                        mdmitem_add.Label = attr_value if attr_value else ''
                    else:
                        pass
                mdmitem_add.Script = chunk['new_metadata']
                mdmparent.Fields.Add(mdmitem_add)

        elif action=='section-insert-lines':
            pass
        else:
            raise ValueError('Patch: action = "{s}": not implemented'.format(s=action))

    for chunk in patch:
        try:
            patch_process_update_metadata(chunk)
        except Exception as e:
            try:
                print('Failed when processing action == {action}, variable == {var}, position == {position}'.format(action=action,var=chunk['variable'],position=chunk['position']))
            except:
                pass
            try:
                print('For reference, metadata is the following: "{s}"'.format(s=chunk['new_metadata']))
            except:
                pass
            raise e

    result = mdmroot.Script
    result = normalize_line_breaks(result) # metadata generation from IBM tools prints \r\n in metadata, it causes an extra empty line everywhere
    result = remove_unnecessary_metadata_section_definition(result)
    
    return result

