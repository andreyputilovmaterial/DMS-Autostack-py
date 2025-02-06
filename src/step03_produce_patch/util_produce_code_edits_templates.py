



TEMPLATE_OUTERSTK_LOOP_CODE = {
        'variable_lvalue_path': 'iter_stk.',
        'variable_rvalue_path': '',
        'code': """
dim brand, cbrand, iter_stk

' <<VAR_LVALUE_NAME>>
for each brand in <<VAR_LVALUE_NAME>>.categories
cbrand = ccategorical(brand)
    ' ADD YOUR EXPRESSION HERE
    ' if DV_BrandAssigned=*cbrand then
    if True then
    'with <<VAR_LVALUE_NAME>>[cbrand]
    set iter_stk = <<VAR_LVALUE_PATH>><<VAR_LVALUE_NAME>>[cbrand]
        
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

TEMPLATE_STACK_LOOP = {
        'variable_lvalue_path': '<<VAR_LVALUE_PATH>><<VAR_LVALUE_NAME>>.', # we need it
        'variable_rvalue_path': '<<VAR_RVALUE_PATH>><<VAR_RVALUE_NAME>>[cbrand].', # we need it; don't add variable name - it is already generated with recursive code
        'code': """
' <<VAR_LVALUE_NAME>>
' from: <<VAR_RVALUE_NAME>>
'if <<CATEGORIESCHECKEXAMPLE>> then
if <<CATEGORIESCHECK>> then
    <<RECURSIVE>>
    ' {@}
end if
"""
}

TEMPLATE_STACK_CATEGORICALYN = {
        'variable_lvalue_path': '<<VAR_LVALUE_PATH>><<VAR_LVALUE_NAME>>', # we definitely not need it and it will not work, it will break, and that's some good news, we'll see that something is off
        'variable_rvalue_path': '<<VAR_RVALUE_PATH>><<VAR_RVALUE_NAME>>', # we definitely not need it and it will not work, it will break, and that's some good news, we'll see that something is off
        'code': """
' <<VAR_LVALUE_NAME>>
' from: <<VAR_RVALUE_NAME>>
'if <<CATEGORIESCHECKEXAMPLE>> then
if <<CATEGORIESCHECK>> then
    <<VAR_LVALUE_PATH>><<VAR_LVALUE_NAME>> = iif( <<VAR_RVALUE_PATH>><<VAR_RVALUE_NAME>> is null, null, iif( <<VAR_RVALUE_PATH>><<VAR_RVALUE_NAME>>=*cbrand, {Yes}, {No} ) )
end if
' {@}
"""
}

TEMPLATE_LOOP_PARENT = {
        'variable_lvalue_path': 'iter_stk_<<VAR_LVALUE_NAME>>.', # we certainly need
        'variable_rvalue_path': 'iter_<<VAR_RVALUE_NAME>>.', # we certainly need it
        'code': """
' <<VAR_LVALUE_NAME>>
' from: <<VAR_RVALUE_NAME>>
' process everything within this loop
dim cat_stk_<<VAR_LVALUE_NAME>>, iter_stk_<<VAR_LVALUE_NAME>>, iter_<<VAR_RVALUE_NAME>>
for each cat_stk_<<VAR_LVALUE_NAME>> in <<VAR_LVALUE_PATH>><<VAR_LVALUE_NAME>>.Categories
    set iter_stk_<<VAR_LVALUE_NAME>> = <<VAR_LVALUE_PATH>><<VAR_LVALUE_NAME>>[cat_stk_<<VAR_LVALUE_NAME>>.name]
    set iter_<<VAR_RVALUE_NAME>> = <<VAR_RVALUE_PATH>><<VAR_RVALUE_NAME>>[cat_stk_<<VAR_LVALUE_NAME>>.name]

    ' {@}

next
"""
}