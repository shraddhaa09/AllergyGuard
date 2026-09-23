"""User-provided allergy preferences; no product evidence logic belongs here."""

from dataclasses import dataclass, field
from enum import StrEnum


class AllergySeverity(StrEnum):
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"


@dataclass(frozen=True)
class UserAllergy:
    allergen: str
    severity: AllergySeverity = AllergySeverity.HIGH
    avoidance_required: bool = True
    notes: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "allergen", self.allergen.upper().strip())
        if isinstance(self.severity, str):
            object.__setattr__(self, "severity", AllergySeverity(self.severity.upper()))
        if not self.allergen:
            raise ValueError("A user allergy must name an allergen.")


@dataclass
class UserProfile:
    allergies: list[UserAllergy] = field(default_factory=list)

    def allergy_for(self, allergen: str) -> UserAllergy | None:
        return next((item for item in self.allergies if item.allergen == allergen.upper()), None)
