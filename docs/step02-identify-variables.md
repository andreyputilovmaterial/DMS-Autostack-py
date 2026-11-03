# Step 02 — identify variables & categories to stack

`--program mdd-autostk-identify-variables` decides which questions/variables and
which categories the autostacker should stack on. It reads the MDD report JSON
(the same shape produced by the MDD reader, e.g.
`src/lib/mdmreadpy/tests/fixtures/*.mdd.json`) and writes a variable/category
spec JSON that the next step (`mdd-autostk-prepare-patch`) consumes.

This document describes the **intent**, the **math**, and the **adapters**
separately, then the versioning mechanism.

---

## 1. Intent (high level)

An MDD questionnaire contains:

- **categorical variables** (single questions), e.g. `Gender` with categories
  `Male`, `Female`, `OtherSpec`;
- **loops** with iterations, e.g. `BrandLoop` with inner questions
  `BrandLoop.LTR`, `BrandLoop.Ethnicity`, ...;
- **categories themselves**, attached to categorical variables and to the inner
  questions of loops.

Stacking means turning "the same question asked once per brand/iteration" into a
single stacked question that iterates over a loop. To do that well we want the
**biggest group of questions that share the same categories**, because those
questions are the ones that can be folded together.

The ideal is "many questions sharing ~ten categories". The key insight is that
this is a **mutually reinforcing ("interlapping") group**:

- common categories add weight to the questions that share them,
- those questions add weight back to the categories they share,
- which adds weight to *other* questions that also share those categories,
- and so on, repeated to convergence.

The biggest such group is the best stacking candidate.

### Loops already multiply

Loop inner questions need **no special boost**. The MDD reader flattens every
loop sub-field into its own variable and repeats the shared categories for each
of them (e.g. `BrandLoop.Ethnicity.categories[...]` mirrors
`Ethnicity.categories[...]`). A loop with *N* sub-fields therefore contributes
*N* variables that all share the same categories — a multiplicative boost that
falls out of the flattening for free.

### The core trade-off

- **Few questions sharing a long category list** should rank *lower* than many
  questions sharing fewer categories.
- **Many questions sharing only 2–3 categories** should also rank *lower*.
- `10 questions × 14 categories` vs `20 questions × 7 categories` is the
  canonical open question — the "correct" answer is a tunable trade-off, not a
  single rule, and depends on coefficient choices.

The final result is therefore highly sensitive to the coefficients below; that
is expected and the whole point of having versioned algorithms.

---

## 2. Math / algorithm (version `v1`)

The `v1` algorithm operates on the internal model (see §3) and knows nothing
about the JSON report format. It has these stages:

1. **Seed weights.** Every category starts at
   `w_cat = 0.1 * priority(category)`; every question starts at `w_q = 0.01`
   (raised toward `0.35` effect for `assignertext` questions).

   `priority(category)` is an adjustment ratio in `[0.01, 1]`:
   - priority-category config → `1`;
   - `Other`/`None`-style names → `0.85`;
   - `dv_country`/`uslocationdata.state` → `0.35`;
   - `_1`, `Yes`/`No` names → `0.01`;
   - anything else → `1`.

2. **Mutual propagation** (`CONFIG_PROCESS_ITERATIONS = 4` rounds):
   - each category pulls weight from every question that uses it:
     `w_cat ← 1 − (1 − w_cat) · (1 − w_q · 0.08)`;
   - each question pulls weight from its categories (sorted by weight, with a
     decaying factor `0.08, 0.048, ...`):
     `w_q ← 1 − (1 − w_q) · (1 − w_cat · factor)`.

   This is the "categories reinforce questions, questions reinforce categories"
   loop written as a probability-style accumulation (`1 − ∏(1 − x)`), so weights
   stay in `[0, 1)` and can never overshoot.

3. **Pick candidate categories.** Sort categories by weight, keep those above
   `10%` of the top weight, cap at `36`.

4. **Enumerate combinations.** For every combination of
   `num_categories_pick` (= 3) candidate categories, score the questions that
   use *all* of them; a question's contribution is
   `(0.8 + 0.2 · w_q)` averaged over the combination, raised to the 4th power
   (to strongly favour questions that share *all* chosen categories). The best
   combination wins.

5. **Emit the result.** The result variables are the questions using all of the
   winning categories; the result categories are the categories recurring across
   those variables, trimmed to the popular ones (frequency cutoff, excluding
   `None*`).

### Coefficients

| Constant | Value | Meaning |
| --- | --- | --- |
| `CONFIG_CAT_WGT_START_WITH` | `0.1` | initial category weight |
| `CONFIG_INITIAL_Q_WGT` | `0.01` | initial question weight |
| `CONFIG_INCREASE_QWGT_IF_ASSIGNER` | `0.35` | assigner-question boost |
| `CONFIG_PROCESS_ITERATIONS` | `4` | propagation rounds |
| `CONFIG_WEIGHT_DECREASE_IF_NOT_PRIORITY` | `0.1` | penalty for non-priority categories |
| `CONFIG_NUM_CATEGORIES_PICK` | `3` | categories combined to select questions |

The `10×14` vs `20×7` trade-off is currently implicit in these constants (the
`0.8 + 0.2·w_q` blend, the `^4` exponent, the `10%`/`36` cutoffs). `v2` should
make it an explicit, tunable coefficient.

---

## 3. Adapters (JSON → model)

The adapter layer (`adapters/`) is the only code that knows the MDD JSON report
shape. It is separate from, and shared by, all algorithm versions.

- `adapters/util_var_functions.py` — parses flat item names:
  `Var` → variable, `Var.categories[Cat]` → category, empty → blank; lowercases
  and normalizes punctuation.
- `adapters/mdd_fields.py` — `build_model(fields_all)` walks the flat `fields`
  list and produces the internal model:

  ```python
  questions = { <lowercase name>: {
      'name', 'label',
      'iterations': [<category lower>...],
      'record_ref': <raw JSON row>,   # opaque, kept only for debug output
      'is_assigner': bool,
      'skip': bool,                   # QTA assigner / no-case-data heuristics
  } }
  categories = { <lowercase name>: {
      'name',
      'used': [<question lower>...],
  } }
  ```

  `is_assigner` and `skip` are precomputed here so the algorithm never reads
  `properties`/`attributes` of the raw row.

  `normalize_config(config)` also lives here: it turns the CLI string
  `priority_categories_str` into a normalized `priority_categories` list and
  fills in the `num_categories_pick` default.

The model is a plain-dict contract. `v1` and `v2` both accept
`find_variables_to_stack(questions, categories, config)`.

---

## 4. Algorithm versioning

The CLI accepts `--config-algorithm-ver {v1,v2}` (default `v1`). Each version is
its own package under `algorithms/` and exposes the same
`find_variables_to_stack(dict_questions, dict_categories, config)` signature:

```
algorithms/
    v1/find_variables_stack.py   # single best match
    v2/find_variables_stack.py   # ranked candidate groups
```

Rules:

- versions must **not** import each other and there is **no fallback** between
  them — once execution enters `v2`, `v1` is unreachable;
- `entry.py` is the only starter script and the only module using the three-way
  conditional import; every other module uses plain relative imports;
- the chosen version is echoed into the output JSON as `algorithm_ver`.

To add `v3`: create `algorithms/v3/` with the same function, add its `__init__`
package, and add one line to the `ALGORITHM_IMPL` registry in `entry.py`.

## 5. Algorithm version `v2` (ranked candidate groups)

`v2` is a clean-room re-implementation of the same intent. Instead of a single
best match it returns **multiple candidate groups ranked best-first**; each
candidate is a group of categories plus the questions that use all of them.

1. **Prepare.** Drop questions flagged `skip`; weight each category with
   `_category_quality`: junk names (`Other`/`None`/`PreferNotSay`) → `0.15`,
   scale names (`_1`, `Yes`/`No`) → `0.3`, otherwise `1.0` (non-priority
   categories get `×0.3` when a priority list is supplied).
2. **Enumerate candidates.** Candidate category-sets are the intersections of
   question category lists, for single questions and every question pair. For
   each set, the group's questions are those using every category in it.
3. **Collapse to closed groups.** For each question-set keep the maximal
   category-set (the largest shared list).
4. **Score.** `score = questions^2 × effective_categories`, where
   `effective_categories` saturates toward `10` (diminishing returns), so "few
   questions × huge list" is not rewarded linearly.
5. **Emit.** Top `20` candidates, best first; `categories`/`variables` at the
   top level mirror the best candidate for backward compatibility with step 03.

Output shape:

```json
{
  "algorithm_ver": "v2",
  "variables": ["..."],
  "categories": ["..."],
  "variables_raw": ["..."],
  "candidates": [
    { "categories": ["..."], "variables": ["..."], "score": 112.8 }
  ],
  "comment": { "candidate_count": 8, "config": { ... } }
}
```

Coefficients (module constants in `algorithms/v2/find_variables_stack.py`):
`QUESTION_EXPONENT=2`, `CATEGORY_SATURATION=10`, `JUNK_RATIO=0.15`,
`SCALE_RATIO=0.3`, `PRIORITY_PENALTY=0.3`, `MIN_CATEGORIES=2`,
`MIN_QUESTIONS=2`, `MAX_CANDIDATES=20`.

---

## 6. Worked example (primary test fixture)

`tests/fixtures/a1_v3.mdd.json` (synthetic — **not real/sensitive data**) is the
primary example for step 02. It is shaped so that the expected selection is the
six brand categories `Nike`, `Tesla`, `CocaCola`, `Select`, `YesStream`,
`NoStream`, which must win over three deliberately planted challengers:

1. a long state list repeated across 3 questions (many shared categories, few
   questions),
2. `OtherSpec` / `NoneAbove` junk categories repeated across many questions,
3. the same brand list extended with `Square`, `Sellers`, `Mailchimp`,
   `Salesforce`, `Hello`, ... — a longer list that covers fewer questions.

`v1` selects the expected six brands, verified by
`tests/test_step02_identify_variables.py`.

