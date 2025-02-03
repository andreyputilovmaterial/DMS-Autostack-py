
import sys
import re








if __name__ == '__main__':
    # run as a program
    import processor_onnextcase_code_obj
elif '.' in __name__:
    # package
    from . import processor_onnextcase_code_obj
else:
    # included with no parent package
    import processor_onnextcase_code_obj





class PatchSectionOnNextCaseInsertException(Exception):
    """Error"""

class PatchSectionOnNextCaseInsert:

    handled_action = 'section/onnextcase/insert'

    def __init__(self,txt):
        try:
            self.txt = txt
            self.config = {}
            self.section_span = None
            code_node_root = None
            self.result_chunks_dict = {}
            self.chunks_emitted = []
            find_regex_results = re.finditer(re.compile(r'((?:^|\n)\s*?event\s*?\(\s*?'+r'OnNextCase'+r'\b[^\n]*?\s*?\)\s*?(?:\'[^\n]*?)?\s*?\n)((?:[^\n]*?\n)*?)(\s*?end\b\s*?\bevent\b)',flags=re.I|re.DOTALL),txt)
            if find_regex_results:
                 find_regex_results =  [m for m in find_regex_results] # so that I can refer to multiple items of a generator multiple times
            if find_regex_results and len(find_regex_results)>0:
                find_regex_result = find_regex_results[0]
                self.section_span = {
                    'opening_clause': find_regex_result.span(1),
                    'body': find_regex_result.span(2),
                    'closing_clause': find_regex_result.span(3),
                }
                # comment
                # we use all three parts (including opening clause and closing) when parsing existing codes
                # but we only replace the middle part in the output file, we keep that "opening clause" and 'closing clause" untouched
                scripts_outer = '{opening_part}{body_part}{closing_part}'.format(
                    opening_part = txt[ self.section_span['opening_clause'][0] : self.section_span['opening_clause'][1] ],
                    body_part = txt[ self.section_span['body'][0] : self.section_span['body'][1] ],
                    closing_part = txt[ self.section_span['closing_clause'][0] : self.section_span['closing_clause'][1] ],
                )
                scripts_inner = '{opening_part}{body_part}{closing_part}'.format(
                    opening_part = '',
                    body_part = txt[ self.section_span['body'][0] : self.section_span['body'][1] ],
                    closing_part = '',
                )
                try:
                    root_chunk_substitions = {
                        'variable_lvalue_path': '',
                        'variable_rvalue_path': ''
                    }
                    root_chunk_scripts = '\n\' {@}\n\n'
                    code_node_root = processor_onnextcase_code_obj.CodeNode(root_chunk_scripts,root_chunk_substitions)
                    self.result_chunks_dict[''] = code_node_root
                except Exception as e:
                    print('for debugging purposes, scripts are:\n\n{m}\n\n'.format(m=scripts_inner), file=sys.stderr)
                    raise PatchSectionOnNextCaseInsertException('failed to create root Code object: {e}'.format(e=e)) from e
        except Exception as e:
            raise PatchSectionOnNextCaseInsertException('failed to init PatchSectionOnnextcaseInsert processor: {e}'.format(e=e)) from e

    def __call__(self, edit):
        self.process_edit(edit)
        for piece in self.issue_resulting_chunk():
            yield piece

    def process_edit(self, patch):

        def print_log_processing(item):
            print('processing onnextcase item "{item}"...'.format(item=item))
        
        print_log_processing(patch['payload']['variable'])
        
        variable_name = patch['payload']['variable']
        parent_position = '{pos}'.format(pos=ParsePositionAddressOnly(patch['position']))
        variable_position = '{path}{subfield}'.format(subfield=variable_name,path='{path}.'.format(path=parent_position) if parent_position else '')
        code_to_add = patch['payload']['lines']['code']
        code_to_add_substitutions = patch['payload']['lines']

        result_chunk = processor_onnextcase_code_obj.CodeNode(code_to_add,code_to_add_substitutions)

        if parent_position in self.result_chunks_dict:
            parent = self.result_chunks_dict[parent_position]
            parent.add(result_chunk)
            self.result_chunks_dict[variable_position] = result_chunk
        else:
            raise ValueError('Error generating edits: item not found: {p}'.format(p=parent_position))

    def issue_resulting_chunk(self):
        substitutions = {
            'variable_lvalue_path': '',
            'variable_rvalue_path': '',
        }
        txt = self.result_chunks_dict[''].render(substitutions)
        # chunk_last_del = { 'op': 'remove', 'del': self.section_span['body'][1]-self.section_span['body'][0], 'pos': self.section_span['opening_clause'][1] }
        chunk_last_add = { 'op': 'add', 'text': txt, 'pos': self.section_span['closing_clause'][0] }
        # we reset all previously emitted
        # so that they don't overlap
        # and we incorporate all changes in the last, newly emitted, chunk
        # I know, poor very poor design
        for chunk_flush in self.chunks_emitted:
            for key in [k for k in chunk_flush.keys()]:
                if key not in ['op','pos']:
                    del chunk_flush[key]
            chunk_flush['op'] = 'dummy'
            chunk_flush['pos'] = None
        # yield chunk_last_del
        yield chunk_last_add
        # self.chunks_emitted.append(chunk_last_del)
        self.chunks_emitted.append(chunk_last_add)



class ParsePositionAddressOnly:
    def __init__(self,position):
        self.position = None
        if isinstance(position,list):
            failed = None
            for attempt in position:
                try:
                    self.__init__(attempt)
                    failed = None
                    break
                except Exception as e:
                    failed = e
            if failed:
                raise e
        elif isinstance(position,str):
            self.position = position
        elif not position:
            self.position = ''
        elif isinstance(position,dict) and 'type' in position and position['type']=='address':
            self.position = position['position']
        else:
            raise Exception('wrong position format for the chunk: "{p}"'.format(p=position))
    def __str__(self):
        return '{s}'.format(s=self.position)



