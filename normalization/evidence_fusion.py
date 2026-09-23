"""Convert normalized ingredients into traceable allergen evidence.

This is intentionally downstream of normalization: it consumes normalized
concepts and curated allergy knowledge, rather than parsing OCR text itself.
"""

import re
from collections import defaultdict
from typing import Iterable

from .allergy_knowledge import resolve_canonical_concept
from .dictionary import ALLERGEN_SYNONYMS
from .schemas import AllergenAssessment, AllergenEvidence, IngredientEvidence, NormalizationResult


ALLERGENS = tuple(ALLERGEN_SYNONYMS)


def extract_contains_evidence(text: str) -> list[AllergenEvidence]:
    """Extract explicit label ``CONTAINS:`` statements as strong evidence."""
    if not text:
        return []
    match = re.search(r"\bCONTAINS?\s*:\s*([^\.\n]+)", str(text), flags=re.IGNORECASE)
    if not match:
        return []
    evidence = []
    for item in re.split(r"[,;]", match.group(1)):
        term = item.strip().lower()
        canonical, allergen = resolve_canonical_concept(term)
        if allergen:
            evidence.append(AllergenEvidence(
                allergen=allergen,
                ingredient=term,
                canonical_concept=canonical,
                evidence_type="CONTAINS_STATEMENT",
                source="label_contains_statement",
                confidence=1.0,
                provenance="label_contains_statement",
                supporting_text=item.strip(),
                status="strong",
            ))
    return evidence


def evidence_from_normalization(
    result: NormalizationResult,
    ingredient_evidence: IngredientEvidence | None = None,
) -> list[AllergenEvidence]:
    """Generate allergen evidence without promoting uncertain matches."""
    source = "ingredient_list"
    nested = ingredient_evidence is not None and ingredient_evidence.level == "nested"
    supporting_text = result.raw_term
    normalized_surface = result.normalized_term or ""
    resolved_concept, resolved_allergen = resolve_canonical_concept(normalized_surface) if normalized_surface else (None, None)

    if result.status == "known" and resolved_allergen:
        evidence_type = "NESTED_INGREDIENT" if nested else (
            "DIRECT_INGREDIENT" if result.normalized_term == result.canonical_concept else "NORMALIZED_INGREDIENT"
        )
        return [AllergenEvidence(
            allergen=resolved_allergen,
            ingredient=result.normalized_term or result.raw_term,
            canonical_concept=resolved_concept,
            evidence_type=evidence_type,
            source=source,
            confidence=result.confidence,
            provenance=result.provenance,
            supporting_text=supporting_text,
            status="strong",
        )]

    # Candidate normalization is useful but remains potential evidence.
    if result.status == "candidate" and resolved_allergen:
        return [AllergenEvidence(
            allergen=resolved_allergen,
            ingredient=result.normalized_term or result.raw_term,
            canonical_concept=resolved_concept,
            evidence_type="FUZZY_NORMALIZATION",
            source=source,
            confidence=result.confidence,
            provenance=result.provenance,
            supporting_text=supporting_text,
            status="weak",
        )]

    if result.status == "ambiguous":
        candidates = []
        for candidate in result.candidate_matches or []:
            if candidate.allergen:
                candidates.append(AllergenEvidence(
                    allergen=candidate.allergen,
                    ingredient=candidate.candidate,
                    canonical_concept=candidate.canonical_concept,
                    evidence_type="PARTIAL_MATCH",
                    source=source,
                    confidence=min(candidate.confidence, 0.75),
                    provenance="candidate_segmentation",
                    supporting_text=supporting_text,
                    status="weak",
                ))
        return candidates
    return []


def collect_allergen_evidence(
    normalized_results: Iterable[NormalizationResult],
    ingredient_evidence: Iterable[IngredientEvidence] | None = None,
    source_text: str | None = None,
) -> list[AllergenEvidence]:
    """Collect and deduplicate evidence from normalized ingredient records."""
    results = list(normalized_results)
    extraction_items = list(ingredient_evidence) if ingredient_evidence is not None else [None] * len(results)
    evidence = extract_contains_evidence(source_text or "")
    for result, extracted in zip(results, extraction_items):
        evidence.extend(evidence_from_normalization(result, extracted))

    deduplicated = []
    seen = set()
    for item in evidence:
        # Duplicate extraction records must not artificially strengthen fusion.
        key = (item.allergen, item.ingredient, item.supporting_text.lower(), item.source)
        if key not in seen:
            seen.add(key)
            deduplicated.append(item)
    return deduplicated


def fuse_allergen_evidence(
    evidence: Iterable[AllergenEvidence],
    normalized_results: Iterable[NormalizationResult] | None = None,
) -> list[AllergenAssessment]:
    """Create deterministic allergen-level statuses.

    Fusion uses the strongest unique evidence plus a capped 0.02 bonus for
    additional distinct supporting ingredients.  It is matching confidence,
    not a medical probability.  Strong evidence (>=0.95) is DETECTED; weaker
    plausible evidence is POTENTIAL.  With known non-allergen ingredients but
    no evidence, status is NOT_DETECTED; all-unknown input is insufficient.
    """
    grouped: dict[str, list[AllergenEvidence]] = defaultdict(list)
    for item in evidence:
        grouped[item.allergen].append(item)
    results = list(normalized_results or [])
    has_known_ingredient = any(result.status == "known" for result in results)
    assessments = []
    for allergen in ALLERGENS:
        items = grouped[allergen]
        if items:
            unique_ingredients = {(item.ingredient, item.source) for item in items}
            confidence = min(1.0, max(item.confidence for item in items) + 0.02 * (len(unique_ingredients) - 1))
            status = "DETECTED" if any(item.confidence >= 0.95 and item.status == "strong" for item in items) else "POTENTIAL"
            explanation = (
                "Strong explicit allergen evidence found." if status == "DETECTED"
                else "Potential allergen evidence found; manual verification recommended."
            )
        elif not results or not has_known_ingredient:
            confidence, status = 0.0, "INSUFFICIENT_EVIDENCE"
            explanation = "Available extraction or normalization evidence is too incomplete for a conclusion."
        else:
            confidence, status = 0.0, "NOT_DETECTED"
            explanation = "No known allergen detected from available ingredient evidence."
        assessments.append(AllergenAssessment(allergen, status, confidence, items, explanation))
    return assessments


def assess_allergens(
    normalized_results: Iterable[NormalizationResult],
    ingredient_evidence: Iterable[IngredientEvidence] | None = None,
    source_text: str | None = None,
) -> tuple[list[AllergenEvidence], list[AllergenAssessment]]:
    results = list(normalized_results)
    evidence = collect_allergen_evidence(results, ingredient_evidence, source_text)
    return evidence, fuse_allergen_evidence(evidence, results)
