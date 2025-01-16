@ECHO OFF

ECHO Clear up dist\...
IF EXIST dist (
    REM -
) ELSE (
    MKDIR dist
)
DEL /F /Q dist\*

ECHO Calling pinliner...
REM REM :: comment: please delete .pyc files before every call of the mdmautostktoolsap_bundle - this is implemented in my fork of the pinliner
@REM python src-make\lib\pinliner\pinliner\pinliner.py src -o dist/mdmautostktoolsap_bundle.py --verbose
python src-make\lib\pinliner\pinliner\pinliner.py src -o dist/mdmautostktoolsap_bundle.py
if %ERRORLEVEL% NEQ 0 ( echo ERROR: Failure && pause && exit /b %errorlevel% )
ECHO Done

ECHO Patching mdmautostktoolsap_bundle.py...
ECHO # ... >> dist/mdmautostktoolsap_bundle.py
ECHO # print('within mdmautostktoolsap_bundle') >> dist/mdmautostktoolsap_bundle.py
REM REM :: no need for this, the root package is loaded automatically
@REM ECHO # import mdmautostktoolsap_bundle >> dist/mdmautostktoolsap_bundle.py
ECHO from src import run_universal >> dist/mdmautostktoolsap_bundle.py
ECHO run_universal.main() >> dist/mdmautostktoolsap_bundle.py
ECHO # print('out of mdmautostktoolsap_bundle') >> dist/mdmautostktoolsap_bundle.py

PUSHD dist
COPY ..\run.bat .\run_autostacking.bat
powershell -Command "(gc 'run_autostacking.bat' -encoding 'Default') -replace '(dist[/\\])?mdmautostktoolsap_bundle.py', 'mdmautostktoolsap_bundle.py' | Out-File -encoding 'Default' 'run_autostacking.bat'"
POPD


ECHO End

