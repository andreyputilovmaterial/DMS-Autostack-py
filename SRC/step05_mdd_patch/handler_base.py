
import sys



# if __name__ == '__main__':
#     # run as a program
#     import processor_simple_insert
# elif '.' in __name__:
#     # package
#     from . import processor_simple_insert
# else:
#     # included with no parent package
#     import processor_simple_insert



class FileLoaderException(Exception):
    """Error"""

class FileLoader:

    def __init__(self,filecontents):
        self.rawcontents = filecontents
        self.processors = {}
        self.final_edits = []
        # self.register_processor(processor_simple_insert.PatchInsert)

    def apply_patch(self,chunk):
        action = chunk['action']
        if action not in self.processors:
            raise FileLoaderException('Patch Error: unsupported type: "{t}"'.format(t=action))
        for edit in self.processors[action](chunk):
            self.final_edits.append(edit)
    
    def register_processor(self,cl):
        proc = cl(self.rawcontents)
        handled_action = proc.handled_action
        self.processors[handled_action] = proc
    
    def compile_patched_contents(self):
        # example of data:
        # item = { 'op': 'remove', 'pos': 123, 'del': 12 }, { 'op': 'add', 'pos': 135, 'text': '...' }
        def validate_not_overlapping(chunks):
            def does_overlap(x,y):
                return max(x.start,y.start) < min(x.stop,y.stop)
            ranges_prev = []
            for chunk in chunks:
                s = chunk['pos']
                l = None
                op = chunk['op']
                if op=='remove':
                    l = chunk['del']
                elif op=='add':
                    l = 0 # len(chunk['text'])
                elif op=='dummy':
                    # skip
                    s = 0
                    l = 0
                    pass
                else:
                    raise FileLoaderException('unrecognized op of a chunk: "{o}"'.format(o=op))
                assert isinstance(s,int) and isinstance(l,int), 'working on patch: checking if previous patches overlap: start and end positions are not interers, please check'
                for range_check in ranges_prev:
                    if does_overlap(range(s,s+l),range_check):
                        print('overlapping edits: ( {x_start}, {x_stop} ) and ( {y_start}, {y_stop} )'.format(x_start=s,x_stop=s+l,y_start=range_check.start,y_stop=range_check.stop), file=sys.stderr)
                        return False
                ranges_prev.append(range(s,s+l))
            return True
        if not validate_not_overlapping(self.final_edits):
            raise FileLoaderException('patch error: edits overlap. failed')
        result = ''
        start = 0
        pos = 0
        for chunk in self.final_edits:
            op = chunk['op']
            if op=='dummy':
                continue
            pos = chunk['pos']
            assert isinstance(start,int), 'working on patch: start position is not interer, please check'
            assert isinstance(pos,int), 'working on patch: end position is not interer, please check'
            result = result + self.rawcontents[start:pos]
            start = pos
            if op=='remove':
                start = pos + chunk['del']
            elif op=='add':
                result = result + chunk['text']
                start = pos
            else:
                raise FileLoaderException('unrecognized op of a chunk: "{o}"'.format(o=op))
        result = result + self.rawcontents[start:]
        return result
    
    def __str__(self):
        return self.compile_patched_contents()
        

