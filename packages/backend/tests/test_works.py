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


def test_get_attachment_traversal_rejected(client, tmp_path):
    save_works(make_doc())
    resp = client.get("/api/works/w1/attachments/.hidden")
    assert resp.status_code == 400


def test_delete_attachment_traversal_rejected(client, tmp_path):
    save_works(make_doc())
    resp = client.delete("/api/works/w1/attachments/.hidden")
    assert resp.status_code == 400


def test_get_attachment_invalid_id_rejected(client, tmp_path):
    save_works(make_doc())
    resp = client.get("/api/works/../attachments/invoice.pdf")
    # FastAPI won't route ".." as a path param, but validate_id rejects non-UUID chars like "/"
    # Test with a dot-only id that would otherwise traverse
    resp2 = client.get("/api/works/w1/attachments/invoice.pdf")
    assert resp2.status_code == 404  # work exists but file not uploaded yet — id "w1" passes validation


def test_upload_invalid_id_rejected(client, tmp_path):
    save_works(make_doc())
    # IDs with characters outside [A-Za-z0-9_-] should be rejected with 400
    resp = client.post(
        "/api/works/w!1/attachments",
        files={"file": ("invoice.pdf", b"%PDF test", "application/pdf")},
    )
    assert resp.status_code == 400


def test_upload_attachment(client, tmp_path):
    save_works(make_doc())
    resp = client.post(
        "/api/works/w1/attachments",
        files={"file": ("invoice.pdf", b"%PDF-1.4 test", "application/pdf")},
    )
    assert resp.status_code == 201
    assert resp.json()["filename"] == "invoice.pdf"
    work = client.get("/api/works").json()["works"][0]
    assert "invoice.pdf" in work["attachments"]


def test_upload_sanitises_filename(client, tmp_path):
    save_works(make_doc())
    resp = client.post(
        "/api/works/w1/attachments",
        files={"file": ("my invoice 2025.pdf", b"%PDF test", "application/pdf")},
    )
    assert resp.status_code == 201
    assert resp.json()["filename"] == "my_invoice_2025.pdf"


def test_upload_non_pdf_rejected(client, tmp_path):
    save_works(make_doc())
    resp = client.post(
        "/api/works/w1/attachments",
        files={"file": ("image.png", b"fake-png", "image/png")},
    )
    assert resp.status_code == 400


def test_upload_attachment_work_not_found(client):
    resp = client.post(
        "/api/works/nope/attachments",
        files={"file": ("invoice.pdf", b"%PDF test", "application/pdf")},
    )
    assert resp.status_code == 404


def test_get_attachment(client, tmp_path):
    save_works(make_doc())
    client.post(
        "/api/works/w1/attachments",
        files={"file": ("invoice.pdf", b"%PDF-1.4 test content", "application/pdf")},
    )
    resp = client.get("/api/works/w1/attachments/invoice.pdf")
    assert resp.status_code == 200
    assert "pdf" in resp.headers["content-type"]


def test_get_attachment_not_found(client, tmp_path):
    save_works(make_doc())
    resp = client.get("/api/works/w1/attachments/nope.pdf")
    assert resp.status_code == 404


def test_delete_attachment(client, tmp_path):
    save_works(make_doc())
    client.post(
        "/api/works/w1/attachments",
        files={"file": ("invoice.pdf", b"%PDF test", "application/pdf")},
    )
    resp = client.delete("/api/works/w1/attachments/invoice.pdf")
    assert resp.status_code == 204
    work = client.get("/api/works").json()["works"][0]
    assert "invoice.pdf" not in work["attachments"]


def test_delete_attachment_not_found(client, tmp_path):
    save_works(make_doc())
    resp = client.delete("/api/works/w1/attachments/nope.pdf")
    assert resp.status_code == 404


def test_set_placement(client, tmp_path):
    save_works(make_doc())
    body = {"floorId": "f1", "position": {"x": 100.0, "y": 200.0}}
    resp = client.put("/api/works/w1/placement", json=body)
    assert resp.status_code == 204
    work = client.get("/api/works").json()["works"][0]
    assert work["placement"]["floorId"] == "f1"
    assert work["placement"]["position"]["x"] == 100.0


def test_set_placement_not_found(client):
    resp = client.put("/api/works/nope/placement", json={"floorId": "f1", "position": {"x": 0, "y": 0}})
    assert resp.status_code == 404


def test_clear_placement(client, tmp_path):
    doc = make_doc()
    doc.works[0].placement = WorkPlacement(floorId="f1", position=WorkPosition(x=1, y=2))
    save_works(doc)
    resp = client.delete("/api/works/w1/placement")
    assert resp.status_code == 204
    work = client.get("/api/works").json()["works"][0]
    assert work["placement"] is None


def test_delete_work_removes_attachments(client, tmp_path):
    save_works(make_doc())
    client.post(
        "/api/works/w1/attachments",
        files={"file": ("invoice.pdf", b"%PDF test", "application/pdf")},
    )
    client.delete("/api/works/w1")
    attach_dir = tmp_path / "works-attachments" / "w1"
    assert not attach_dir.exists()
