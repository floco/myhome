import re
import pytest
from fastapi.testclient import TestClient

from myhome import persistence_property_search as ps
from myhome.main import app
from myhome.models_property_search import PropertySuggestion

SEARCH = {"name": "Plots Novo Mesto", "prompt": "land >= 800 m2 near Novo Mesto under 200k EUR"}


@pytest.fixture()
def normal_client(client):
    tc = TestClient(app)
    assert tc.post("/api/auth/login", json={"username": "normaluser", "password": "normal123"}).status_code == 200
    return tc


def _create(client, home_id, **kw):
    resp = client.post(f"/api/homes/{home_id}/property-searches", json={**SEARCH, **kw})
    assert resp.status_code == 201, resp.text
    return resp.json()


def _suggestion(home_id, search_id, id="g1", url="https://a.si/1"):
    ps.insert_suggestions(home_id, [PropertySuggestion(
        id=id, searchId=search_id, runId="r1", title="Nice plot", listingUrl=url, type="land",
        price=150000, currency="EUR", landSize=820, location="Novo Mesto", sourceSite="nepremicnine.net",
        reason="Matches size and budget", createdAt="2026-11-08T08:00:00+00:00",
    )])


def test_create_and_list_search(client, home_id):
    created = _create(client, home_id)
    assert created["maxResultsPerRun"] == 10 and created["maxListingAgeDays"] == 7 and created["createdAt"]
    listed = client.get(f"/api/homes/{home_id}/property-searches").json()
    assert [s["id"] for s in listed] == [created["id"]]


def test_create_search_validates_time(client, home_id):
    resp = client.post(f"/api/homes/{home_id}/property-searches", json={**SEARCH, "time": "8h"})
    assert resp.status_code == 422


def test_create_search_validates_limits(client, home_id):
    assert client.post(f"/api/homes/{home_id}/property-searches", json={**SEARCH, "maxResultsPerRun": 0}).status_code == 422
    assert client.post(f"/api/homes/{home_id}/property-searches", json={**SEARCH, "name": ""}).status_code == 422


def test_update_and_delete_search(client, home_id):
    s = _create(client, home_id)
    assert client.put(f"/api/homes/{home_id}/property-searches/{s['id']}", json={"frequency": "weekly"}).status_code == 204
    assert client.get(f"/api/homes/{home_id}/property-searches").json()[0]["frequency"] == "weekly"
    assert client.delete(f"/api/homes/{home_id}/property-searches/{s['id']}").status_code == 204
    assert client.delete(f"/api/homes/{home_id}/property-searches/{s['id']}").status_code == 404


def test_run_now_sets_flag(client, home_id):
    s = _create(client, home_id)
    assert client.post(f"/api/homes/{home_id}/property-searches/{s['id']}/run-now").status_code == 204
    assert client.get(f"/api/homes/{home_id}/property-searches").json()[0]["runRequestedAt"]


def test_list_runs_empty(client, home_id):
    s = _create(client, home_id)
    assert client.get(f"/api/homes/{home_id}/property-searches/{s['id']}/runs").json() == []


def test_accept_creates_property_and_hides_suggestion(client, home_id):
    s = _create(client, home_id)
    _suggestion(home_id, s["id"])
    resp = client.post(f"/api/homes/{home_id}/property-suggestions/g1/accept")
    assert resp.status_code == 201
    props = client.get(f"/api/homes/{home_id}/properties").json()["properties"]
    assert len(props) == 1
    p = props[0]
    assert p["status"] == "watching" and p["listingUrl"] == "https://a.si/1" and p["type"] == "land"
    assert p["landSize"] == 820 and p["address"] == "Novo Mesto"
    assert "Matches size and budget" in p["notes"] and re.search(r"\bnepremicnine\.net\b", p["notes"]) and "EUR" in p["notes"]
    assert client.get(f"/api/homes/{home_id}/property-suggestions").json() == []
    assert client.post(f"/api/homes/{home_id}/property-suggestions/g1/accept").status_code == 409


def test_reject_and_pin(client, home_id):
    s = _create(client, home_id)
    _suggestion(home_id, s["id"], "g1", "https://a.si/1")
    _suggestion(home_id, s["id"], "g2", "https://a.si/2")
    assert client.post(f"/api/homes/{home_id}/property-suggestions/g1/pin").status_code == 204
    assert client.post(f"/api/homes/{home_id}/property-suggestions/g2/reject").status_code == 204
    listed = client.get(f"/api/homes/{home_id}/property-suggestions").json()
    assert [(x["id"], x["status"]) for x in listed] == [("g1", "pinned")]
    client.post(f"/api/homes/{home_id}/property-suggestions/g1/pin")
    assert client.get(f"/api/homes/{home_id}/property-suggestions").json()[0]["status"] == "new"
    assert client.post(f"/api/homes/{home_id}/property-suggestions/nope/reject").status_code == 404


def test_config_get_masks_key(client, home_id):
    resp = client.put(f"/api/homes/{home_id}/property-search-config", json={"brevoApiKey": "xkeysib-1"})
    assert resp.status_code == 200
    body = client.get(f"/api/homes/{home_id}/property-search-config").json()
    assert body["brevoApiKeySet"] is True and "brevoApiKey" not in body


def test_config_put_empty_key_keeps_existing(client, home_id):
    client.put(f"/api/homes/{home_id}/property-search-config", json={"brevoApiKey": "xkeysib-1"})
    client.put(f"/api/homes/{home_id}/property-search-config", json={"brevoApiKey": "", "retentionDays": 12})
    cfg = ps.load_config(home_id)
    assert cfg.brevoApiKey == "xkeysib-1" and cfg.retentionDays == 12


def test_config_validates_recipients(client, home_id):
    resp = client.put(f"/api/homes/{home_id}/property-search-config", json={"recipients": ["not-an-email"]})
    assert resp.status_code == 422
    resp = client.put(f"/api/homes/{home_id}/property-search-config", json={"recipients": [" a@b.si "]})
    assert resp.json()["recipients"] == ["a@b.si"]


def test_config_requires_admin(normal_client, home_id):
    assert normal_client.get(f"/api/homes/{home_id}/property-search-config").status_code == 403
    assert normal_client.put(f"/api/homes/{home_id}/property-search-config", json={}).status_code == 403


def test_ro_user_cannot_create_search(ro_client):
    # ro_client builds its own users fixture; any home id is fine, middleware rejects first.
    assert ro_client.post("/api/homes/h/property-searches", json=SEARCH).status_code == 403
