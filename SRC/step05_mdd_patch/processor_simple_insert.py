

import re





def find_position(pattern,txt):
    if isinstance(pattern,int):
        return pattern
    elif isinstance(pattern,re.Pattern): # this is literally not possible, because we are reading data from json, and re.Pattern can\'t be sent through json
        find_regex_results = re.finditer(pattern,txt)
        if not find_regex_results:
            return None
        captured_group_num = 1
        # we expect that pattern includes 2 gropus, and we add something in between
        # even if something is not captured in between those 2 groups, we don't delete it
        # so this is kind of extraneous
        # but this syntax makes it clear, we are adding after the first group before the second one, so that it's not confusing if we are adding before or after the regex
        # and, to re-iterate on this, we are only adding, we are not replacing/modyfying it somehow with a regex
        _, pos = [m for m in find_regex_results][0].span(captured_group_num)
        return pos
    elif not pattern:
        return 0
    elif isinstance(pattern,dict):
        assert 'type' in pattern, 'trying to find a position in text, and the position is specified as dict but position[type] is missing'
        pattern_type = pattern['type']
        if pattern_type=='custom':
            return find_position(pattern['payload'],txt)
        elif pattern_type=='none':
            return find_position(None,txt)
        elif pattern_type=='address':
            raise Exception('trying to find a position in text, and the position is specified as text: we can\'t do that (for reference, position is "{t}")'.format(t=pattern))
        elif pattern_type=='position':
            return find_position(pattern['position'],txt)
        elif pattern_type=='re':
            pattern_re=re.compile(pattern['pattern'],flags=pattern['flags'] if 'flags' in pattern else None)
            return find_position(pattern_re,txt)
        else:
            raise Exception('trying to find a position in text, and the position is specified as dict but not of any recognized format: we can\'t do that (for reference, position[type] is "{t}")'.format(t=pattern['type']))
    else:
        raise PatchInsertException('can\'t parse and find position: "{pos}"'.format(pos=pattern))





class PatchInsertException(Exception):
    """Error"""

class PatchInsert():

    handled_action = 'insert'

    def __init__(self,txt):
        self.txt = txt

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
                    pos = find_position(attempt,txt)
                    if pos is not None:
                        break
            else:
                pos = find_position(chunk['position'],txt)
            return pos
        
        txt = what_to_add(chunk)
        pos = where_to_add(chunk,self.txt)
        yield { 'op': 'add', 'text': txt, 'pos': pos }