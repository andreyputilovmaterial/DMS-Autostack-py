# import os, time, re, sys
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





def normalize_line_breaks(s):
    return re.sub(r'(?:\r\n|\r|\n)','\n',s,flags=re.DOTALL)

def sanitize_item_name(item_name):
    return re.sub(r'\s*$','',re.sub(r'^\s*','',re.sub(r'\s*([\[\{\]\}\.])\s*',lambda m:'{m}'.format(m=m[1]),item_name,flags=re.I))).lower()

def extract_field_name(item_name):
    m = re.match(r'^\s*((?:\w.*?\.)?)(\w+)\s*$',item_name,flags=re.I)
    if m:
        return re.sub(r'\s*\.\s*$','',m[1]),m[2]
    else:
        raise ValueError('Can\'t extract field name from "{s}"'.format(s=item_name))

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







def patch_generate_scripts_mdata(mdd_data,patch,config):
    
    result = ''
    t = datetime.now()

    mdmroot = win32com.client.Dispatch("MDM.Document")
    mdmroot.IncludeSystemVariables = False
    mdmroot.Contexts.Base = "Analysis"
    mdmroot.Contexts.Current = "Analysis"
    mdmroot.Script = '{opening_part}{mdata}{closing_part}'.format(opening_part='Metadata(en-us, question, label)\n',closing_part='\nEnd Metadata',mdata='')

    mdd_data = [ field for field in mdd_data if detect_item_type_from_mdddata_fields_report(field['name'])=='variable' or field['name']=='' ]
    # def check_if_variable_exists(item_name):
    #     return check_if_variable_exists_based_on_mdd_read_records(mdd_data,item_name)

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
            for attr_name, attr_value in chunk['new_attributes'].items():
                if attr_name=='MDMRead_type':
                    variable_is_plain = variable_is_plain or re.match(r'^\s*?plain\b',attr_value)
                    variable_is_categorical = variable_is_categorical or re.match(r'^\s*?plain/(?:categorical|multipunch|singlepunch)',attr_value)
                    variable_is_loop = variable_is_loop or re.match(r'^\s*?(?:array|grid|loop)\b',attr_value)
                    variable_is_block = variable_is_block or re.match(r'^\s*?(?:block)\b',attr_value)
                if attr_name=='MDMRead_is_grid':
                    variable_is_grid = variable_is_grid or re.match(r'^\s*?true\b',attr_value)
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
            for attr_name, attr_value in chunk['new_attributes'].items():
                # if attr_name=='ObjectTypeValue':
                #     mdmitem_add.ObjectTypeValue = attr_value
                if attr_name=='DataType':
                    mdmitem_add.DataType = attr_value
                elif attr_name=='Label':
                    mdmitem_add.Label = attr_value if attr_value else ''
                else:
                    pass
            mdmitem_add.Script = chunk['new_metadata']
            mdmparent.Fields.Add(mdmitem_add)

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
    
    return result

def patch_generate_scripts_edits(mdd_data,patch,config):
    
    result = ''
    t = datetime.now()

    mdd_data = [ field for field in mdd_data if detect_item_type_from_mdddata_fields_report(field['name'])=='variable' ]
    def check_if_variable_exists(item_name):
        return check_if_variable_exists_based_on_mdd_read_records(mdd_data,item_name)
    
    for chunk in patch:
        try:
            action = chunk['action']
            if action=='variable-new':
                result = '{old_code}{linebreak}{added_code}'.format(old_code=result,linebreak='\n',added_code=chunk['new_edits'])
            else:
                raise ValueError('Patch: action = "{s}": not implemented'.format(s=action))
        except Exception as e:
            try:
                print('Failed when processing {{ {action}, {var}, {position} }}'.format(action=action,var=chunk['variable'],position=chunk['position']))
            except:
                pass
            raise e

    result = normalize_line_breaks(result) # metadata generation from IBM tools prints \r\n in metadata, it causes an extra empty line everywhere
    
    return result



def entry_point(runscript_config={}):

    time_start = datetime.now()
    script_name = 'mdmautostktoolsap mdd patch script'

    parser = argparse.ArgumentParser(
        description="MDD: produce patches and/or scripts from patches",
        prog='mdd-patch'
    )
    parser.add_argument(
        '-1',
        '--inp-mdd-scheme',
        type=str,
        help='JSON with fields data from MDD Input File',
        required=True
    )
    parser.add_argument(
        '--action',
        help='Param to pass patch type: there are special types for stacking, etc...',
        type=str,
        required=False
    )
    parser.add_argument(
        '--patch',
        help='Provide specs',
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

    action = None
    if args.action:
        if args.action=='generate-for-stk':
            action = 'generate-for-stk'
        elif args.action=='generate-scripts-metadata':
            action = 'generate-scripts-metadata'
        elif args.action=='generate-scripts-edits':
            action = 'generate-scripts-edits'
        elif args.action=='generate-scripts':
            raise TypeError('MDD patch script: general "generate-scripts" action is not supported, please use "generate-scripts-metadata" or "generate-scripts-edits"')
        else:
            raise TypeError('MDD patch script: this action is not implemented yet: "{a}"'.format(a=args.action))

    patch_specs = None
    patch_specs_file_name = None
    if args.patch:
        patch_specs_file_name = Path(args.patch)
        patch_specs_file_name = '{f}'.format(f=patch_specs_file_name.resolve())
        if not(Path(patch_specs_file_name).is_file()):
            raise FileNotFoundError('file not found: {fname}'.format(fname=patch_specs_file_name))
        with open(patch_specs_file_name) as f_l:
                try:
                    patch_specs = json.load(f_l)
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

    mdd_data = []
    try:
        mdd_data = ([sect for sect in inp_mdd_scheme['sections'] if sect['name']=='fields'])[0]['content']
    except:
        pass

    result = None
    if action=='generate-for-stk':
        raise Exception('generating patch for stk is not implemented here, please call a different script')
    elif action=='generate-scripts-metadata':
        result = patch_generate_scripts_mdata(mdd_data,patch_specs,config)
    elif action=='generate-scripts-edits':
        result = patch_generate_scripts_edits(mdd_data,patch_specs,config)
    elif action=='generate-scripts':
            raise TypeError('MDD patch script: general "generate-scripts" action is not supported, please use "generate-scripts-metadata" or "generate-scripts-edits"')
    else:
        raise TypeError('MDD patch script: this action is not implemented yet: "{a}"'.format(a=action))
    
    # result_json = json.dumps(result, indent=4)

    print('{script_name}: saving as "{fname}"'.format(fname=result_final_fname,script_name=script_name))
    with open(result_final_fname, "w",encoding='utf-8') as outfile:
        outfile.write(result)

    time_finish = datetime.now()
    print('{script_name}: finished at {dt} (elapsed {duration})'.format(dt=time_finish,duration=time_finish-time_start,script_name=script_name))



if __name__ == '__main__':
    entry_point({'arglist_strict':True})
