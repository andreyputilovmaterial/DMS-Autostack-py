
import re


def validate_name(n):
    return not not re.match(r'^[\w\-\./]*$',n,flags=re.I|re.DOTALL)

class PatchError(Exception):
    """Patch cass: error"""

# inhereting from dict to have it json serializable
class Patch(dict):
    def __init__(self,**kwargs):
        action = self.action
        if not validate_name(action):
            raise PatchError('Patch: "action" attribute validation failed ({a})'.format(a=self.action))
        if not 'position' in kwargs:
            raise PatchError('Patch: "position" attribute is required ({a})'.format(a=self.action))
        if not 'payload' in kwargs:
            raise PatchError('Patch: "payload" attribute is required ({a})'.format(a=self.action))
        kwargs.update({'action':action})
        return super().__init__(**kwargs)

class PatchInsert(Patch):
    action = 'insert'
    def __init__(self,position,payload,comment=None):
        args = {
            'position': position,
            'payload': payload,
        }
        if comment:
            args.update({'comment':comment})
        return super().__init__(**args)

class PatchSectionMetadataInsert(Patch):
    action = 'section/metadata/insert'
    def __init__(self,position,payload,comment=None):
        if not 'variable' in payload:
            raise PatchError('Patch: "variable" attribute of "payload" attribute is required ({a})'.format(a=self.action))
        if not 'metadata' in payload:
            raise PatchError('Patch: "metadata" attribute of "payload" attribute is required ({a})'.format(a=self.action))
        if not 'attributes' in payload:
            raise PatchError('Patch: "attributes" attribute of "payload" attribute is required ({a})'.format(a=self.action))
        args = {
            'position': position,
            'payload': payload,
        }
        if comment:
            args.update({'comment':comment})
        return super().__init__(**args)

class PatchSectionOnNextCaseInsert(Patch):
    action = 'section/onnextcase/insert'
    def __init__(self,position,payload,comment=None):
        if not 'variable' in payload:
            raise PatchError('Patch: "variable" attribute of "payload" attribute is required ({a})'.format(a=self.action))
        if not 'lines' in payload:
            raise PatchError('Patch: "lines" attribute of "payload" attribute is required ({a})'.format(a=self.action))
        args = {
            'position': position,
            'payload': payload,
        }
        if comment:
            args.update({'comment':comment})
        return super().__init__(**args)

class PatchSectionInputSourceInsert(Patch):
    action = 'section/inputsource/insert'
    def __init__(self,position,payload,comment=None):
        raise PatchError('Patch: PatchSectionOnNextCaseInsert: not implemented')

class PatchSectionOutputSourceInsert(Patch):
    action = 'section/outputsource/insert'
    def __init__(self,position,payload,comment=None):
        raise PatchError('Patch: PatchSectionOnNextCaseInsert: not implemented')

class PatchSectionOtherInsert(Patch):
    action = 'section/other/insert'
    def __init__(self,position,section_name,payload,comment=None):
        def clean(section_name):
            assert re.match(r'^\s*?\w+\s*?$',section_name,flags=re.I|re.DOTALL), 'PatchSectionOther: section name must be alphanumeric, no spaces ("{s}")'.format(s=section_name)
            return section_name
        args = {
            'position': position,
            'section': clean(section_name),
            # 'section': {
            #     'name': section_name,
            #     'pattern': Position(re.compile(r'((?:^|\n)\s*?event\s*?\(\s*?'+clean(section_name)+r'\b[^\n]*?\s*?\)\s*?(?:\'[^\n]*?)?\s*?\n(?:[^\n]*?\n)*?)(\s*?end\b\s*?\bevent\b)',flags=re.I|re.DOTALL)),
            # },
            'payload': payload,
        }
        if comment:
            args.update({'comment':comment})
        return super().__init__(**args)



# this fn (actually, formatted as class, but conceptually a fn)
# this fn does not look for item, or resolve the path, as you could have expected
# it just gets the input, of various formats - can be sent a number, a string, a regex pattern
# and formats it for the final patch object formatted as json
# different types of inputs mean differetn types of address
# if it's a number, it's position, like line number, if it's a string, it can be item name in metadata, if it's a regex, that's what we search for in scripts, and find the position to insert the patched piece, etc...
# but this is not controlled here, we don't look what is being passed, we only format it for the json, only pass through
class Position(dict):
    def __init__(self,position):
        result = {}
        if isinstance(position,re.Pattern):
            result = {
                'type': 're',
                'pattern': position.pattern,
                'flags': position.flags,
            }
        elif isinstance(position,int):
            result = {
                'type': 'position',
                'position': position,
            }
        elif isinstance(position,str):
            result = {
                'type': 'address',
                'position': position,
            }
        elif not position:
            result = {
                'type': 'none',
            }
        else:
            # raise Exception('prep position attribute for patch chunk: can\'t handle this type of "pos" attribute: "{p}"'.format(pos=position))
            result = {
                'type': 'custom',
                'payload': position,
            }
        assert 'type' in result, 'prep position attribute for patch chunk: result validation failed, missing "type" (for reference, "position" passed is "{p}")'.format(pos=position)
        super().__init__(result)
