# import os, time, re, sys
from datetime import datetime, timezone
# from dateutil import tz
import argparse
from pathlib import Path
import json




if __name__ == '__main__':
    # run as a program
    import util_edits as utility_edits
    import util_metadata as utility_metadata
elif '.' in __name__:
    # package
    from . import util_edits as utility_edits
    from . import util_metadata as utility_metadata
else:
    # included with no parent package
    import util_edits as utility_edits
    import util_metadata as utility_metadata








def entry_point(runscript_config={}):

    time_start = datetime.now()
    script_name = 'mdmautostktoolsap mdd patch script'

    parser = argparse.ArgumentParser(
        description="MDD: produce patches and/or scripts from patches",
        prog='mdd-patch'
    )
    parser.add_argument(
        '-1',
        '--inp-mdd-scheme',
        type=str,
        help='JSON with fields data from MDD Input File',
        required=True
    )
    parser.add_argument(
        '--action',
        help='Param to pass patch type: there are special types for stacking, etc...',
        type=str,
        required=False
    )
    parser.add_argument(
        '--patch',
        help='Provide specs',
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

    action = None
    if args.action:
        if args.action=='generate-for-stk':
            action = 'generate-for-stk'
        elif args.action=='generate-scripts-metadata':
            action = 'generate-scripts-metadata'
        elif args.action=='generate-scripts-edits':
            action = 'generate-scripts-edits'
        elif args.action=='generate-scripts':
            raise TypeError('MDD patch script: general "generate-scripts" action is not supported, please use "generate-scripts-metadata" or "generate-scripts-edits"')
        else:
            raise TypeError('MDD patch script: this action is not implemented yet: "{a}"'.format(a=args.action))

    patch_specs = None
    patch_specs_file_name = None
    if args.patch:
        patch_specs_file_name = Path(args.patch)
        patch_specs_file_name = '{f}'.format(f=patch_specs_file_name.resolve())
        if not(Path(patch_specs_file_name).is_file()):
            raise FileNotFoundError('file not found: {fname}'.format(fname=patch_specs_file_name))
        with open(patch_specs_file_name) as f_l:
                try:
                    patch_specs = json.load(f_l)
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

    result = None
    if action=='generate-for-stk':
        raise Exception('generating patch for stk is not implemented here, please call a different script')
    elif action=='generate-scripts-metadata':
        result = utility_metadata.generate_scripts(mdd_data,patch_specs,config)
    elif action=='generate-scripts-edits':
        result = utility_edits.generate_scripts(mdd_data,patch_specs,config)
    elif action=='generate-scripts':
            raise TypeError('MDD patch script: general "generate-scripts" action is not supported, please use "generate-scripts-metadata" or "generate-scripts-edits"')
    else:
        raise TypeError('MDD patch script: this action is not implemented yet: "{a}"'.format(a=action))
    
    # result_json = json.dumps(result, indent=4)

    print('{script_name}: saving as "{fname}"'.format(fname=result_final_fname,script_name=script_name))
    with open(result_final_fname, "w",encoding='utf-8') as outfile:
        outfile.write(result)

    time_finish = datetime.now()
    print('{script_name}: finished at {dt} (elapsed {duration})'.format(dt=time_finish,duration=time_finish-time_start,script_name=script_name))



if __name__ == '__main__':
    entry_point({'arglist_strict':True})
