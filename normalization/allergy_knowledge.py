"""Explicit curated knowledge linking normalized concepts to allergens."""

from .dictionary import ALLERGEN_SYNONYMS
from .ingredient_dictionary import INGREDIENT_SYNONYMS


def resolve_canonical_concept(term: str) -> tuple[str, str | None]:
    """Return ``(canonical_concept, allergen)`` for a normalized surface form."""
    normalized = term.lower().strip()
    for allergen, terms in ALLERGEN_SYNONYMS.items():
        if normalized in terms:
            return terms[normalized], allergen
    return INGREDIENT_SYNONYMS.get(normalized, normalized), None
