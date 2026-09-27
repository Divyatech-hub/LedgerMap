from collections.abc import Iterator
from types import SimpleNamespace

import pytest

from ledgermap.config import get_settings
from ledgermap.integrations.llm import gemini_chat_correction, gemini_classifier
from ledgermap.integrations.llm.chat_correction import (
    ChatCorrectionRequest,
    ChatLineItemSummary,
)
from ledgermap.integrations.llm.classifier import ClassificationRequest

TAXONOMY = {"2001": "Capital Account", "3001": "Freight Charges"}


class _FakeModels:
    def __init__(self, response: SimpleNamespace) -> None:
        self.response = response
        self.calls: list[dict] = []

    async def generate_content(self, **kwargs: object) -> SimpleNamespace:
        self.calls.append(kwargs)
        return self.response


def _fake_client(response: SimpleNamespace) -> SimpleNamespace:
    return SimpleNamespace(aio=SimpleNamespace(models=_FakeModels(response)))


@pytest.fixture(autouse=True)
def _fresh_settings() -> Iterator[None]:
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_classifier_accepts_a_code_from_the_taxonomy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = _fake_client(SimpleNamespace(text=" 3001\n"))
    monkeypatch.setattr(gemini_classifier, "get_gemini_client", lambda: client)

    result = await gemini_classifier.classify_with_gemini(
        ClassificationRequest(
            account_name="Freight Inward", ancestors=("Expenses",), taxonomy=TAXONOMY
        )
    )

    assert result.code == "3001"
    assert client.aio.models.calls[0]["model"] == "gemini-3.5-flash-lite"


@pytest.mark.asyncio
async def test_classifier_rejects_an_invented_code(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = _fake_client(SimpleNamespace(text="9999"))
    monkeypatch.setattr(gemini_classifier, "get_gemini_client", lambda: client)

    result = await gemini_classifier.classify_with_gemini(
        ClassificationRequest(account_name="Mystery", ancestors=(), taxonomy=TAXONOMY)
    )

    assert result.code is None
    assert result.raw_response == "9999"


def _chat_request() -> ChatCorrectionRequest:
    return ChatCorrectionRequest(
        message="Freight should be 3001",
        line_items=(
            ChatLineItemSummary(
                id=7, raw_name="Freight Inward", ancestors=(), matched_code="2001"
            ),
        ),
        taxonomy=TAXONOMY,
    )


@pytest.mark.asyncio
async def test_chat_interpreter_applies_a_valid_function_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    call = SimpleNamespace(
        name="report_correction",
        args={
            "confident_line_item_id": 7,
            "resulting_code": "3001",
            "candidate_line_item_ids": [],
            "explanation": "Freight Inward is freight.",
        },
    )
    client = _fake_client(SimpleNamespace(function_calls=[call]))
    monkeypatch.setattr(gemini_chat_correction, "get_gemini_client", lambda: client)

    result = await gemini_chat_correction.interpret_chat_correction_with_gemini(
        _chat_request()
    )

    assert result.line_item_id == 7
    assert result.resulting_code == "3001"


@pytest.mark.asyncio
async def test_chat_interpreter_handles_no_function_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = _fake_client(SimpleNamespace(function_calls=None))
    monkeypatch.setattr(gemini_chat_correction, "get_gemini_client", lambda: client)

    result = await gemini_chat_correction.interpret_chat_correction_with_gemini(
        _chat_request()
    )

    assert result.line_item_id is None
    assert result.candidate_ids == ()

