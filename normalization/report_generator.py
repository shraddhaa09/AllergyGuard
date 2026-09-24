"""
report_generator.py
---------------------
Phase 3: the "Explainable Report" component from the architecture
diagrams (Layer 4 in System_Architecture.png) -- combines allergen
evidence + personalized messaging into one structured, explainable
result that a FastAPI endpoint can return as JSON and the frontend can
render directly.

Explicitly avoids medical-safety claims (per the project's own
principle #4 in "what's still missing"): the report never says a
product is "safe", only what evidence was or wasn't found.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Dict, List, Optional

from .allergen_knowledge import AllergenAssessment
from .risk_messaging import build_user_messages

DISCLAIMER = (
    "This result is based only on the ingredient information visible in "
    "the photo you provided. It is a screening aid, not a medical or "
    "safety guarantee. When in doubt, check the physical label or "
    "consult the manufacturer."
)

_OVERALL_PRIORITY = ["DETECTED", "POTENTIAL", "INSUFFICIENT_EVIDENCE", "NOT_DETECTED"]


@dataclass
class ExplainableReport:
    product_name: Optional[str]
    ocr_confidence: Optional[float]
    overall_status: str
    per_allergen: List[dict]
    disclaimer: str = DISCLAIMER

    def to_dict(self) -> dict:
        return asdict(self)


def _overall_status(assessments: Dict[str, AllergenAssessment]) -> str:
    """The single worst-case status across the user's flagged allergens,
    so the frontend can show one headline badge alongside the breakdown."""
    statuses = {a.status for a in assessments.values()}
    for candidate in _OVERALL_PRIORITY:
        if candidate in statuses:
            return candidate
    return "NOT_DETECTED"


def generate_explainable_report(
    assessments: Dict[str, AllergenAssessment],
    user_allergies: Dict[str, Optional[str]],
    *,
    product_name: Optional[str] = None,
    ocr_confidence: Optional[float] = None,
) -> ExplainableReport:
    """
    assessments: full allergen -> AllergenAssessment map (from
        allergen_knowledge.assess_allergens), already computed once per image.
    user_allergies: {"MILK": "severe", "PEANUT": None, ...} -- only these
        allergens are surfaced in the report.
    """
    relevant = {a: assessments[a] for a in user_allergies if a in assessments}
    messages = build_user_messages(assessments, user_allergies)

    per_allergen = []
    for allergen, assessment in relevant.items():
        message = messages[allergen]
        per_allergen.append({
            "allergen": assessment.display_name,
            "status": assessment.status,
            "headline": message.headline,
            "detail": message.detail,
            "severity_note": message.severity_note,
            "evidence": [
                {
                    "matched_term": e.matched_synonym,
                    "found_in": e.source_text,
                    "match_type": e.match_type,
                    "confidence": round(e.confidence, 2),
                }
                for e in assessment.evidence
            ],
        })

    return ExplainableReport(
        product_name=product_name,
        ocr_confidence=ocr_confidence,
        overall_status=_overall_status(relevant) if relevant else "NOT_DETECTED",
        per_allergen=per_allergen,
    )