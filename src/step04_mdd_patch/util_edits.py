import re



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
            # maybe having this fn is not totally right
            # python offers everything to work with regexs, and I am developing a different hack to work with regexs differently...
            # anyway, workling like this is easier for me
            # I am not just doing replacements, that might work, or might not work
            # I am finding exact position of found sequence and doing string concatenation
            find_regex_results = re.finditer(regex,text,flags=re_flags)
            if not find_regex_results:
                raise ValueError('searching for pattern failed')
            return [m for m in find_regex_results][0].span(captured_group_num)
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
                part_subfields = newlines_between_items*CONFIG_NUMLINEBREAKS_AROUND+(newlines_between_items*CONFIG_NUMLINEBREAKS_INBETWEEN).join([ trim_lines('{subfield_code}'.format(subfield_code=trim_lines(add_indent(subfield.render(self._substitutions_for_childer),indent)))) for subfield in self._children ])+newlines_between_items*CONFIG_NUMLINEBREAKS_AROUND,
            )
        else:
            return re.sub(r'(?:^|\n)(\s*?)(\'\s*\{@\})\s*?\n','',code_to_add,flags=re.I|re.DOTALL)



def generate_scripts(mdd_data,patch,config):

    def print_log_processing(item):
        print('processing onnextcase scripts for {item}...'.format(item=item))

    
    result_chunks_dict = {}
    result_root_chunk_substitions = {'variable_stk_path':'','variable_unstacked_path':''}
    result_root_chunk = Code('\n\' {@}\n\n',result_root_chunk_substitions)
    result_chunks_dict[''] = result_root_chunk

    mdd_data = [ field for field in mdd_data if detect_item_type_from_mdddata_fields_report(field['name'])=='variable' ]
    
    for chunk in patch:
        try:
            action = chunk['action']
            if action=='variable-new':
                if 'new_edits' in chunk and chunk['new_edits']:
                    print_log_processing('{path}.{field_name}'.format(path=chunk['position'],field_name=chunk['variable']))
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
            elif action=='section-insert-lines':
                pass
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



