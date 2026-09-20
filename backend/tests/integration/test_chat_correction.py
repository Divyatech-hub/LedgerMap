from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from ledgermap.integrations.llm.chat_correction import ChatCorrectionResult
from ledgermap.integrations.llm.classifier import ClassificationResult

FIXTURE = Path(__file__).parents[3] / "prototype" / "TB.xlsx"


def _create_client(db_client: TestClient, name: str) -> int:
    response = db_client.post("/clients", json={"name": name})
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _upload_run(db_client: TestClient, client_id: int, period: str = "2024-01") -> dict:
    with FIXTURE.open("rb") as fixture_file:
        response = db_client.post(
            f"/runs/clients/{client_id}",
            data={"period": period},
            files={"file": ("TB.xlsx", fixture_file, "application/octet-stream")},
        )
    assert response.status_code == 201, response.text
    return response.json()


@pytest.fixture
def llm_enabled(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Turn on llm_classification_enabled for one test and stub the
    upload-time review classifier so no real API call happens during
    _upload_run — only the /chat endpoint's own interpreter is under test.
    """
    from ledgermap.config import get_settings
    from ledgermap.integrations.llm import anthropic_classifier

    async def no_op_classify(request):  # noqa: ANN001, ARG001
        return ClassificationResult(code=None, raw_response="NONE_MATCH")

    monkeypatch.setattr(anthropic_classifier, "classify_with_anthropic", no_op_classify)
    monkeypatch.setenv("LLM_CLASSIFICATION_ENABLED", "true")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_chat_correction_returns_503_when_llm_disabled(db_client: TestClient) -> None:
    client_id = _create_client(db_client, "Chat Disabled Co")
    run = _upload_run(db_client, client_id)

    response = db_client.post(f"/runs/{run['id']}/chat", json={"message": "anything"})

    assert response.status_code == 503


def test_chat_correction_applies_a_confident_match(
    db_client: TestClient, llm_enabled: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    from ledgermap.integrations.llm import anthropic_chat_correction

    client_id = _create_client(db_client, "Chat Confident Co")
    run = _upload_run(db_client, client_id)
    target_item = run["line_items"][0]

    async def fake_interpret(request):  # noqa: ANN001, ARG001
        return ChatCorrectionResult(
            line_item_id=target_item["id"],
            resulting_code="9001",
            candidate_ids=(),
            explanation="This is clearly the Freight Charges account.",
        )

    monkeypatch.setattr(
        anthropic_chat_correction,
        "interpret_chat_correction_with_anthropic",
        fake_interpret,
    )

    response = db_client.post(
        f"/runs/{run['id']}/chat",
        json={
            "message": f"{target_item['raw_name']} should be 9001",
            "corrected_by": "acc@example.com",
        },
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["applied"] is True
    assert body["correction"]["resulting_code"] == "9001"
    assert body["correction"]["line_item_id"] == target_item["id"]

    fetched_run = db_client.get(f"/runs/{run['id']}").json()
    corrected = next(
        item for item in fetched_run["line_items"] if item["id"] == target_item["id"]
    )
    assert corrected["matched_code"] == "9001"
    assert corrected["method"] == "corrected"


def test_chat_correction_returns_candidates_when_ambiguous(
    db_client: TestClient, llm_enabled: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    from ledgermap.integrations.llm import anthropic_chat_correction

    client_id = _create_client(db_client, "Chat Ambiguous Co")
    run = _upload_run(db_client, client_id)
    candidate_ids = tuple(item["id"] for item in run["line_items"][:2])

    async def fake_interpret(request):  # noqa: ANN001, ARG001
        return ChatCorrectionResult(
            line_item_id=None,
            resulting_code=None,
            candidate_ids=candidate_ids,
            explanation="Two accounts could match 'credit card'.",
        )

    monkeypatch.setattr(
        anthropic_chat_correction,
        "interpret_chat_correction_with_anthropic",
        fake_interpret,
    )

    response = db_client.post(
        f"/runs/{run['id']}/chat", json={"message": "credit card should be 2069"}
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["applied"] is False
    assert {c["id"] for c in body["candidates"]} == set(candidate_ids)
