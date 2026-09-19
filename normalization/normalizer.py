import re

from .dictionary import ALLERGEN_SYNONYMS
from .fuzzy_matcher import fuzzy_match
from .schemas import NormalizationResult


def clean_text(text: str) -> str:
    """
    Basic normalization of OCR/model text.
    """

    text = text.lower().strip()

    text = re.sub(r"\s+", " ", text)

    text = re.sub(r"[^\w\s-]", "", text)

    return text


def build_exact_index():
    index = {}

    for allergen, terms in ALLERGEN_SYNONYMS.items():
        for term, canonical in terms.items():
            index[term] = {
                "allergen": allergen,
                "canonical": canonical
            }

    return index


EXACT_INDEX = build_exact_index()


def normalize_ingredient(
    raw_term: str,
    fuzzy_threshold: int = 85
) -> NormalizationResult:

    if not raw_term or not raw_term.strip():
        return NormalizationResult(
            raw_term=raw_term,
            normalized_term=None,
            canonical_concept=None,
            match_type="no_match",
            confidence=0.0,
            status="unknown"
        )

    cleaned = clean_text(raw_term)

    # --------------------------------------------------
    # 1. Exact match
    # --------------------------------------------------

    if cleaned in EXACT_INDEX:

        info = EXACT_INDEX[cleaned]

        return NormalizationResult(
            raw_term=raw_term,
            normalized_term=info["canonical"],
            canonical_concept=info["canonical"],
            match_type="exact",
            confidence=1.0,
            status="known"
        )

    # --------------------------------------------------
    # 2. Fuzzy match
    # --------------------------------------------------

    match = fuzzy_match(
        cleaned,
        threshold=fuzzy_threshold
    )

    if match:

        return NormalizationResult(
            raw_term=raw_term,
            normalized_term=match["canonical"],
            canonical_concept=match["canonical"],
            match_type="fuzzy_synonym",
            confidence=match["score"],
            status="known"
        )

    # --------------------------------------------------
    # 3. Unknown
    # --------------------------------------------------

    return NormalizationResult(
        raw_term=raw_term,
        normalized_term=None,
        canonical_concept=None,
        match_type="no_match",
        confidence=0.0,
        status="unknown"
    )


def normalize_ingredients(
    ingredients: list[str],
    fuzzy_threshold: int = 85
) -> list[NormalizationResult]:

    return [
        normalize_ingredient(
            ingredient,
            fuzzy_threshold=fuzzy_threshold
        )
        for ingredient in ingredients
    ]