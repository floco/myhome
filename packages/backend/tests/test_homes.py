# packages/backend/tests/test_homes.py


def test_get_house_rejects_path_traversal_home_id(client):
    # A bare ".." is a single path segment (no "/"), so it matches the
    # {home_id} route param and reaches _home_dir() -- this is exactly the
    # payload the shared validate_safe_id() check exists to reject.
    resp = client.get("/api/homes/%2e%2e/house")
    assert resp.status_code == 400


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
