def test_reset_requires_admin(ro_client, home_id):
    resp = ro_client.post(f"/api/homes/{home_id}/modules/chores/reset")
    assert resp.status_code == 403


def test_reset_rejects_unknown_module(client, home_id):
    resp = client.post(f"/api/homes/{home_id}/modules/bogus/reset")
    assert resp.status_code == 400


def test_reset_rejects_home_module(client, home_id):
    resp = client.post(f"/api/homes/{home_id}/modules/home/reset")
    assert resp.status_code == 400


def test_reset_rejects_plan_module(client, home_id):
    resp = client.post(f"/api/homes/{home_id}/modules/plan/reset")
    assert resp.status_code == 400


def test_reset_returns_404_for_unknown_home(client):
    resp = client.post("/api/homes/nonexistent/modules/chores/reset")
    assert resp.status_code == 404


def test_reset_clears_chores_and_logs_activity(client, home_id):
    client.post(f"/api/homes/{home_id}/chores", json={
        "name": "Sweep", "emoji": "🧹", "periodDays": 7, "nextDueDate": "2027-01-01T00:00:00Z",
    })
    resp = client.post(f"/api/homes/{home_id}/modules/chores/reset")
    assert resp.status_code == 204
    assert client.get(f"/api/homes/{home_id}/chores").json()["chores"] == []

    log = client.get(f"/api/homes/{home_id}/activity").json()
    reset_entries = [e for e in log["entries"] if e["module"] == "chores" and e["action"] == "reset"]
    assert len(reset_entries) == 1
    assert reset_entries[0]["description"] == "reset chore data"


def test_reset_does_not_touch_other_modules(client, home_id):
    client.post(f"/api/homes/{home_id}/chores", json={
        "name": "Sweep", "emoji": "🧹", "periodDays": 7, "nextDueDate": "2027-01-01T00:00:00Z",
    })
    client.post(f"/api/homes/{home_id}/works", json={"title": "Roof repair", "status": "planned", "date": "2026-04-01"})

    client.post(f"/api/homes/{home_id}/modules/chores/reset")

    assert client.get(f"/api/homes/{home_id}/chores").json()["chores"] == []
    works = client.get(f"/api/homes/{home_id}/works").json()["works"]
    assert len(works) == 1
    assert works[0]["title"] == "Roof repair"


def test_reset_all_resettable_module_ids_succeed(client, home_id):
    resettable = [
        "chores", "inventory", "consumables", "works", "kb", "costs",
        "locations", "properties", "build", "contacts", "insurance",
    ]
    for module_id in resettable:
        resp = client.post(f"/api/homes/{home_id}/modules/{module_id}/reset")
        assert resp.status_code == 204, f"{module_id} reset failed: {resp.text}"
