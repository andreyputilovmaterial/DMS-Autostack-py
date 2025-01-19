# import os, time, re, sys
import code
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




CONFIG_NUMLINEBREAKS_INBETWEEN = 2
CONFIG_NUMLINEBREAKS_AROUND = 1




def find_code_position_marker(path):
    return '\' #mdmautostkap-code-marker: ({path})'.format(path=path)



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
            for attr_name, attr_value in chunk['attributes'].items():
                if attr_name=='MDMRead_type':
                    variable_is_plain = variable_is_plain or not not re.match(r'^\s*?plain\b',attr_value)
                    variable_is_categorical = variable_is_categorical or not not re.match(r'^\s*?plain/(?:categorical|multipunch|singlepunch)',attr_value)
                    variable_is_loop = variable_is_loop or not not re.match(r'^\s*?(?:array|grid|loop)\b',attr_value)
                    variable_is_block = variable_is_block or not not re.match(r'^\s*?(?:block)\b',attr_value)
                if attr_name=='MDMRead_is_grid':
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
    result = remove_unnecessary_metadata_section_definition(result)
    
    return result

def patch_generate_scripts_edits(mdd_data,patch,config):

    class Code:
        def __init__(self,scripts,substitutions_for_childer):
            self._scripts = scripts
            self._substitutions_for_childer = substitutions_for_childer
            self._children = []
        
        def add(self,nested):
            self._children.append(nested)
        
        # def __str__(self):
        # we can't use __str__ because we need some parameters passed from parent level
        def render(self,substitutions):
            # actually, rendering
            # the most interesting part goes here
            def find_regex_span(regex,text,captured_group_num=0,re_flags=re.I|re.DOTALL):
                find_regex_results = re.finditer(regex,text,flags=re_flags)
                if not find_regex_results:
                    raise ValueError('searching for pattern failed')
                return [m for m in find_regex_results][0].span(captured_group_num)
            def trim_lines(s):
                s = re.sub(r'^(?:\s*?\n)*','',s,flags=re.DOTALL)
                s = re.sub(r'(?:\s*?\n)*$','',s,flags=re.DOTALL)
                s = re.sub(r'\n?$','',s,flags=re.DOTALL)
                return s + '\n'
            def add_indent(s,indent):
                s = '\n'+re.sub(r'\n?$','',s) # I am adding a line break at the beginning to make wotking with regexs easier
                s = re.sub(r'(\n)',lambda m: '{k}{i}'.format(i=indent,k=m[1]),s)
                return s[1:] # remove line break at the beginning that we added

            code_to_add = self._scripts
            code_to_add = code_to_add.replace('<<STK_VARIABLE_PATH>>',substitutions['variable_stk_path']).replace('<<UNSTK_VARIABLE_PATH>>',substitutions['variable_unstacked_path'])
            if len(self._children)>0:
                code_to_add = trim_lines(code_to_add)
                nested_code_marker_span = find_regex_span(r'(?:^|\n)([^\S\r\n]*?)(\'\s*\{@\})\s*?\n',code_to_add)
                code_to_add_part_leading = code_to_add[:nested_code_marker_span[0]]
                code_to_add_part_trailing = code_to_add[nested_code_marker_span[1]:]
                code_to_add_marker = re.sub(r'^\n','',code_to_add[nested_code_marker_span[0]:nested_code_marker_span[1]])
                indent_span = find_regex_span(r'^(\s*)\'',code_to_add_marker,captured_group_num=1)
                indent = code_to_add_marker[indent_span[0]:indent_span[1]]
                assert not '\n' in indent
                newlines_between_items = '{s}{n}'.format(s=indent,n='\n')
                return '{part_begin}{part_subfields}{part_end}'.format(
                    part_begin = trim_lines(code_to_add_part_leading),
                    part_end = trim_lines(code_to_add_part_trailing),
                    part_subfields = newlines_between_items*CONFIG_NUMLINEBREAKS_AROUND+(newlines_between_items*CONFIG_NUMLINEBREAKS_INBETWEEN).join([ '{subfield_code}'.format(subfield_code=trim_lines(add_indent(subfield.render(self._substitutions_for_childer),indent))) for subfield in self._children ])+newlines_between_items*CONFIG_NUMLINEBREAKS_AROUND,
                )
            else:
                return re.sub(r'(?:^|\n)(\s*?)(\'\s*\{@\})\s*?\n','',code_to_add,flags=re.I|re.DOTALL)

            # position_marker = ' {@}'
            # marker_nested_code = chunk['new_edits_nestedcode_position'] if 'new_edits_nestedcode_position' in chunk else '\' #mdmautostkap-code-marker: '
            # # prepare place where it is added
            # position = len(result)-1
            # if position_marker in result:
            #     position = result.index(position_marker)
            #     position = [m for m in re.finditer(r'[^\S\r\n]*$',result[:position],flags=re.DOTALL)][0].span(0)[0]
            # result_leadingpart = result[:position]
            # result_trailingpart = result[position:]
            # # prepare and format that code_to_add
            # indents = [m for m in re.finditer(r'^([^\S\r\n]*).*?$',result_trailingpart,flags=re.DOTALL)][0].span(1)
            # indents = result_trailingpart[indents[0]:indents[1]]
            # code_to_add = '\n'+re.sub(r'\n$','',code_to_add)
            # code_to_add = re.sub(r'\n','\n'+indents,code_to_add)
            # code_to_add = code_to_add.replace('<<PATH>>',prefix)
            # code_to_add = code_to_add[1:] + '\n'
            # if marker_nested_code in code_to_add:
            #     code_to_add = code_to_add.replace(marker_nested_code,marker_nested_code+'({fullpath})'.format(fullpath='{path}{item}'.format(item=chunk['variable'],path='.{p}'.format(p=path) if path else '')))
            # result = result_leadingpart + code_to_add + result_trailingpart
            # # result = '{old_code}{linebreak}{added_code}'.format(old_code=result,linebreak='\n',added_code=chunk['new_edits'])
    
    result_chunks_dict = {}
    result_root_chunk_substitions = {'variable_stk_path':'','variable_unstacked_path':''}
    result_root_chunk = Code('\n\' {@}\n\n',result_root_chunk_substitions)
    result_chunks_dict[''] = result_root_chunk
    # t = datetime.now()

    mdd_data = [ field for field in mdd_data if detect_item_type_from_mdddata_fields_report(field['name'])=='variable' ]
    # def check_if_variable_exists(item_name):
    #     return check_if_variable_exists_based_on_mdd_read_records(mdd_data,item_name)
    
    for chunk in patch:
        try:
            action = chunk['action']
            if action=='variable-new':
                variable_position = '{path}{subfield}'.format(subfield=chunk['variable'],path='{path}.'.format(path=chunk['position']) if chunk['position'] else '')
                parent_position = chunk['position']
                code_to_add = chunk['new_edits']['code']
                code_to_add_substitutions = chunk['new_edits']
                result_chunk = Code(code_to_add,code_to_add_substitutions)
                if parent_position in result_chunks_dict:
                    parent = result_chunks_dict[parent_position]
                    parent.add(result_chunk)
                    result_chunks_dict[variable_position] = result_chunk
                else:
                    raise ValueError('Error generating edits: item not found: {p}'.format(p=parent_position))
            else:
                raise ValueError('Patch: action = "{s}": not implemented'.format(s=action))
        except Exception as e:
            try:
                print('Failed when processing {{ {action}, {var}, {position} }}'.format(action=action,var=chunk['variable'],position=chunk['position']))
            except:
                pass
            raise e

    # render result_chunks_dict!
    # result_chunks_dict = '{r}'.format(r=result_chunks_dict)
    result = '{r}'.format(r=result_root_chunk.render(result_root_chunk_substitions))
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
