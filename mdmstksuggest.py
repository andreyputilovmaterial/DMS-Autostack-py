
import sys, os
import json, re
from datetime import datetime
import math

from collections import namedtuple










def escape_html(s):
    return re.sub(r'[^\w]',lambda char: '&#{num};'.format(num=ord(char[0][0])),s)

def unescape_html(s):
    return re.sub(r'&\#(\d+);',lambda m: '{result}'.format(result=chr(int(m[1]))),s)



def split_words(s):
    return '{s}{eend}'.format(s=re.sub(r'(?:(?:&#60|<)(?:&#60|<)HIDDENLINEBREAK(?:&#62;|>)(?:&#62;|>)|(?:(?:\b\w+\b)|(?:\s+)|.))',lambda m: '<<MDMREPDELIMITER>>{m}'.format(m=m[0]),s),eend='<<MDMREPDELIMITER>>').split('<<MDMREPDELIMITER>>')


def is_info_item(item_name):
    return re.match(r'^\s*?Info&#58;&#32;',item_name)


def recognize_col_type_by_label(col_def):
    col_type = None
    if re.match(r'^(?:\s|(?:&#32;))*?Label(?:\s|(?:&#32;))*?(?:(?:\(|(?:&#40;)).*?(?:\)|(?:&#41;)))?(?:\s|(?:&#32;))*?$',col_def):
        # Label
        col_type = 'label'
    elif  re.match(r'^(?:\s|(?:&#32;))*?(?:Custom)?(?:\s|(?:&#32;))*?(?:Property|properties)(?:\s|(?:&#32;))*?(?:(?:\(|(?:&#40;)).*?(?:\)|(?:&#41;)))?(?:\s|(?:&#32;))*?$',col_def):
        # Custom properties
        col_type = 'properties'
    elif  re.match(r'^(?:\s|(?:&#32;))*?Translate(?:\s|(?:&#32;))*?(?:(?:\(|(?:&#40;))(?:\s|(?:&#32;))*?\w+(?:\s|(?:&#32;))*?(?:\)|(?:&#41;)))(?:\s|(?:&#32;))*?$',col_def):
        # Translations
        col_type = 'translations'
    else:
        col_type = True
    return col_type

def unicode_remove_accents(txt):
    raise Exception('remove accents func: not implemented; please grab some implementation suitable for your needs')

def filter_duplicates(seq):
    seen = set()
    seen_add = seen.add
    return [x for x in seq if not (x in seen or seen_add(x))]







DiffItemKeep = namedtuple('DiffItemKeep', ['line'])
DiffItemInsert = namedtuple('DiffItemInsert', ['line'])
DiffItemRemove = namedtuple('DiffItemRemove', ['line'])



# a function or Myers diff
# re-written to python from js by AP 11/30/2022
# sourced 11/17/2022 from https://github.com/wickedest/myers-diff, Apache 2.0 license */ /* authors can be found there on that page */ /* license is not attached but can be found here https:/* github.com/wickedest/myers-diff/blob/master/LICENSE */

class MyersDiffSplitter:
    def __init__(self,data,delimiter):
        self.data = data
        self.pos = None
        self.start = None
        self.delimiter = delimiter
    def __iter__(self):
        self.start = 0
        self.pos = ( 0 if not self.delimiter else ( data.index(self.delimiter, self.start) if self.delimiter in self.data[self.start:] else -1 ) )
        return self
    def __next__(self):
        if len(self.data) == 0:
            raise StopIteration
        elif not self.delimiter:
            if self.start>=len(self.data):
                raise StopIteration
            else:
                part = {'text':self.data[self.start],'pos':self.start}
                self.start = self.start + 1
                return part
        elif self.pos<0:
            if self.start<=len(self.data):
                # handle remaining text.  the `start` might be at some */ /*  position less than `text.length`.  it may also be _exactly_ */ /*  `text.length` if the `text` ends with a double `ch`, e.g. */ /*  "\n\n", the `start` is set to `pos + 1` below, which is one */ /*  after the first "\n" of the pair.  it would also be split. */
                part = {'text':self.data[self.start:],'pos':self.start}
                self.pos = -1
                self.start = len(self.data) + 1
                return part
            else:
                raise StopIteration
        else:
            word = self.data[self.start:self.pos]
            part = {'text':word,'pos':self.start}
            self.start = self.pos + 1
            self.pos = ( 0 if not self.delimiter else ( data.index(self.delimiter, self.start) if self.delimiter in self.data[self.start:] else -1 ) )
            return part

def myers_diff_get_default_settings():
    return {
        'compare': 'array', # array|lines|words|chars
        'ignorewhitespace': False,
        'ignorecase': False,
        'ignoreaccents': False
    }

class MyersDiffEncodeContext:
    def __init__(self, encoder, data, options={}):
        re = None
        self.encoder = encoder
        self._codes = {}
        self._modified = {}
        self._parts = [];
        count = 0
        splitter_delimiter = None
        if 'compare' in options:
            if options['compare']=='lines':
                splitter_delimiter = "\n"
            elif options['compare']=='words':
                splitter_delimiter = ' '
            elif options['compare']=='chars':
                splitter_delimiter = ''
            elif options['compare']=='array':
                splitter_delimiter = None
            else:
                # default
                # that would be chars, or array, that would work the same
                splitter_delimiter = None
        split = MyersDiffSplitter(data,splitter_delimiter)
        part = None
        for part in split:
            # if options.lowercase..., options.ignoreAccents
            # line = lower(line) ...
            # part = { 'text': part_txt, 'pos': count }
            line = str(part['text'])
            if ('ignorewhitespace' in options) and (options['ignorewhitespace']):
                line = re.sub(r'^\s*','',re.sub(r'\s*$','',re.sub(r'\s+',' ',line)))
            if ('ignorecase' in options) and (options['ignorecase']):
                line = line.lower()
            if ('ignoreaccents' in options) and (options['ignoreaccents']):
                line = unicode_remove_accents(line)
            aCode = encoder.get_code(line)
            self._codes[str(count)] = aCode
            self._parts.append(part)
            count = count + 1
    def finish(self):
        del self.encoder
    def _get_codes(self):
        return self._codes
    def _get_length(self):
        return len(self._codes.keys())
    def _get_modified(self):
        return self._modified
    codes = property(_get_codes)
    modified = property(_get_modified)
    length = property(_get_length)

class MyersDiffEncoder:
    code = 0
    diff_codes = {}
    def __init__(self):
        self.code = 0
        self.diff_codes = {}
    def encode(self, data,options={}):
        return MyersDiffEncodeContext(self,data,options)
    def get_code(self, line):
        if str(line) in self.diff_codes:
            return self.diff_codes[str(line)]
        self.code = self.code + 1
        self.diff_codes[str(line)] = self.code
        return self.code

class Myers:
    @staticmethod
    def compare_lcs(lhsctx, rhsctx, callback):
        lhs_start = 0
        rhs_start = 0
        lhs_line = 0
        rhs_line = 0
        while ((lhs_line < lhsctx.length) or (rhs_line < rhsctx.length)):
            if not str(lhs_line) in lhsctx.modified:
                lhsctx.modified[str(lhs_line)] = False
            if not str(rhs_line) in rhsctx.modified:
                rhsctx.modified[str(rhs_line)] = False
            if ((lhs_line < lhsctx.length) and (not lhsctx.modified[str(lhs_line)]) and (rhs_line < rhsctx.length) and (not rhsctx.modified[str(rhs_line)])):
                # equal lines
                lhs_line = lhs_line + 1
                rhs_line = rhs_line + 1
            else:
                # maybe deleted and/or inserted lines
                lhs_start = lhs_line
                rhs_start = rhs_line
                while ((lhs_line < lhsctx.length) and ((rhs_line >= rhsctx.length) or ((str(lhs_line) in lhsctx.modified) and (lhsctx.modified[str(lhs_line)])))):
                    lhs_line = lhs_line + 1
                while ((rhs_line < rhsctx.length) and ((lhs_line >= lhsctx.length) or ((str(rhs_line) in rhsctx.modified) and (rhsctx.modified[str(rhs_line)])))):
                    rhs_line = rhs_line + 1
                if ((lhs_start < lhs_line) or (rhs_start < rhs_line)):
                    lat = min([lhs_start, lhsctx.length-1 if lhsctx.length>0 else 0])
                    rat = min([rhs_start, rhsctx.length-1 if rhsctx.length>0 else 0])
                    lpart = lhsctx._parts[min([lhs_start, lhsctx.length - 1])]
                    rpart = rhsctx._parts[min([rhs_start, rhsctx.length - 1])]
                    item = {
                        'lhs': {
                            'at': lat,
                            'del': lhs_line - lhs_start,
                            'pos': lpart['pos'] if lpart else None,
                            'text': lpart['text'] if lpart else None
                        },
                        'rhs': {
                            'at': rat,
                            'add': rhs_line - rhs_start,
                            'pos': rpart['pos'] if rpart else None,
                            'text': rpart['text'] if rpart else None
                        }
                    }
                    callback(item)

    @staticmethod
    def get_shortest_middle_snake(lhsctx, lhs_lower, lhs_upper, rhsctx, rhs_lower, rhs_upper, vectorU, vectorD):
        max = lhsctx.length + rhsctx.length + 1
        if not max:
            raise Exception('unexpected state');
        kdown = lhs_lower - rhs_lower
        kup = lhs_upper - rhs_upper
        delta = (lhs_upper - lhs_lower) - (rhs_upper - rhs_lower)
        odd = (delta & 1) != 0
        offset_down = max - kdown
        offset_up = max - kup
        maxd = ((lhs_upper - lhs_lower + rhs_upper - rhs_lower) // 2) + 1
        ret = {
            'x': 0,
            'y': 0
        }
        d = None
        k = None
        x = None
        y = None
        if offset_down + kdown + 1>=len(vectorD):
            # redim
            # print('redim {var} to {n}, len is {l}!'.format(var='vectorD',n=offset_down + kdown + 1,l=len(vectorD)))
            raise Exception('redim {var} to {n}, len is {l}!'.format(var='vectorD',n=offset_down + kdown + 1,l=len(vectorD)))
            # vectorD = [*vectorD,*[None for i in range(len(vectorD),offset_down + kdown + 1+1)]]
        vectorD[offset_down + kdown + 1] = lhs_lower
        if offset_up + kup - 1>=len(vectorU):
            # redim
            # print('redim {var} to {n}, len is {l}!'.format(var='vectorU',n=offset_up + kup - 1,l=len(vectorU)))
            raise Exception('redim {var} to {n}, len is {l}!'.format(var='vectorU',n=offset_up + kup - 1,l=len(vectorU)))
            # vectorU = [*vectorU,*[None for i in range(len(vectorU),offset_up + kup - 1+1)]]
        vectorU[offset_up + kup - 1] = lhs_upper
        for d in range(maxd+1):
            for k in range(kdown - d, kdown + d+1, 2):
                if (k == kdown - d):
                    x = vectorD[offset_down + k + 1]
                    # down
                else:
                    x = vectorD[offset_down + k - 1] + 1
                    # right
                    if ((k < (kdown + d)) and (vectorD[offset_down + k + 1] >= x)):
                        x = vectorD[offset_down + k + 1]
                        # down
                y = x - k
                # find the end of the furthest reaching forward D-path in diagonal k.
                while ((x < lhs_upper) and (y < rhs_upper) and (lhsctx.codes[str(x)] == rhsctx.codes[str(y)])):
                    x = x + 1
                    y = y + 1
                if offset_down + k>=len(vectorD):
                    # redim
                    # print('redim {var} to {n}, len is {l}!'.format(var='vectorD',n= offset_down + k,l=len(vectorD)))
                    raise Exception('redim {var} to {n}, len is {l}!'.format(var='vectorD',n= offset_down + k,l=len(vectorD)))
                    # vectorD = [*vectorD,*[None for i in range(len(vectorD),offset_down + k+1)]]
                vectorD[offset_down + k] = x
                # overlap ?
                if (odd and (kup - d < k) and (k < kup + d)):
                    if (vectorU[offset_up + k] <= vectorD[offset_down + k]):
                        ret['x'] = vectorD[offset_down + k]
                        ret['y'] = vectorD[offset_down + k] - k
                        return (ret)
            # Extend the reverse path.
            for k in range(kup - d, kup + d+1, 2):
                # find the only or better starting point
                if (k == kup + d):
                    x = vectorU[offset_up + k - 1]
                    # up
                else:
                    x = vectorU[offset_up + k + 1] - 1
                    # left
                    if ((k > kup - d) and (vectorU[offset_up + k - 1] < x)):
                        x = vectorU[offset_up + k - 1]
                        # up
                y = x - k
                while ((x > lhs_lower) and (y > rhs_lower) and (lhsctx.codes[str(x - 1)] == rhsctx.codes[str(y - 1)])):
                    # diagonal
                    x = x - 1
                    y = y - 1
                if offset_up + k>=len(vectorU):
                    # redim
                    # print('redim {var} to {n}, len is {l}!'.format(var='vectorU',n= offset_up + k,l=len(vectorU)))
                    raise Exception('redim {var} to {n}, len is {l}!'.format(var='vectorU',n= offset_up + k,l=len(vectorU)))
                    # vectorU = [*vectorU,*[None for i in range(len(vectorU),offset_up + k+1)]]
                vectorU[offset_up + k] = x
                # overlap ?
                if (not odd and (kdown - d <= k) and (k <= kdown + d)):
                    if offset_up + k>=len(vectorU):
                        # redim
                        # print('redim {var} to {n}, len is {l}!'.format(var='vectorU',n=offset_up + k,l=len(vectorU)))
                        raise Exception('redim {var} to {n}, len is {l}!'.format(var='vectorU',n=offset_up + k,l=len(vectorU)))
                        # vectorU = [*vectorU,*[None for i in range(len(vectorU),offset_up + k+1)]]
                    if offset_down + k>=len(vectorD):
                        # redim
                        # print('redim {var} to {n}, len is {l}!'.format(var='vectorD',n=offset_down + k,l=len(vectorD)))
                        raise Exception('redim {var} to {n}, len is {l}!'.format(var='vectorD',n=offset_down + k,l=len(vectorD)))
                        # vectorD = [*vectorD,*[None for i in range(len(vectorD),offset_down + k+1)]]
                    if (vectorU[offset_up + k] <= vectorD[offset_down + k]):
                        ret['x'] = vectorD[offset_down + k]
                        ret['y'] = vectorD[offset_down + k] - k
                        return (ret)
        # should never get to this state
        raise Exception('unexpected state')
    @staticmethod
    def get_longest_common_subsequence(lhsctx, lhs_lower, lhs_upper, rhsctx, rhs_lower, rhs_upper, vectorU, vectorD):
        # trim off the matching items at the beginning
        while ((lhs_lower < lhs_upper) and (rhs_lower < rhs_upper) and (lhsctx.codes[str(lhs_lower)] == rhsctx.codes[str(rhs_lower)])):
            lhs_lower = lhs_lower + 1
            rhs_lower = rhs_lower + 1
        # trim off the matching items at the end
        while ((lhs_lower < lhs_upper) and (rhs_lower < rhs_upper) and (lhsctx.codes[str(lhs_upper - 1)] == rhsctx.codes[str(rhs_upper - 1)])):
            lhs_upper = lhs_upper - 1
            rhs_upper = rhs_upper - 1
        if (lhs_lower == lhs_upper):
            while (rhs_lower < rhs_upper):
                rhsctx.modified[str(rhs_lower)] = True
                rhs_lower = rhs_lower + 1
        elif (rhs_lower == rhs_upper):
            while (lhs_lower < lhs_upper):
                lhsctx.modified[str(lhs_lower)] = True
                lhs_lower = lhs_lower + 1
        else:
            p_p = Myers.get_shortest_middle_snake(lhsctx, lhs_lower, lhs_upper, rhsctx, rhs_lower, rhs_upper, vectorU, vectorD)
            x = p_p['x']
            y = p_p['y']
            Myers.get_longest_common_subsequence(lhsctx, lhs_lower, x, rhsctx, rhs_lower, y, vectorU, vectorD)
            Myers.get_longest_common_subsequence(lhsctx, x, lhs_upper, rhsctx, y, rhs_upper, vectorU, vectorD)

    # Compare {@code lhs} to {@code rhs}.  Changes are compared from left
    # * to right such that items are deleted from left, or added to right,
    # * or just otherwise changed between them.
    # *
    # * @param   {string} lhs - The left-hand source text.
    # * @param   {string} rhs - The right-hand source text.
    @staticmethod
    def diff(lhs, rhs, options=None):
        encoder = MyersDiffEncoder()
        if (not hasattr(lhs,'__len__')):
            raise Exception('illegal argument \'lhs\'')
        if (not hasattr(rhs,'__len__')):
            raise Exception('illegal argument \'rhs\'')
        if not hasattr(options,'__getitem__'):
            options = {}
        settings = {**myers_diff_get_default_settings(),**options}
        lhsctx = encoder.encode(lhs,settings)
        rhsctx = encoder.encode(rhs,settings)
        # Myers.LCS(lhsctx, rhsctx)
        Myers.get_longest_common_subsequence(lhsctx, 0, lhsctx.length, rhsctx, 0, rhsctx.length, [None for i in range(0,4*(len(lhs)+len(rhs))+10)], [None for i in range(0,4*(len(lhs)+len(rhs))+10)] )
        # compare lhs/rhs codes and build a list of comparisons
        changes = []
        compare = 1 # that means lines not chars
        def _changeItem(item):
            # add context information
            def _lhs_get_part(n):
                return lhsctx._parts[n]
            def _rhs_get_part(n):
                return rhsctx._parts[n]
            item['lhs']['get_part'] = _lhs_get_part
            item['rhs']['get_part'] = _rhs_get_part
            if (compare == 0):
                # chars
                item['lhs']['length'] = item['lhs']['del']
                item['rhs']['length'] = item['rhs']['add']
            else:
                # words and lines
                item['lhs']['length'] = 0
                if (item['lhs']['del']):
                    # get the index of the second-last item being deleted
                    # plus its length, minus the start pos.
                    i = item['lhs']['at'] + item['lhs']['del'] - 1
                    part = lhsctx._parts[i]
                    item['lhs']['length'] = part['pos'] + 1 - lhsctx._parts[item['lhs']['at']]['pos']
                item['rhs']['length'] = 0
                if (item['rhs']['add']):
                    # get the index of the second-last item being added,
                    # plus its length, minus the start pos.
                    i = item['rhs']['at'] + item['rhs']['add'] - 1
                    part = rhsctx._parts[i]
                    item['rhs']['length'] = part['pos'] + 1 - rhsctx._parts[item['rhs']['at']]['pos']
            changes.append(item)
        Myers.compare_lcs(lhsctx, rhsctx, _changeItem)
        lhsctx.finish()
        rhsctx.finish()
        return changes

    # converts results formatted with lhs and rhs to a list with DiffItemKeep, DiffItemInsert, DiffItemRemove items
    @staticmethod
    def to_records(diff,a,b):
        results = []
        lastIndex = 0
        for diffObj in diff:
            results = [
                *results,
                *map(
                    lambda line: DiffItemKeep(line),
                    a[ lastIndex : diffObj['lhs']['at'] ]
                ),
                *map(
                    lambda line: DiffItemRemove(line),
                    a[ diffObj['lhs']['at'] : diffObj['lhs']['at'] + diffObj['lhs']['del'] ]
                ),
                *map(
                    lambda line: DiffItemInsert(line),
                    b[diffObj['rhs']['at'] : diffObj['rhs']['at'] + diffObj['rhs']['add'] ]
                )
            ]
            lastIndex = diffObj['lhs']['at'] + diffObj['lhs']['del']
        results = [
            *results,
            *map(
                lambda line: DiffItemKeep(line),
                a[lastIndex:]
            )
        ];
        return results









# the function to create data for the final report, and return it in json
def process_mdd(json_lmdd):

    time_start = datetime.utcnow()

    # this "data" contains also general fields for mdd names, timestamp, script ver, etc
    # here we go and iti it
    result = {
        "ReportType": "MDDSTK",
        "MDMREPSCRIPT": "true",
        "MDD": json_lmdd['MDD'],
        "DateTimeReportGenerated": str(datetime.utcnow()),
        "MDMREP_SCRIPT_VER": "latest",
        "FileProperties": {
            "ReportTitle": "MDM&#32;STK&#32;{mdd_lmdd}".format(mdd_lmdd=json_lmdd['MDD']),
            "ReportHeading": "MDM&#32;STK&#32;{mdd_lmdd}".format(mdd_lmdd=json_lmdd['MDD']),
            "ReportInfo": [
                escape_html('Hi! Please see the STK results below.'),
                '{part1}{part2}{part3}{part4}{part5}'.format(part1=escape_html('MDD: '),part2=json_lmdd['MDD'],part3='',part4='',part5=''),
                "Run&#58;&#32;{t}".format(t=escape_html(str(time_start)))
            ]
        }
    }

    # "records" is the list of records in left and right input files
    records_lmdd = (json_lmdd['Records'] if 'Records' in json_lmdd else [])
    # and "rows" are the same as records but not the whole row with cells for labels, properties, translations but just the first cell that is a question or category name, i.e. item name
    #rows_lmdd = [ unescape_html(row[0]) for row in records_lmdd ]
    
    # process...
    
    records = []
    
    result['ColumnHeaders'] = ['Main Column','Additional Info']
    
    dict_questions = {}
    dict_categories = {}
    
    s = re.compile(r'^\s*?Fields\.(?:\w|\xA0)+.*?',flags=re.DOTALL|re.ASCII|re.I)
    s2 = re.compile(r'^\s*?Fields\.(?:\w|\xA0)+(?:\.(?:\w|\xA0)+)*\.(?:categories|elements)\s*?\[.*?',flags=re.DOTALL|re.ASCII|re.I)
    fields_all = [ row for row in records_lmdd if s.match(unescape_html(row[0])) and not s2.match(unescape_html(row[0])) ]
    #records.append(['(All Questions are listed below)',''])
    #records.extend([['{qname}'.format(qname=row),''] for row in fields_all])
    for row in fields_all:
        name = re.sub(r'^fields\.((?:\w|\xA0)+(?:\.(?:\w|\xA0)+)*).*?$',lambda m: '{res}'.format(res=m[1]),re.sub(r'\.(?:categories|elements)\[.*?$','',unescape_html(row[0]),flags=re.DOTALL|re.ASCII|re.I),flags=re.DOTALL|re.ASCII|re.I)
        name_lcase = name.lower()
        dict_questions[name_lcase] = {
            'name': '{n}'.format(n=name),
            'iterations': [],
            'records_ref': row,
            'label': unescape_html(row[1])
        }
    
    #fields_with_iterations = [ re.sub(r'^\s*?((?:\w|\xA0)+(?:\.(?:\w|\xA0)+)*)\.(?:categories|elements)\s*?\[\s*?((?:\w|\xA0)+)\s*?\].*?\s*?$',lambda m: '{qname}\t{iter}'.format(qname=m[1],iter=m[2]),row,flags=re.DOTALL|re.ASCII|re.I) for row in list( filter( lambda itemname: re.match(r'^fields\.(?:\w|\xA0)+\.(?:elements|categories)\[.*?',itemname), rows_lmdd ) ) ]
    s = re.compile(r'^\s*?Fields\.(?:\w|\xA0)+(?:\.(?:\w|\xA0)+)*\.(?:categories|elements)\s*?\[.*?',flags=re.DOTALL|re.ASCII|re.I)
    def format_category_record(row):
        try:
            name = unescape_html(row[0])
            m = re.match(r'^\s*Fields\.((?:\w|\xA0)+(?:\.(?:\w|\xA0)+)*)\.(?:categories|elements)\s*?\[\s*?\{?\s*?((?:\w|\xA0)+)\s*?\]?\s*?\].*?$',name,flags=re.DOTALL|re.ASCII|re.I)
            return {
                'field_name': '{r}'.format(r=m[1]),
                'category_name': '{r}'.format(r=m[2]),
                'label': unescape_html(row[1])
            }
        except TypeError as e:
            print('failed at {line}'.format(line=unescape_html(row[0])))
            raise e
    fields_with_iterations = [ format_category_record(row) for row in records_lmdd if s.match(unescape_html(row[0])) ]
    #records.append(['(Questions with iterations are listed below)',''])
    #records.extend(fields_with_iterations)
    for field in fields_with_iterations:
        field_name = field['field_name']
        field_name_lower = field_name.lower()
        category_name = field['category_name']
        category_name_lower = category_name.lower()
        dict_questions[field_name_lower]['iterations'].append(category_name_lower)
        if not category_name_lower in dict_categories:
            dict_categories[category_name_lower] = { 'name': '{r}'.format(r=category_name), 'used': [] }
        dict_categories[category_name_lower]['used'].append(field_name_lower)
    
    # now we are trying to find frequent categories
    def calc_adjusted_frequency(category):
        ratio = 1
        if( re.match(r'.*?(?:Other|OtherSpec|None|NoneAbove).*?',category['name'],flags=re.DOTALL|re.ASCII|re.I) ):
            ratio = .85
        if( re.match(r'^\s*?(?:_\d+)\s*?$',category['name'],flags=re.DOTALL|re.ASCII|re.I) ):
            ratio = .03
        if( re.match(r'^\s*?(?:Yes|No)\s*?$',category['name'],flags=re.DOTALL|re.ASCII|re.I) ):
            ratio = .01
        return len(category['used']) * ratio
    for category_key, category in dict_categories.items():
        category['adjusted_frequency'] = calc_adjusted_frequency(category)
    u = sorted( [ category['adjusted_frequency'] for category_key, category in dict_categories.items() ] )
    #print(list(dict_categories.items()))
    if len(u) == 0:
         u = [0]
    u_med_value = u[len(u)-1]*.64 # int("{:.0f}".format(u[len(u)-1]*.64))
    u_med_index = None
    for i in range(0,len(u)-1):
        if( (u[i]>u_med_value) and (u_med_index is None)):
            u_med_index = i
            break
    u_med_value = u[u_med_index]
    #print('len(u) = {l0}, u[0] = {l1}, u[max] = {l2}, u_percentile_75 = {l3}'.format(l0=len(u),l1=u[0],l2=u[len(u)-1],l3='u[{l0}] = {l1}'.format(l0=u_med_index,l1=u[u_med_index])))
    key_categories = []
    for category_name, category in dict_categories.items():
        if( category['adjusted_frequency'] >= u_med_value ):
            key_categories.append('{cat}'.format(cat=category_name))
    def cmp_adjusted_category_frequencies(e):
        return ( -dict_categories[e]['adjusted_frequency'], e )
    key_categories = sorted(key_categories,key=cmp_adjusted_category_frequencies)
    #records.append(['(Frequent categories:)',''])
    ##print(key_categories_sorted)
    #for key_category in key_categories:
    #    category = dict_categories[key_category]
    #    records.append(['{cat}'.format(cat=category['name']),'...used {count} (adjusted={count2}) times in {questions}'.format(count=len(category['used']),count2=category['adjusted_frequency'],questions=','.join(category['used']))])
    
    # bencmarking each category - how things change if we exclude this exact category?
    key_categories_bench = {}
    for category_test in key_categories:
        list_included = set()
        list_excluded = set()
        for c in key_categories:
            list_included = list_included.union(dict_categories[c]['used'])
            if not (c.lower()==category_test.lower()):
                list_excluded = list_excluded.union(dict_categories[c]['used'])
        key_categories_bench[category_test] = {'list_included':list_included,'list_excluded':list_excluded}
        #print('DEBUG: cat == {cat}, list_included = {list_included_count}, list_excluded = {list_excluded_count}: {list_excluded}'.format(cat=category_test,list_included_count=len(list(list_included)),list_excluded_count=len(list(list_excluded)),list_excluded=list(list_excluded)))
    for category_test in key_categories:
        matching = set()
        for c in key_categories:
            if True:
            #if not (c.lower()==category_test.lower()):
                cmp_a = set(key_categories_bench[c]['list_excluded'])
                cmp_b = set(key_categories_bench[category_test]['list_excluded'])
                #matching_score = ( 1 if cmp_a == cmp_b else 0 )
                matching_score = 1.0 - 1.0 * len(cmp_a^cmp_b) / len(cmp_a)
                if matching_score > .00001:
                    matching.add((c,matching_score))
                    #matching.add('{result}/{score}'.format(result=c,score=matching_score))
        key_categories_bench[category_test]['matching'] = matching
        #print('category tested: {cat}, matching == {matching}'.format(cat=category_test,matching=key_categories_bench[category_test]['matching']))
    for category_test in key_categories:
        key_categories_bench[category_test]['w'] = 1
        key_categories_bench[category_test]['w_upd'] = 1
    for attempt in range(1,10):
        for category_test in key_categories:
            key_categories_bench[category_test]['w_upd'] = 0
            for c in key_categories_bench[category_test]['matching']:
                key_categories_bench[category_test]['w_upd'] = key_categories_bench[category_test]['w_upd'] + c[1] * key_categories_bench[c[0]]['w']
        for category_test in key_categories:
            key_categories_bench[category_test]['w'] = key_categories_bench[category_test]['w_upd'] / len(key_categories_bench[category_test]['matching'])
            #print('iteration #{attempt}: {cat}, weight = {w}'.format(attempt=attempt,cat=category_test,w=key_categories_bench[category_test]['w']))
    def cmp_key_categories_by_weights(e):
        return (-key_categories_bench[e]['w'],e)
    key_categories = sorted(key_categories,key=cmp_key_categories_by_weights)[:3]
    print('Selected categories: {key_categories}'.format(key_categories=key_categories))
    records.append(['(Selected key categories for stacking)',''])
    for cat in key_categories:
        records.append(['{qname}'.format(qname=cat),''])
    stk_questions_combined_list = []
    for item in key_categories:
        stk_questions_combined_list.extend(dict_categories[item]['used'])
    stk_questions_combined_list = filter_duplicates(stk_questions_combined_list)
    print('the following questions will be stacked: {q}'.format(q=[dict_questions[q]['name'] for q in stk_questions_combined_list]))
    records.append(['(Questions to be stacked)',''])
    for cat in [dict_questions[q]['name'] for q in stk_questions_combined_list]:
        records.append(['{qname}'.format(qname=cat),''])
    
    ## for debugging purposes...
    #records.append(['(Questions are listed below)',''])
    #for field_name, field in dict_questions.items():
    #    records.append(['{qname}'.format(qname=field['name']),'[ {categories} ]'.format(categories=','.join(field['iterations']))])
    
    
    
    # ...
    
    # add "records" to the report
    #records.append(['(The end)',''])
    result['Records'] = records
    print('Done. Writing result...\n')

    # and return the report in json
    return json.dumps(result)



if __name__ == "__main__":
	start_time = datetime.utcnow()
	input_json_lmdd = None
	if len(sys.argv)>1:
		input_json_lmdd = sys.argv[1]
	if (input_json_lmdd==None):
		raise Exception("MDM Diff: Input file is not specified")
	if (not os.path.isfile(input_json_lmdd)):
		raise Exception("MDM Diff: Input file is missing")
	print("Creating diffed data...\n")
	print("Loading input JSON data...\n")
	f_lmdd = open(input_json_lmdd)
	print("Reading JSON...\n")
	report_lmdd = json.load(f_lmdd)
	print("Working...\n")
	output = process_mdd(report_lmdd)
	report_file_name = 'report.stk.{mdd_lmdd}.json'.format(
        mdd_lmdd = re.sub(r'^\s*?report\.','',re.sub(r'\.json\s*?$','',input_json_lmdd))
    )
	print("Writing results...\n")
	with open(report_file_name,'w') as output_file:
		output_file.write(output)
	end_time = datetime.utcnow()
	#elapsed_time = end_time - start_time
	print("Finished") # + str(elapsed_time)
