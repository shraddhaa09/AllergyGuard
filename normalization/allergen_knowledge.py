"""
allergen_knowledge.py
----------------------
Phase 1 of the "still missing" work: broader allergen coverage.

Extends AllergyGuard's allergen ontology from the original baseline
(WHEAT, SOY, MILK) to the FDA "Big 9" major food allergens, and keeps the
same evidence-based philosophy already established in the project:

    OCR found the word  !=  allergen detected

Every match is returned as structured `AllergenEvidence`, and every
allergen gets an `AllergenAssessment` with one of the four statuses the
project has already defined:

    DETECTED              - strong evidence (explicit CONTAINS statement,
                             or a confident exact ingredient match)
    POTENTIAL              - a plausible but not-confident match
                             (e.g. a fuzzy/OCR-noisy match)
    NOT_DETECTED           - usable ingredient text was available and no
                             evidence for this allergen was found in it
    INSUFFICIENT_EVIDENCE  - not enough reliable text to decide either way

This module has NO dependency on PaddleOCR, Florence-2, Qwen2-VL, or any
of the rest of the pipeline. It only consumes plain strings, so it can be
dropped into the existing `normalization/` or a new `allergy_engine/`
package and wired up to whatever ingredient-extraction output you already
have (raw_text / cleaned_text candidates from ingredient_extractor.py).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence

try:
    from rapidfuzz import fuzz
    _HAS_RAPIDFUZZ = True
except ImportError:  # pragma: no cover - fallback keeps this dependency-free
    import difflib
    _HAS_RAPIDFUZZ = False


# ---------------------------------------------------------------------------
# 1. Allergen ontology
# ---------------------------------------------------------------------------
# FDA "Big 9" major food allergens (post-FASTER Act, which added sesame).
# Each entry lists ingredient-level synonyms/derivatives that OCR'd labels
# commonly contain. This is a starting ontology, not a medical/legal source
# of truth -- it is meant to be extended the same way WHEAT/SOY/MILK already
# were in the baseline rule set.

ALLERGEN_DATABASE: Dict[str, Dict[str, object]] = {
    "WHEAT": {
        "display_name": "Wheat",
        "synonyms": [
            "WHEAT", "WHEAT FLOUR", "ENRICHED FLOUR", "ENRICHED WHEAT FLOUR",
            "WHOLE WHEAT", "WHOLE WHEAT FLOUR", "BREAD FLOUR", "DURUM",
            "DURUM WHEAT", "SEMOLINA", "SPELT", "BULGUR", "FARINA",
            "GRAHAM FLOUR", "VITAL WHEAT GLUTEN", "WHEAT GLUTEN", "COUSCOUS",
            "WHEAT STARCH", "WHEAT BRAN",
        ],
    },
    "SOY": {
        "display_name": "Soy",
        "synonyms": [
            "SOY", "SOYBEAN", "SOYBEAN OIL", "SOY LECITHIN", "SOYA",
            "SOYA SAUCE", "SOY SAUCE", "TEXTURED VEGETABLE PROTEIN", "TVP",
            "TOFU", "EDAMAME", "MISO", "TEMPEH", "HYDROLYZED SOY PROTEIN",
        ],
    },
    "MILK": {
        "display_name": "Milk",
        "synonyms": [
            "MILK", "BUTTER", "CHEESE", "COTTAGE CHEESE", "CREAM", "WHEY",
            "CASEIN", "CASEINATE", "SODIUM CASEINATE", "LACTOSE", "GHEE",
            "CUSTARD", "YOGURT", "SOUR CREAM", "MILK SOLIDS",
            "NONFAT MILK POWDER", "BUTTERMILK", "MILK POWDER",
        ],
    },
    "EGG": {
        "display_name": "Egg",
        "synonyms": [
            "EGG", "EGGS", "EGG WHITE", "EGG YOLK", "WHOLE EGG", "ALBUMIN",
            "OVALBUMIN", "MAYONNAISE", "MERINGUE", "LYSOZYME",
            "DRIED EGG", "EGG POWDER",
        ],
    },
    "PEANUT": {
        "display_name": "Peanut",
        "synonyms": [
            "PEANUT", "PEANUTS", "PEANUT OIL", "PEANUT BUTTER", "GROUNDNUT",
            "GROUND NUT", "ARACHIS OIL", "PEANUT FLOUR",
        ],
    },
    "TREE_NUT": {
        "display_name": "Tree Nuts",
        "synonyms": [
            "ALMOND", "ALMONDS", "CASHEW", "CASHEWS", "WALNUT", "WALNUTS",
            "PECAN", "PECANS", "PISTACHIO", "PISTACHIOS", "HAZELNUT",
            "HAZELNUTS", "MACADAMIA", "MACADAMIA NUT", "BRAZIL NUT",
            "BRAZIL NUTS", "PINE NUT", "PINE NUTS", "NUT BUTTER",
            "ALMOND MILK", "CASHEW BUTTER",
        ],
    },
    "FISH": {
        "display_name": "Fish",
        "synonyms": [
            "FISH", "ANCHOVY", "ANCHOVIES", "COD", "SALMON", "TUNA",
            "TILAPIA", "FISH SAUCE", "FISH OIL", "SURIMI", "BASS", "TROUT",
        ],
    },
    "SHELLFISH": {
        "display_name": "Shellfish (Crustacean)",
        "synonyms": [
            "SHRIMP", "PRAWN", "PRAWNS", "CRAB", "LOBSTER", "CRAWFISH",
            "CRAYFISH", "CRUSTACEAN", "SHELLFISH",
        ],
    },
    "SESAME": {
        "display_name": "Sesame",
        "synonyms": [
            "SESAME", "SESAME SEED", "SESAME SEEDS", "SESAME OIL", "TAHINI",
            "SESAME FLOUR", "SESAME PASTE", "BENNE SEED",
        ],
    },
}

ALL_ALLERGENS: List[str] = list(ALLERGEN_DATABASE.keys())

# Matching thresholds (0-100 scale). Tunable per-deployment.
EXACT_MATCH_SCORE = 100
FUZZY_MATCH_THRESHOLD = 82  # below this, we don't even call it "potential"


# ---------------------------------------------------------------------------
# 2. Evidence + assessment data model
# ---------------------------------------------------------------------------

@dataclass
class AllergenEvidence:
    allergen: str
    matched_synonym: str
    source_text: str            # the actual ingredient/CONTAINS text it came from
    match_type: str              # "explicit_contains" | "exact_ingredient" | "fuzzy_ingredient"
    similarity: float            # 0-100
    confidence: float            # 0-1, derived from match_type + similarity


@dataclass
class AllergenAssessment:
    allergen: str
    status: str                  # DETECTED | POTENTIAL | NOT_DETECTED | INSUFFICIENT_EVIDENCE
    evidence: List[AllergenEvidence] = field(default_factory=list)

    @property
    def display_name(self) -> str:
        return ALLERGEN_DATABASE.get(self.allergen, {}).get("display_name", self.allergen)


# ---------------------------------------------------------------------------
# 3. Matching helpers
# ---------------------------------------------------------------------------

def _similarity(a: str, b: str) -> float:
    """Token/phrase similarity 0-100, using rapidfuzz if available."""
    a, b = a.upper().strip(), b.upper().strip()
    if a == b:
        return 100.0
    if _HAS_RAPIDFUZZ:
        return fuzz.token_sort_ratio(a, b)
    return difflib.SequenceMatcher(None, a, b).ratio() * 100.0


def _best_match_in_text(text: str, synonyms: Sequence[str]) -> Optional[tuple]:
    """
    Returns (matched_synonym, similarity, is_exact) for the best synonym
    match found as a substring/near-substring of `text`, or None.
    """
    text_u = text.upper()
    best: Optional[tuple] = None

    for syn in synonyms:
        if syn in text_u:
            # exact substring match -> perfect score, short-circuits fuzzy search
            return (syn, 100.0, True)

        # fuzzy fallback: compare synonym against each word-window of text
        words = text_u.split()
        for window in (1, 2, 3):
            for i in range(len(words) - window + 1):
                phrase = " ".join(words[i:i + window])
                score = _similarity(phrase, syn)
                if best is None or score > best[1]:
                    best = (syn, score, False)

    if best and best[1] >= FUZZY_MATCH_THRESHOLD:
        return best
    return None


# ---------------------------------------------------------------------------
# 4. Core evidence-based assessment
# ---------------------------------------------------------------------------

def assess_allergens(
    ingredient_terms: Sequence[str],
    contains_statement_terms: Sequence[str] = (),
    *,
    has_ingredient_text: bool = True,
    ocr_confidence: Optional[float] = None,
    target_allergens: Optional[Sequence[str]] = None,
    min_reliable_ocr_confidence: float = 0.6,
) -> Dict[str, AllergenAssessment]:
    """
    Evidence-based allergen assessment, following the project's existing
    principle: OCR finding a word is not the same as an allergen being
    confirmed.

    Parameters
    ----------
    ingredient_terms:
        Cleaned ingredient candidates (e.g. from ingredient_extractor.py's
        hierarchical extraction -- flatten parent + child terms first).
    contains_statement_terms:
        Terms parsed specifically from a "CONTAINS: ..." declaration, if
        one was found. These carry the strongest evidence.
    has_ingredient_text:
        False if no ingredient/CONTAINS section could be located at all
        (e.g. oreo.jpg in the project's own evaluation set).
    ocr_confidence:
        Average OCR confidence for the extracted text, if available.
    target_allergens:
        Which allergens to evaluate. Defaults to the full ontology.
    min_reliable_ocr_confidence:
        Below this, evidence is downgraded to INSUFFICIENT_EVIDENCE even if
        a fuzzy match was found, since low-confidence OCR text is not a
        trustworthy source for that match.

    Returns
    -------
    Dict[allergen -> AllergenAssessment]
    """
    targets = list(target_allergens) if target_allergens else ALL_ALLERGENS
    results: Dict[str, AllergenAssessment] = {}

    # Global insufficiency check: no usable text at all.
    globally_insufficient = (
        not has_ingredient_text
        and not contains_statement_terms
        and not ingredient_terms
    )

    ocr_unreliable = ocr_confidence is not None and ocr_confidence < min_reliable_ocr_confidence

    for allergen in targets:
        synonyms = ALLERGEN_DATABASE[allergen]["synonyms"]
        evidence: List[AllergenEvidence] = []

        # a) explicit CONTAINS: statement -> strongest evidence
        for term in contains_statement_terms:
            match = _best_match_in_text(term, synonyms)
            if match:
                syn, score, is_exact = match
                evidence.append(AllergenEvidence(
                    allergen=allergen,
                    matched_synonym=syn,
                    source_text=term,
                    match_type="explicit_contains",
                    similarity=score,
                    confidence=0.99 if is_exact else 0.90,
                ))

        # b) ingredient list evidence -> exact vs fuzzy
        for term in ingredient_terms:
            match = _best_match_in_text(term, synonyms)
            if match:
                syn, score, is_exact = match
                evidence.append(AllergenEvidence(
                    allergen=allergen,
                    matched_synonym=syn,
                    source_text=term,
                    match_type="exact_ingredient" if is_exact else "fuzzy_ingredient",
                    similarity=score,
                    confidence=0.90 if is_exact else max(0.4, score / 150),
                ))

        # c) decide status
        if globally_insufficient:
            status = "INSUFFICIENT_EVIDENCE"
        elif any(e.match_type == "explicit_contains" for e in evidence):
            status = "DETECTED"
        elif any(e.match_type == "exact_ingredient" for e in evidence) and not ocr_unreliable:
            status = "DETECTED"
        elif evidence:
            # only fuzzy matches, or an exact match riding on unreliable OCR
            status = "INSUFFICIENT_EVIDENCE" if ocr_unreliable else "POTENTIAL"
        elif not has_ingredient_text:
            status = "INSUFFICIENT_EVIDENCE"
        else:
            status = "NOT_DETECTED"

        results[allergen] = AllergenAssessment(allergen=allergen, status=status, evidence=evidence)

    return results