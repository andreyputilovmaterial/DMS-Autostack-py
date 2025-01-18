@ECHO OFF
SETLOCAL enabledelayedexpansion


@REM ::insert your files here
SET "MDD_FILE=..\tests\v0.001\R2401582.mdd"




@REM :: adjust config options per your needs
@REM :: when using "if" in BAT files, "1==1" is true and "1==0" is false

@REM :: list some examples of categories that you stack on
SET "CONFIG_PREFER_CATEGORIES=Disney,Mailchimp,Nike"





SET "CONFIG_PRODUCE_HTML_MDD=1==1"






@REM :: go
IF "%CONFIG_PREFER_CATEGORIES%"=="" (
    REM ECHO
) ELSE (
    SET "CONFIG_PREFER_CATEGORIES=--config-priority-categories !CONFIG_PREFER_CATEGORIES!"
)

REM :: file names with file schemes in json
SET "MDD_FILE_SCHEME=%MDD_FILE%.json"
SET "MDD_FILE_VARIABLES=%MDD_FILE%-stack-var-list-suggested.json"
SET "MDD_FILE_PATCH=%MDD_FILE%-patch.json"
SET "MDD_FILE_SYNTAX_MDATA=%MDD_FILE%-stk-mdata.mrs"
SET "MDD_FILE_SYNTAX_EDITS=%MDD_FILE%-stk-edits.mrs"
@REM SET "MDD_FILE_SYNTAX_TEMPLATE_STEP1=%MDD_FILE%-mdmstk_template_401_prestack.dms"
@REM SET "MDD_FILE_SYNTAX_TEMPLATE_STEP2=%MDD_FILE%-mdmstk_template_402_stack.dms"
SET "MDD_FILE_RESULT_STEP1=%MDD_FILE%_401_STKPrep.dms"
SET "MDD_FILE_RESULT_STEP2=%MDD_FILE%_402_STKCreate.dms"

ECHO -
ECHO 1. read MDD
ECHO read from: %MDD_FILE%
ECHO write to: .json
python dist/mdmautostktoolsap_bundle.py --program read_mdd --mdd "%MDD_FILE%" --config-features label,attributes,properties,scripting --config-section fields --config-contexts Analysis,Question
if %ERRORLEVEL% NEQ 0 ( echo ERROR: Failure && pause && goto CLEANUP && exit /b %errorlevel% )

IF %CONFIG_PRODUCE_HTML_MDD% (
    ECHO -
    ECHO 1.1. generate html
    python dist/mdmautostktoolsap_bundle.py --program report --inpfile "%MDD_FILE_SCHEME%"
    if %ERRORLEVEL% NEQ 0 ( echo ERROR: Failure && pause && goto CLEANUP && exit /b %errorlevel% )
)

ECHO -
ECHO 2. decide on which questions and loops should be stacked
python dist/mdmautostktoolsap_bundle.py --program mdd-autostacking-pick-variables --inp-mdd-scheme "%MDD_FILE_SCHEME%" %CONFIG_PREFER_CATEGORIES% --output-filename "%MDD_FILE_VARIABLES%"
if %ERRORLEVEL% NEQ 0 ( echo ERROR: Failure && pause && goto CLEANUP && exit /b %errorlevel% )

ECHO -
ECHO 3. prepare patch file
python dist/mdmautostktoolsap_bundle.py --program mdd-autostacking-prepare-patch --inp-mdd-scheme "%MDD_FILE_SCHEME%" --var-list "%MDD_FILE_VARIABLES%" --output-filename "%MDD_FILE_PATCH%"
if %ERRORLEVEL% NEQ 0 ( echo ERROR: Failure && pause && goto CLEANUP && exit /b %errorlevel% )

ECHO -
ECHO 4. produce files
python dist/mdmautostktoolsap_bundle.py --program mdd-patch --action generate-scripts-metadata --inp-mdd-scheme "%MDD_FILE_SCHEME%" --patch "%MDD_FILE_PATCH%" --output-filename "%MDD_FILE_SYNTAX_MDATA%"
if %ERRORLEVEL% NEQ 0 ( echo ERROR: Failure && pause && goto CLEANUP && exit /b %errorlevel% )
python dist/mdmautostktoolsap_bundle.py --program mdd-patch --action generate-scripts-edits --inp-mdd-scheme "%MDD_FILE_SCHEME%" --patch "%MDD_FILE_PATCH%" --output-filename "%MDD_FILE_SYNTAX_EDITS%"
if %ERRORLEVEL% NEQ 0 ( echo ERROR: Failure && pause && goto CLEANUP && exit /b %errorlevel% )

ECHO -
ECHO 5. put it all together
python dist/mdmautostktoolsap_bundle.py --program mdd-autostk-text-utility --action template-401 --mdata "%MDD_FILE_SYNTAX_MDATA%" --edits "%MDD_FILE_SYNTAX_EDITS%" --output-filename "%MDD_FILE_RESULT_STEP1%"
if %ERRORLEVEL% NEQ 0 ( echo ERROR: Failure && pause && goto CLEANUP && exit /b %errorlevel% )
python dist/mdmautostktoolsap_bundle.py --program mdd-autostk-text-utility --action template-402 --output-filename "%MDD_FILE_RESULT_STEP2%"
if %ERRORLEVEL% NEQ 0 ( echo ERROR: Failure && pause && goto CLEANUP && exit /b %errorlevel% )




ECHO -
ECHO 7 del .json temporary files

@REM DEL "%MDD_FILE_SCHEME%"
@REM DEL "%MDD_FILE_VARIABLES%"
@REM DEL "%MDD_FILE_PATCH%"
@REM DEL "%MDD_FILE_SYNTAX_MDATA%"
@REM DEL "%MDD_FILE_SYNTAX_EDITS%"
@REM DEL "%MDD_FILE_SYNTAX_TEMPLATE_STEP1%"
@REM DEL "%MDD_FILE_SYNTAX_TEMPLATE_STEP2%"

ECHO -
:CLEANUP
ECHO 999. Clean up
REM REM :: comment: just deleting trach .pyc files after the execution - they are saved when modules are loaded from within bndle file created with pinliner
REM REM :: however, it is necessary to delete these .pyc files before every call of the mdmautostktoolsap_bundle
REM REM :: it means, 6 more times here, in this script; but I don't do it cause I have this added to the linliner code - see my pinliner fork
DEL *.pyc
IF EXIST __pycache__ (
DEL /F /Q __pycache__\*
)
IF EXIST __pycache__ (
RMDIR /Q /S __pycache__
)

ECHO done!
exit /b %errorlevel%

