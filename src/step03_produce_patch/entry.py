from datetime import datetime, timezone
import argparse
from pathlib import Path
import json




if __name__ == '__main__':
    # run as a program
    import patch_generate
    import util_prepare_vars
elif '.' in __name__:
    # package
    from . import patch_generate
    from . import util_prepare_vars
else:
    # included with no parent package
    import patch_generate
    import util_prepare_vars















def entry_point(runscript_config={}):

    time_start = datetime.now()
    script_name = 'mdmautostktoolsap mdd stk generate patch script'

    parser = argparse.ArgumentParser(
        description="MDD: produce patches for stk",
        prog='mdd-autostacking-prepare-patch'
    )
    parser.add_argument(
        '-1',
        '--inp-mdd-scheme',
        type=str,
        help='JSON with fields data from MDD Input File',
        required=True
    )
    parser.add_argument(
        '--var-list',
        help='Provide specs with variables to process',
        type=str,
        required=True
    )
    parser.add_argument(
        '--config-code-style',
        help='Optional flags to be passed with preferences on generated code style',
        type=str,
        required=False
    )
    parser.add_argument(
        '--output-patch-401',
        help='Set preferred output file name, with path,for patch file for 401_PreStack script',
        type=str,
        required=False
    )
    parser.add_argument(
        '--output-patch-402',
        help='Set preferred output file name, with path,for patch file for 402_Stack script',
        type=str,
        required=False
    )
    args = None
    args_rest = None
    if( ('arglist_strict' in runscript_config) and (not runscript_config['arglist_strict']) ):
        args, args_rest = parser.parse_known_args()
    else:
        args = parser.parse_args()
    
    inp_filename = ''
    if args.inp_mdd_scheme:
        inp_filename = Path(args.inp_mdd_scheme)
        inp_filename = '{inp_filename}'.format(inp_filename=inp_filename.resolve())
    else:
        raise FileNotFoundError('Inp source: file not provided; please use --inp-mdd-scheme option')

    config = {}
    if args.config_code_style:
        spec = args.config_code_style
        code_style_config = {}
        for flag in spec.split(','):
            if flag=='categorycheck-operator':
                code_style_config['assignment_op'] = 'operator'
            elif flag=='categorycheck-containsany':
                code_style_config['assignment_op'] = 'containsany'
            elif flag=='categorycheck-explicitcatlist':
                code_style_config['category_list_style'] = 'explicitcatlist'
            elif flag=='categorycheck-definedcategories':
                code_style_config['category_list_style'] = 'definedcategories'
            elif flag=='categorycheck-globaldmgrvar':
                code_style_config['category_list_style'] = 'globaldmgrvar'
            else:
                raise Exception('can\'t handle config option: {p}'.format(p=flag))
        config['code_style'] = {
            'category_check': code_style_config,
        }

    variable_specs = None
    variable_specs_file_name = None
    if args.var_list:
        variable_specs_file_name = Path(args.var_list)
        variable_specs_file_name = '{f}'.format(f=variable_specs_file_name.resolve())
        if not(Path(variable_specs_file_name).is_file()):
            raise FileNotFoundError('file not found: {fname}'.format(fname=variable_specs_file_name))
        with open(variable_specs_file_name) as f_l:
                try:
                    variable_specs = json.load(f_l)
                except json.JSONDecodeError as e:
                    # just a more descriptive message to the end user
                    # can happen if the tool is started two times in parallel and it is writing to the same json simultaneously
                    raise TypeError('MDD Patch: Can\'t read file with variable specs as JSON: {msg}'.format(msg=e))

    result_patch_401_fname = None
    if args.output_patch_401:
        result_patch_401_fname = Path(args.output_patch_401)
    else:
        raise FileNotFoundError('Out filename with 401 patch: file not provided; please use --output-patch-401 option')
    result_patch_402_fname = None
    if args.output_patch_402:
        result_patch_402_fname = Path(args.output_patch_402)
    else:
        raise FileNotFoundError('Out filename with 402 patch: file not provided; please use --output-patch-402 option')
    

    if not(Path(inp_filename).is_file()):
        raise FileNotFoundError('file not found: {fname}'.format(fname=inp_filename))

    inp_mdd_scheme = None
    with open(inp_filename) as f_l:
        try:
            inp_mdd_scheme = json.load(f_l)
        except json.JSONDecodeError as e:
            # just a more descriptive message to the end user
            # can happen if the tool is started two times in parallel and it is writing to the same json simultaneously
            raise TypeError('Patch: Can\'t read left file as JSON: {msg}'.format(msg=e))
    
    print('{script_name}: script started at {dt}'.format(dt=time_start,script_name=script_name))

    mdd_data_records = util_prepare_vars.get_mdd_data_records_from_input_data(inp_mdd_scheme)

    mdd_data_root = [ field for field in mdd_data_records if field['name']=='' ][0]
    mdd_data_questions = [ field for field in mdd_data_records if util_prepare_vars.detect_item_type_from_mdddata_fields_report(field['name'])=='variable' ]
    mdd_data_categories = [ cat for cat in mdd_data_records if util_prepare_vars.detect_item_type_from_mdddata_fields_report(cat['name'])=='category' ]

    variable_records = util_prepare_vars.prepare_variable_records(mdd_data_questions,mdd_data_categories,mdd_data_root)
    category_records = util_prepare_vars.prepare_category_records(mdd_data_questions,mdd_data_categories,mdd_data_root)

    config['datetime'] = time_start

    result_401, result_402 = patch_generate.generate_patches_stk(variable_specs,variable_records,category_records,config)
    
    result_json_401 = json.dumps(result_401, indent=4)
    print('{script_name}: saving as "{fname}"'.format(fname=result_patch_401_fname,script_name=script_name))
    with open(result_patch_401_fname, "w") as outfile:
        outfile.write(result_json_401)
    result_json_402 = json.dumps(result_402, indent=4)
    print('{script_name}: saving as "{fname}"'.format(fname=result_patch_402_fname,script_name=script_name))
    with open(result_patch_402_fname, "w") as outfile:
        outfile.write(result_json_402)

    time_finish = datetime.now()
    print('{script_name}: finished at {dt} (elapsed {duration})'.format(dt=time_finish,duration=time_finish-time_start,script_name=script_name))



if __name__ == '__main__':
    entry_point({'arglist_strict':True})
