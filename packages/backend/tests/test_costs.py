import pytest
from fastapi.testclient import TestClient
from myhome.main import app
from myhome.models_costs import CostEntry, CostsDocument
from myhome.persistence_costs import save_costs


def make_doc() -> CostsDocument:
    return CostsDocument(
        entries=[
            CostEntry(
                id="e1",
                categoryId="cat-fuel",
                date="2025-10-14",
                totalAmount=1650.0,
                quantity=1500.0,
                unitPrice=1.10,
                supplier="Butagaz",
            )
        ]
    )


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    return TestClient(app)


def test_get_costs_empty_when_no_file(client):
    resp = client.get("/api/costs")
    assert resp.status_code == 200
    assert resp.json()["entries"] == []


def test_get_costs_returns_saved_data(client, tmp_path):
    save_costs(make_doc())
    resp = client.get("/api/costs")
    assert resp.status_code == 200
    assert resp.json()["entries"][0]["id"] == "e1"


def test_create_entry(client):
    payload = {
        "categoryId": "cat-fuel",
        "date": "2025-10-14",
        "totalAmount": 1650.0,
        "quantity": 1500.0,
        "unitPrice": 1.10,
        "supplier": "Butagaz",
    }
    resp = client.post("/api/costs/entries", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["categoryId"] == "cat-fuel"
    assert data["totalAmount"] == 1650.0
    assert data["quantity"] == 1500.0
    assert "id" in data
    get = client.get("/api/costs")
    assert any(e["supplier"] == "Butagaz" for e in get.json()["entries"])


def test_create_lump_sum_entry(client):
    resp = client.post("/api/costs/entries", json={
        "categoryId": "cat-tax",
        "date": "2025-03-01",
        "totalAmount": 1648.0,
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["quantity"] is None
    assert data["unitPrice"] is None


def test_update_entry_partial(client, tmp_path):
    save_costs(make_doc())
    resp = client.put("/api/costs/entries/e1", json={"totalAmount": 1800.0, "supplier": "TotalEnergies"})
    assert resp.status_code == 204
    entry = client.get("/api/costs").json()["entries"][0]
    assert entry["totalAmount"] == 1800.0
    assert entry["supplier"] == "TotalEnergies"
    assert entry["quantity"] == 1500.0    # unchanged
    assert entry["unitPrice"] == 1.10     # unchanged


def test_update_entry_404(client):
    resp = client.put("/api/costs/entries/nonexistent", json={"totalAmount": 100.0})
    assert resp.status_code == 404


def test_delete_entry(client, tmp_path):
    save_costs(make_doc())
    resp = client.delete("/api/costs/entries/e1")
    assert resp.status_code == 204
    assert client.get("/api/costs").json()["entries"] == []


def test_delete_entry_404(client):
    resp = client.delete("/api/costs/entries/nonexistent")
    assert resp.status_code == 404
