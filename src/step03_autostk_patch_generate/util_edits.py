import re


# code templates

# what code are we generating here
# is something like `.BrandFamiliarity_YN = BrandFamiliarity[cbrand].GV`
# the pattern is `stk_var = original_var`
# sometimes it is not just a top-level variable, we need to iterate over something
# so `iter.GV = unstk_iter.GV`, or something like this
# and "variable_stk_path" and "variable_unstacked_path" are holding the name "iter" and "unstk_iter" here
CONFIG_CODE_LOOP_OUTERSTKLOOP = {
    'variable_stk_path': 'iter_stk.',
    'variable_unstacked_path': '',
    'code': """
dim brand, cbrand, iter_stk

' <<STK_VARIABLE_NAME>>
for each brand in <<STK_VARIABLE_NAME>>.categories
cbrand = ccategorical(brand)
'with <<STK_VARIABLE_NAME>>[cbrand]
set iter_stk = <<STK_VARIABLE_PATH>><<STK_VARIABLE_NAME>>[cbrand]
	
	' STK_ID
	iter_stk.STK_ID = ctext(brand.name)+"_"+ctext(Respondent.ID)
	
	' STK_Iteration
	iter_stk.STK_Iteration = cbrand
	
	' {@}
	
'end with
next
set iter_stk = null
"""
}

CONFIG_CODE_LOOP_UNSTACK_SIMPLE = {
    'variable_stk_path': '<<STK_VARIABLE_PATH>><<STK_VARIABLE_NAME>>.', # not sure we need it, we don't expect that we need to process subfields separately; we need to find some really complicated tests to check it, where we stack at 2 different levels - I can imaging this could happen, let's find some tests and see
    'variable_unstacked_path': '<<UNSTK_VARIABLE_PATH>><<UNSTK_VARIABLE_NAME>>[cbrand].<<UNSTK_VARIABLE_FIELDNAME>>.', # not sure we need it, we don't expect that we need to process subfields separately; we need to find some really complicated tests to check it, where we stack at 2 different levels - I can imaging this could happen, let's find some tests and see
    'code': """
' <<STK_VARIABLE_NAME>>
' from: <<UNSTK_VARIABLE_NAME>>
if containsany( <<UNSTK_VARIABLE_PATH>><<UNSTK_VARIABLE_NAME>>.DefinedCategories(), cbrand ) then
    <<STK_VARIABLE_PATH>><<STK_VARIABLE_NAME>> = <<UNSTK_VARIABLE_PATH>><<UNSTK_VARIABLE_NAME>>[cbrand].<<UNSTK_VARIABLE_FIELDNAME>>
end if
' {@}
"""
}

CONFIG_CODE_LOOP_UNSTACK_OBJECT_LOOP_OR_BLOCK = {
    'variable_stk_path': '<<STK_VARIABLE_PATH>><<STK_VARIABLE_NAME>>.', # we need it
    'variable_unstacked_path': '<<UNSTK_VARIABLE_PATH>><<UNSTK_VARIABLE_NAME>>[cbrand].', # we need it; don't add variable name - it is already generated with recursive code
    'code': """
' <<STK_VARIABLE_NAME>>
' from: <<UNSTK_VARIABLE_NAME>>
' TODO: generate code iterating over all categories and subfields
if containsany( <<UNSTK_VARIABLE_PATH>><<UNSTK_VARIABLE_NAME>>.DefinedCategories(), cbrand ) then
    ' {@}
end if
"""
}

CONFIG_CODE_LOOP = {
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

CONFIG_CODE_CATEGORICALYN = {
    'variable_stk_path': '<<STK_VARIABLE_PATH>><<STK_VARIABLE_NAME>>', # we definitely not need it and it will not work, it will break, and that's some good news, we'll see that something is off
    'variable_unstacked_path': '<<UNSTK_VARIABLE_PATH>><<UNSTK_VARIABLE_NAME>>', # we definitely not need it and it will not work, it will break, and that's some good news, we'll see that something is off
    'code': """
' <<STK_VARIABLE_NAME>>
' from: <<UNSTK_VARIABLE_NAME>>
<<STK_VARIABLE_PATH>><<STK_VARIABLE_NAME>> = iif( <<UNSTK_VARIABLE_PATH>><<UNSTK_VARIABLE_NAME>> is null, null, iif( <<UNSTK_VARIABLE_PATH>><<UNSTK_VARIABLE_NAME>>=*cbrand, {Yes}, {No} ) )
' {@}
"""
}


def prepare_syntax_substitutions( d, stk_variable_name='', unstk_variable_name='', unstk_variable_fieldname='' ):
    result = {}
    assert not '.' in stk_variable_name
    assert not '.' in unstk_variable_name
    assert not '.' in unstk_variable_fieldname
    for key in d:
        # first, copy, to ensure we are not modifying the reference, we are moifying the copy
        text = '{s}'.format(s=d[key])
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








def generate_code_outerstkloop_walkthrough( mdmitem_stk, mdmitem_unstk, stk_variable_name, unstk_variable_name, unstk_variable_fieldname ):
    result = {**CONFIG_CODE_LOOP_OUTERSTKLOOP} # copy, not modify
    return prepare_syntax_substitutions( result, stk_variable_name, unstk_variable_name, unstk_variable_fieldname )

def generate_code_loop_unstack_simple( mdmitem_stk, mdmitem_unstk, stk_variable_name, unstk_variable_name, unstk_variable_fieldname ):
    result = {**CONFIG_CODE_LOOP_UNSTACK_SIMPLE} # copy, not modify
    return prepare_syntax_substitutions( result, stk_variable_name, unstk_variable_name, unstk_variable_fieldname )

def generate_code_loop_unstack_structural( mdmitem_stk, mdmitem_unstk, stk_variable_name, unstk_variable_name, unstk_variable_fieldname ):
    result = {**CONFIG_CODE_LOOP_UNSTACK_OBJECT_LOOP_OR_BLOCK} # copy, not modify
    result_add = generate_recursive_onnextcase_code(mdmitem_stk,mdmitem_unstk)
    result['code'] = re.sub(r'^(.*?)\n\s*?\'\s*?\{@\}[^\n]*?\n(.*?)$',lambda m: '{code_begin}{code_add}{code_end}'.format(code_begin=re.sub(r'\n?$','\n',m[1],flags=re.I|re.DOTALL),code_end=re.sub(r'\n?$','\n',m[2],flags=re.I|re.DOTALL),code_add=re.sub(r'\n?$','\n',result_add,flags=re.I|re.DOTALL)),result['code'],flags=re.I|re.DOTALL)
    return prepare_syntax_substitutions( result, stk_variable_name, unstk_variable_name, unstk_variable_fieldname )

def generate_code_unstack_categorical_yn( mdmitem_stk, mdmitem_unstk, stk_variable_name, unstk_variable_name, unstk_variable_fieldname ):
    result = {**CONFIG_CODE_CATEGORICALYN} # copy, not modify
    return prepare_syntax_substitutions( result, stk_variable_name, unstk_variable_name, unstk_variable_fieldname )

def generate_code_loop_walkthrough( mdmitem_stk, mdmitem_unstk, stk_variable_name, unstk_variable_name, unstk_variable_fieldname ):
    result = {**CONFIG_CODE_LOOP} # copy, not modify
    return prepare_syntax_substitutions( result, stk_variable_name, unstk_variable_name, unstk_variable_fieldname )

