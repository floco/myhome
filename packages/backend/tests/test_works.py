import pytest
from fastapi.testclient import TestClient
from myhome.main import app
from myhome.models_works import Work, WorkPlacement, WorkPosition, WorksDocument
from myhome.persistence_works import save_works


def make_doc() -> WorksDocument:
    return WorksDocument(
        works=[Work(id="w1", title="Boiler repair", status="done", date="2025-11-10", totalCost=1200.0)]
    )


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    return TestClient(app)


def test_get_works_empty_when_no_file(client):
    resp = client.get("/api/works")
    assert resp.status_code == 200
    assert resp.json()["works"] == []


def test_get_works_returns_saved_data(client, tmp_path):
    save_works(make_doc())
    resp = client.get("/api/works")
    assert resp.status_code == 200
    assert resp.json()["works"][0]["id"] == "w1"


def test_create_work(client):
    payload = {"title": "Roof repair", "status": "planned", "date": "2026-04-01"}
    resp = client.post("/api/works", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "Roof repair"
    assert data["status"] == "planned"
    assert data["attachments"] == []
    assert data["placement"] is None
    assert "id" in data
    assert len(client.get("/api/works").json()["works"]) == 1


def test_create_work_full_fields(client):
    payload = {
        "title": "Boiler install",
        "description": "New 24kW unit",
        "status": "done",
        "categoryId": "wcat-plumbing",
        "date": "2025-11-10",
        "totalCost": 3200.0,
        "supplierId": "sup-1",
        "notes": "## Details\n\nViessmann unit",
    }
    resp = client.post("/api/works", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["totalCost"] == 3200.0
    assert data["supplierId"] == "sup-1"
    assert data["notes"].startswith("##")


def test_update_work_partial(client, tmp_path):
    save_works(make_doc())
    resp = client.put("/api/works/w1", json={"status": "in_progress", "totalCost": 1500.0})
    assert resp.status_code == 204
    work = client.get("/api/works").json()["works"][0]
    assert work["status"] == "in_progress"
    assert work["totalCost"] == 1500.0
    assert work["title"] == "Boiler repair"  # unchanged


def test_update_work_404(client):
    resp = client.put("/api/works/nope", json={"status": "done"})
    assert resp.status_code == 404


def test_delete_work(client, tmp_path):
    save_works(make_doc())
    resp = client.delete("/api/works/w1")
    assert resp.status_code == 204
    assert client.get("/api/works").json()["works"] == []


def test_delete_work_404(client):
    resp = client.delete("/api/works/nope")
    assert resp.status_code == 404
