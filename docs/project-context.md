# Project Context — DMS-Autostack-py

> Last updated: 2026-11-03

## Purpose

`DMS-Autostack-py` automates "stacking" of MDD (IBM/Unicom Dimensions) questionnaire
data. It reads an `.mdd` file, decides which questions/loops to stack, produces
`401_PreStack.dms` and `402_Stack.dms` scripts, and applies patches to them.

## Layout

- `src/launcher.py` — the single entry point. Dispatches to a named program via
  `--program <name>`; imports every reader/reporter/step lazily so the launcher itself
  has no third-party dependencies.
- `src/program_step02_identify_variables/` — chooses variables/categories to stack.
- `src/program_step03_prepare_patch/` — produces the JSON patch specs.
- `src/program_step04_write_template/` — writes the base `401`/`402` templates.
- `src/lib/mdmreadpy/` (submodule) — MDD reader (nested `mdmreportpy` HTML reporter).
- `src/lib/mdmpatchpy/` (submodule) — applies JSON patches to `.dms`/`.txt` files.
- `src/lib/mdmreport_excel/` (submodule) — Excel reporter.
- `src_dev_build/` — build-time tooling (the `pinliner` bundler submodule and
  `inline_run_init.py`); intentionally has no `__init__.py` so it is never bundled.
- `dist/` — build output (single-file bundle + launcher BATs); gitignored.

## Build & run

- `build.bat` (Windows) / `build.sh` (macOS/Linux) produce
  `dist/mdmautostktoolsap_bundle.py` via `pinliner`, generate
  `src/GENERATED/_VERSION.py`, copy `run.bat` into `dist/`, inline the `run_init`
  venv+dependency preamble, and verify the bundle with `--program done`.
- `run.bat` calls `run_init.bat` (venv setup + dependency install) and then runs the
  autostacking steps against the bundle.
- `python src/launcher.py --program done` is a dependency-free smoke test.

## Programs (`--program`)

`read_mdd`, `report` / `report_html`, `report_excel`,
`mdd-autostk-identify-variables`, `mdd-autostk-prepare-patch`,
`mdd-autostk-write-template`, `mdd-patch`, `test`, `done`, `version`.

## 2026-11-03 maintenance sync (from MDM-Diff-py)

- Submodules pulled to latest: `mdmreadpy` (restructured into `src/`),
  `mdmreport_excel` (restructured into `src/`), `pinliner`; `mdmpatchpy` already current.
- `src-make/` renamed to `src_dev_build/` (pinliner submodule path changed), matching
  the convention that build tooling lives outside the bundled `src/` package.
- `src/launcher.py` rewritten: lazy imports, `done` + `version` programs, colored
  output and error reporting.
- `build.bat`/`build.sh` updated: version generation, LICENSE/README copy,
  `--program done` verification, run_init inlining.
- Added optional-dependency packaging: root `requirements.txt`, `run_init.bat`/`.sh`,
  `src_dev_build/inline_run_init.py`; `run.bat` now calls `run_init.bat` and uses the
  venv Python.
- Added `.clinerules/` (ported from MDM-Diff-py, minus the diff-specific
  `05-diff-older-frozen.md`).
- `src_dev_build/inline_run_init.py` excludes dev-only (build-time) packages —
  `csscompressor`/`rjsmin`, used only for CSS/JS minification when compiling the
  report template — from the runtime dependency list inlined into distributed
  launchers; runtime optional deps (`pywin32`, `pandas`, `xlsxwriter`) are kept.

## 2026-11-03 argument-passing refactor (sync from MDM-Diff-py)

- Removed the `arglist_strict`/`runscript_config` mechanism. The launcher now
  forwards `*argcs, **kwargs` straight to each program's `entry_point`, and the
  entry points accept `(*argcs, **kwargs)` and call
  `parser.parse_args(*argcs, **kwargs)`, matching MDM-Diff-py's
  `call_*`/`entry_point` pattern.
- Updated: `src/launcher.py`,
  `src/program_step02_identify_variables/entry.py`,
  `src/program_step03_prepare_patch/entry.py`,
  `src/program_step04_write_template/templater.py`, and the `mdmpatchpy`
  submodule's `entry.py`.
- Note: `src/lib/mdmpatchpy/entry.py` lives in the MDM-Patchtools-py submodule;
  that change must be committed and pushed to the submodule remote before the
  outer repo can reference it.


## 2026-11-03 step02 algorithm/adapters split + versioned algorithms

- Split `src/program_step02_identify_variables/` into an adapter layer and a
  versioned algorithm layer:
  - `adapters/` — `mdd_fields.py` (flattens the MDD JSON `fields` list into the
    internal `questions`/`categories` model; precomputes `is_assigner`/`skip`),
    `util_var_functions.py` (item-name parsing). Only this layer knows the JSON
    report shape.
  - `algorithms/v1/` — the previous `find_variables_stack.py` algorithm, now
    consuming the model (plain relative imports / stdlib only).
  - `algorithms/v2/` — placeholder that raises `NotImplementedError`.
- Added `--config-algorithm-ver {v1,v2}` (default `v1`) to the
  `mdd-autostk-identify-variables` entry point; the version is echoed into the
  output as `algorithm_ver`. Versions are separate packages with no cross-imports
  and no fallback.
- Only `entry.py` (a starter script) uses the three-way conditional import; all
  other modules use plain relative imports (per MDM-Diff-py's
  `02-python-portability.md` standard).
- Documented intent/math/adapters in `docs/step02-identify-variables.md`.
- Fixed `.gitignore` to the MDM-Diff-py standard: ignore `tests-real-sensitive-data/`
  only; regular `tests/` and `test_*.py` are now tracked (previously `[Tt]est*`
  ignored all tests).
- Added `tests/test_step02_identify_variables.py` (stdlib `unittest`, subprocess
  end-to-end) covering v1 default / explicit v1 / v2 placeholder.
- Added primary example fixture `tests/fixtures/a1_v3.mdd.json` (synthetic, not
  real/sensitive) with the expected selection being the six brand categories
  (`Nike`, `Tesla`, `CocaCola`, `Select`, `YesStream`, `NoStream`); a test
  asserts `v1` picks them over the planted challengers (state list, junk
  categories, extended brand list).
- Note: `adapters/mdd_fields.normalize_config` preserves the pre-existing
  `.isnumeric` (missing `()`) quirk in the `num_categories_pick` normalization;
  left untouched to avoid a behavior change.

## Repository rules

See `.clinerules/`.
