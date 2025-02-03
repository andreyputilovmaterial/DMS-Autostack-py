
import re



def trim_dots(s):
    return re.sub(r'^\s*?\.','',re.sub(r'\.\s*?$','',s,flags=re.I),flags=re.I)

def sanitize_item_name(item_name):
    return re.sub(r'\s*$','',re.sub(r'^\s*','',re.sub(r'\s*([\[\{\]\}\.])\s*',lambda m:'{m}'.format(m=m[1]),item_name,flags=re.I))).lower()

def extract_field_name(item_name):
    m = re.match(r'^\s*((?:\w.*?\.)*)(\w+)\s*$',item_name,flags=re.I)
    if m:
        return re.sub(r'\s*\.\s*$','',m[1]),m[2]
    else:
        raise ValueError('Can\'t extract field name from "{s}"'.format(s=item_name))

def extract_parent_name(item_name):
    if item_name=='':
        return '', ''
    m = re.match(r'^\s*(\w+)((?:\.\w*?)*)\s*$',item_name,flags=re.I)
    if m:
        return trim_dots(m[1]), trim_dots(m[2])
    else:
        raise ValueError('Can\'t extract field name from "{s}"'.format(s=item_name))

def extract_category_name(item_name):
    m = re.match(r'^\s*(\w+.*?\w)\.(?:categories|elements)\s*?\[\s*?\{?\s*?(\w+)\s*?\}?\s*?\]\s*$',item_name,flags=re.I)
    if m:
        return trim_dots(m[1]), trim_dots(m[2])
    else:
        raise ValueError('Can\'t extract category name from "{s}"'.format(s=item_name))



def detect_var_type_by_record(variable_record):
    variable_attributes_captured_with_mdd_read = {}
    if not 'attributes' in variable_record:
        raise ValueError('Input data does not include "attributes" data, please adjust settings that you use to run mdd_read')
    else:
        assert isinstance(variable_record,dict)
    variable_attributes_captured_with_mdd_read = {**variable_record['attributes']}
    if not 'type' in variable_attributes_captured_with_mdd_read:
        raise ValueError('Input data must follow certain format and must include "type" within its list of attributes generated with mdd_read')

    # detect variable type - we are doing it from grabbing data from attributes that were written by mdd_read
    variable_type = None
    # variable_is_plain = re.match(r'^\s*?plain\b',variable_attributes_captured_with_mdd_read['type'])
    variable_is_categorical = re.match(r'^\s*?plain/(?:categorical|multipunch|singlepunch)',variable_attributes_captured_with_mdd_read['type'])
    variable_is_loop = re.match(r'^\s*?(?:array|grid|loop)\b',variable_attributes_captured_with_mdd_read['type'])
    # variable_is_block = re.match(r'^\s*?(?:block)\b',variable_attributes_captured_with_mdd_read['type'])
    if variable_is_loop:
        variable_type = 'loop'
    elif variable_is_categorical:
        variable_type = 'categorical'
    else:
        raise ValueError('Can\'t handle this type of variable: {s}'.format(s=variable_attributes_captured_with_mdd_read['type']))
    return variable_type

