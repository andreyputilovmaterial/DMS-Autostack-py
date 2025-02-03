
import argparse
# from pathlib import Path
import traceback






if __name__ == '__main__':
    # run as a program
    from lib.mdmreadpy import read_mdd
    from lib.mdmreadpy.lib.mdmreportpy import report_create
    from step02_guess_vars import entry as autostk_var_guesser
    from step03_produce_patch import entry as autostk_patch_generate
    from step04_text_utility import templater as autostk_templates
    from lib.mdmpatchpy import entry as mdd_patch
elif '.' in __name__:
    # package
    from .lib.mdmreadpy import read_mdd
    from .lib.mdmreadpy.lib.mdmreportpy import report_create
    from .step02_guess_vars import entry as autostk_var_guesser
    from .step03_produce_patch import entry as autostk_patch_generate
    from .step04_text_utility import templater as autostk_templates
    from .lib.mdmpatchpy import entry as mdd_patch
else:
    # included with no parent package
    from lib.mdmreadpy import read_mdd
    from lib.mdmreadpy.lib.mdmreportpy import report_create
    from step02_guess_vars import entry as autostk_var_guesser
    from step03_produce_patch import entry as autostk_patch_generate
    from step04_text_utility import templater as autostk_templates
    from lib.mdmpatchpy import entry as mdd_patch






def call_read_mdd_program():
    return read_mdd.entry_point({'arglist_strict':False})

def call_report_program():
    return report_create.entry_point({'arglist_strict':False})

def call_autostk_var_guesser_program():
    return autostk_var_guesser.entry_point({'arglist_strict':False})

def call_autostk_generate_patch_program():
    return autostk_patch_generate.entry_point({'arglist_strict':False})

def call_mdd_patch_program():
    return mdd_patch.entry_point({'arglist_strict':False})

def call_autostk_temp_text_program():
    return autostk_templates.entry_point({'arglist_strict':False})





run_programs = {
    'read_mdd': call_read_mdd_program,
    'report': call_report_program,
    'mdd-autostacking-pick-variables': call_autostk_var_guesser_program,
    'mdd-autostacking-prepare-patch': call_autostk_generate_patch_program,
    'mdd-patch': call_mdd_patch_program,
    'mdd-autostk-text-utility': call_autostk_temp_text_program,
}



def main():
    try:
        parser = argparse.ArgumentParser(
            description="Universal caller of mdmautostktoolsap-py utilities"
        )
        parser.add_argument(
            #'-1',
            '--program',
            choices=dict.keys(run_programs),
            type=str,
            required=True
        )
        args, args_rest = parser.parse_known_args()
        if args.program:
            program = '{arg}'.format(arg=args.program)
            if program in run_programs:
                run_programs[program]()
            else:
                raise AttributeError('program to run not recognized: {program}'.format(program=args.program))
        else:
            print('program to run not specified')
            raise AttributeError('program to run not specified')
    except Exception as e:
        # the program is designed to be user-friendly
        # that's why we reformat error messages a little bit
        # stack trace is still printed (I even made it longer to 20 steps!)
        # but the error message itself is separated and printed as the last message again

        # for example, I don't write "print('File Not Found!');exit(1);", I just write "raise FileNotFoundErro()"
        print('')
        print('Stack trace:')
        print('')
        traceback.print_exception(e,limit=20)
        print('')
        print('')
        print('')
        print('Error:')
        print('')
        print('{e}'.format(e=e))
        print('')
        exit(1)


if __name__ == '__main__':
    main()


