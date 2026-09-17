from ledgermap.domain.models import MappingMethod
from ledgermap.services.matching import resolve_name


def test_exact_match_precedes_fuzzy_match() -> None:
    result = resolve_name("Business Credit Card", {"business credit card": "2069"})

    assert result.code == "2069"
    assert result.method is MappingMethod.EXACT


def test_ambiguous_or_missing_match_is_review() -> None:
    result = resolve_name("Unseen Account", {"office rent": "3001"})

    assert result.code is None
    assert result.method is MappingMethod.REVIEW