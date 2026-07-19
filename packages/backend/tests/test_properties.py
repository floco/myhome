import pytest
from myhome.models_properties import Property, PropertiesDocument
from myhome.persistence_properties import save_properties


def make_doc() -> PropertiesDocument:
    return PropertiesDocument(
        properties=[Property(id="p1", name="Casa da Rua das Flores", type="house", status="watching")]
    )


def test_get_properties_empty_when_none(client, home_id):
    resp = client.get(f"/api/homes/{home_id}/properties")
    assert resp.status_code == 200
    assert resp.json()["properties"] == []


def test_get_properties_returns_saved_data(client, home_id):
    save_properties(home_id, make_doc())
    resp = client.get(f"/api/homes/{home_id}/properties")
    assert resp.status_code == 200
    assert resp.json()["properties"][0]["id"] == "p1"


def test_create_property(client, home_id):
    payload = {"name": "Terreno Norte", "type": "land"}
    resp = client.post(f"/api/homes/{home_id}/properties", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Terreno Norte"
    assert data["type"] == "land"
    assert data["status"] == "watching"
    assert data["emoji"] == "🏠"
    assert data["pros"] == []
    assert data["cons"] == []
    assert data["attachments"] == []
    assert "id" in data
    assert len(client.get(f"/api/homes/{home_id}/properties").json()["properties"]) == 1


def test_create_property_full_fields(client, home_id):
    payload = {
        "name": "Casa Sul",
        "emoji": "🏡",
        "type": "house",
        "status": "visited",
        "locationId": "loc1",
        "address": "Rua Sul 5",
        "price": 250000.0,
        "landSize": 500.0,
        "builtSize": 180.0,
        "bedrooms": 3,
        "bathrooms": 2,
        "listingUrl": "https://example.com/listing",
        "contact": "Maria, +351 912 345 678",
        "pros": ["Great light", "Walk to town"],
        "cons": ["No garage"],
        "notes": "Needs a new roof",
    }
    resp = client.post(f"/api/homes/{home_id}/properties", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["price"] == 250000.0
    assert data["locationId"] == "loc1"
    assert data["pros"] == ["Great light", "Walk to town"]
    assert data["cons"] == ["No garage"]
    assert data["bedrooms"] == 3


def test_update_property_partial(client, home_id):
    save_properties(home_id, make_doc())
    resp = client.put(f"/api/homes/{home_id}/properties/p1", json={"status": "visited", "price": 250000.0})
    assert resp.status_code == 204
    item = client.get(f"/api/homes/{home_id}/properties").json()["properties"][0]
    assert item["status"] == "visited"
    assert item["price"] == 250000.0
    assert item["name"] == "Casa da Rua das Flores"  # unchanged


def test_update_property_404(client, home_id):
    resp = client.put(f"/api/homes/{home_id}/properties/nope", json={"status": "visited"})
    assert resp.status_code == 404


def test_delete_property(client, home_id):
    save_properties(home_id, make_doc())
    resp = client.delete(f"/api/homes/{home_id}/properties/p1")
    assert resp.status_code == 204
    assert client.get(f"/api/homes/{home_id}/properties").json()["properties"] == []


def test_delete_property_404(client, home_id):
    resp = client.delete(f"/api/homes/{home_id}/properties/nope")
    assert resp.status_code == 404
