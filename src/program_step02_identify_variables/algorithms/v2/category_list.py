"""Build the combined category list for a group of questions (``v2`` helper).

Extracted into its own module so the "given a list of questions, produce the
categories to stack on" logic lives in one controlled, testable place. It
supports an intersection and a union mode, plus an optional frequency threshold
that drops categories not seen in enough of the selected questions.
"""


def build_category_list(question_keys, dict_questions, dict_categories,
                        mode='intersection', min_frequency=None):
    """Return a sorted list of category names for the given questions.

    ``mode``:

    - ``'intersection'`` — categories used by *every* question (shared stubs).
    - ``'union'`` — every category used by at least one question.

    ``min_frequency`` (optional, ``0 <= f <= 1``): keep only categories used by
    at least ``f`` of the selected questions; ``None`` disables the filter. It is
    a no-op for ``'intersection'`` (every returned category already has frequency
    ``1.0``).
    """
    question_keys = list(question_keys)
    if not question_keys:
        return []

    if min_frequency is not None and not (0.0 <= min_frequency <= 1.0):
        raise ValueError(
            'min_frequency must be between 0 and 1: {f}'.format(f=min_frequency)
        )

    frequency = {}
    for q in question_keys:
        for category_key in dict_questions[q]['iterations']:
            frequency[category_key] = frequency.get(category_key, 0) + 1

    if mode == 'union':
        kept = set(frequency)
    else:
        kept = {c for c, count in frequency.items() if count == len(question_keys)}

    if min_frequency is not None:
        cutoff = min_frequency * len(question_keys)
        kept = {c for c in kept if frequency[c] >= cutoff}

    return sorted(dict_categories[c]['name'] for c in kept)
