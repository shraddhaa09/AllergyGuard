"""Explainable multi-stage ingredient normalization."""

import re

from .allergy_knowledge import resolve_canonical_concept
from .dataset_matcher import dataset_match
from .dictionary import ALLERGEN_SYNONYMS
from .ingredient_dictionary import INGREDIENT_SYNONYMS
from .schemas import CandidateMatch, NormalizationResult


def clean_text(text: str) -> str:
    """Apply explainable, non-destructive cleanup to an OCR ingredient term."""
    cleaned = text.lower().strip()
    # Hierarchical extraction normally expands these expressions first.  For a
    # direct caller, retain the parent term rather than merging it with a nested
    # child into a synthetic phrase such as ``vegetable oil soybean``.
    cleaned = re.split(r"[\[({]", cleaned, maxsplit=1)[0]
    cleaned = re.sub(r"[^\w\s-]", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned)
    # These repairs insert a boundary; they never invent a missing word.
    cleaned = re.sub(r"(?<=[a-z])(?=flour\b|chips\b|oil\b)", " ", cleaned)
    return cleaned.strip()


def build_exact_index() -> dict[str, dict[str, str | None]]:
    index = {}
    for allergen, terms in ALLERGEN_SYNONYMS.items():
        for term, canonical in terms.items():
            index[term] = {"canonical": canonical, "allergen": allergen}
    for term, canonical in INGREDIENT_SYNONYMS.items():
        index.setdefault(term, {"canonical": canonical, "allergen": None})
    return index


EXACT_INDEX = build_exact_index()


def _result_from_match(
    raw_term: str, cleaned_term: str, normalized_term: str, match_type: str,
    confidence: float, provenance: str, status: str,
    candidates: list[CandidateMatch] | None = None,
) -> NormalizationResult:
    canonical, allergen = resolve_canonical_concept(normalized_term)
    return NormalizationResult(
        raw_term=raw_term,
        cleaned_term=cleaned_term,
        normalized_term=normalized_term,
        canonical_concept=canonical,
        match_type=match_type,
        confidence=confidence,
        status=status,
        allergen=allergen,
        candidate_matches=candidates,
        provenance=provenance,
    )


def normalize_ingredient(
    raw_term: str, fuzzy_threshold: int = 85, dataset_threshold: float = 0.90,
    candidate_threshold: float = 0.70,
) -> NormalizationResult:
    """Normalize through curated, dataset, then candidate-segmentation stages.

    Confidence is deterministic matching confidence, not a calibrated
    probability: curated exact=1.00; compact/dataset exact=1.00; dataset fuzzy
    is the weighted similarity score; segmentation retains its known score.
    """
    if not raw_term or not raw_term.strip():
        return NormalizationResult(raw_term, None, None, None, "no_match", 0.0, "unknown")

    cleaned = re.sub(r"^unbleached\s+", "", clean_text(raw_term))
    if cleaned in EXACT_INDEX:
        return _result_from_match(raw_term, cleaned, cleaned, "curated_exact", 1.0, "curated_dictionary", "known")

    match = dataset_match(cleaned, threshold=dataset_threshold)
    if match and match["accepted"]:
        return _result_from_match(
            raw_term, cleaned, match["candidate"], match["match_type"], match["score"],
            "dataset_vocabulary", "known", match["candidates"],
        )

    # Lazy import avoids the candidate segmenter's backwards-compatible import
    # of ``clean_text`` and ``EXACT_INDEX`` from this module.
    from .candidate_segmenter import generate_candidate_segments

    segments = generate_candidate_segments(raw_term)
    # A multiword known segment inside a longer phrase is stronger evidence of
    # partial extraction than an unrelated whole-phrase fuzzy candidate.
    if segments and any(segment.end - segment.start >= 2 for segment in segments):
        candidates = []
        for segment in segments:
            canonical, allergen = resolve_canonical_concept(segment.text)
            candidates.append(CandidateMatch(segment.text, segment.confidence, "candidate_segmentation", None, segment.confidence, allergen, canonical))
        return NormalizationResult(
            raw_term, cleaned, None, None, "partial_match", max(item.confidence for item in candidates),
            "ambiguous", None, candidates, "candidate_segmentation", raw_term,
        )

    if match and match["score"] >= candidate_threshold:
        return _result_from_match(
            raw_term, cleaned, match["candidate"], "dataset_candidate", match["score"],
            "dataset_vocabulary", "candidate", match["candidates"],
        )

    return NormalizationResult(raw_term, cleaned, None, None, "no_match", 0.0, "unknown", provenance="unknown", unresolved_text=raw_term)


def normalize_ingredients(
    ingredients: list[str], fuzzy_threshold: int = 85, dataset_threshold: float = 0.90,
    candidate_threshold: float = 0.70,
) -> list[NormalizationResult]:
    return [normalize_ingredient(item, fuzzy_threshold, dataset_threshold, candidate_threshold) for item in ingredients]
