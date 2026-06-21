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
                supplierId="sup-butagaz",
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
        "supplierId": "sup-butagaz",
    }
    resp = client.post("/api/costs/entries", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["categoryId"] == "cat-fuel"
    assert data["totalAmount"] == 1650.0
    assert data["supplierId"] == "sup-butagaz"
    assert "id" in data


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
    assert data["supplierId"] is None


def test_update_entry_partial(client, tmp_path):
    save_costs(make_doc())
    resp = client.put("/api/costs/entries/e1", json={"totalAmount": 1800.0, "supplierId": "sup-total"})
    assert resp.status_code == 204
    entry = client.get("/api/costs").json()["entries"][0]
    assert entry["totalAmount"] == 1800.0
    assert entry["supplierId"] == "sup-total"
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


def test_old_supplier_field_loads_with_supplierId_none(client, tmp_path):
    import json
    # Simulate a costs.json file written before the migration
    old_data = {
        "version": 1,
        "entries": [{"id": "e1", "categoryId": "cat-fuel", "date": "2025-01-01", "totalAmount": 100.0, "supplier": "OldSupplier"}]
    }
    (tmp_path / "costs.json").write_text(json.dumps(old_data))
    resp = client.get("/api/costs")
    assert resp.status_code == 200
    entry = resp.json()["entries"][0]
    assert entry["supplierId"] is None  # old field dropped, new field defaults to None
