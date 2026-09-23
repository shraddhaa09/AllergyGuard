"""Deterministic personalized allergen decision categories, not medical advice."""

from dataclasses import dataclass
from enum import StrEnum
from typing import Iterable

from .schemas import AllergenAssessment, AllergenEvidence
from .user_profile import UserAllergy, UserProfile


class RiskLevel(StrEnum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    NO_MATCH = "NO_MATCH"


@dataclass
class PersonalizedAllergenRisk:
    allergen: str
    risk_level: RiskLevel
    assessment_status: str
    reason: str
    supporting_ingredients: list[str]
    evidence_types: list[str]
    confidence: float
    provenance: list[str]
    sources: list[str]
    unresolved_text: list[str]
    conflict_note: str | None = None


@dataclass
class ProductRiskAssessment:
    overall_risk: RiskLevel
    matched_allergens: list[str]
    allergen_results: list[PersonalizedAllergenRisk]
    explanation: str
    warnings: list[str]
    unresolved_evidence: list[str]


_ASSESSMENT_PRECEDENCE = {"DETECTED": 4, "POTENTIAL": 3, "INSUFFICIENT_EVIDENCE": 2, "NOT_DETECTED": 1}
_RISK_PRECEDENCE = {
    RiskLevel.HIGH: 5,
    RiskLevel.MEDIUM: 4,
    RiskLevel.INSUFFICIENT_EVIDENCE: 3,
    RiskLevel.LOW: 2,
    RiskLevel.NO_MATCH: 1,
}


def _select_assessment(assessments: list[AllergenAssessment]) -> tuple[AllergenAssessment, str | None]:
    """Keep the strongest final assessment and surface any conflicting inputs."""
    selected = max(assessments, key=lambda item: _ASSESSMENT_PRECEDENCE.get(item.status, 0))
    statuses = {item.status for item in assessments}
    note = None
    if len(statuses) > 1:
        note = "Conflicting assessment statuses were retained; the strongest status was used deterministically."
    return selected, note


def _risk_for_assessment(user_allergy: UserAllergy, assessment: AllergenAssessment | None, conflict_note: str | None) -> PersonalizedAllergenRisk:
    if assessment is None:
        return PersonalizedAllergenRisk(
            user_allergy.allergen, RiskLevel.NO_MATCH, "NOT_ASSESSED",
            "No product allergen assessment is available for this profile allergen.", [], [], 0.0, [], [], [], conflict_note,
        )

    evidence: list[AllergenEvidence] = assessment.evidence
    ingredients = list(dict.fromkeys(item.ingredient for item in evidence))
    evidence_types = list(dict.fromkeys(item.evidence_type for item in evidence))
    provenance = list(dict.fromkeys(item.provenance for item in evidence))
    sources = list(dict.fromkeys(item.source for item in evidence))
    unresolved = list(dict.fromkeys(item.supporting_text for item in evidence if item.evidence_type == "PARTIAL_MATCH"))
    status_to_risk = {
        "DETECTED": RiskLevel.HIGH,
        "POTENTIAL": RiskLevel.MEDIUM,
        "INSUFFICIENT_EVIDENCE": RiskLevel.INSUFFICIENT_EVIDENCE,
        "NOT_DETECTED": RiskLevel.LOW,
    }
    level = status_to_risk.get(assessment.status, RiskLevel.INSUFFICIENT_EVIDENCE)
    reasons = {
        RiskLevel.HIGH: f"{assessment.allergen.title()} is associated with the user's allergy profile and was detected from available ingredient evidence.",
        RiskLevel.MEDIUM: f"{assessment.allergen.title()} may be present based on uncertain ingredient evidence; manual verification is recommended.",
        RiskLevel.LOW: f"No known {assessment.allergen.lower()} allergen was detected from available evidence.",
        RiskLevel.INSUFFICIENT_EVIDENCE: f"Available evidence is insufficient to determine whether {assessment.allergen.lower()} is present.",
    }
    return PersonalizedAllergenRisk(
        assessment.allergen, level, assessment.status, reasons[level], ingredients, evidence_types,
        assessment.confidence, provenance, sources, unresolved, conflict_note,
    )


def assess_personalized_risk(
    profile: UserProfile, allergen_assessments: Iterable[AllergenAssessment],
) -> ProductRiskAssessment:
    """Map fusion assessments to user-specific decision categories.

    These categories are deterministic system decisions, not medical risk scores,
    probabilities, diagnoses, or safety guarantees.
    """
    supplied_assessments = list(allergen_assessments)
    grouped: dict[str, list[AllergenAssessment]] = {}
    for assessment in supplied_assessments:
        grouped.setdefault(assessment.allergen, []).append(assessment)

    results = []
    for allergy in profile.allergies:
        available = grouped.get(allergy.allergen, [])
        if not available and not supplied_assessments:
            available = [AllergenAssessment(
                allergy.allergen, "INSUFFICIENT_EVIDENCE", 0.0, [],
                "No allergen assessment was available for the product.",
            )]
        selected, conflict = _select_assessment(available) if available else (None, None)
        results.append(_risk_for_assessment(allergy, selected, conflict))

    overall = max((item.risk_level for item in results), key=lambda level: _RISK_PRECEDENCE[level], default=RiskLevel.NO_MATCH)
    matched = [item.allergen for item in results if item.risk_level in {RiskLevel.HIGH, RiskLevel.MEDIUM}]
    unresolved = list(dict.fromkeys(text for item in results for text in item.unresolved_text))
    warnings = []
    if overall == RiskLevel.HIGH:
        warnings.append("Potentially relevant allergen detected for this user. Manual verification is recommended.")
    elif overall == RiskLevel.MEDIUM:
        warnings.append("Potential allergen evidence was found, but the evidence is uncertain. Manual verification is recommended.")
    elif overall == RiskLevel.INSUFFICIENT_EVIDENCE:
        warnings.append("Available evidence is insufficient to determine whether the relevant allergen is present.")
    elif overall == RiskLevel.LOW:
        warnings.append("No known allergen detected from available evidence.")
    else:
        warnings.append("No product allergen assessment matched this user profile.")
    return ProductRiskAssessment(
        overall, matched, results,
        "Personalized deterministic assessment based on the supplied profile and available allergen evidence; it is not medical advice.",
        warnings, unresolved,
    )
