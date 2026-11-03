# Step-02 test fixtures

`a1_v3.mdd.json` is the primary example for `mdd-autostk-identify-variables`
(step 02). It is a synthetic MDD report — **not real/sensitive data** — and it
was produced by the MDD reader (`python src/read_mdd.py --mdd ...`).

It is shaped to exercise the variable/category selection trade-off. The
**expected selection** (what step-02 v1 should pick) is the six brand
categories:

- `Nike`, `Tesla`, `CocaCola`, `Select`, `YesStream`, `NoStream`

These are shared by several brand questions and win over the challengers that
are deliberately present in the data:

1. a long state list repeated across 3 questions (many shared categories, but
   few questions),
2. `OtherSpec` / `NoneAbove` categories repeated across many questions (junk),
3. the same brand list extended with `Square`, `Sellers`, `Mailchimp`,
   `Salesforce`, `Hello`, etc., producing a longer list that covers fewer
   questions.

The exact shape is documented in the mdmreadpy submodule's
`docs/report-json-format.md`; the committed fixtures there are the reader's
example outputs.
