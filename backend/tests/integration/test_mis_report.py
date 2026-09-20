from pathlib import Path

from fastapi.testclient import TestClient

FIXTURE = Path(__file__).parents[3] / "prototype" / "TB.xlsx"


def _create_client(db_client: TestClient, name: str) -> int:
    response = db_client.post("/clients", json={"name": name})
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _upload_run(db_client: TestClient, client_id: int, period: str) -> dict:
    with FIXTURE.open("rb") as fixture_file:
        response = db_client.post(
            f"/runs/clients/{client_id}",
            data={"period": period},
            files={"file": ("TB.xlsx", fixture_file, "application/octet-stream")},
        )
    assert response.status_code == 201, response.text
    return response.json()


def test_mis_report_has_no_periods_before_any_run(db_client: TestClient) -> None:
    client_id = _create_client(db_client, "Empty Co")

    report = db_client.get(f"/clients/{client_id}/mis")

    assert report.status_code == 200
    body = report.json()
    assert body["periods"] == []
    assert body["rows"] == []
    assert body["unresolved_periods"] == []


def test_mis_report_aggregates_one_run_by_code(db_client: TestClient) -> None:
    client_id = _create_client(db_client, "Delta Retail")
    run = _upload_run(db_client, client_id, period="2024-01")

    report = db_client.get(f"/clients/{client_id}/mis").json()

    assert report["periods"] == ["2024-01"]
    # Every resolved code from the run should appear as a row.
    resolved_codes = {
        item["matched_code"] for item in run["line_items"] if item["matched_code"]
    }
    row_codes = {row["code"] for row in report["rows"]}
    assert resolved_codes == row_codes

    # Amounts for a code are the sum of every line item resolved to it.
    code_2068_total = sum(
        float(item["amount"])
        for item in run["line_items"]
        if item["matched_code"] == "2068"
    )
    row_2068 = next(row for row in report["rows"] if row["code"] == "2068")
    assert float(row_2068["cells"]["2024-01"]["amount"]) == code_2068_total

    # This run had review items, so its period is flagged as unresolved.
    assert run["review_rows"] > 0
    assert "2024-01" in report["unresolved_periods"]


def test_mis_report_lines_up_multiple_periods_and_reflects_corrections(
    db_client: TestClient,
) -> None:
    client_id = _create_client(db_client, "Epsilon Corp")
    first_run = _upload_run(db_client, client_id, period="2024-01")

    review_item = next(
        item for item in first_run["line_items"] if item["status"] == "review"
    )
    correction = db_client.post(
        f"/runs/{first_run['id']}/line-items/{review_item['id']}/corrections",
        json={"resulting_code": "7777"},
    )
    assert correction.status_code == 201, correction.text

    _upload_run(db_client, client_id, period="2024-02")

    report = db_client.get(f"/clients/{client_id}/mis").json()

    assert report["periods"] == ["2024-01", "2024-02"]

    corrected_row = next(row for row in report["rows"] if row["code"] == "7777")
    assert "2024-01" in corrected_row["cells"]
    assert corrected_row["cells"]["2024-01"]["method"] == "corrected"
    # The second run resolves the same account from mapping memory now, so it
    # should also appear in that column as an exact match, not a review item.
    assert "2024-02" in corrected_row["cells"]
    assert corrected_row["cells"]["2024-02"]["method"] == "exact"

    # 2024-01 still had review items at upload time.
    assert "2024-01" in report["unresolved_periods"]
