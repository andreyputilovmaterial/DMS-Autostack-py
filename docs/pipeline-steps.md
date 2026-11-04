# Pipeline steps — inputs, outputs, and config options

This document describes every `--program` exposed by the launcher, one step at
a time. For each step you get:

- **What it does** — a one-paragraph description,
- **Minimal input** — the smallest input file/command that makes it run,
- **Minimal output** — the smallest shape of what it writes,
- **Config options** — every CLI option the step accepts.

The programs are normally wired together by `run.bat` / `run.sh`, which call:

```text
read_mdd
  -> report / report_html / report_excel   (optional, human review)
  -> mdd-autostk-identify-variables        (step 02)
  -> mdd-autostk-prepare-patch             (step 03)
  -> mdd-autostk-write-template            (step 04, twice: 401 + 402)
  -> mdd-patch                             (twice: 401 + 402)
```

## Final goal

The whole pipeline turns an input `.mdd` questionnaire into two runnable
IBM/Unicom Dimensions scripts:

- `*_401_STKPrep.dms` — prepares the data for stacking (the "PreStack" step),
- `*_402_STKCreate.dms` — creates the stacked dataset (the "Stack" step).

## How it is done, in one paragraph

A canned base template is written first (`mdd-autostk-write-template`), a JSON
patch is then produced from the input MDD
(`mdd-autostk-prepare-patch`, based on the variable/category selection from
`mdd-autostk-identify-variables`), and that patch is finally applied to the base
template (`mdd-patch`) to produce the two final `.dms` scripts.

Each program is invoked the same way, either from source:

```bash
python -m src.launcher --program <name> [options...]
```

or

```bash
python -m src.path.to.program [options...]
```

or against the built single-file bundle:

```bash
python dist/mdmautostktoolsap_bundle.py --program <name> [options...]
```

---

## 0. `read_mdd` — turn an `.mdd` file into the JSON "scheme"

### What it does

Reads a proprietary IBM/Unicom Dimensions `.mdd` file through the COM API and
dumps its contents (languages, shared lists, fields, pages, routing) into a
single JSON file next to the input. This JSON is the common input consumed by
every later step. It is the only step that needs Windows + IBM/Unicom
Professional + `pywin32`.

### Minimal input

An `.mdd` file (binary, proprietary). There is no text "minimal example" for the
input itself; the minimal invocation is:

```bash
python -m src.launcher --program read_mdd --mdd "R123456.mdd"
```

### Minimal output

`R123456.mdd.json`, written next to the input file:

```json
{
  "report_type": "MDD",
  "source_file": "R123456.mdd",
  "report_datetime_utc": "2026-11-04T00:00:00Z",
  "report_scheme": {
    "columns": ["name", "label", "attributes", "properties", "scripting"],
    "column_headers": {
      "name": "Item name",
      "label": "Label",
      "attributes": "Item Attributes",
      "properties": "Custom properties",
      "scripting": "Scripts"
    }
  },
  "sections": [
    { "name": "fields", "content": [
      { "name": "Gender", "label": "Gender" },
      { "name": "Gender.Categories[Male]", "label": "Male" },
      { "name": "Gender.Categories[Female]", "label": "Female" }
    ] }
  ]
}
```

The `sections[].content` records carry the raw `name`, `label`, `attributes`,
`properties`, and `scripting` of each field (per `--config-features` param when calling `--program read_mdd`; `--config-sharedlists-listcats stepinto` is important (it is the default) to have all categories from shared lists explicitly listed, not just have one reference to shared list itself); `step 02` and `step 03` read the
`fields` section.

### Config options

| Option | Values / default | Meaning |
| --- | --- | --- |
| `--mdd` | path (required) | Input MDD file. |
| `--method` | `open` (default), `join` | `open` locks the file exclusively; `join` merges it into a fresh document (fallback when the file is in use). |
| `--config-features` | comma list; default `label,attributes,properties,translations,scripting` | Which per-field content to read into the JSON. |
| `--config-contexts` | comma list; default `Question,Analysis` | Which label/property contexts to read. |
| `--config-sections` | comma list; default `languages,shared_lists,fields,pages,routing` | Which document sections to include. |
| `--config-sharedlists-listcats` | `stepinto` (default), `stepover` | Expand a shared-list reference into its categories, or keep only the reference. |
| `--config-row-name-convention` | `ap` (default), `mdm` | How each row's `name` is composed (`Parent.Categories[Cat]` vs raw FullName). |

---

## 1. `report` / `report_html` — render the JSON scheme to HTML

`report` and `report_html` are aliases for the same HTML renderer.

### What it does

Loads a `read_mdd` JSON file and renders it into a browsable HTML table report.
Useful for eyeballing the questionnaire before/after autostacking.

Unnecessary but can be used to browse contents of input MDD.

### Minimal input

A `read_mdd` JSON file:

```bash
python -m src.launcher --program report --inpfile "R123456.mdd.json"
```

### Minimal output

`R123456.mdd.html` (same directory; the `.json` suffix is replaced with `.html`).

### Config options

| Option | Values / default | Meaning |
| --- | --- | --- |
| `--inpfile` | path (required) | JSON produced by `read_mdd`. |
| `--output-format` | `html` (only implemented) | Output format. |
| `--output-filename` | path | Override the output file name. |
| `--disable-plugin` | repeatable, from the plugin list | Disable one or more report plugins. |

---

## 2. `report_excel` — render the JSON scheme to Excel

### What it does

Same idea as `report`, but flattens each section into a pandas DataFrame and
writes a multi-sheet `.xlsx` workbook.

Unnecessary but can be used to browse contents of input MDD.

### Minimal input

```bash
python -m src.launcher --program report_excel --inpfile "R123456.mdd.json"
```

### Minimal output

`R123456.mdd.xlsx` (same directory; `.json` replaced with `.xlsx`).

### Config options

| Option | Values / default | Meaning |
| --- | --- | --- |
| `--inpfile` | path (required) | JSON produced by `read_mdd`. |
| `--output-format` | `excel` (only implemented) | Output format. |
| `--output-filename` | path | Override the output file name. |
| `--flags` | comma list | Program-behavior flags (passed to the Excel backend). |
| `--config-column-headers` | `text` (default), `fieldname` | Use human-readable headers or raw JSON field names. |

---

## 3. `mdd-autostk-identify-variables` (step 02) — choose what to stack

### What it does

Reads the `fields` section of a `read_mdd` JSON, flattens it into an internal
`questions`/`categories` model, and runs a versioned algorithm (`v1` or `v2`) to
pick which variables and categories should be stacked. The result is a JSON
"variable spec" consumed by step 03. See
[`step02-identify-variables.md`](step02-identify-variables.md) for the intent and
math.

### Minimal input

A `read_mdd` JSON with at least a `fields` section:

```json
{
  "sections": [
    { "name": "fields", "content": [
      { "name": "Gender", "label": "Gender" },
      { "name": "Gender.Categories[Male]", "label": "Male" },
      { "name": "Gender.Categories[Female]", "label": "Female" },
      { "name": "BrandLoop.LTR", "label": "LTR" },
      { "name": "BrandLoop.LTR.Categories[Nike]", "label": "Nike" }
    ] }
  ]
}
```

```bash
python -m src.launcher --program mdd-autostk-identify-variables \
  --inp-mdd-scheme "R123456.mdd.json" \
  --output-filename "R123456.mdd-stack-var-list-suggested.json"
```

### Minimal output

A JSON spec file. `v2` (default) returns ranked candidates:

```json
{
  "algorithm_ver": "v2",
  "variables": ["BrandLoop.LTR"],
  "categories": ["Nike"],
  "variables_raw": ["BrandLoop.LTR"],
  "candidates": [
    { "categories": ["Nike"], "variables": ["BrandLoop.LTR"], "score": 12.34 }
  ],
  "comment": { "candidate_count": 1, "config": { } }
}
```

`v1` returns a single best match instead of `candidates`, and also emits
`variables_metadata` with the internal per-question records:

```json
{
  "algorithm_ver": "v1",
  "variables": ["BrandLoop.LTR"],
  "categories": ["Nike"],
  "variables_raw": ["BrandLoop.LTR"],
  "variables_metadata": [
    { "name": "BrandLoop.LTR", "flags": { "is_assigner": false, "skip": false }, "iterations": ["nike"] }
  ],
  "comment": { }
}
```

### Config options

| Option | Values / default | Meaning |
| --- | --- | --- |
| `--inp-mdd-scheme` | path (required) | JSON produced by `read_mdd`. |
| `--config-priority-categories` | comma-separated names | Soft hint of example categories to prefer (affects weights, not a guarantee). |
| `--config-algorithm-ver` | `v2` (default), `v1` | Algorithm version. |
| `--config-category-mode` | `intersection` (v2 default), `union` (v1 default) | Build the category list from shared stubs only, or from all categories of the selected questions. |
| `--config-category-min-frequency` | `0..1` float | Union mode only: drop categories below this share of the selected questions. |
| `--output-filename` | path (required) | Where the spec JSON is written. |

---

## 4. `mdd-autostk-prepare-patch` (step 03) — produce the patch JSONs

### What it does

Reads the `read_mdd` JSON (`--inp-mdd-scheme`) and the step-02 variable spec
(`--var-list`), then computes the metadata/code edits needed to stack the chosen
variables. It writes two JSON patch files: one for the `401_PreStack` script and
one for the `402_Stack` script.

### Minimal input

1. A `read_mdd` JSON (same as step 02).
2. A step-02 variable spec (the `--output-filename` from step 02).

```bash
python -m src.launcher --program mdd-autostk-prepare-patch \
  --inp-mdd-scheme "R123456.mdd.json" \
  --var-list "R123456.mdd-stack-var-list-suggested.json" \
  --output-patch-401 "R123456.mdd-patch-401.json" \
  --output-patch-402 "R123456.mdd-patch-402.json"
```

### Minimal output

Two JSON files. Each is a **list of patch chunks**. A chunk always has an
`action`, a `position`, a `payload`, and (in this pipeline) a `comment.target`
that says which script it belongs to:

```json
[
  {
    "action": "section/metadata/insert",
    "position": { "type": "address", "position": "BrandLoop.LTR" },
    "payload": {
      "variable": "BrandLoop.LTR",
      "metadata": { },
      "attributes": { }
    },
    "comment": { "target": "401_PreStack_script" }
  },
  {
    "action": "section/onnextcase/insert",
    "position": { "type": "re", "pattern": "Event\\(OnNextCase\\)", "flags": 2 },
    "payload": {
      "variable": "BrandLoop.LTR",
      "lines": [ "..." ]
    },
    "comment": { "target": "402_Stack_script" }
  }
]
```

Known actions: `insert`, `section/metadata/insert`, `section/onnextcase/insert`,
`section/other/insert`. Known `position` types: `re` (`pattern` + `flags`),
`position` (line number), `address` (item name), `none`, `custom`.

### Config options

| Option | Values / default | Meaning |
| --- | --- | --- |
| `--inp-mdd-scheme` (also `-1`) | path (required) | JSON produced by `read_mdd`. |
| `--var-list` | path (required) | Step-02 variable spec JSON. |
| `--config-code-style` | comma list | Generated-code style flags (see below). |
| `--config-stk-iteration-field` | name (default `STK_Iteration`) | Name of the generated field that stores the stacking iteration index inside the outer stacking loop. |
| `--output-patch-401` | path (required) | Patch file for the 401 script. |
| `--output-patch-402` | path (required) | Patch file for the 402 script. |

`--config-code-style` flags:

| Flag | Effect |
| --- | --- |
| `categorycheck-operator` | Use the `=*` operator for category checks (faster). |
| `categorycheck-containsany` | Use `.ContainsAny(...)` (slower). |
| `categorycheck-explicitcatlist` | Check against an explicit category list. |
| `categorycheck-definedcategories` | Use `.DefinedCategories()`. |
| `categorycheck-globaldmgrvar` | Build the category list once in `OnJobStart` and store it in a `dmgrglobal` var. |

These are grouped internally as `assignment_op` (operator/containsany) and
`category_list_style` (explicitcatlist/definedcategories/globaldmgrvar).

---

## 5. `mdd-autostk-write-template` (step 04) — write the base templates

### What it does

Writes one of the two canned base `.dms` templates (`401_PreStack` or
`402_Stack`) to a file. The templates contain placeholders and markers that the
step-03 patches locate and edit. It takes no MDD input.

### Minimal input

```bash
python -m src.launcher --program mdd-autostk-write-template \
  --action template-401 \
  --output-filename "R123456.mdd_401_temp.dms"
```

### Minimal output

A `.dms` text file. The beginning of the 401 template is representative:

```text
' -----------------------------------------------------------------------
' IPS Table Shell Version 7.0.0
'
' -----------------------------------------------------------------------
' Run this script after unstacked Prep/Weight/etc. - creates a new inflated version of the R-data to prepare for stacking
'
#include "Includes/Globals.mrs"
#include "Includes/DMS/LoggingPrep.dms"
#define SCRIPT_NAME     "401_STKPrep.dms"
...
```

### Config options

| Option | Values / default | Meaning |
| --- | --- | --- |
| `--action` | `template-401`, `template-402` (required) | Which template to write. |
| `--output-filename` | path (required) | Where the template is written. |

---

## 6. `mdd-patch` — apply a patch file to a text/script

### What it does

Loads a text file (`--inp-filename` + `--inp-type`) and applies every chunk in a
patch JSON (`--patch`), in order, to produce a new file. In the pipeline it is
called twice: once to turn the 401 template into the final 401 script, and once
for 402.

### Minimal input

1. A base template (from step 04).
2. A patch JSON (from step 03).

```bash
python -m src.launcher --program mdd-patch \
  --inp-filename "R123456.mdd_401_temp.dms" \
  --inp-type dms \
  --patch "R123456.mdd-patch-401.json" \
  --output-filename "R123456.mdd_401_STKPrep.dms"
```

### Minimal output

The patched file (e.g. `*_401_STKPrep.dms` / `*_402_STKCreate.dms`), which is
the final script that IBM/Unicom Professional runs.

### Config options

| Option | Values / default | Meaning |
| --- | --- | --- |
| `--inp-filename` | path (required) | File to patch. |
| `--inp-type` | `dms`, `txt`, `mrs` (required; `mdd` is not implemented) | How to interpret the file. |
| `--patch` | path (required) | Patch JSON (list of chunks). |
| `--output-filename` | path (required) | Patched output file. |

---

## Utility programs

| Program | Meaning |
| --- | --- |
| `test` | Prints a hello message; used as a wiring sanity check. |
| `done` | Prints `done`; used as a dependency-free smoke test (`python -m src.launcher --program done`). |
| `version` | Prints the build version string (`GENERATED/_VERSION.py`, or `unknown` before a build). |




