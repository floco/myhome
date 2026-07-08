from myhome.persistence_activity import load_activity_log


def test_creating_chore_logs_activity(client, home_id):
    client.post(f"/api/homes/{home_id}/chores", json={
        "name": "Sweep kitchen", "emoji": "🧹", "periodDays": 7,
        "nextDueDate": "2026-01-01T00:00:00Z",
    })
    entries = load_activity_log(home_id).entries
    assert any(e.module == "chores" and e.action == "create" and e.entityLabel == "Sweep kitchen" for e in entries)


def test_updating_chore_logs_activity(client, home_id):
    chore = client.post(f"/api/homes/{home_id}/chores", json={
        "name": "Sweep kitchen", "emoji": "🧹", "periodDays": 7,
        "nextDueDate": "2026-01-01T00:00:00Z",
    }).json()
    client.put(f"/api/homes/{home_id}/chores/{chore['id']}", json={"description": "Updated"})
    entries = load_activity_log(home_id).entries
    assert any(e.module == "chores" and e.action == "update" and e.entityLabel == "Sweep kitchen" for e in entries)


def test_deleting_chore_logs_activity(client, home_id):
    chore = client.post(f"/api/homes/{home_id}/chores", json={
        "name": "Sweep kitchen", "emoji": "🧹", "periodDays": 7,
        "nextDueDate": "2026-01-01T00:00:00Z",
    }).json()
    client.delete(f"/api/homes/{home_id}/chores/{chore['id']}")
    entries = load_activity_log(home_id).entries
    assert any(e.module == "chores" and e.action == "delete" and e.entityLabel == "Sweep kitchen" for e in entries)


def test_completing_chore_logs_activity(client, home_id):
    chore = client.post(f"/api/homes/{home_id}/chores", json={
        "name": "Sweep kitchen", "emoji": "🧹", "periodDays": 7,
        "nextDueDate": "2026-01-01T00:00:00Z",
    }).json()
    client.post(f"/api/homes/{home_id}/chores/{chore['id']}/complete", json={"notes": ""})
    entries = load_activity_log(home_id).entries
    assert any(e.module == "chores" and e.action == "complete" and e.entityLabel == "Sweep kitchen" for e in entries)


def test_completing_assignment_logs_activity(client, home_id):
    chore = client.post(f"/api/homes/{home_id}/chores", json={
        "name": "Sweep kitchen", "emoji": "🧹", "periodDays": 7,
        "nextDueDate": "2026-01-01T00:00:00Z",
    }).json()
    assignment = client.post(f"/api/homes/{home_id}/assignments", json={
        "choreId": chore["id"], "roomId": None, "position": None, "nextDueDate": "2026-01-01T00:00:00Z",
    }).json()
    client.post(f"/api/homes/{home_id}/assignments/{assignment['id']}/complete", json={"notes": ""})
    entries = load_activity_log(home_id).entries
    assert any(e.module == "chores" and e.action == "complete" and e.entityLabel == "Sweep kitchen" for e in entries)


def test_creating_work_logs_activity(client, home_id):
    client.post(f"/api/homes/{home_id}/works", json={"title": "Fix boiler", "date": "2026-01-01"})
    entries = load_activity_log(home_id).entries
    assert any(e.module == "works" and e.action == "create" and e.entityLabel == "Fix boiler" for e in entries)


def test_updating_work_logs_activity(client, home_id):
    work = client.post(f"/api/homes/{home_id}/works", json={"title": "Fix boiler", "date": "2026-01-01"}).json()
    client.put(f"/api/homes/{home_id}/works/{work['id']}", json={"status": "in_progress"})
    entries = load_activity_log(home_id).entries
    assert any(e.module == "works" and e.action == "update" and e.entityLabel == "Fix boiler" for e in entries)


def test_deleting_work_logs_activity(client, home_id):
    work = client.post(f"/api/homes/{home_id}/works", json={"title": "Fix boiler", "date": "2026-01-01"}).json()
    client.delete(f"/api/homes/{home_id}/works/{work['id']}")
    entries = load_activity_log(home_id).entries
    assert any(e.module == "works" and e.action == "delete" and e.entityLabel == "Fix boiler" for e in entries)
