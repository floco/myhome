import pytest
from myhome.models_locations import Location, LocationCriterion, LocationRating, LocationsDocument
from myhome.persistence_locations import save_locations


def make_doc() -> LocationsDocument:
    return LocationsDocument(
        criteria=[LocationCriterion(id="crit1", name="Safety", description="", weight="medium")],
        locations=[Location(id="loc1", name="Nantes", emoji="🇫🇷")],
    )


# --- GET ---

def test_get_locations_empty(client, home_id):
    resp = client.get(f"/api/homes/{home_id}/locations")
    assert resp.status_code == 200
    data = resp.json()
    assert data["criteria"] == []
    assert data["locations"] == []
    assert data["ratings"] == []


# --- criteria CRUD ---

def test_create_criterion(client, home_id):
    resp = client.post(
        f"/api/homes/{home_id}/locations/criteria",
        json={"name": "Healthcare", "description": "Quality of care", "weight": "high"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Healthcare"
    assert data["weight"] == "high"
    assert "id" in data


def test_create_criterion_defaults(client, home_id):
    resp = client.post(f"/api/homes/{home_id}/locations/criteria", json={"name": "Safety"})
    assert resp.status_code == 201
    assert resp.json()["weight"] == "medium"


def test_update_criterion(client, home_id):
    save_locations(home_id, make_doc())
    resp = client.put(f"/api/homes/{home_id}/locations/criteria/crit1", json={"weight": "low"})
    assert resp.status_code == 204
    data = client.get(f"/api/homes/{home_id}/locations").json()
    assert data["criteria"][0]["weight"] == "low"


def test_update_criterion_not_found(client, home_id):
    resp = client.put(f"/api/homes/{home_id}/locations/criteria/nope", json={"name": "X"})
    assert resp.status_code == 404


def test_delete_criterion_cascades_ratings(client, home_id):
    doc = make_doc()
    doc.ratings.append(LocationRating(locationId="loc1", criterionId="crit1", score=3, note=""))
    save_locations(home_id, doc)
    resp = client.delete(f"/api/homes/{home_id}/locations/criteria/crit1")
    assert resp.status_code == 204
    data = client.get(f"/api/homes/{home_id}/locations").json()
    assert data["criteria"] == []
    assert data["ratings"] == []


def test_delete_criterion_not_found(client, home_id):
    resp = client.delete(f"/api/homes/{home_id}/locations/criteria/nope")
    assert resp.status_code == 404


def test_reorder_criteria(client, home_id):
    save_locations(home_id, LocationsDocument(criteria=[
        LocationCriterion(id="c1", name="A"), LocationCriterion(id="c2", name="B"),
    ]))
    resp = client.put(f"/api/homes/{home_id}/locations/criteria/reorder", json={"orderedIds": ["c2", "c1"]})
    assert resp.status_code == 204
    data = client.get(f"/api/homes/{home_id}/locations").json()
    assert [c["id"] for c in data["criteria"]] == ["c2", "c1"]


def test_reorder_criteria_mismatched_ids(client, home_id):
    save_locations(home_id, LocationsDocument(criteria=[LocationCriterion(id="c1", name="A")]))
    resp = client.put(f"/api/homes/{home_id}/locations/criteria/reorder", json={"orderedIds": ["c1", "nope"]})
    assert resp.status_code == 400


# --- locations CRUD ---

def test_create_location(client, home_id):
    resp = client.post(f"/api/homes/{home_id}/locations/locations", json={"name": "Zagreb", "emoji": "🇭🇷"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Zagreb"
    assert data["emoji"] == "🇭🇷"


def test_create_location_default_emoji(client, home_id):
    resp = client.post(f"/api/homes/{home_id}/locations/locations", json={"name": "Nice"})
    assert resp.status_code == 201
    assert resp.json()["emoji"] == "📍"


def test_update_location(client, home_id):
    save_locations(home_id, make_doc())
    resp = client.put(f"/api/homes/{home_id}/locations/locations/loc1", json={"name": "Nantes Metro"})
    assert resp.status_code == 204
    data = client.get(f"/api/homes/{home_id}/locations").json()
    assert data["locations"][0]["name"] == "Nantes Metro"


def test_update_location_not_found(client, home_id):
    resp = client.put(f"/api/homes/{home_id}/locations/locations/nope", json={"name": "X"})
    assert resp.status_code == 404


def test_delete_location_cascades_ratings(client, home_id):
    save_locations(home_id, make_doc())
    client.put(f"/api/homes/{home_id}/locations/ratings/loc1/crit1", json={"score": 3, "note": "ok"})
    resp = client.delete(f"/api/homes/{home_id}/locations/locations/loc1")
    assert resp.status_code == 204
    data = client.get(f"/api/homes/{home_id}/locations").json()
    assert data["locations"] == []
    assert data["ratings"] == []


def test_delete_location_not_found(client, home_id):
    resp = client.delete(f"/api/homes/{home_id}/locations/locations/nope")
    assert resp.status_code == 404


def test_reorder_locations(client, home_id):
    save_locations(home_id, LocationsDocument(locations=[Location(id="l1", name="A"), Location(id="l2", name="B")]))
    resp = client.put(f"/api/homes/{home_id}/locations/locations/reorder", json={"orderedIds": ["l2", "l1"]})
    assert resp.status_code == 204
    data = client.get(f"/api/homes/{home_id}/locations").json()
    assert [l["id"] for l in data["locations"]] == ["l2", "l1"]


# --- ratings ---

def test_upsert_rating(client, home_id):
    save_locations(home_id, make_doc())
    resp = client.put(f"/api/homes/{home_id}/locations/ratings/loc1/crit1", json={"score": 5, "note": "Great"})
    assert resp.status_code == 204
    data = client.get(f"/api/homes/{home_id}/locations").json()
    assert data["ratings"][0]["score"] == 5
    assert data["ratings"][0]["note"] == "Great"


def test_upsert_rating_replaces_existing(client, home_id):
    save_locations(home_id, make_doc())
    client.put(f"/api/homes/{home_id}/locations/ratings/loc1/crit1", json={"score": 2, "note": "meh"})
    client.put(f"/api/homes/{home_id}/locations/ratings/loc1/crit1", json={"score": 5, "note": "great"})
    data = client.get(f"/api/homes/{home_id}/locations").json()
    assert len(data["ratings"]) == 1
    assert data["ratings"][0]["score"] == 5


def test_upsert_rating_unknown_location(client, home_id):
    save_locations(home_id, LocationsDocument(criteria=[LocationCriterion(id="crit1", name="Safety")]))
    resp = client.put(f"/api/homes/{home_id}/locations/ratings/nope/crit1", json={"score": 3})
    assert resp.status_code == 404


def test_upsert_rating_unknown_criterion(client, home_id):
    save_locations(home_id, LocationsDocument(locations=[Location(id="loc1", name="X")]))
    resp = client.put(f"/api/homes/{home_id}/locations/ratings/loc1/nope", json={"score": 3})
    assert resp.status_code == 404


def test_clear_rating(client, home_id):
    save_locations(home_id, make_doc())
    client.put(f"/api/homes/{home_id}/locations/ratings/loc1/crit1", json={"score": 4, "note": "x"})
    resp = client.delete(f"/api/homes/{home_id}/locations/ratings/loc1/crit1")
    assert resp.status_code == 204
    data = client.get(f"/api/homes/{home_id}/locations").json()
    assert data["ratings"] == []


def test_clear_rating_not_found(client, home_id):
    resp = client.delete(f"/api/homes/{home_id}/locations/ratings/loc1/crit1")
    assert resp.status_code == 404
