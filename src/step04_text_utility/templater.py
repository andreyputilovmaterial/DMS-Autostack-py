# import os, time, re, sys
import os
from datetime import datetime, timezone
# from dateutil import tz
import argparse
from pathlib import Path
import re
import json



if __name__ == '__main__':
    # run as a program
    import template_401
    import template_402
elif '.' in __name__:
    # package
    from . import template_401
    from . import template_402
else:
    # included with no parent package
    import template_401
    import template_402











def entry_point(runscript_config={}):

    time_start = datetime.now()
    script_name = 'mdmautostktoolsap mdd stk texttools'

    parser = argparse.ArgumentParser(
        description="MDD: produce text files",
        prog='mdd-autostk-text-utility'
    )
    parser.add_argument(
        '--action',
        help='Specify template name and action',
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

    action = None
    if args.action:
        if args.action=='template-401':
            action = 'template-401'
        elif args.action=='template-402':
            action = 'template-402'
        else:
            raise TypeError('mdd autostk texttools: this action is not implemented yet: "{a}"'.format(a=args.action))

    result_final_fname = None
    if args.output_filename:
        result_final_fname = Path(args.output_filename)
    else:
        raise FileNotFoundError('Inp source: file not provided; please use --inp-mdd-scheme option')
    

    
    print('{script_name}: script started at {dt}'.format(dt=time_start,script_name=script_name))

    result = None
    template = ''
    if action=='template-401':
        template = template_401.TEMPLATE
    elif action=='template-402':
        template = template_402.TEMPLATE
    else:
        raise TypeError('mdd autostk texttools: this action is not implemented yet: "{a}"'.format(a=args.action))
    print('{script_name}: template: "{t}"'.format(t=action,script_name=script_name))

    result = template
     
    print('{script_name}: saving as "{fname}"'.format(fname=result_final_fname,script_name=script_name))
    with open(result_final_fname, "w",encoding='utf-8') as outfile:
        outfile.write(result)

    time_finish = datetime.now()
    print('{script_name}: finished at {dt} (elapsed {duration})'.format(dt=time_finish,duration=time_finish-time_start,script_name=script_name))



if __name__ == '__main__':
    entry_point({'arglist_strict':True})
