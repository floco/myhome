import json
import pytest
from myhome.models import HouseDocument, House, Floor
from myhome.persistence import save_house


def make_doc() -> HouseDocument:
    return HouseDocument(
        version=1,
        house=House(name="Test", units="m", gridSnap=0.1),
        floors=[Floor(id="f1", name="Ground", order=0, walls=[], openings=[], rooms=[])],
    )


def test_get_house_404_when_missing(client):
    resp = client.get("/api/house")
    assert resp.status_code == 404


def test_put_house_then_get(client):
    doc = make_doc()
    put_resp = client.put(
        "/api/house",
        content=doc.model_dump_json(),
        headers={"Content-Type": "application/json"},
    )
    assert put_resp.status_code == 204

    get_resp = client.get("/api/house")
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert data["floors"][0]["id"] == "f1"
    assert data["house"]["name"] == "Test"


def test_get_floor_svg_404_when_no_house(client):
    resp = client.get("/api/house/floors/f1/svg")
    assert resp.status_code == 404


def test_get_floor_svg_404_for_unknown_floor(client, tmp_path):
    save_house(make_doc())
    resp = client.get("/api/house/floors/unknown/svg")
    assert resp.status_code == 404


def test_get_floor_svg_returns_svg(client, tmp_path):
    save_house(make_doc())
    resp = client.get("/api/house/floors/f1/svg")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("image/svg+xml")
    assert "<svg" in resp.text


def test_get_ha_areas_returns_empty_without_token(client, monkeypatch):
    monkeypatch.delenv("SUPERVISOR_TOKEN", raising=False)
    resp = client.get("/api/ha/areas")
    assert resp.status_code == 200
    assert resp.json() == []
