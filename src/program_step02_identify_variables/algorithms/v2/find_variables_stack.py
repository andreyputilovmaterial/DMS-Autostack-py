"""Algorithm version ``v2`` — placeholder.

Same contract as ``v1``: ``find_variables_to_stack(dict_questions,
dict_categories, config)`` returns a result dict with at least ``variables`` and
``categories`` (plus debug data).

This is intentionally unimplemented. It exists so the CLI can already route to
``--config-algorithm-ver v2`` and so future experiments have a home that does
not touch the stable ``v1`` implementation. ``v1`` and ``v2`` are separate
packages and must not import each other.

Design intent (not yet implemented):
- keep the same mutual-reinforcement principle (categories reinforce their
  questions, questions reinforce their categories, iterated to convergence);
- make the trade-off between "number of questions sharing categories" and
  "number of shared categories" an explicit, tunable coefficient rather than a
  hardcoded combination of constants;
- no explicit loop handling is required: the reader already flattens loop
  sub-fields and repeats the shared categories for each, which is the
  multiplicative boost.
"""


def find_variables_to_stack(dict_questions, dict_categories, config={}):
    raise NotImplementedError(
        'algorithm version "v2" is a placeholder and is not implemented yet; '
        'use --config-algorithm-ver v1 (the default)'
    )
