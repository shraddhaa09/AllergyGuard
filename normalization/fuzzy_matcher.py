from rapidfuzz import fuzz, process

from .dictionary import ALLERGEN_SYNONYMS


def build_term_index():
    index = {}

    for allergen, terms in ALLERGEN_SYNONYMS.items():
        for term, canonical in terms.items():
            index[term] = {
                "allergen": allergen,
                "canonical": canonical
            }

    return index


TERM_INDEX = build_term_index()


def fuzzy_match(term: str, threshold: int = 85):
    """
    Find the closest known synonym for a term.

    Returns:
        dict or None
    """

    if not TERM_INDEX:
        return None

    result = process.extractOne(
        term,
        TERM_INDEX.keys(),
        scorer=fuzz.ratio
    )

    if result is None:
        return None

    matched_term, score, _ = result

    if score < threshold:
        return None

    match_info = TERM_INDEX[matched_term]

    return {
        "matched_term": matched_term,
        "allergen": match_info["allergen"],
        "canonical": match_info["canonical"],
        "score": score / 100.0
    }