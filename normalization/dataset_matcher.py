"""Indexed, deterministic retrieval from the dataset-derived vocabulary."""

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from rapidfuzz import fuzz, process

from .allergy_knowledge import resolve_canonical_concept
from .ingredient_vocabulary import VOCABULARY_PATH, load_vocabulary
from .schemas import CandidateMatch


def _compact(text: str) -> str:
    return "".join(character for character in text.lower() if character.isalnum())


@dataclass(frozen=True)
class VocabularyIndex:
    frequencies: dict[str, int]
    token_index: dict[str, tuple[str, ...]]
    compact_index: dict[str, str]
    first_character_index: dict[str, tuple[str, ...]]


@lru_cache(maxsize=4)
def load_vocabulary_index(path: str) -> VocabularyIndex:
    """Load once per vocabulary path and build compact retrieval indices."""
    vocabulary_path = Path(path)
    if not vocabulary_path.exists():
        return VocabularyIndex({}, {}, {}, {})
    dataframe = load_vocabulary(vocabulary_path)
    frequencies = {
        str(row.raw_term).lower(): int(row.frequency)
        for row in dataframe[["raw_term", "frequency"]].itertuples(index=False)
        if str(row.raw_term).strip()
    }
    token_index: dict[str, set[str]] = {}
    first_character_index: dict[str, set[str]] = {}
    compact_index: dict[str, str] = {}
    for term in frequencies:
        compact_index.setdefault(_compact(term), term)
        if term:
            first_character_index.setdefault(term[0], set()).add(term)
        for token in set(term.split()):
            token_index.setdefault(token, set()).add(term)
    return VocabularyIndex(
        frequencies,
        {key: tuple(value) for key, value in token_index.items()},
        compact_index,
        {key: tuple(value) for key, value in first_character_index.items()},
    )


def _candidate_pool(term: str, index: VocabularyIndex) -> tuple[str, ...]:
    candidates: set[str] = set()
    for token in set(term.split()):
        candidates.update(index.token_index.get(token, ()))
    if candidates:
        return tuple(candidates)
    return index.first_character_index.get(term[:1], ())[:2000]


def retrieve_dataset_candidates(
    term: str, limit: int = 5, vocabulary_path: str | Path = VOCABULARY_PATH,
) -> list[CandidateMatch]:
    """Rank plausible dataset candidates without automatically accepting them."""
    cleaned = term.lower().strip()
    index = load_vocabulary_index(str(Path(vocabulary_path).resolve()))
    if not cleaned or not index.frequencies:
        return []
    compact = _compact(cleaned)
    compact_match = index.compact_index.get(compact)
    if compact_match:
        canonical, allergen = resolve_canonical_concept(compact_match)
        return [CandidateMatch(compact_match, 1.0, "compact_exact", index.frequencies[compact_match], 1.0, allergen, canonical)]

    pool = _candidate_pool(cleaned, index)
    if not pool:
        return []
    # WRatio is only a retrieval heuristic.  Keep a wider shortlist because its
    # partial-match preference can otherwise hide a cleaner full-term typo.
    shortlist_size = min(len(pool), 100)
    rough_matches = process.extract(cleaned, pool, scorer=fuzz.WRatio, limit=shortlist_size)
    ratio_matches = process.extract(cleaned, pool, scorer=fuzz.ratio, limit=shortlist_size)
    shortlisted_terms = {candidate for candidate, _, _ in rough_matches}
    shortlisted_terms.update(candidate for candidate, _, _ in ratio_matches)
    ranked = []
    for candidate in shortlisted_terms:
        character_score = fuzz.ratio(cleaned, candidate) / 100.0
        token_score = fuzz.token_sort_ratio(cleaned, candidate) / 100.0
        compact_score = fuzz.ratio(compact, _compact(candidate)) / 100.0
        similarity = round(0.45 * character_score + 0.30 * token_score + 0.25 * compact_score, 4)
        canonical, allergen = resolve_canonical_concept(candidate)
        ranked.append(CandidateMatch(candidate, similarity, "dataset_fuzzy", index.frequencies[candidate], similarity, allergen, canonical))
    return sorted(ranked, key=lambda item: (item.similarity, item.frequency or 0), reverse=True)[:limit]


def dataset_match(
    term: str, threshold: float = 0.90, vocabulary_path: str | Path = VOCABULARY_PATH,
) -> dict | None:
    """Return best candidate, ranked alternatives, and threshold acceptance."""
    candidates = retrieve_dataset_candidates(term, limit=5, vocabulary_path=vocabulary_path)
    if not candidates:
        return None
    best = candidates[0]
    exact = best.match_method == "compact_exact"
    return {
        "candidate": best.candidate,
        "score": best.similarity,
        "match_type": "dataset_exact" if exact else best.match_method,
        "accepted": exact or best.similarity >= threshold,
        "candidates": candidates,
    }
