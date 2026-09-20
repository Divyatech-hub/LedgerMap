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


def test_upload_persists_taxonomy_and_mis_report_shows_descriptions(
    db_client: TestClient,
) -> None:
    client_id = _create_client(db_client, "Zeta Manufacturing")
    _upload_run(db_client, client_id)

    report = db_client.get(f"/clients/{client_id}/mis").json()

    row_3001 = next((row for row in report["rows"] if row["code"] == "3001"), None)
    assert row_3001 is not None
    assert row_3001["description"] == "Freight Charges"
