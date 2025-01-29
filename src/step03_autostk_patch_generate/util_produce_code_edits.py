import re


# this is for benchmarking and testing
# first letter is
#  - "C" (for "ContainsAny"), or
#  - "O" (for "operator", which is "=*")
# second letter is
#  - "D" (For ".DefinedCategories()"), or
#  - "E" (for "explicit category list"), or
#  - "G" (for "global" dmgr job variables - we'll read category list in OnJobStart event, and then use this list)
# I will try different syntax styles and benchmark speed
# CONFIG_CHECK_CATEGORIES_STYLE = 'CD'
CONFIG_CHECK_CATEGORIES_STYLE = 'OD'
# CONFIG_CHECK_CATEGORIES_STYLE = 'CE'
# CONFIG_CHECK_CATEGORIES_STYLE = 'OE'
# CONFIG_CHECK_CATEGORIES_STYLE = 'CG'
# CONFIG_CHECK_CATEGORIES_STYLE = 'OG'



def prepare_syntax_substitutions( d, stk_variable_name='', unstk_variable_name='', unstk_variable_fieldname='' ):
    result = {}
    assert not '.' in stk_variable_name
    assert not '.' in unstk_variable_name
    assert not '.' in unstk_variable_fieldname
    for key in d:
        text = '{s}'.format(s=d[key]) # this line ensures we are working with a copy not reference
        text = text.replace('<<STK_VARIABLE_NAME>>',stk_variable_name)
        text = text.replace('<<UNSTK_VARIABLE_NAME>>',unstk_variable_name)
        text = text.replace('<<UNSTK_VARIABLE_FIELDNAME>>',unstk_variable_fieldname)
        result[key] = text
    result['stk_variable_name'] = stk_variable_name
    result['unstk_variable_name'] = unstk_variable_name
    result['unstk_variable_fieldname'] = unstk_variable_fieldname
    return result

def generate_recursive_onnextcase_code(mdmitem_stk,mdmitem_ref):
    def recursive(mdmitem_stk,mdmitem_ref,indent,name_part):
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
        if mdmitem_stk.ObjectTypeValue==0 or mdmitem_stk.ObjectTypeValue==0:
            # regular, plain variable
            result = ''
            result = result + '\' {t}\n'.format(t=mdmitem_ref.Name)
            result = result + '<<DEST_PATH>><<DEST>> = <<SOURCE_PATH>><<SOURCE>>\n'
            result = result.replace('<<DEST>>',mdmitem_stk.Name).replace('<<SOURCE>>',mdmitem_ref.Name)
            return trim_lines(add_indent(result,indent))
        elif mdmitem_stk.ObjectTypeValue==1 or mdmitem_stk.ObjectTypeValue==2:
            # loop/array/grid
            result = ''
            result = result + 'dim cat_<<n>>\nfor each cat_<<n>> in <<DEST_PATH>><<DEST>>.categories\n'
            for subfield in mdmitem_stk.Fields:
                result_field = recursive(subfield,mdmitem_ref.Fields[subfield.name],indent=indent+'\t',name_part=name_part+'_'+subfield.Name)
                result_field = result_field.replace('<<DEST_PATH>>','<<DEST_PATH>><<DEST>>[cat_<<n>>.name].').replace('<<SOURCE_PATH>>','<<SOURCE_PATH>><<SOURCE>>[cat_<<n>>.name].')
                result = result + result_field
            result = result + 'next\n'
            result = result.replace('<<DEST>>',mdmitem_stk.Name)
            result = result.replace('<<SOURCE>>',mdmitem_ref.Name)
            result = result.replace('<<n>>',name_part)
            return trim_lines(add_indent(result,indent))
        elif mdmitem_stk.ObjectTypeValue==3:
            # block of fields
            result = ''
            result = result + '' # leading code - set loop iterations, etc... nothing for block of fields
            for subfield in mdmitem_stk.Fields:
                result_field = recursive(subfield,mdmitem_ref.Fields[subfield.name],indent=indent+'\t',name_part=name_part+'_'+subfield.Name)
                result_field = result_field.replace('<<DEST_PATH>>','<<DEST_PATH>><<DEST>>.').replace('<<SOURCE_PATH>>','<<SOURCE_PATH>><<SOURCE>>.')
                result = result + result_field
            result = result.replace('<<DEST>>',mdmitem_stk.Name)
            result = result.replace('<<SOURCE>>',mdmitem_ref.Name)
            result = result.replace('<<n>>',name_part)
            result = result + ''  # trailing code - end if, next... nothing for block of fields
            return trim_lines(add_indent(result,indent))
        else:
            raise ValueError('can\'t generate onnextcase codes: unrecognized item type: {t} ( stk var: {stkvar}, unstk var: {unstkvar} )'.format(t=mdmitem_stk.ObjectTypeValue,stkvar=mdmitem_stk.Name,unstkvar=mdmitem_ref.Name))
    result = recursive(mdmitem_stk,mdmitem_ref,indent='',name_part=mdmitem_stk.Name)
    result = result.replace('<<DEST_PATH>>','<<STK_VARIABLE_PATH>>').replace('<<SOURCE_PATH>>','<<UNSTK_VARIABLE_PATH>><<UNSTK_VARIABLE_NAME>>[cbrand].')
    return result






def generate_code_check_categories( variable_with_categories_name, categories_iterating_over, category_check, code_style={} ):
    class Cat:
        # the only goal is to provide conversion to str method
        # so that we don't care if we pass mdm categories, dict with 'name' attribute, or just categories as strings
        # maybe having a class looked more aestethically appealing to me
        # but this could have been just a function
        def __init__(self,o):
            self.o = o
        def __str__(self):
            if isinstance(self.o,str):
                return '{s}'.format(s=self.o)
            elif isinstance(self.o,dict):
                return '{s}'.format(s=self.o['name'])
            # elif isinstance(self.o,win32com.client.CDispatch):
            # I don't want to have unnecessary dependency in this file just to check if a category is an mdm category
            # I can just check against a class name as a string
            elif 'win32com.client.CDispatch' in '{cl}'.format(cl=self.o.__class__):
                return '{s}'.format(s=self.o.Name)
            else:
                return '{s}'.format(s=self.o)
    assert categories_iterating_over is not None
    code_style_assignment_op = 'operator'
    if 'assignment_op' in code_style:
        code_style_assignment_op = code_style['assignment_op']
    code_style_category_list_style = 'definedcategories'
    if 'category_list_style' in code_style:
        code_style_category_list_style = code_style['category_list_style']
    result = None
    if code_style_assignment_op=='operator':
        result = '<<CATCHECK>> =* {<<CATLIST>>}'
    elif code_style_assignment_op=='containsany':
        result = 'containsany( <<CATCHECK>>, {<<CATLIST>>} )'
    else:
        raise ValueError('generate_code_check_categories: unrecognized code_style_assignment_op: {s}'.format(s=code_style_assignment_op))
    if code_style_category_list_style=='definedcategories':
        result = result.replace('{<<CATLIST>>}','<<VARNAME>>.DefinedCategories()')
    elif code_style_category_list_style=='explicitcatlist':
        result = result.replace('<<CATLIST>>',','.join(['{s}'.format(s=Cat(cat)) for cat in categories_iterating_over]))
    elif code_style_category_list_style=='globaldmgrvar':
        result = result.replace('{<<CATLIST>>}','dmgrGlobal.DefinedCategories_<<VARNAME>>')
        raise ValueError('generating code with dmgrGlobal - not implemented yet (it is more complicated than it\'s looking)')
    else:
        raise ValueError('generate_code_check_categories: unrecognized code_style_category_list_style: {s}'.format(s=code_style_category_list_style))
    result = result.replace('<<CATCHECK>>',category_check)
    result = result.replace('<<VARNAME>>',variable_with_categories_name)
    return result




def generate_code_outerstkloop_walkthrough( mdmitem_stk, mdmitem_unstk, stk_variable_name, unstk_variable_name, unstk_variable_fieldname, categories_iterating_over ):
    TEMPLATE = {
        'variable_stk_path': 'iter_stk.',
        'variable_unstacked_path': '',
        'code': """
dim brand, cbrand, iter_stk

' <<STK_VARIABLE_NAME>>
for each brand in <<STK_VARIABLE_NAME>>.categories
cbrand = ccategorical(brand)
    ' ADD YOUR EXPRESSION HERE
    ' if DV_BrandAssigned=*cbrand then
    if True then
    'with <<STK_VARIABLE_NAME>>[cbrand]
    set iter_stk = <<STK_VARIABLE_PATH>><<STK_VARIABLE_NAME>>[cbrand]
        
        ' STK_ID
        iter_stk.STK_ID = ctext(brand.name)+"_"+ctext(Respondent.ID)
        
        ' STK_Iteration
        iter_stk.STK_Iteration = cbrand
        
        ' {@}
        
    'end with
    end if
next
set iter_stk = null
"""
    }
    result = {**TEMPLATE} # copy, not modify
    return prepare_syntax_substitutions( result, stk_variable_name, unstk_variable_name, unstk_variable_fieldname )

def generate_code_loop_unstack_simple( mdmitem_stk, mdmitem_unstk, stk_variable_name, unstk_variable_name, unstk_variable_fieldname, categories_iterating_over ):
    TEMPLATE = {
        'variable_stk_path': '<<STK_VARIABLE_PATH>><<STK_VARIABLE_NAME>>.', # not sure we need it, we don't expect that we need to process subfields separately; we need to find some really complicated tests to check it, where we stack at 2 different levels - I can imaging this could happen, let's find some tests and see
        'variable_unstacked_path': '<<UNSTK_VARIABLE_PATH>><<UNSTK_VARIABLE_NAME>>[cbrand].<<UNSTK_VARIABLE_FIELDNAME>>.', # not sure we need it, we don't expect that we need to process subfields separately; we need to find some really complicated tests to check it, where we stack at 2 different levels - I can imaging this could happen, let's find some tests and see
        'code': """
' <<STK_VARIABLE_NAME>>
' from: <<UNSTK_VARIABLE_NAME>>
'if <<CATEGORIESCHECKEXAMPLE>> then
if <<CATEGORIESCHECK>> then
    <<STK_VARIABLE_PATH>><<STK_VARIABLE_NAME>> = <<UNSTK_VARIABLE_PATH>><<UNSTK_VARIABLE_NAME>>[cbrand].<<UNSTK_VARIABLE_FIELDNAME>>
end if
' {@}
"""
    }
    result = {**TEMPLATE} # copy, not modify
    code_style_configletter1 = CONFIG_CHECK_CATEGORIES_STYLE[0] if len(CONFIG_CHECK_CATEGORIES_STYLE)>=2 else None
    code_style_configletter2 = CONFIG_CHECK_CATEGORIES_STYLE[1] if len(CONFIG_CHECK_CATEGORIES_STYLE)>=2 else None
    code_style = {
        'assignment_op': 'operator' if code_style_configletter1=='O' else ( 'containsany' if code_style_configletter1=='C' else '???' ),
        'category_list_style': 'definedcategories' if code_style_configletter2=='D' else ( 'explicitcatlist' if code_style_configletter2=='E' else ( 'globaldmgrvar' if code_style_configletter2=='G' else '???' ) ),
    }
    code_style_compare = {
        **code_style,
        'category_list_style': 'definedcategories' if code_style['category_list_style']=='explicitcatlist' else 'explicitcatlist',
    }
    result['code'] = result['code'].replace( '<<CATEGORIESCHECKEXAMPLE>>', generate_code_check_categories( variable_with_categories_name='<<UNSTK_VARIABLE_PATH>><<UNSTK_VARIABLE_NAME>>', categories_iterating_over=categories_iterating_over, category_check='cbrand', code_style=code_style_compare ) )
    result['code'] = result['code'].replace( '<<CATEGORIESCHECK>>', generate_code_check_categories( variable_with_categories_name='<<UNSTK_VARIABLE_PATH>><<UNSTK_VARIABLE_NAME>>', categories_iterating_over=categories_iterating_over, category_check='cbrand', code_style=code_style ) )
    return prepare_syntax_substitutions( result, stk_variable_name, unstk_variable_name, unstk_variable_fieldname )

def generate_code_loop_unstack_structural( mdmitem_stk, mdmitem_unstk, stk_variable_name, unstk_variable_name, unstk_variable_fieldname, categories_iterating_over ):
    TEMPLATE = {
        'variable_stk_path': '<<STK_VARIABLE_PATH>><<STK_VARIABLE_NAME>>.', # we need it
        'variable_unstacked_path': '<<UNSTK_VARIABLE_PATH>><<UNSTK_VARIABLE_NAME>>[cbrand].', # we need it; don't add variable name - it is already generated with recursive code
        'code': """
' <<STK_VARIABLE_NAME>>
' from: <<UNSTK_VARIABLE_NAME>>
' TODO: generate code iterating over all categories and subfields
'if <<CATEGORIESCHECKEXAMPLE>> then
if <<CATEGORIESCHECK>> then
    ' {@}
end if
"""
    }
    result = {**TEMPLATE} # copy, not modify
    result_add = generate_recursive_onnextcase_code(mdmitem_stk,mdmitem_unstk)
    code_style_configletter1 = CONFIG_CHECK_CATEGORIES_STYLE[0] if len(CONFIG_CHECK_CATEGORIES_STYLE)>=2 else None
    code_style_configletter2 = CONFIG_CHECK_CATEGORIES_STYLE[1] if len(CONFIG_CHECK_CATEGORIES_STYLE)>=2 else None
    code_style = {
        'assignment_op': 'operator' if code_style_configletter1=='O' else ( 'containsany' if code_style_configletter1=='C' else '???' ),
        'category_list_style': 'definedcategories' if code_style_configletter2=='D' else ( 'explicitcatlist' if code_style_configletter2=='E' else ( 'globaldmgrvar' if code_style_configletter2=='G' else '???' ) ),
    }
    code_style_compare = {
        **code_style,
        'category_list_style': 'definedcategories' if code_style['category_list_style']=='explicitcatlist' else 'explicitcatlist',
    }
    result['code'] = result['code'].replace( '<<CATEGORIESCHECKEXAMPLE>>', generate_code_check_categories( variable_with_categories_name='<<UNSTK_VARIABLE_PATH>><<UNSTK_VARIABLE_NAME>>', categories_iterating_over=categories_iterating_over, category_check='cbrand', code_style=code_style_compare ) )
    result['code'] = result['code'].replace( '<<CATEGORIESCHECK>>', generate_code_check_categories( variable_with_categories_name='<<UNSTK_VARIABLE_PATH>><<UNSTK_VARIABLE_NAME>>', categories_iterating_over=categories_iterating_over, category_check='cbrand', code_style=code_style ) )
    result['code'] = re.sub(r'^(.*?)\n\s*?\'\s*?\{@\}[^\n]*?\n(.*?)$',lambda m: '{code_begin}{code_add}{code_end}'.format(code_begin=re.sub(r'\n?$','\n',m[1],flags=re.I|re.DOTALL),code_end=re.sub(r'\n?$','\n',m[2],flags=re.I|re.DOTALL),code_add=re.sub(r'\n?$','\n',result_add,flags=re.I|re.DOTALL)),result['code'],flags=re.I|re.DOTALL)
    return prepare_syntax_substitutions( result, stk_variable_name, unstk_variable_name, unstk_variable_fieldname )

def generate_code_unstack_categorical_yn( mdmitem_stk, mdmitem_unstk, stk_variable_name, unstk_variable_name, unstk_variable_fieldname, categories_iterating_over ):
    TEMPLATE = {
        'variable_stk_path': '<<STK_VARIABLE_PATH>><<STK_VARIABLE_NAME>>', # we definitely not need it and it will not work, it will break, and that's some good news, we'll see that something is off
        'variable_unstacked_path': '<<UNSTK_VARIABLE_PATH>><<UNSTK_VARIABLE_NAME>>', # we definitely not need it and it will not work, it will break, and that's some good news, we'll see that something is off
        'code': """
' <<STK_VARIABLE_NAME>>
' from: <<UNSTK_VARIABLE_NAME>>
'if <<CATEGORIESCHECKEXAMPLE>> then
if <<CATEGORIESCHECK>> then
    <<STK_VARIABLE_PATH>><<STK_VARIABLE_NAME>> = iif( <<UNSTK_VARIABLE_PATH>><<UNSTK_VARIABLE_NAME>> is null, null, iif( <<UNSTK_VARIABLE_PATH>><<UNSTK_VARIABLE_NAME>>=*cbrand, {Yes}, {No} ) )
end if
' {@}
"""
    }
    result = {**TEMPLATE} # copy, not modify
    code_style_configletter1 = CONFIG_CHECK_CATEGORIES_STYLE[0] if len(CONFIG_CHECK_CATEGORIES_STYLE)>=2 else None
    code_style_configletter2 = CONFIG_CHECK_CATEGORIES_STYLE[1] if len(CONFIG_CHECK_CATEGORIES_STYLE)>=2 else None
    code_style = {
        'assignment_op': 'operator' if code_style_configletter1=='O' else ( 'containsany' if code_style_configletter1=='C' else '???' ),
        'category_list_style': 'definedcategories' if code_style_configletter2=='D' else ( 'explicitcatlist' if code_style_configletter2=='E' else ( 'globaldmgrvar' if code_style_configletter2=='G' else '???' ) ),
    }
    code_style_compare = {
        **code_style,
        'category_list_style': 'definedcategories' if code_style['category_list_style']=='explicitcatlist' else 'explicitcatlist',
    }
    result['code'] = result['code'].replace( '<<CATEGORIESCHECKEXAMPLE>>', generate_code_check_categories( variable_with_categories_name='<<UNSTK_VARIABLE_PATH>><<UNSTK_VARIABLE_NAME>>', categories_iterating_over=categories_iterating_over, category_check='cbrand', code_style=code_style_compare ) )
    result['code'] = result['code'].replace( '<<CATEGORIESCHECK>>', generate_code_check_categories( variable_with_categories_name='<<UNSTK_VARIABLE_PATH>><<UNSTK_VARIABLE_NAME>>', categories_iterating_over=categories_iterating_over, category_check='cbrand', code_style=code_style ) )
    return prepare_syntax_substitutions( result, stk_variable_name, unstk_variable_name, unstk_variable_fieldname )

def generate_code_loop_walkthrough( mdmitem_stk, mdmitem_unstk, stk_variable_name, unstk_variable_name, unstk_variable_fieldname, categories_iterating_over ):
    TEMPLATE = {
        'variable_stk_path': 'iter_stk_<<STK_VARIABLE_NAME>>.', # we certainly need
        'variable_unstacked_path': 'iter_<<UNSTK_VARIABLE_NAME>>.', # we certainly need it
        'code': """
' <<STK_VARIABLE_NAME>>
' from: <<UNSTK_VARIABLE_NAME>>
' process everything within this loop
dim cat_stk_<<STK_VARIABLE_NAME>>, iter_stk_<<STK_VARIABLE_NAME>>, iter_<<UNSTK_VARIABLE_NAME>>
for each cat_stk_<<STK_VARIABLE_NAME>> in <<STK_VARIABLE_PATH>><<STK_VARIABLE_NAME>>.Categories
    set iter_stk_<<STK_VARIABLE_NAME>> = <<STK_VARIABLE_PATH>><<STK_VARIABLE_NAME>>[cat_stk_<<STK_VARIABLE_NAME>>.name]
    set iter_<<UNSTK_VARIABLE_NAME>> = <<UNSTK_VARIABLE_PATH>><<UNSTK_VARIABLE_NAME>>[cat_stk_<<STK_VARIABLE_NAME>>.name]

    ' {@}

next
"""
    }
    result = {**TEMPLATE} # copy, not modify
    return prepare_syntax_substitutions( result, stk_variable_name, unstk_variable_name, unstk_variable_fieldname )

