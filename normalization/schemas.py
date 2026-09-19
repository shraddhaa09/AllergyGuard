from dataclasses import dataclass
from typing import Optional


@dataclass
class NormalizationResult:
    raw_term: str
    normalized_term: Optional[str]
    canonical_concept: Optional[str]
    match_type: str
    confidence: float
    status: str


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