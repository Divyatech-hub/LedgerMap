from decimal import Decimal

import pytest

from ledgermap.domain.models import AccountNode, MappingCandidate, MappingMethod
from ledgermap.integrations.llm.classifier import (
    NONE_MATCH,
    ClassificationRequest,
    ClassificationResult,
    validate_classification,
)
from ledgermap.services.llm_review import classify_reviews_with_llm
from ledgermap.services.run_pipeline import ProcessedLineItem

TAXONOMY = {"2001": "Capital Account", "3001": "Freight Charges"}


def _review_item(name: str, ancestors: tuple[str, ...] = ()) -> ProcessedLineItem:
    return ProcessedLineItem(
        node=AccountNode(
            name=name, amount=Decimal("100"), depth=0, ancestors=ancestors
        ),
        candidate=MappingCandidate(
            code=None,
            confidence=0.4,
            method=MappingMethod.REVIEW,
            review_reason="low_fuzzy_confidence",
        ),
    )


def _resolved_item(name: str, code: str) -> ProcessedLineItem:
    return ProcessedLineItem(
        node=AccountNode(name=name, amount=Decimal("100"), depth=0),
        candidate=MappingCandidate(
            code=code, confidence=1.0, method=MappingMethod.EXACT
        ),
    )


def test_validate_classification_accepts_a_real_code() -> None:
    assert validate_classification("3001", TAXONOMY) == "3001"


def test_validate_classification_rejects_none_match() -> None:
    assert validate_classification(NONE_MATCH, TAXONOMY) is None


def test_validate_classification_rejects_an_invented_code() -> None:
    # The model must never get a code it didn't actually have — this is the
    # closed-list rule from the README's design decision 5.
    assert validate_classification("9999", TAXONOMY) is None


@pytest.mark.asyncio
async def test_classify_reviews_with_llm_skips_already_resolved_items() -> None:
    items = [_resolved_item("Capital", "2001")]

    async def fail_if_called(_request: ClassificationRequest) -> ClassificationResult:
        raise AssertionError("classifier should not be called for a resolved item")

    result = await classify_reviews_with_llm(
        items, taxonomy=TAXONOMY, classify=fail_if_called
    )

    assert result == items


@pytest.mark.asyncio
async def test_classify_reviews_with_llm_resolves_a_review_item() -> None:
    items = [_review_item("Freight In", ancestors=("Expenses",))]

    async def classify(request: ClassificationRequest) -> ClassificationResult:
        assert request.account_name == "Freight In"
        assert request.ancestors == ("Expenses",)
        assert request.taxonomy == TAXONOMY
        return ClassificationResult(code="3001", raw_response="3001")

    result = await classify_reviews_with_llm(
        items, taxonomy=TAXONOMY, classify=classify
    )

    assert result[0].candidate.code == "3001"
    assert result[0].candidate.method == MappingMethod.LLM


@pytest.mark.asyncio
async def test_classify_reviews_with_llm_leaves_item_in_review_on_none_match() -> None:
    items = [_review_item("Some Random Fee")]

    async def classify(_request: ClassificationRequest) -> ClassificationResult:
        return ClassificationResult(code=None, raw_response=NONE_MATCH)

    result = await classify_reviews_with_llm(
        items, taxonomy=TAXONOMY, classify=classify
    )

    assert result[0].candidate.code is None
    assert result[0].candidate.method == MappingMethod.REVIEW


@pytest.mark.asyncio
async def test_classify_reviews_with_llm_skips_entirely_without_a_taxonomy() -> None:
    items = [_review_item("Whatever")]

    async def fail_if_called(_request: ClassificationRequest) -> ClassificationResult:
        raise AssertionError("classifier should not be called with an empty taxonomy")

    result = await classify_reviews_with_llm(
        items, taxonomy={}, classify=fail_if_called
    )

    assert result == items
