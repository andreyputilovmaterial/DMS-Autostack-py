@ECHO OFF

ECHO Clear up dist\...
IF EXIST dist (
    REM -
) ELSE (
    MKDIR dist
)
DEL /F /Q dist\*

ECHO -
ECHO -
ECHO Update program version
IF NOT EXIST src\GENERATED (
    MKDIR src\GENERATED
)
ECHO '''For auto-generated files''' > src\GENERATED\__init__.py
ECHO # THIS IS AUTO-GENERATED > src\GENERATED\_VERSION.py
python -c "from datetime import datetime; print(f'# {datetime.now()}')" >> src\GENERATED\_VERSION.py
ECHO _VERSION = ''' >> src\GENERATED\_VERSION.py
git describe --tags --dirty >> src\GENERATED\_VERSION.py
ECHO ''' >> src\GENERATED\_VERSION.py
ECHO Done

ECHO -
ECHO -
ECHO Re-building mdd_read program (and nested html template)...
PUSHD src\lib\mdmreadpy
CALL build.bat
if %ERRORLEVEL% NEQ 0 ( echo ERROR: Failure && pause && exit /b %errorlevel% )
POPD
ECHO Done

ECHO -
ECHO -
ECHO Produce distributable .py bundle - calling pinliner (with --main entry point)...
REM REM :: comment: please delete .pyc files before every call of the mdmautostktoolsap_bundle - this is implemented in my fork of the pinliner
@REM python src_dev_build\lib\pinliner\pinliner\pinliner.py src -o dist/mdmautostktoolsap_bundle.py --verbose
python src_dev_build\lib\pinliner\pinliner\pinliner.py src -o dist/mdmautostktoolsap_bundle.py --main src.launcher --main-attr main
if %ERRORLEVEL% NEQ 0 ( echo ERROR: Failure && pause && exit /b %errorlevel% )
ECHO Done

ECHO -
ECHO -
ECHO Copy BAT run scripts
PUSHD dist
COPY ..\run.bat .\run_autostacking.bat
powershell -NoProfile -Command "(gc 'run_autostacking.bat' -encoding 'Default') -replace '(dist[/\\])?mdmautostktoolsap_bundle.py', 'mdmautostktoolsap_bundle.py' | Out-File -encoding 'Default' 'run_autostacking.bat'"
POPD
ECHO Done

ECHO -
ECHO -
ECHO Bring LICENSE and README.md to dist...
COPY /Y LICENSE dist\LICENSE
COPY /Y README.md dist\README.md
ECHO Done

ECHO -
ECHO -
ECHO Inline run_init - venv setup + explicit pip installs - into dist launchers...
python src_dev_build\inline_run_init.py
if %ERRORLEVEL% NEQ 0 ( echo ERROR: Failure && pause && exit /b %errorlevel% )
ECHO Done

ECHO -
ECHO -
ECHO Verify the bundle: run --program done...
python dist\mdmautostktoolsap_bundle.py --program done
if %ERRORLEVEL% NEQ 0 ( echo ERROR: Failure && pause && exit /b %errorlevel% )
ECHO Done

ECHO -
ECHO -
ECHO All done, the end
