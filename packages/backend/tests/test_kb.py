import pytest
from fastapi.testclient import TestClient
from myhome.main import app
from myhome.models_kb import KBDocument, KBEntry
from myhome.persistence_kb import save_kb


def make_doc() -> KBDocument:
    return KBDocument(
        entries=[KBEntry(id="e1", title="How to paint", content="# Painting", createdAt="2026-06-28T10:00:00Z", updatedAt="2026-06-28T10:00:00Z")]
    )


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    return TestClient(app)


def test_get_kb_empty_when_no_file(client):
    resp = client.get("/api/kb")
    assert resp.status_code == 200
    assert resp.json()["entries"] == []


def test_get_kb_returns_saved_data(client, tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    save_kb(make_doc())
    resp = client.get("/api/kb")
    assert resp.status_code == 200
    assert resp.json()["entries"][0]["id"] == "e1"


def test_create_entry(client):
    payload = {"title": "How to paint", "content": "# Painting"}
    resp = client.post("/api/kb", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "How to paint"
    assert data["content"] == "# Painting"
    assert "id" in data
    assert "createdAt" in data
    assert "updatedAt" in data


def test_update_entry(client):
    # Create first
    resp = client.post("/api/kb", json={"title": "Old title", "content": ""})
    entry_id = resp.json()["id"]
    # Update
    resp = client.put(f"/api/kb/{entry_id}", json={"title": "New title"})
    assert resp.status_code == 204
    # Verify
    entries = client.get("/api/kb").json()["entries"]
    assert entries[0]["title"] == "New title"


def test_update_entry_not_found(client):
    resp = client.put("/api/kb/nonexistent", json={"title": "x"})
    assert resp.status_code == 404


def test_delete_entry(client):
    resp = client.post("/api/kb", json={"title": "To delete", "content": ""})
    entry_id = resp.json()["id"]
    resp = client.delete(f"/api/kb/{entry_id}")
    assert resp.status_code == 204
    assert client.get("/api/kb").json()["entries"] == []


def test_delete_entry_not_found(client):
    resp = client.delete("/api/kb/nonexistent")
    assert resp.status_code == 404
