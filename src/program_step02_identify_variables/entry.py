"""Entry point for ``mdd-autostk-identify-variables``.

Starter script: it can be launched directly (``python entry.py``) or dispatched
from the launcher, so it uses the three-way conditional import. It owns the CLI,
JSON loading, adapter invocation and algorithm-version dispatch. The algorithm
versions themselves are plain imported modules and must not be touched here.
"""

import argparse
from datetime import datetime
from pathlib import Path
import json


if __name__ == '__main__':
    from adapters import mdd_fields
    from algorithms.v1 import find_variables_stack as find_variables_stack_v1
    from algorithms.v2 import find_variables_stack as find_variables_stack_v2
elif '.' in __name__:
    from .adapters import mdd_fields
    from .algorithms.v1 import find_variables_stack as find_variables_stack_v1
    from .algorithms.v2 import find_variables_stack as find_variables_stack_v2
else:
    from adapters import mdd_fields
    from algorithms.v1 import find_variables_stack as find_variables_stack_v1
    from algorithms.v2 import find_variables_stack as find_variables_stack_v2


ALGORITHM_IMPL = {
    'v1': find_variables_stack_v1,
    'v2': find_variables_stack_v2,
}


def entry_point(*argcs, **kwargs):

    time_start = datetime.now()
    script_name = 'mdmautostktoolsap autostacking suggest-loop-and-variables script'

    parser = argparse.ArgumentParser(
        description="Autostacking: guess which loops and variables to stack on",
        prog='mdd-autostk-identify-variables'
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
        '--config-algorithm-ver',
        help='Algorithm version: v1 (default) or v2 (ranked candidate groups)',
        type=str,
        choices=list(ALGORITHM_IMPL.keys()),
        default='v1',
        required=False
    )
    parser.add_argument(
        '--output-filename',
        help='Set preferred output file name, with path',
        type=str,
        required=False
    )
    args = parser.parse_args(*argcs, **kwargs)

    inp_filename = ''
    if args.inp_mdd_scheme:
        inp_filename = Path(args.inp_mdd_scheme)
        inp_filename = '{inp_filename}'.format(inp_filename=inp_filename.resolve())
    else:
        raise FileNotFoundError('Inp source: file not provided; please use --inp-mdd-scheme option')

    config = {}
    if args.config_priority_categories:
        config['priority_categories_str'] = args.config_priority_categories
    config['algorithm_ver'] = args.config_algorithm_ver

    result_final_fname = None
    if args.output_filename:
        result_final_fname = Path(args.output_filename)
    else:
        raise FileNotFoundError('Out filename: file not provided; please use --output-filename option')

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

    # adapter: normalize config, then turn the JSON fields list into the model
    config = mdd_fields.normalize_config(config)
    dict_questions, dict_categories = mdd_fields.build_model(data)

    # algorithm: run the selected version on the model
    algorithm_module = ALGORITHM_IMPL[args.config_algorithm_ver]
    result = algorithm_module.find_variables_to_stack(dict_questions, dict_categories, config)

    result_json = json.dumps(result, indent=4)

    print('{script_name}: saving as "{fname}"'.format(fname=result_final_fname,script_name=script_name))
    with open(result_final_fname, "w") as outfile:
        outfile.write(result_json)

    time_finish = datetime.now()
    print('{script_name}: finished at {dt} (elapsed {duration})'.format(dt=time_finish,duration=time_finish-time_start,script_name=script_name))


if __name__ == '__main__':
    entry_point()
