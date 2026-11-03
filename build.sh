#!/usr/bin/env bash
# POSIX (macOS / Linux) counterpart of build.bat.

set -u

fail() {
    echo "ERROR: Failure" >&2
    exit 1
}

echo "Clear up dist/..."
rm -rf dist
mkdir -p dist

echo "-"
echo "-"
echo "Update program version"
mkdir -p src/GENERATED
printf "%s\n" "'''For auto-generated files'''" > src/GENERATED/__init__.py
printf "%s\n" "# THIS IS AUTO-GENERATED" > src/GENERATED/_VERSION.py
python -c "from datetime import datetime; print(f'# {datetime.now()}')" >> src/GENERATED/_VERSION.py
printf "%s\n" "_VERSION = '''" >> src/GENERATED/_VERSION.py
git describe --tags --dirty >> src/GENERATED/_VERSION.py
printf "%s\n" "'''" >> src/GENERATED/_VERSION.py
echo "Done"

echo "-"
echo "-"
echo "Re-building mdd_read program (and nested html template)..."
(
    set -e
    cd src/lib/mdmreadpy
    bash build.sh
) || fail
echo "Done"

echo "-"
echo "-"
echo "Produce distributable .py bundle - calling pinliner..."
python src_dev_build/lib/pinliner/pinliner/pinliner.py src -o dist/mdmautostktoolsap_bundle.py || fail
echo "Done"

echo "-"
echo "-"
echo "Patching mdmautostktoolsap_bundle.py..."
cat >> dist/mdmautostktoolsap_bundle.py <<'EOF'
# ...
# print('within mdmautostktoolsap_bundle')
from src import launcher
launcher.main()
# print('out of mdmautostktoolsap_bundle')
EOF
echo "Done"

echo "-"
echo "-"
echo "Copy BAT run scripts"
cp run.bat dist/run_autostacking.bat
sed -i.bak \
    -e 's#dist/mdmautostktoolsap_bundle\.py#mdmautostktoolsap_bundle.py#g' \
    dist/run_autostacking.bat
rm -f dist/run_autostacking.bat.bak
echo "Done"

echo "-"
echo "-"
echo "Bring LICENSE and README.md to dist..."
cp LICENSE dist/LICENSE
cp README.md dist/README.md
echo "Done"

echo "-"
echo "-"
echo "Inline run_init (venv setup + explicit pip installs) into dist launchers..."
python src_dev_build/inline_run_init.py || fail
echo "Done"

echo "-"
echo "-"
echo "Verify the bundle: run --program done..."
python dist/mdmautostktoolsap_bundle.py --program done || fail
echo "Done"

echo "-"
echo "-"
echo "All done, the end"
