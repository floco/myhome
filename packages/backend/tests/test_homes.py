# packages/backend/tests/test_homes.py
import pytest


def test_get_house_returns_404_for_nonexistent_home_id(client):
    # A bare ".." is a single path segment (no "/"), so it matches the
    # {home_id} route param. The house document is now a SQL row keyed by
    # home_id (a query parameter, not a filesystem path), so a malformed id
    # simply matches no row -- 404, not the old path-injection guard's 400.
    resp = client.get("/api/homes/%2e%2e/house")
    assert resp.status_code == 404


def test_get_homes_returns_empty_list(client):
    resp = client.get("/api/homes")
    assert resp.status_code == 200
    assert resp.json() == []


def test_create_home_existing(client):
    resp = client.post("/api/homes", json={"name": "Rue des Lilas", "type": "existing"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Rue des Lilas"
    assert data["type"] == "existing"
    assert "chores" in data["enabledModules"]
    assert "id" in data
    assert "createdAt" in data


def test_create_home_project(client):
    resp = client.post("/api/homes", json={"name": "Dream Build", "type": "project"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["type"] == "project"
    assert "chores" not in data["enabledModules"]
    assert "works" in data["enabledModules"]


def test_get_homes_lists_created_homes(client):
    client.post("/api/homes", json={"name": "A", "type": "existing"})
    client.post("/api/homes", json={"name": "B", "type": "project"})
    resp = client.get("/api/homes")
    assert resp.status_code == 200
    names = [h["name"] for h in resp.json()]
    assert "A" in names
    assert "B" in names


def test_patch_home_name(client):
    home_id = client.post("/api/homes", json={"name": "Old", "type": "existing"}).json()["id"]
    resp = client.patch(f"/api/homes/{home_id}", json={"name": "New"})
    assert resp.status_code == 200
    assert resp.json()["name"] == "New"


def test_patch_home_enabled_modules(client):
    home_id = client.post("/api/homes", json={"name": "Test", "type": "existing"}).json()["id"]
    resp = client.patch(f"/api/homes/{home_id}", json={"enabledModules": ["home", "plan"]})
    assert resp.status_code == 200
    assert resp.json()["enabledModules"] == ["home", "plan"]


def test_patch_home_returns_404_for_unknown(client):
    resp = client.patch("/api/homes/nonexistent", json={"name": "X"})
    assert resp.status_code == 404


def test_delete_home(client):
    home_id = client.post("/api/homes", json={"name": "Test", "type": "existing"}).json()["id"]
    resp = client.delete(f"/api/homes/{home_id}")
    assert resp.status_code == 204
    homes = client.get("/api/homes").json()
    assert all(h["id"] != home_id for h in homes)


def test_delete_home_returns_404_for_unknown(client):
    resp = client.delete("/api/homes/nonexistent")
    assert resp.status_code == 404


def test_create_home_demo_enables_all_modules(client):
    resp = client.post("/api/homes", json={"name": "Demo House", "type": "demo"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["type"] == "demo"
    from myhome.models_homes import ALL_MODULE_IDS
    assert set(data["enabledModules"]) == set(ALL_MODULE_IDS)


def test_create_home_demo_seeds_every_module(client):
    resp = client.post("/api/homes", json={"name": "Demo House", "type": "demo"})
    assert resp.status_code == 201
    home_id = resp.json()["id"]

    for path, key in [
        ("/chores", "chores"), ("/inventory", "items"), ("/costs", "entries"),
        ("/works", "works"), ("/kb", "entries"), ("/consumables", "consumables"),
    ]:
        r = client.get(f"/api/homes/{home_id}{path}")
        assert r.status_code == 200
        items = r.json()[key]
        assert len(items) >= 32, f"{path} returned only {len(items)} records"

    house_resp = client.get(f"/api/homes/{home_id}/house")
    assert house_resp.status_code == 200
    assert len(house_resp.json()["floors"]) == 2


def test_create_home_demo_cleans_up_on_seeding_failure(client, monkeypatch):
    import myhome.persistence_homes as ph

    def boom(home_id: str) -> None:
        raise RuntimeError("seeding exploded")

    monkeypatch.setattr(ph, "seed_demo_home", boom)

    before = client.get("/api/homes").json()
    with pytest.raises(RuntimeError):
        client.post("/api/homes", json={"name": "Broken Demo", "type": "demo"})
    after = client.get("/api/homes").json()
    assert len(after) == len(before)
