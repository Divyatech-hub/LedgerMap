from pathlib import Path

from fastapi.testclient import TestClient

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


def test_upload_persists_a_reviewable_run(db_client: TestClient) -> None:
    client_id = _create_client(db_client, "Acme Trading LLC")

    run = _upload_run(db_client, client_id)

    assert run["client_id"] == client_id
    assert run["period"] == "2024-01"
    assert run["total_rows"] > 0
    assert run["total_rows"] == run["resolved_rows"] + run["review_rows"]
    assert any(item["matched_code"] == "2068" for item in run["line_items"])

    fetched = db_client.get(f"/runs/{run['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["id"] == run["id"]

    client_runs = db_client.get(f"/clients/{client_id}/runs")
    assert client_runs.status_code == 200
    assert [r["id"] for r in client_runs.json()] == [run["id"]]


def test_correction_updates_line_item_and_persists_mapping(
    db_client: TestClient,
) -> None:
    client_id = _create_client(db_client, "Beta Holdings")
    run = _upload_run(db_client, client_id)

    review_item = next(
        item for item in run["line_items"] if item["status"] == "review"
    )

    correction = db_client.post(
        f"/runs/{run['id']}/line-items/{review_item['id']}/corrections",
        json={
            "resulting_code": "9999",
            "chat_message": "Should be 9999 not left for review",
            "corrected_by": "accountant@example.com",
        },
    )
    assert correction.status_code == 201, correction.text
    assert correction.json()["resulting_code"] == "9999"
    assert correction.json()["previous_code"] is None
    assert correction.json()["is_conflict"] is False

    fetched_run = db_client.get(f"/runs/{run['id']}").json()
    corrected = next(
        item for item in fetched_run["line_items"] if item["id"] == review_item["id"]
    )
    assert corrected["matched_code"] == "9999"
    assert corrected["status"] == "resolved"
    assert corrected["method"] == "corrected"

    # A second run for the same client should now resolve that same account
    # from persisted mapping memory instead of leaving it for review.
    second_run = _upload_run(db_client, client_id, period="2024-02")
    same_account = next(
        item
        for item in second_run["line_items"]
        if item["raw_name"] == review_item["raw_name"]
    )
    assert same_account["matched_code"] == "9999"
    assert same_account["method"] == "exact"


def test_recorrecting_an_approved_mapping_is_flagged_as_a_conflict(
    db_client: TestClient,
) -> None:
    client_id = _create_client(db_client, "Gamma Partners")
    run = _upload_run(db_client, client_id)
    review_item = next(
        item for item in run["line_items"] if item["status"] == "review"
    )

    first = db_client.post(
        f"/runs/{run['id']}/line-items/{review_item['id']}/corrections",
        json={"resulting_code": "9999", "corrected_by": "accountant@example.com"},
    )
    assert first.status_code == 201, first.text
    assert first.json()["is_conflict"] is False

    # A different accountant later corrects the same account to a different
    # code. This overwrites the earlier human-approved mapping, so it must be
    # flagged as a conflict in the audit trail rather than applied silently.
    second = db_client.post(
        f"/runs/{run['id']}/line-items/{review_item['id']}/corrections",
        json={"resulting_code": "8888", "corrected_by": "other-accountant@example.com"},
    )
    assert second.status_code == 201, second.text
    assert second.json()["previous_code"] == "9999"
    assert second.json()["resulting_code"] == "8888"
    assert second.json()["is_conflict"] is True


def test_run_for_unknown_client_returns_404(db_client: TestClient) -> None:
    with FIXTURE.open("rb") as fixture_file:
        response = db_client.post(
            "/runs/clients/999999",
            data={"period": "2024-01"},
            files={"file": ("TB.xlsx", fixture_file, "application/octet-stream")},
        )
    assert response.status_code == 404
