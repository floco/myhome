import pytest
from fastapi.testclient import TestClient
from myhome.main import app
from myhome.models_settings import CostCategory, InventoryCategory, SettingsDocument
from myhome.persistence_settings import save_settings


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    return TestClient(app)


def test_get_settings_returns_defaults_when_no_file(client):
    resp = client.get("/api/settings")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["costCategories"]) == 5
    assert data["costCategories"][0]["name"] == "Fuel / Mazout"
    assert len(data["inventoryCategories"]) == 6


def test_get_settings_returns_saved_data(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    save_settings(SettingsDocument(
        costCategories=[CostCategory(id="c1", name="Gas", emoji="🔥", unit="m³", color="#ff8800")],
        inventoryCategories=[],
    ))
    resp = TestClient(app).get("/api/settings")
    assert resp.status_code == 200
    assert resp.json()["costCategories"][0]["name"] == "Gas"


def test_put_cost_categories(client):
    new_cats = [
        {"id": "c1", "name": "Gas", "emoji": "🔥", "unit": "m³", "color": "#ff8800"},
        {"id": "c2", "name": "Tax", "emoji": "🏠", "unit": None, "color": "#9966cc"},
    ]
    resp = client.put("/api/settings/cost-categories", json=new_cats)
    assert resp.status_code == 204
    data = client.get("/api/settings").json()
    assert len(data["costCategories"]) == 2
    assert data["costCategories"][0]["name"] == "Gas"
    assert data["costCategories"][1]["unit"] is None


def test_put_cost_categories_replaces_all(client):
    client.put("/api/settings/cost-categories", json=[
        {"id": "c1", "name": "A", "emoji": "A", "unit": None, "color": "#000"},
        {"id": "c2", "name": "B", "emoji": "B", "unit": None, "color": "#000"},
    ])
    client.put("/api/settings/cost-categories", json=[
        {"id": "c3", "name": "C", "emoji": "C", "unit": None, "color": "#000"},
    ])
    data = client.get("/api/settings").json()
    assert len(data["costCategories"]) == 1
    assert data["costCategories"][0]["name"] == "C"


def test_put_inventory_categories(client):
    new_cats = [
        {"id": "i1", "name": "Books"},
        {"id": "i2", "name": "Clothing"},
    ]
    resp = client.put("/api/settings/inventory-categories", json=new_cats)
    assert resp.status_code == 204
    data = client.get("/api/settings").json()
    assert len(data["inventoryCategories"]) == 2
    assert data["inventoryCategories"][1]["name"] == "Clothing"


def test_put_cost_category_placement(client):
    resp = client.put("/api/settings/cost-categories/cat-fuel/placement", json={
        "floorId": "floor-1",
        "position": {"x": 100.5, "y": 200.0},
    })
    assert resp.status_code == 204
    settings = client.get("/api/settings").json()
    fuel = next(cat for cat in settings["costCategories"] if cat["id"] == "cat-fuel")
    assert fuel["placement"]["floorId"] == "floor-1"
    assert fuel["placement"]["position"]["x"] == 100.5


def test_delete_cost_category_placement(client):
    # First place it
    client.put("/api/settings/cost-categories/cat-fuel/placement", json={
        "floorId": "floor-1",
        "position": {"x": 100.0, "y": 200.0},
    })
    # Then remove it
    resp = client.delete("/api/settings/cost-categories/cat-fuel/placement")
    assert resp.status_code == 204
    settings = client.get("/api/settings").json()
    fuel = next(cat for cat in settings["costCategories"] if cat["id"] == "cat-fuel")
    assert fuel["placement"] is None


def test_put_cost_category_placement_404(client):
    resp = client.put("/api/settings/cost-categories/nonexistent/placement", json={
        "floorId": "f1", "position": {"x": 0, "y": 0}
    })
    assert resp.status_code == 404


def test_get_settings_returns_default_work_categories(client):
    resp = client.get("/api/settings")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["workCategories"]) == 5
    assert data["workCategories"][0]["name"] == "Plumbing"
    assert data["suppliers"] == []


def test_put_work_categories(client):
    new_cats = [{"id": "w1", "name": "Masonry", "emoji": "🧱"}]
    resp = client.put("/api/settings/work-categories", json=new_cats)
    assert resp.status_code == 204
    data = client.get("/api/settings").json()
    assert len(data["workCategories"]) == 1
    assert data["workCategories"][0]["name"] == "Masonry"


def test_put_suppliers(client):
    resp = client.put("/api/settings/suppliers", json=[{"id": "s1", "name": "Acme Plumbers"}])
    assert resp.status_code == 204
    data = client.get("/api/settings").json()
    assert data["suppliers"][0]["name"] == "Acme Plumbers"


def test_put_suppliers_replaces_all(client):
    client.put("/api/settings/suppliers", json=[{"id": "s1", "name": "A"}, {"id": "s2", "name": "B"}])
    client.put("/api/settings/suppliers", json=[{"id": "s3", "name": "C"}])
    data = client.get("/api/settings").json()
    assert len(data["suppliers"]) == 1
    assert data["suppliers"][0]["name"] == "C"
