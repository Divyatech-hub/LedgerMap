from collections.abc import Mapping

from rapidfuzz import fuzz, process

from ledgermap.domain.models import MappingCandidate, MappingMethod


def normalize_name(value: str) -> str:
    return " ".join(value.casefold().split())


def resolve_name(
    raw_name: str,
    mappings: Mapping[str, str | None],
    *,
    fuzzy_threshold: int = 90,
) -> MappingCandidate:
    normalized = normalize_name(raw_name)
    exact = mappings.get(normalized)
    if exact:
        return MappingCandidate(code=exact, confidence=1.0, method=MappingMethod.EXACT)

    choices = list(mappings)
    if not choices:
        return MappingCandidate(
            code=None,
            confidence=0.0,
            method=MappingMethod.REVIEW,
            review_reason="no_mapping_candidates",
        )
    match = process.extractOne(normalized, choices, scorer=fuzz.token_sort_ratio)
    if match is None or match[1] < fuzzy_threshold or not mappings[match[0]]:
        return MappingCandidate(
            code=None,
            confidence=(match[1] / 100 if match else 0.0),
            method=MappingMethod.REVIEW,
            review_reason="low_fuzzy_confidence",
        )
    return MappingCandidate(
        code=mappings[match[0]],
        confidence=match[1] / 100,
        method=MappingMethod.FUZZY,
    )