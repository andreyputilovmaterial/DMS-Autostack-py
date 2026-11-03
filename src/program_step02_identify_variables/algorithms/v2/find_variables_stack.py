"""Algorithm version ``v2`` — ranked candidate groups (clean-room).

Independent re-implementation of the same intent as ``v1``: find the biggest
mutually-reinforcing ("interlapping") group of questions and categories.

Unlike ``v1`` (which returns a single best match), ``v2`` enumerates multiple
candidate groups and returns them ranked best-first. Each candidate is a group
of categories plus the questions that use every one of them.

The algorithm is **name-invariant**: apart from an optional explicit
``priority_categories`` config list, the result depends only on the *structure*
of the scheme (which questions share which categories) and never on how a
category is spelled. A category called ``None``, ``NoneOfThese``,
``NoneAbove`` or ``none67`` is weighted exactly like any other category.

How it works (high level):

1. Drop questions flagged ``skip``.
2. Enumerate candidate category-sets as the intersections of question category
   lists, for single questions and every question pair. For each candidate set,
   the group's questions are those that use *every* category in the set.
3. Keep only "closed" groups: for each question-set, keep the largest
   category-set (the maximal shared list).
4. Score each group with a tunable objective that balances question count and
   shared-category count, then return the top candidates best-first.

The coefficients below are the whole tuning surface — see
``docs/step02-identify-variables.md`` for the trade-off discussion.
"""

import math


# --- tunable coefficients ------------------------------------------------
QUESTION_EXPONENT = 2.0        # how strongly question count weighs
CATEGORY_SATURATION = 10.0     # categories contribute up to ~this many
PRIORITY_PENALTY = 0.3         # penalty for non-priority categories (when given)
MIN_CATEGORIES = 2             # minimum categories for a candidate group
MIN_QUESTIONS = 2              # minimum questions for a candidate group
MAX_CANDIDATES = 20            # how many candidates to emit


def _category_quality(name, priority_categories):
    """Return a per-category weight in ``(0, 1]``.

    The only name-dependent adjustment is the explicit, user-supplied
    ``priority_categories`` list. Every other category gets a neutral weight of
    ``1.0`` regardless of how it is spelled, so renaming a category never
    changes the result.
    """
    quality = 1.0
    if priority_categories and name.lower() not in priority_categories:
        quality *= PRIORITY_PENALTY
    return quality


def _category_effective(qualities):
    """Combine category weights with diminishing returns.

    Saturates toward ``CATEGORY_SATURATION`` so that "few questions sharing a
    huge category list" is not rewarded linearly past roughly ten categories.
    """
    total = sum(qualities)
    return CATEGORY_SATURATION * (1.0 - math.exp(-total / CATEGORY_SATURATION))


def _group_score(num_questions, qualities):
    """Score a candidate group.

    The objective is ``questions^QUESTION_EXPONENT * effective_categories``: a
    weighted product of "how many questions share the categories" and "how many
    useful categories they share". Both extremes — few questions with a long
    list, or many questions with only 2-3 categories — score lower than the
    ideal of many questions sharing ~ten categories.
    """
    return (num_questions ** QUESTION_EXPONENT) * _category_effective(qualities)


# main fn here
def find_variables_to_stack(dict_questions, dict_categories, config={}):
    priority_categories = config.get('priority_categories') or []

    # questions we are allowed to stack on
    active = {q: v for q, v in dict_questions.items() if not v.get('skip')}
    active_keys = set(active.keys())

    # candidate category-sets: each question's own list + every pair intersection
    candidate_sets = set()
    question_keys = list(active.keys())
    for q in question_keys:
        cats = frozenset(active[q]['iterations'])
        if cats:
            candidate_sets.add(cats)
    for i in range(len(question_keys)):
        ci = frozenset(active[question_keys[i]]['iterations'])
        for j in range(i + 1, len(question_keys)):
            inter = ci & frozenset(active[question_keys[j]]['iterations'])
            if inter:
                candidate_sets.add(inter)

    # build one candidate per category-set, then collapse to closed groups
    groups = {}
    for cat_set in candidate_sets:
        if len(cat_set) < MIN_CATEGORIES:
            continue
        shared = None
        for c in cat_set:
            used = set(dict_categories[c]['used']) & active_keys
            shared = used if shared is None else (shared & used)
        shared = shared or set()
        if len(shared) < MIN_QUESTIONS:
            continue
        qualities = [
            _category_quality(dict_categories[c]['name'], priority_categories)
            for c in cat_set
        ]
        score = _group_score(len(shared), qualities)
        qkey = frozenset(shared)
        # keep the maximal (highest-scoring) category-set for each question-set
        if qkey not in groups or score > groups[qkey]['score']:
            groups[qkey] = {
                'category_set': cat_set,
                'questions': shared,
                'score': score,
            }

    ranked = sorted(groups.values(), key=lambda g: -g['score'])[:MAX_CANDIDATES]

    candidates = []
    for g in ranked:
        candidates.append({
            'categories': sorted(dict_categories[c]['name'] for c in g['category_set']),
            'variables': sorted(dict_questions[q]['name'] for q in g['questions']),
            'score': g['score'],
        })

    best = candidates[0] if candidates else {'categories': [], 'variables': []}

    result = {
        'algorithm_ver': config.get('algorithm_ver', 'v2'),
        'variables': best['variables'],
        'categories': best['categories'],
        'variables_raw': best['variables'],
        'candidates': candidates,
        'comment': {
            'candidate_count': len(candidates),
            'config': {
                'question_exponent': QUESTION_EXPONENT,
                'category_saturation': CATEGORY_SATURATION,
                'priority_penalty': PRIORITY_PENALTY,
                'min_categories': MIN_CATEGORIES,
                'min_questions': MIN_QUESTIONS,
                'max_candidates': MAX_CANDIDATES,
            },
        },
    }
    return result

