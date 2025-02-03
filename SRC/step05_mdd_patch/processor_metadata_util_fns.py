
import re



class MDMItemNotFound(Exception):
    """MDM item not found"""
def find_item(path,mdmitem):
    def extract_top_field_name(item_name):
        def val(s):
            return not not re.match(r'^(?:\w+\.)*\w+$',s)
        def norm(name):
            s = name
            s = re.sub(r'\[\s*?\{?\s*?(?:\w+|\.\.)?\s*?\}?\s*?\]','',s,flags=re.I)
            s = re.sub(r'\s','',s,flags=re.I)
            s = s.lower()
            if val(s):
                return s
            else:
                raise ValueError('looking for item in records, but name does not follow convention: {s}'.format(s=s))
        def trim_dots(s):
            return re.sub(r'^\s*?\.','',re.sub(r'\.\s*?$','',s))
        item_name_clean = norm(item_name)
        m = re.match(r'^\s*(\w+)((?:(?:\.\w+)*)?)\s*$',item_name_clean,flags=re.I)
        if m:
            return trim_dots(m[1]), trim_dots(m[2])
        else:
            raise ValueError('Can\'t extract field name from "{s}"'.format(s=item_name))
    if path=='':
        return mdmitem
    path_root, path_rest = extract_top_field_name(path)
    if mdmitem.Fields.Exist(path_root):
        result = mdmitem.Fields[path_root]
        if path_rest:
            return find_item(path_rest,result)
        else:
            return result
    else:
        raise MDMItemNotFound('Item not found: {s}'.format(s=path))





def detect_new_var_type_by_attrs(variable_attributes):
    result = None
    variable_is_plain = False
    variable_is_categorical = False
    variable_is_loop = False
    variable_is_grid = False
    variable_is_block = False
    for attr_name, attr_value in variable_attributes.items():
        if attr_name=='type':
            variable_is_plain = variable_is_plain or not not re.match(r'^\s*?plain\b',attr_value)
            variable_is_categorical = variable_is_categorical or not not re.match(r'^\s*?plain/(?:categorical|multipunch|singlepunch)',attr_value)
            variable_is_loop = variable_is_loop or not not re.match(r'^\s*?(?:array|grid|loop)\b',attr_value)
            variable_is_block = variable_is_block or not not re.match(r'^\s*?(?:block)\b',attr_value)
        if attr_name=='is_grid':
            variable_is_grid = variable_is_grid or not not re.match(r'^\s*?true\b',attr_value)
    if variable_is_plain or variable_is_categorical:
        result = 'plain'
    elif variable_is_loop:
        if variable_is_grid:
            result = 'grid'
        else:
            result = 'loop'
    elif variable_is_block:
        result = 'block'
    # flags = {
    #     'is_plain': variable_is_plain,
    #     'is_categorical': variable_is_categorical,
    #     'is_loop': variable_is_loop,
    #     'is_grid': variable_is_grid,
    #     'is_block': variable_is_block,
    # }
    return result



def create_mdm_variable( variable_name, mdmroot, variable_type ):
    mdmitem = None
    if variable_type == 'plain':
        mdmitem = mdmroot.CreateVariable(variable_name, variable_name)
    elif variable_type == 'grid':
        mdmitem = mdmroot.CreateGrid(variable_name, variable_name)
    elif variable_type == 'loop':
        mdmitem = mdmroot.CreateArray(variable_name, variable_name)
    elif variable_type == 'block':
        mdmitem = mdmroot.CreateClass(variable_name, variable_name)
    elif not variable_type:
        raise ValueError('Cat\'t create object: unrecognized type')
    else:
        raise ValueError('Can\'t handle this type of bject: {s}'.format(s=variable_type))
    return mdmitem





# warning: we are making updates to mdmroot
# not a clear function
# but that aligns with what we need
# it does not make sense to call .Dispatch() from a COM object and create a copy every time
# this would be slow
def update_metadata(mdmroot,position,variable_name,scripts,variable_attributes):


    try:
        mdmparent = find_item(position,mdmroot)
    except MDMItemNotFound as e:
        # if parent does not exist, we don't handle it here
        # let the exception pass through
        raise e
    
    # first we detect what type of item are we creating
    # because it looks similar in syntax but very different classes are used to create it
    # so we need to identify
    # if we are creating something that is a grid, or array, or a block with fields (called "class" within interfaces),
    # note, "grid" and "loop" are very different classes, even final scripts are almost identical
    # (grids have "expand grid" modifier and loops have just "expand" modifier, while modifiers are usually ignored...
    # so it's funny that such little difference is so important at the moment of creating an object),
    # and final objects are almost similar
    variable_type = detect_new_var_type_by_attrs(variable_attributes)

    # ok, we detected format
    # let's go ahead and create this variable
    mdmitem_add = create_mdm_variable( variable_name, mdmroot, variable_type )
    
    # let's update all other attributes indicated with attributes
    for attr_name, attr_value in variable_attributes.items():
        # if attr_name=='object_type_value':
        #     mdmitem_add.ObjectTypeValue = attr_value
        # we don't have to set .ObjectTypeValue and we can't set .ObjectTypeValue
        # this attribute is already set if we used the right interface -
        # - CreateGrid(), CreateArray(), CreateVariable(), CreateElements()... etc methods
        # will already create on object derived from the right interface - IGrid, IArray, etc...
        # and .ObjectTypeValue will be already set
        if attr_name=='data_type':
            mdmitem_add.DataType = attr_value
        elif attr_name=='Label':
            mdmitem_add.Label = attr_value if attr_value else ''
        else:
            # we don't handle anything else other than DataType or Label
            # I don't know why are we doing it with DataType and Label,
            # because all should be captured in scripts - labels, data types, etc... everything
            # however, I had an issue that labels were disappearing when switching from Question to Analysis context
            # that's why I am passing labels separately arbitrary so that we are sure that labels are set to correct values
            # and passing DataTypes - that's probably meaningless
            pass
    
    mdmitem_add.Script = scripts
    mdmparent.Fields.Add(mdmitem_add) # all tree is updated, and mdmroot now holds updated scripts
    return mdmroot





