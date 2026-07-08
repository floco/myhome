def test_get_activity_requires_admin(client, home_id, ro_client):
    client.post(f"/api/homes/{home_id}/works", json={"title": "Fix boiler", "date": "2026-01-01"})
    resp = ro_client.get(f"/api/homes/{home_id}/activity")
    assert resp.status_code == 403


def test_get_activity_returns_entries_newest_first(client, home_id):
    client.post(f"/api/homes/{home_id}/works", json={"title": "First", "date": "2026-01-01"})
    client.post(f"/api/homes/{home_id}/works", json={"title": "Second", "date": "2026-01-02"})

    resp = client.get(f"/api/homes/{home_id}/activity")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert [e["entityLabel"] for e in data["entries"]] == ["Second", "First"]
    assert data["entries"][0]["description"] == "added work 'Second'"


def test_get_activity_filters_by_module(client, home_id):
    client.post(f"/api/homes/{home_id}/works", json={"title": "Fix boiler", "date": "2026-01-01"})
    client.post(f"/api/homes/{home_id}/kb", json={"title": "Router guide", "content": "..."})

    resp = client.get(f"/api/homes/{home_id}/activity?module=kb")
    entries = resp.json()["entries"]
    assert len(entries) == 1
    assert entries[0]["module"] == "kb"


def test_get_activity_filters_by_user(client, home_id):
    client.post(f"/api/homes/{home_id}/works", json={"title": "Fix boiler", "date": "2026-01-01"})

    resp = client.get(f"/api/homes/{home_id}/activity?userId=nonexistent-user")
    assert resp.json()["entries"] == []


def test_get_activity_paginates(client, home_id):
    for i in range(3):
        client.post(f"/api/homes/{home_id}/works", json={"title": f"Work {i}", "date": "2026-01-01"})

    resp = client.get(f"/api/homes/{home_id}/activity?limit=2&offset=0")
    data = resp.json()
    assert len(data["entries"]) == 2
    assert data["total"] == 3
