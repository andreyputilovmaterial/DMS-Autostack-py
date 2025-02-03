# import os, time, re, sys
import sys
from datetime import datetime, timezone
# from dateutil import tz
import argparse
from pathlib import Path
import json




if __name__ == '__main__':
    # run as a program
    import handler_dms
elif '.' in __name__:
    # package
    from . import handler_dms
else:
    # included with no parent package
    import handler_dms








def entry_point(runscript_config={}):

    time_start = datetime.now()
    script_name = 'mdmtoolsap mdd patch script'

    parser = argparse.ArgumentParser(
        description="MDD: produce patches and/or scripts from patches",
        prog='mdd-patch'
    )
    parser.add_argument(
        '--inp-filename',
        help='Set preferred input file name, with path',
        type=str,
        required=False
    )
    parser.add_argument(
        '--inp-type',
        help='How to process the file, is it a dms file, or mdd file, mrs script...',
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
    
    config = {}

    FileLoader = None
    if not args.inp_type:
        raise Exception('file type not specified, please use --inp-type option')
    elif args.inp_type=='dms':
        FileLoader = handler_dms.FileLoader
    elif args.inp_type=='mdd':
        raise Exception('can\'t handle mdd: not implemented')
    elif args.inp_type=='mrs':
        raise Exception('can\'t handle mrs: not implemented')
    else:
        raise Exception('unsupported file type: "{t}"'.format(t=args.inp_type))


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

    inp_fname = None
    if args.inp_filename:
        inp_fname = Path(args.inp_filename)
    else:
        raise FileNotFoundError('Inp source: file not provided; please use --inp-filename option')
    if not(Path(inp_fname).is_file()):
        raise FileNotFoundError('file not found: {fname}'.format(fname=inp_fname))
    
    result_final_fname = None
    if args.output_filename:
        result_final_fname = Path(args.output_filename)
    else:
        raise FileNotFoundError('Out source: file not provided; please use --output-filename option')
    
    print('{script_name}: script started at {dt}'.format(dt=time_start,script_name=script_name))

    data = None
    with open(inp_fname,'r',encoding='utf-8') as inp_file_obj:
        data = inp_file_obj.read()

    data_loaded = FileLoader(data)
    for i, chunk in enumerate(patch_specs):
        try:
            data_loaded.apply_patch(chunk)
        except Exception as e:
            print('failed when applying patch #{n} on {fname}'.format(n=i,fname=inp_fname), file=sys.stderr)
            print('for debugging purposes, the patch chunk {action} was:\n{t}...'.format(t=json.dumps(chunk),action=chunk['action'] if 'action' in chunk else '-')[:245], file=sys.stderr)
            raise e

    result_str = '{t}'.format(t=data_loaded)

    print('{script_name}: saving as "{fname}"'.format(fname=result_final_fname,script_name=script_name))
    with open(result_final_fname, "w",encoding='utf-8') as outfile:
        outfile.write(result_str)

    time_finish = datetime.now()
    print('{script_name}: finished at {dt} (elapsed {duration})'.format(dt=time_finish,duration=time_finish-time_start,script_name=script_name))



if __name__ == '__main__':
    entry_point({'arglist_strict':True})
