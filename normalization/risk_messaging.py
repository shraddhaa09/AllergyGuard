"""
risk_messaging.py
-------------------
Phase 2 of the "still missing" work: turn the technical statuses
(DETECTED / POTENTIAL / NOT_DETECTED / INSUFFICIENT_EVIDENCE) into the
simple, personalized language the project note already sketched out:

    (Red)    Allergen found
    (Orange) Please check the label
    (White)  Can't determine
    (Green)  No known match found

Also enforces the project's stated design principle: never claim the
product is medically "safe". The wording always stays evidence-based
("no allergen found in the visible information"), not a safety claim.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

from .allergen_knowledge import AllergenAssessment

SEVERITY_LEVELS = ("mild", "moderate", "severe")

_STATUS_META = {
    "DETECTED": {"emoji": "\U0001F534", "label": "Allergen found"},          # red circle
    "POTENTIAL": {"emoji": "\U0001F7E0", "label": "Please check the label"},  # orange circle
    "NOT_DETECTED": {"emoji": "\U0001F7E2", "label": "No known match found"},  # green circle
    "INSUFFICIENT_EVIDENCE": {"emoji": "\u26AA", "label": "Can't determine"},  # white circle
}


@dataclass
class PersonalizedMessage:
    allergen: str
    status: str
    emoji: str
    headline: str
    detail: str
    severity_note: Optional[str] = None


def _detail_text(assessment: AllergenAssessment) -> str:
    name = assessment.display_name
    status = assessment.status

    if status == "DETECTED":
        sources = sorted({e.matched_synonym.title() for e in assessment.evidence})
        joined = ", ".join(sources[:4])
        return f"{name} was found in the visible ingredient information ({joined})."

    if status == "POTENTIAL":
        sources = sorted({e.matched_synonym.title() for e in assessment.evidence})
        joined = ", ".join(sources[:3]) if sources else "a possible match"
        return (
            f"We found text that may indicate {name.lower()} ({joined}), "
            "but the image isn't clear enough to confirm it."
        )

    if status == "NOT_DETECTED":
        return (
            f"No mention of {name.lower()} was found in the visible ingredient "
            "information. This does not guarantee the product is free of it."
        )

    # INSUFFICIENT_EVIDENCE
    return (
        "We couldn't read enough of the ingredient information to check for "
        f"{name.lower()}. Try a clearer, closer photo of the ingredient list."
    )


def _severity_note(status: str, severity: Optional[str]) -> Optional[str]:
    if not severity or severity not in SEVERITY_LEVELS:
        return None

    if status in ("DETECTED", "POTENTIAL") and severity == "severe":
        return (
            "You've flagged this as a severe allergy — treat this result with "
            "extra caution and consider avoiding the product unless you can "
            "verify the ingredients another way."
        )
    if status == "INSUFFICIENT_EVIDENCE" and severity == "severe":
        return (
            "Because this is a severe allergy, we recommend not relying on an "
            "unclear image — please recheck with a clearer photo or the "
            "printed label."
        )
    if status == "POTENTIAL" and severity == "mild":
        return "Given this is a mild allergy, you may choose to check the label yourself before deciding."
    return None


def build_user_message(
    assessment: AllergenAssessment,
    severity: Optional[str] = None,
) -> PersonalizedMessage:
    """Convert one AllergenAssessment into a plain-language, personalized message."""
    meta = _STATUS_META[assessment.status]
    return PersonalizedMessage(
        allergen=assessment.allergen,
        status=assessment.status,
        emoji=meta["emoji"],
        headline=f'{meta["emoji"]} {meta["label"]}',
        detail=_detail_text(assessment),
        severity_note=_severity_note(assessment.status, severity),
    )


def build_user_messages(
    assessments: Dict[str, AllergenAssessment],
    user_allergies: Dict[str, Optional[str]],
) -> Dict[str, PersonalizedMessage]:
    """
    Build personalized messages only for the allergens the user actually
    cares about.

    user_allergies: {"MILK": "severe", "SOY": None, ...}
    """
    out: Dict[str, PersonalizedMessage] = {}
    for allergen, severity in user_allergies.items():
        assessment = assessments.get(allergen)
        if assessment is None:
            continue
        out[allergen] = build_user_message(assessment, severity)
    return out