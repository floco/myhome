import pytest
from myhome.models_consumables import Consumable, ConsumableDocument, ConsumableTransaction
from myhome.persistence_consumables import save_consumables


def make_doc() -> ConsumableDocument:
    return ConsumableDocument(
        consumables=[
            Consumable(
                id="c1",
                name="AA Batteries",
                emoji="🔋",
                unit="count",
                quantity=6.0,
                minQuantity=4.0,
            )
        ],
        transactions=[
            ConsumableTransaction(
                id="t1",
                consumableId="c1",
                delta=6.0,
                quantityAfter=6.0,
                timestamp="2026-07-02T10:00:00Z",
            )
        ],
    )


# --- GET /api/homes/{home_id}/consumables ---

def test_get_consumables_empty(client, home_id):
    resp = client.get(f"/api/homes/{home_id}/consumables")
    assert resp.status_code == 200
    data = resp.json()
    assert data["consumables"] == []
    assert data["transactions"] == []


def test_get_consumables_returns_saved(client, tmp_path, home_id):
    save_consumables(home_id, make_doc())
    resp = client.get(f"/api/homes/{home_id}/consumables")
    assert resp.status_code == 200
    assert resp.json()["consumables"][0]["id"] == "c1"


# --- POST /api/homes/{home_id}/consumables ---

def test_create_consumable(client, home_id):
    payload = {"name": "Dish soap", "emoji": "🧴", "unit": "mL", "quantity": 500.0, "minQuantity": 100.0}
    resp = client.post(f"/api/homes/{home_id}/consumables", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Dish soap"
    assert data["unit"] == "mL"
    assert data["quantity"] == 500.0
    assert "id" in data
    assert data["placement"] is None


def test_create_consumable_defaults(client, home_id):
    resp = client.post(f"/api/homes/{home_id}/consumables", json={"name": "Batteries"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["emoji"] == "🛒"
    assert data["unit"] == "count"
    assert data["quantity"] == 0.0


# --- PUT /api/homes/{home_id}/consumables/{id} ---

def test_update_consumable(client, tmp_path, home_id):
    save_consumables(home_id, make_doc())
    resp = client.put(f"/api/homes/{home_id}/consumables/c1", json={"name": "AAA Batteries", "minQuantity": 6.0})
    assert resp.status_code == 204
    data = client.get(f"/api/homes/{home_id}/consumables").json()
    assert data["consumables"][0]["name"] == "AAA Batteries"
    assert data["consumables"][0]["minQuantity"] == 6.0


def test_update_consumable_not_found(client, home_id):
    resp = client.put(f"/api/homes/{home_id}/consumables/nope", json={"name": "X"})
    assert resp.status_code == 404


# --- DELETE /api/homes/{home_id}/consumables/{id} ---

def test_delete_consumable(client, tmp_path, home_id):
    save_consumables(home_id, make_doc())
    resp = client.delete(f"/api/homes/{home_id}/consumables/c1")
    assert resp.status_code == 204
    data = client.get(f"/api/homes/{home_id}/consumables").json()
    assert data["consumables"] == []
    assert data["transactions"] == []


def test_delete_consumable_not_found(client, home_id):
    resp = client.delete(f"/api/homes/{home_id}/consumables/nope")
    assert resp.status_code == 404


# --- PUT /api/homes/{home_id}/consumables/{id}/placement ---

def test_set_placement(client, tmp_path, home_id):
    save_consumables(home_id, make_doc())
    payload = {"placement": {"floorId": "f1", "roomId": "r1", "position": {"x": 3.0, "y": 4.0}}}
    resp = client.put(f"/api/homes/{home_id}/consumables/c1/placement", json=payload)
    assert resp.status_code == 204
    data = client.get(f"/api/homes/{home_id}/consumables").json()
    assert data["consumables"][0]["placement"]["floorId"] == "f1"


def test_clear_placement(client, tmp_path, home_id):
    save_consumables(home_id, make_doc())
    client.put(
        f"/api/homes/{home_id}/consumables/c1/placement",
        json={"placement": {"floorId": "f1", "position": {"x": 1.0, "y": 2.0}}},
    )
    resp = client.put(f"/api/homes/{home_id}/consumables/c1/placement", json={"placement": None})
    assert resp.status_code == 204
    data = client.get(f"/api/homes/{home_id}/consumables").json()
    assert data["consumables"][0]["placement"] is None


# --- POST /api/homes/{home_id}/consumables/{id}/stock ---

def test_update_stock_adds_transaction(client, tmp_path, home_id):
    save_consumables(home_id, make_doc())
    resp = client.post(f"/api/homes/{home_id}/consumables/c1/stock", json={"quantity": 10.0, "note": "restocked"})
    assert resp.status_code == 204
    data = client.get(f"/api/homes/{home_id}/consumables").json()
    assert data["consumables"][0]["quantity"] == 10.0
    assert len(data["transactions"]) == 2
    new_tx = next(t for t in data["transactions"] if t["id"] != "t1")
    assert new_tx["delta"] == 4.0
    assert new_tx["quantityAfter"] == 10.0
    assert new_tx["note"] == "restocked"


def test_update_stock_negative_delta(client, tmp_path, home_id):
    save_consumables(home_id, make_doc())
    client.post(f"/api/homes/{home_id}/consumables/c1/stock", json={"quantity": 2.0})
    data = client.get(f"/api/homes/{home_id}/consumables").json()
    new_tx = next(t for t in data["transactions"] if t["id"] != "t1")
    assert new_tx["delta"] == -4.0


def test_update_stock_not_found(client, home_id):
    resp = client.post(f"/api/homes/{home_id}/consumables/nope/stock", json={"quantity": 5.0})
    assert resp.status_code == 404


# --- DELETE /api/homes/{home_id}/consumable-transactions/{id} ---

def test_delete_transaction(client, tmp_path, home_id):
    save_consumables(home_id, make_doc())
    resp = client.delete(f"/api/homes/{home_id}/consumable-transactions/t1")
    assert resp.status_code == 204
    data = client.get(f"/api/homes/{home_id}/consumables").json()
    assert data["transactions"] == []


def test_delete_transaction_not_found(client, home_id):
    resp = client.delete(f"/api/homes/{home_id}/consumable-transactions/nope")
    assert resp.status_code == 404
