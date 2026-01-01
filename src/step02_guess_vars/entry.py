# import os, time, re, sys
import os
from datetime import datetime, timezone
# from dateutil import tz
import argparse
from pathlib import Path
import json





if __name__ == '__main__':
    # run as a program
    import find_variables_stack
elif '.' in __name__:
    # package
    from . import find_variables_stack
else:
    # included with no parent package
    import find_variables_stack





# this is an algorithmic approach
# to choose the right vars that we stack
# all is done autocatically
# the code here finds the biggest number of categories that produce the biggest cumulative weight projected to biggest number of variables

# the result is: list of variables, list of categories, and additional data that helps us in debugging










def entry_point(runscript_config={}):

    time_start = datetime.now()
    script_name = 'mdmautostktoolsap autostacking suggest-loop-and-variables script'

    parser = argparse.ArgumentParser(
        description="Autostacking: guess which loops and variables to stack on",
        prog='mdd-autostacking-pick-variables'
    )
    parser.add_argument(
        '--inp-mdd-scheme',
        type=str,
        help='JSON with fields data from MDD Input File',
        required=True
    )
    parser.add_argument(
        '--config-priority-categories',
        help='Priority categories: examples of categories that you stack on',
        type=str,
        required=False
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
    if args.config_priority_categories:
        config['priority_categories_str'] = args.config_priority_categories


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
            raise Exception('Autostacking variable and loop guesser: Can\'t read input file as JSON: {msg}'.format(msg=e))
    
    print('{script_name}: script started at {dt}'.format(dt=time_start,script_name=script_name))

    data = []
    try:
        data = ([sect for sect in inp_mdd_scheme['sections'] if sect['name']=='fields'])[0]['content']
    except:
        pass

    result = find_variables_stack.find_variables_to_stack(data,config)
    
    result_json = json.dumps(result, indent=4)

    print('{script_name}: saving as "{fname}"'.format(fname=result_final_fname,script_name=script_name))
    with open(result_final_fname, "w") as outfile:
        outfile.write(result_json)

    time_finish = datetime.now()
    print('{script_name}: finished at {dt} (elapsed {duration})'.format(dt=time_finish,duration=time_finish-time_start,script_name=script_name))



if __name__ == '__main__':
    entry_point({'arglist_strict':True})
