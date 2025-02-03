
import re




if __name__ == '__main__':
    # run as a program
    import processor_simple_insert
elif '.' in __name__:
    # package
    from . import processor_simple_insert
else:
    # included with no parent package
    import processor_simple_insert




def sanitize_section_name(s):
    assert re.match(r'^\s*?\w+\s*?$',section_name,flags=re.I|re.DOTALL), 'PatchSectionOther: section name must be alphanumeric, no spaces ("{s}")'.format(s=section_name)
    s = re.sub(r'^\s*','',re.sub(r'\s*$','',s,flags=re.I|re.DOTALL),flags=re.I|re.DOTALL)
    s = s.lower()
    return s




class PatchSectionOtherInsertException(processor_simple_insert.PatchInsertException):
    """Error"""

class PatchSectionOtherInsert(processor_simple_insert.PatchInsert):

    handled_action = 'section/other/insert'

    def __init__(self,txt):
        # self.txt = txt
        super().__init__(txt)

        self.config = {} # not used, as of now

        self.sections_dict = {}
        regex = re.compile(r'((?:^|\n)\s*?event\s*?\(\s*?'+r'(\w+)'+r'\b[^\n]*?\s*?\)\s*?(?:\'[^\n]*?)?\s*?\n)((?:[^\n]*?\n)*?)(\s*?end\b\s*?\bevent\b)',flags=re.I|re.DOTALL)
        find_regex_results = re.finditer(regex,txt)
        if find_regex_results:
            find_regex_results =  [m for m in find_regex_results] # so that I can refer to multiple items of a generator multiple times
        for section_pattern in find_regex_results:
            if section_pattern:
                section_pattern = find_regex_results[0]
                section_span = {
                    'opening_clause': section_pattern.span(1),
                    'name': section_pattern.span(2),
                    'body': section_pattern.span(3),
                    'closing_clause': section_pattern.span(4),
                }
                # comment
                # we should ony modify middle part
                # opening clause and closing clause should stay untouched
                section_name = txt[ section_span['name'][0] : section_span['name'][1] ]
                section_name_clean = sanitize_section_name(section_name) # section_name.lower() - that's the same
                self.sections_dict[section_name_clean] = {
                    'name': section_name,
                    'section_span': section_span,
                }

    def __call__(self, chunk):
        
        def what_to_add(chunk):
            txt = None
            if isinstance(chunk['payload'],dict):
                txt = chunk['payload']['lines']
            else:
                txt = chunk['payload']
            txt = '{t}'.format(t=txt) # ensure it's text
            return txt

        def where_to_add(chunk,txt):
            pos = None
            if isinstance(chunk['position'],list):
                for attempt in chunk['position']:
                    pos = processor_simple_insert.find_position(attempt,txt)
                    if pos is not None:
                        break
            else:
                pos = processor_simple_insert.find_position(chunk['position'],txt)
            return pos
        
        txt_add = what_to_add(chunk)

        section_name = sanitize_section_name(chunk['section'])
        if section_name not in self.sections_dict:
            raise PatchSectionOtherInsertException('section "{s}" not found'.format(s=chunk['section']))
        section = self.sections_dict[section_name]
        section_txt = self.txt[ section['section_span']['body'][0] : section['section_span']['body'][1] ]

        pos_relative = where_to_add(chunk,section_txt)

        pos_abs = section['section_span']['body'][0] + pos_relative

        yield { 'op': 'add', 'text': txt_add, 'pos': pos_abs }