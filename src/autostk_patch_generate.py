# import os, time, re, sys
import os
from datetime import datetime, timezone
# from dateutil import tz
import argparse
from pathlib import Path
import re
import json



# if __name__ == '__main__':
#     # run as a program
#     import helper_utility_wrappers
# elif '.' in __name__:
#     # package
#     from . import helper_utility_wrappers
# else:
#     # included with no parent package
#     import helper_utility_wrappers




def generate_patch_stk(variable_specs,mdd_data,config):
    result = []
    return result



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
        '--output-filename',
        help='Set preferred output file name, with path',
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

    # report_part_filename = re.sub( r'\.json\s*?$', '', Path(inp_filename).name )
    result_final_fname = None
    if args.output_filename:
        result_final_fname = Path(args.output_filename)
    else:
        raise FileNotFoundError('Inp source: file not provided; please use --inp-mdd-scheme option')
    

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

    mdd_data = []
    try:
        mdd_data = ([sect for sect in inp_mdd_scheme['sections'] if sect['name']=='fields'])[0]['content']
    except:
        pass

    result = generate_patch_stk(variable_specs,mdd_data,config)
    
    result_json = json.dumps(result, indent=4)

    print('{script_name}: saving as "{fname}"'.format(fname=result_final_fname,script_name=script_name))
    with open(result_final_fname, "w") as outfile:
        outfile.write(result_json)

    time_finish = datetime.now()
    print('{script_name}: finished at {dt} (elapsed {duration})'.format(dt=time_finish,duration=time_finish-time_start,script_name=script_name))



if __name__ == '__main__':
    entry_point({'arglist_strict':True})
