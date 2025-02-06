import re





if __name__ == '__main__':
    # run as a program
    import patch_classes
    import util_vars
    import util_produce_code_edits_templates as templates
elif '.' in __name__:
    # package
    from . import patch_classes
    from . import util_vars
    from . import util_produce_code_edits_templates as templates
else:
    # included with no parent package
    import patch_classes
    import util_vars
    import util_produce_code_edits_templates as templates





# TODO: pass CONFIG_CHECK_CATEGORIES_STYLE in config

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
# CONFIG_CHECK_CATEGORIES_STYLE = 'OD'
# CONFIG_CHECK_CATEGORIES_STYLE = 'CE'
# CONFIG_CHECK_CATEGORIES_STYLE = 'OE'
# CONFIG_CHECK_CATEGORIES_STYLE = 'CG'
CONFIG_CHECK_CATEGORIES_STYLE = 'OG'






def trim_lines(s):
    if re.match(r'^\s*$',s):
        return ''
    s = re.sub(r'(^\s*(?:\s*?\n)*\n)(.*?$)',lambda m: m[2],s,flags=re.DOTALL)
    s = re.sub(r'(^.*?\n)(\s*(?:\s*?\n)*$)',lambda m: m[1],s,flags=re.DOTALL)
    return s
def add_indent(s,indent):
    # s = '\n'+s # I am adding a line break at the beginning to make wotking with regexs easier
    # s = re.sub(r'(\n)',lambda m: '{k}{i}'.format(i=indent,k=m[1]),s)
    # s = s[1:] # remove line break at the beginning that we added
    # return s
    if s[-1]=='\n':
        s = s[:-1]
        s = re.split(r'\n',s,flags=re.I|re.DOTALL)
        s = [indent+p for p in s]
        s = '\n'.join(s)
        s = s + '\n'
    else:
        s = re.split(r'\n',s,flags=re.I|re.DOTALL)
        s = [indent+p for p in s]
        s = '\n'.join(s)
    return s

def make_local_var_name(path,field_name):
    txt =  util_vars.trim_dots( '{path}.{field_name}'.format(path=path,field_name=field_name) )
    txt = txt.replace('.','_')
    return txt

def find_mdmparent(mdmitem):
    parent = mdmitem.Parent
    if parent:
        if '@class' in parent.Name:
            return find_mdmparent(parent)
        else:
            return parent
    else:
        raise Exception('failed to find parent')






def prepare_syntax_substitutions( d, stk_variable_name='', unstk_variable_name='' ):
    result = {}
    assert not '.' in stk_variable_name
    assert not '.' in unstk_variable_name
    # assert not '.' in unstk_variable_fieldname
    for key in d:
        text = '{s}'.format(s=d[key]) # this line ensures we are working with a copy not reference
        text = text.replace('<<VAR_LVALUE_NAME>>',stk_variable_name)
        text = text.replace('<<VAR_RVALUE_NAME>>',unstk_variable_name)
        # text = text.replace('<<VAR_RVALUE_FIELDNAME>>',unstk_variable_fieldname)
        result[key] = text
    result['stk_variable_name'] = stk_variable_name
    result['unstk_variable_name'] = unstk_variable_name
    # result['unstk_variable_fieldname'] = unstk_variable_fieldname
    return result

def generate_recursive_onnextcase_code(mdmitem_stk,mdmitem_ref):
    def recursive(mdmitem_stk,mdmitem_ref,indent,name_part):
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
    result = result.replace('<<DEST_PATH>>','<<VAR_LVALUE_PATH>>').replace('<<SOURCE_PATH>>','<<VAR_RVALUE_PATH>><<VAR_RVALUE_NAME>>[cbrand].')
    return result






def generate_code_categories_containsany( variable_with_categories_name, categories_iterating_over, category_check, code_style={} ):
    
    # class Cat:
    #     # the only goal is to provide conversion to str method
    #     # so that we don't care if we pass mdm categories, dict with 'name' attribute, or just categories as strings
    #     # maybe having a class looked more aestethically appealing to me
    #     # but this could have been just a function
    #     def __init__(self,o):
    #         self.o = o
    #     def __str__(self):
    #         if isinstance(self.o,str):
    #             return '{s}'.format(s=self.o)
    #         elif isinstance(self.o,dict):
    #             return '{s}'.format(s=self.o['name'])
    #         # elif isinstance(self.o,win32com.client.CDispatch):
    #         # I don't want to have unnecessary dependency in this file just to check if a category is an mdm category
    #         # I can just check against a class name as a string
    #         elif 'win32com.client.CDispatch' in '{cl}'.format(cl=self.o.__class__):
    #             return '{s}'.format(s=self.o.Name)
    #         else:
    #             return '{s}'.format(s=self.o)

    def iter_cat_names(mdmelements):
        assert 'win32com.client.CDispatch' in '{cl}'.format(cl=mdmelements.__class__), 'generate_code_categories_containsany: iterating over categories_iterating_over: categories should be of IElements interface'
        for mdmcat in mdmelements:
            if mdmcat.IsReference:
                # raise Exception('oh no shared list')
                shared_list_name = mdmcat.ReferenceName
                shared_list_name = re.sub(r'[\^/\\\.\{\}#\s]','',shared_list_name,flags=re.I|re.DOTALL)
                assert re.match(r'^\w+$',shared_list_name,flags=re.I|re.DOTALL), 'generate_code_categories_containsany: iter_cat_names: trying to collect categories and iterate over mdm elements, and trying to refer to a shared list, and can\'t extract proper name, bad characters still in name: {s}'.format(s=mdmcat.ReferenceName)
                mdmsharedlist = mdmcat.Document.Types[shared_list_name]
                for child in iter_cat_names(mdmsharedlist):
                    yield child
            elif mdmcat.Type==0:
                yield mdmcat.Name
            else:
                for child in iter_cat_names(mdmcat):
                    yield child

    
    assert categories_iterating_over is not None, 'warning: generate_code_categories_containsany: categories_iterating_over is None'

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
        raise ValueError('generate_code_categories_containsany: unrecognized code_style_assignment_op: {s}'.format(s=code_style_assignment_op))
    if code_style_category_list_style=='definedcategories':
        result = result.replace('{<<CATLIST>>}','<<VARNAME>>.DefinedCategories()')
    elif code_style_category_list_style=='explicitcatlist':
        result = result.replace('<<CATLIST>>',','.join([cat_name for cat_name in iter_cat_names(categories_iterating_over)]))
    elif code_style_category_list_style=='globaldmgrvar':
        result = result.replace('{<<CATLIST>>}','dmgrGlobal.<<DEFINEDCATEGORIESGLOBALVAR>>')
        # raise ValueError('generating code with dmgrGlobal - not implemented yet (it is more complicated than it\'s looking)')
    else:
        raise ValueError('generate_code_categories_containsany: unrecognized code_style_category_list_style: {s}'.format(s=code_style_category_list_style))
    result = result.replace('<<CATCHECK>>',category_check)
    result = result.replace('<<VARNAME>>',variable_with_categories_name)

    return result




def generate_patches_outerstkloop_walkthrough( mdmitem_stk, mdmitem_unstk, stk_variable_name, stk_variable_path, unstk_variable_name ):
    template = templates.TEMPLATE_OUTERSTK_LOOP_CODE
    for chunk in generate_patches( template, mdmitem_stk, mdmitem_unstk, stk_variable_name, stk_variable_path, unstk_variable_name, mdmitem_unstk_iterlevel=mdmitem_unstk ):
        yield chunk

def generate_patches_loop_unstack_structural( mdmitem_stk, mdmitem_unstk, stk_variable_name, stk_variable_path, unstk_variable_name ):
    template = templates.TEMPLATE_STACK_LOOP
    for chunk in generate_patches( template, mdmitem_stk, mdmitem_unstk, stk_variable_name, stk_variable_path, unstk_variable_name, mdmitem_unstk_iterlevel=find_mdmparent(mdmitem_unstk) ):
        yield chunk

def generate_patches_unstack_categorical_yn( mdmitem_stk, mdmitem_unstk, stk_variable_name, stk_variable_path, unstk_variable_name ):
    template = templates.TEMPLATE_STACK_CATEGORICALYN
    for chunk in generate_patches( template, mdmitem_stk, mdmitem_unstk, stk_variable_name, stk_variable_path, unstk_variable_name, mdmitem_unstk_iterlevel=mdmitem_unstk ):
        yield chunk

def generate_patches_loop_walkthrough( mdmitem_stk, mdmitem_unstk, stk_variable_name, stk_variable_path, unstk_variable_name ):
    template = templates.TEMPLATE_LOOP_PARENT
    for chunk in generate_patches( template, mdmitem_stk, mdmitem_unstk, stk_variable_name, stk_variable_path, unstk_variable_name, mdmitem_unstk_iterlevel=mdmitem_unstk ):
        yield chunk

def generate_patches( template, mdmitem_stk, mdmitem_unstk, stk_variable_name, stk_variable_path, unstk_variable_name, mdmitem_unstk_iterlevel ):

    result = {**template} # copy, not modify

    is_recursive = '<<RECURSIVE>>' in result['code']
    is_iterative = '<<CATEGORIESCHECK>>' in result['code']

    if is_recursive:
        is_simple = mdmitem_stk.ObjectTypeValue==0
        result_add = generate_recursive_onnextcase_code(mdmitem_stk,mdmitem_unstk)
        result_add = '\n'+trim_lines(result_add)+'\n'
        if is_simple:
            # maybe we don't need unnecessary line breaks and comments for just "GV"
            result_add = re.sub(r'(^|\n)((?:\s*?(?:\'[^\n]*?)?\s*?\n)*)',lambda m: m[1],result_add,flags=re.I|re.DOTALL)
        result['code'] = re.sub(r'^(.*?\n)((\s*?)<<RECURSIVE>>[^\n]*?\n)(.*?)$',lambda m: '{code_begin}{code_add}{code_end}'.format(code_begin=m[1],code_end=m[4],code_add=add_indent(result_add,indent=m[3])),result['code'],flags=re.I|re.DOTALL)
    
    if is_iterative:
        
        variable_local_name = make_local_var_name(path=stk_variable_path,field_name=stk_variable_name)
        variable_definedcategories_local_name = 'DefinedCategories_{n}'.format(n=variable_local_name)

        code_style_configletter1 = CONFIG_CHECK_CATEGORIES_STYLE[0] if len(CONFIG_CHECK_CATEGORIES_STYLE)>=2 else None
        code_style_configletter2 = CONFIG_CHECK_CATEGORIES_STYLE[1] if len(CONFIG_CHECK_CATEGORIES_STYLE)>=2 else None
        code_style = {
            'assignment_op': 'operator' if code_style_configletter1=='O' else ( 'containsany' if code_style_configletter1=='C' else '???' ),
            'category_list_style': 'definedcategories' if code_style_configletter2=='D' else ( 'explicitcatlist' if code_style_configletter2=='E' else ( 'globaldmgrvar' if code_style_configletter2=='G' else '???' ) ),
        }
        code_style_compare_alt1 = {
            **code_style,
            'category_list_style': 'explicitcatlist' if not(code_style['category_list_style']=='explicitcatlist') else 'definedcategories',
        }
        code_style_compare_alt2 = {
            **code_style,
            'category_list_style': 'globaldmgrvar' if not(code_style['category_list_style']=='globaldmgrvar') else 'definedcategories',
        }
        if code_style_configletter2=='G':
            # variable_ref_str = 'DmgrJob.Questions["FirstSecondBank"].Item[0].GV'
            # why this part ".Item[0]" is necessary?
            # friendly speaking, I don't know
            # I think it means that
            # when the syntax is
            # ... } fields - ( ...
            # that "fields -" creates a level that also can be addressed
            # but that's not an actual variable with a name, so we need to skip it, that's why we just add ".Item[0]", to step over this level
            # if we try to find its name, it shows category names
            if not mdmitem_unstk_iterlevel:
                raise Exception('why is that?')
            mdmitem_processed = mdmitem_unstk_iterlevel
            variable_ref_str = ''
            variable_definedcategories_local_name = ''
            field_name = mdmitem_processed.Name
            while True:
                if field_name:
                    variable_ref_str = '.' + field_name + variable_ref_str
                    variable_definedcategories_local_name = '_' + field_name + variable_definedcategories_local_name
                mdmitem_processed = mdmitem_processed.Parent
                field_name = None
                if not mdmitem_processed:
                    break
                elif not mdmitem_processed.Name:
                    continue
                elif '@class' in mdmitem_processed.Name:
                    # see explanation for that ".Item[0]" above - that's actually that level that we need to step over
                    continue
                field_name = mdmitem_processed.Name
                if mdmitem_processed.ObjectTypeValue==1 or mdmitem_processed.ObjectTypeValue==2:
                    variable_ref_str = '.' + 'Item[0]' + variable_ref_str
            variable_ref_str = 'DmgrJob.Questions' + variable_ref_str
            variable_definedcategories_local_name = 'DefinedCategories' + variable_definedcategories_local_name

            result_onjobstart_edits = '\t\' <<VARNAME>>...\n\tDmgrGlobal.Add("<<VARNAME>>")\n\tDmgrGlobal.<<VARNAME>> = <<VARREF>>.DefinedCategories()\n'.replace('<<VARNAME>>',variable_definedcategories_local_name).replace('<<VARREF>>',variable_ref_str)
            yield patch_classes.PatchSectionOtherInsert(
                position = patch_classes.Position(-1),
                section_name = 'OnJobStart',
                comment = {
                    'source_from': unstk_variable_name,
                    'source_for': stk_variable_name,
                    'target': '401_PreStack_script',
                },
                payload = {
                    'variable': stk_variable_name,
                    'lines': result_onjobstart_edits,
                },
            )
        code_script = result['code']
        if not re.match(r'\s*\n\s*$',code_script,flags=re.I|re.DOTALL):
            code_script = code_script + '\n'
        find_regex_results = re.finditer(re.compile(r'(^|\n)(\s*?)([^\s][^\n]*?)(<<CATEGORIESCHECK>>)([^\n]*?)(\s*?\n)',flags=re.I|re.DOTALL),code_script)
        find_regex_results =  [m for m in find_regex_results] if find_regex_results else [] # so that I can refer to multiple items of a generator multiple times
        while len(find_regex_results)>0:
            repl = find_regex_results[0]
            # span(1) = prev linebreak
            # span(2) = indent
            # span(3) = leading part of "if" statement, not including indent
            # span(4) = logic expr within "if" statement
            # span(5) = trailing part of "if" statement
            # span(6) = trailing linebreak
            indent = code_script[repl.span(2)[0]:repl.span(2)[1]]
            part_leading = code_script[:repl.span(2)[0]]
            part_trailing = code_script[repl.span(6)[1]:]
            statement_script = code_script[repl.span(3)[0]:repl.span(5)[1]]
            statement_script_main = statement_script.replace( '<<CATEGORIESCHECK>>', generate_code_categories_containsany( variable_with_categories_name='<<VAR_RVALUE_PATH>><<VAR_RVALUE_NAME>>', categories_iterating_over=mdmitem_unstk_iterlevel.Elements, category_check='cbrand', code_style=code_style ) )
            if code_style['category_list_style'] == 'definedcategories':
                statement_script_main = statement_script_main + ' \' warning: this is slow!'
            statement_script_alt1 = statement_script.replace( '<<CATEGORIESCHECK>>', generate_code_categories_containsany( variable_with_categories_name='<<VAR_RVALUE_PATH>><<VAR_RVALUE_NAME>>', categories_iterating_over=mdmitem_unstk_iterlevel.Elements, category_check='cbrand', code_style=code_style_compare_alt1 ) )
            if code_style_compare_alt1['category_list_style'] == 'definedcategories':
                statement_script_alt1 = statement_script_alt1 + ' \' warning: this is slow!'
            statement_script_alt2 = statement_script.replace( '<<CATEGORIESCHECK>>', generate_code_categories_containsany( variable_with_categories_name='<<VAR_RVALUE_PATH>><<VAR_RVALUE_NAME>>', categories_iterating_over=mdmitem_unstk_iterlevel.Elements, category_check='cbrand', code_style=code_style_compare_alt2 ) )
            if code_style_compare_alt2['category_list_style'] == 'definedcategories':
                statement_script_alt2 = statement_script_alt2 + ' \' warning: this is slow!'
            code_script = part_leading + indent + '\' ' + statement_script_alt2 + '\n' + indent + '\' ' + statement_script_alt1 + '\n' + indent + '' + statement_script_main + '\n' + part_trailing
            find_regex_results = re.finditer(re.compile(r'(^|\n)(\s*?)([^\s][^\n]*?)(<<CATEGORIESCHECK>>)([^\n]*?)(\s*?\n)',flags=re.I|re.DOTALL),code_script)
            find_regex_results =  [m for m in find_regex_results] if find_regex_results else [] # so that I can refer to multiple items of a generator multiple times
        
        code_script = code_script.replace('<<DEFINEDCATEGORIESGLOBALVAR>>',variable_definedcategories_local_name)
        result['code'] = code_script
    
    result_edits = prepare_syntax_substitutions( result, stk_variable_name, unstk_variable_name )
    yield patch_classes.PatchSectionOnNextCaseInsert(
        position = patch_classes.Position(stk_variable_path),
        comment = {
            'source_from': unstk_variable_name,
            'target': '401_PreStack_script',
        },
        payload = {
            'variable': stk_variable_name,
            'lines': result_edits,
        },
    )
