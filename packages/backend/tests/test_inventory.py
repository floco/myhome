import pytest
from fastapi.testclient import TestClient
from myhome.main import app
from myhome.models_inventory import InventoryDocument, InventoryItem, InventoryPlacement, InventoryPosition
from myhome.persistence_inventory import save_inventory


def make_doc() -> InventoryDocument:
    return InventoryDocument(
        items=[
            InventoryItem(
                id="i1",
                name="Samsung TV",
                emoji="📺",
                category="Electronics",
                purchasePrice=1200.0,
                warrantyExpiryDate="2026-05-12",
            )
        ]
    )


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    return TestClient(app)


# --- GET /api/inventory ---

def test_get_inventory_empty_when_no_file(client):
    resp = client.get("/api/inventory")
    assert resp.status_code == 200
    assert resp.json()["items"] == []


def test_get_inventory_returns_saved_data(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    save_inventory(make_doc())
    resp = TestClient(app).get("/api/inventory")
    assert resp.status_code == 200
    assert resp.json()["items"][0]["id"] == "i1"


# --- POST /api/inventory/items ---

def test_create_item(client):
    payload = {
        "name": "Washing machine",
        "emoji": "🧺",
        "category": "Appliance",
        "purchasePrice": 650.0,
    }
    resp = client.post("/api/inventory/items", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Washing machine"
    assert data["emoji"] == "🧺"
    assert data["purchasePrice"] == 650.0
    assert "id" in data
    assert data["placement"] is None
    # Verify persisted
    get = client.get("/api/inventory")
    assert any(i["name"] == "Washing machine" for i in get.json()["items"])


def test_create_item_defaults(client):
    resp = client.post("/api/inventory/items", json={"name": "Generic item"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["emoji"] == "📦"
    assert data["category"] == ""
    assert data["placement"] is None


# --- PUT /api/inventory/items/{id} ---

def test_update_item_partial(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    save_inventory(make_doc())
    c = TestClient(app)
    resp = c.put("/api/inventory/items/i1", json={"name": "LG TV", "purchasePrice": 900.0})
    assert resp.status_code == 204
    item = c.get("/api/inventory").json()["items"][0]
    assert item["name"] == "LG TV"
    assert item["purchasePrice"] == 900.0
    assert item["emoji"] == "📺"          # unchanged
    assert item["category"] == "Electronics"  # unchanged


def test_update_item_404(client):
    resp = client.put("/api/inventory/items/nonexistent", json={"name": "X"})
    assert resp.status_code == 404


# --- DELETE /api/inventory/items/{id} ---

def test_delete_item(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    save_inventory(make_doc())
    c = TestClient(app)
    resp = c.delete("/api/inventory/items/i1")
    assert resp.status_code == 204
    assert c.get("/api/inventory").json()["items"] == []


def test_delete_item_404(client):
    resp = client.delete("/api/inventory/items/nonexistent")
    assert resp.status_code == 404


# --- PUT /api/inventory/items/{id}/placement ---

def test_set_placement(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    save_inventory(make_doc())
    c = TestClient(app)
    payload = {
        "placement": {
            "floorId": "f1",
            "roomId": "r1",
            "position": {"x": 3.4, "y": 2.1},
        }
    }
    resp = c.put("/api/inventory/items/i1/placement", json=payload)
    assert resp.status_code == 204
    item = c.get("/api/inventory").json()["items"][0]
    assert item["placement"]["floorId"] == "f1"
    assert item["placement"]["position"]["x"] == 3.4
    assert item["placement"]["roomId"] == "r1"


def test_clear_placement(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    doc = make_doc()
    doc.items[0].placement = InventoryPlacement(
        floorId="f1", roomId="r1", position=InventoryPosition(x=1.0, y=2.0)
    )
    save_inventory(doc)
    c = TestClient(app)
    resp = c.put("/api/inventory/items/i1/placement", json={"placement": None})
    assert resp.status_code == 204
    assert c.get("/api/inventory").json()["items"][0]["placement"] is None


def test_placement_404(client):
    resp = client.put(
        "/api/inventory/items/nonexistent/placement",
        json={"placement": None},
    )
    assert resp.status_code == 404
