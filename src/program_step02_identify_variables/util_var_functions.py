

import re




def sanitize_item_name(item_name):
    return re.sub(r'\s*$','',re.sub(r'^\s*','',re.sub(r'\s*([\[\{\]\}\.])\s*',lambda m:'{m}'.format(m=m[1]),item_name,flags=re.I))).lower()

def detect_item_type(item_name):
    item_name_clean = sanitize_item_name(item_name)
    if re.match(r'^\s*?$',item_name_clean,flags=re.I):
        return 'blank'
    elif re.match(r'^\s*?(\w(?:[\w\[\{\]\}\.]*?\w)?)\.(?:categories|elements)\s*?\[\s*?\{?\s*?(\w+)\s*?\}?\]\s*?$',item_name_clean,flags=re.I):
        return 'category'
    elif re.match(r'^\s*?(\w(?:[\w\[\{\]\}\.]*?\w)?)\s*?$',item_name_clean,flags=re.I):
        return 'variable'
    else:
        raise ValueError('Item name is not recognized, is it a variable or a category: "{s}"'.format(s=item_name))

def extract_category_name(item_name):
    item_name_clean = sanitize_item_name(item_name)
    matches = re.match(r'^\s*?(\w(?:[\w\[\{\]\}\.]*?\w)?)\.(?:categories|elements)\s*?\[\s*?\{?\s*?(\w+)\s*?\}?\]\s*?$',item_name_clean,flags=re.I)
    return matches[1],matches[2]

