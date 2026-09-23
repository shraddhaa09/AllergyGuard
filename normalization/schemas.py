from dataclasses import dataclass
from typing import Optional


@dataclass
class CandidateMatch:
    candidate: str
    similarity: float
    match_method: str
    frequency: int | None
    confidence: float
    allergen: str | None
    canonical_concept: str | None


@dataclass
class NormalizationResult:
    raw_term: str
    cleaned_term: Optional[str]
    normalized_term: Optional[str]
    canonical_concept: Optional[str]
    match_type: str
    confidence: float
    status: str
    allergen: Optional[str] = None
    candidate_matches: list[CandidateMatch] | None = None
    provenance: str = "unknown"
    unresolved_text: Optional[str] = None


@dataclass
class AllergenEvidence:
    allergen: str
    ingredient: str
    canonical_concept: Optional[str]
    evidence_type: str
    source: str
    confidence: float
    provenance: str
    supporting_text: str
    status: str


@dataclass
class AllergenAssessment:
    allergen: str
    status: str
    confidence: float
    evidence: list[AllergenEvidence]
    explanation: str


@dataclass
class IngredientEvidence:
    image: Optional[str] = None
    source: str = "paddleocr"
    raw_text: str = ""
    cleaned_text: str = ""
    parent: Optional[str] = None
    level: str = "top_level"
    extraction_method: str = "comma_split"
    provenance: str = "ocr_region"
