"""Rule-consistency scenarios for personalized risk assessment, not medical accuracy."""

from collections import Counter

from .risk_assessment import RiskLevel, assess_personalized_risk
from .schemas import AllergenAssessment
from .user_profile import UserAllergy, UserProfile


def assessment(allergen: str, status: str) -> AllergenAssessment:
    return AllergenAssessment(allergen, status, 1.0 if status == "DETECTED" else 0.7, [], "scenario")


def main() -> None:
    scenarios = [
        ("detected", UserProfile([UserAllergy("MILK")]), [assessment("MILK", "DETECTED")], RiskLevel.HIGH),
        ("potential", UserProfile([UserAllergy("SOY")]), [assessment("SOY", "POTENTIAL")], RiskLevel.MEDIUM),
        ("not_detected", UserProfile([UserAllergy("WHEAT")]), [assessment("WHEAT", "NOT_DETECTED")], RiskLevel.LOW),
        ("insufficient", UserProfile([UserAllergy("MILK")]), [assessment("MILK", "INSUFFICIENT_EVIDENCE")], RiskLevel.INSUFFICIENT_EVIDENCE),
        ("no_match", UserProfile([UserAllergy("PEANUT")]), [assessment("WHEAT", "DETECTED")], RiskLevel.NO_MATCH),
    ]
    results = []
    passed_count = 0
    for name, profile, evidence, expected in scenarios:
        actual = assess_personalized_risk(profile, evidence).overall_risk
        passed = actual == expected
        passed_count += passed
        results.append(actual)
        print(f"{name}: expected={expected}; actual={actual}; {'PASS' if passed else 'FAIL'}")
    print(f"Scenarios: {len(scenarios)} | passed: {passed_count}")
    print("Risk distribution:", dict(Counter(results)))
    print("This evaluates rule consistency, not medical accuracy or clinical risk.")


if __name__ == "__main__":
    main()
