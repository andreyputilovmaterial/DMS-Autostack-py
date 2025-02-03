import re
import sys



# import pythoncom
import win32com.client



if __name__ == '__main__':
    # run as a program
    import processor_metadata_util_fns
elif '.' in __name__:
    # package
    from . import processor_metadata_util_fns
else:
    # included with no parent package
    import processor_metadata_util_fns







class PatchSectionMetadataInsertException(Exception):
    """Error"""

class PatchSectionMetadataInsert:

    handled_action = 'section/metadata/insert'

    def __init__(self,txt):
        try:
            self.txt = txt
            self.config = {}
            self.section_span = None
            self.mdmroot = None
            self.chunks_emitted = []
            find_regex_results = re.finditer(re.compile(r'((?:^|\n)\s*?metadata\s*?(?:\([^\n]*?\))?\s*?(?:\'[^\n]*?)?\s*?\n)((?:[^\n]*?\n)*?)(\s*?end\b\s*?\bmetadata\b)',flags=re.I|re.DOTALL),txt)
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
                # we use all three parts (including opening clause and closing) when creating mdm root item and working with object model
                # but we only replace the middle part in the output file, we keep that "opening clause" and 'closing clause" untouched
                mdata = '{opening_part}{body_part}{closing_part}'.format(
                    opening_part = txt[ self.section_span['opening_clause'][0] : self.section_span['opening_clause'][1] ],
                    body_part = txt[ self.section_span['body'][0] : self.section_span['body'][1] ],
                    closing_part = txt[ self.section_span['closing_clause'][0] : self.section_span['closing_clause'][1] ],
                )
                try:
                    mdmroot = win32com.client.Dispatch("MDM.Document")
                    mdmroot.IncludeSystemVariables = False
                    mdmroot.Contexts.Base = "Analysis"
                    mdmroot.Contexts.Current = "Analysis"
                    mdmroot.Script = mdata
                    self.mdmroot = mdmroot
                except Exception as e:
                    print('for debugging purposes, metadata section scripts are:\n\n{m}\n\n'.format(m=mdata), file=sys.stderr)
                    raise PatchSectionMetadataInsertException('failed to create mdm root object: {e}'.format(e=e)) from e
        except Exception as e:
            raise PatchSectionMetadataInsertException('failed to init PatchSectionMetadataInsert processor: {e}'.format(e=e)) from e

    def __call__(self, edit):
        self.process_edit(edit)
        for piece in self.issue_resulting_chunk():
            yield piece
    
    def process_edit(self, patch):
        def print_log_processing(item):
            print('processing metadata item "{item}"...'.format(item=item))
        if not self.section_span:
            raise PatchSectionMetadataInsertException('can\'t apply patch on metadata, metadata section was not found')
        if not self.mdmroot:
            raise PatchSectionMetadataInsertException('can\'t apply patch on metadata, mdmroot element was not inited')
        try:
            position = '{pos}'.format(pos=ParsePositionAddressOnly(patch['position']))
            variable_name = patch['payload']['variable']
            mdata = patch['payload']['metadata']
            attributes = patch['payload']['attributes']
            print_log_processing('{path}.{field_name}'.format(path=position,field_name=variable_name))
            self.mdmroot = processor_metadata_util_fns.update_metadata(self.mdmroot,position,variable_name,mdata,attributes)
        except Exception as e:
            try:
                print('Failed when processing action == {action}, variable == {var}, position == {position}'.format(action=self.action,var=patch['variable'],position=patch['position']), file=sys.stderr)
            except:
                pass
            try:
                print('For debugging purposes, metadata is the following: "{s}"'.format(s=mdata), file=sys.stderr)
            except:
                pass
            raise e

        # return mdmroot

    def issue_resulting_chunk(self):
        def normalize_line_breaks(s):
            return re.sub(r'(?:\r\n|\r|\n)','\n',s,flags=re.DOTALL)
        def remove_unnecessary_metadata_section_definition(script):
            script = script + '\n'
            script = re.sub(r'^\s*?(\s*?(?:\'[^\n]*?)?\n)*?\s*?Metadata\b\s*?(?:\([^\n]*?\))?\s*?(?:\'[^\n]*?)?\s*?\n','',script,flags=re.I|re.DOTALL)
            script = re.sub(r'\n\s*?End\b\s*?\bMetadata\b\s*?(?:\'[^\n]*?)?\s*?\n(\s*?(?:\'[^\n]*?)?\n)*$','\n',script,flags=re.I|re.DOTALL)
            return script
        txt = self.mdmroot.Script
        txt = normalize_line_breaks(txt) # metadata generation from IBM tools prints \r\n in metadata, it causes an extra empty line everywhere
        txt = remove_unnecessary_metadata_section_definition(txt)
        chunk_last_del = { 'op': 'remove', 'del': self.section_span['body'][1]-self.section_span['body'][0], 'pos': self.section_span['opening_clause'][1] }
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
        yield chunk_last_del
        yield chunk_last_add
        self.chunks_emitted.append(chunk_last_del)
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
