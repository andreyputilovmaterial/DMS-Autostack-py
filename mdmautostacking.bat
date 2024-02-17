@ECHO OFF

ECHO -
ECHO - MDM Diff. Starting...
ECHO -

REM set MDD file names
SET "MDD_A=R221603M.mdd"
REM SET "MDD_A=R221503M.mdd"
REM SET "MDD_A=R221646.mdd"
REM SET "MDD_A=R221366.mdd"
REM SET "MDD_A=R2301763.mdd"






REM ECHO get reports
REM ECHO -
REM ECHO "- Getting report for MDD %MDD_A%"
SET "REPORT_A=report.%MDD_A%.json"
REM mrscriptcl mdmrep.mrs "/a:INPUT_MDD=%MDD_A%" "/a:RUN_FEATURES=label,properties,translations"
REM if %ERRORLEVEL% NEQ 0 ( echo ERROR: Failure && pause && exit /b %errorlevel% )
REM python mdmcreatehtmlrep.py "%REPORT_A%"
REM if %ERRORLEVEL% NEQ 0 ( echo ERROR: Failure && pause && exit /b %errorlevel% )





REM get diff
SET "REPORT_STK=report.stk.%MDD_A%.json"
ECHO -
ECHO - Calling the diff script
python mdmstksuggest.py "%REPORT_A%"
if %ERRORLEVEL% NEQ 0 ( echo ERROR: Failure && pause && exit /b %errorlevel% )
::report.diff-report.{mdd_a}-{mdd_b}.json
python mdmcreatehtmlrep.py "%REPORT_STK%"
if %ERRORLEVEL% NEQ 0 ( echo ERROR: Failure && pause && exit /b %errorlevel% )

ECHO -
ECHO - MDM Diff. Reached the end of script
ECHO -
