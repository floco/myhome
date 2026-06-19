import pytest
from fastapi.testclient import TestClient
from myhome.main import app
from myhome.models_chores import ChoreDocument, Chore
from myhome.persistence_chores import save_chores


def make_chore_doc() -> ChoreDocument:
    return ChoreDocument(
        chores=[
            Chore(
                id="c1",
                name="🧹 Sweep",
                emoji="🧹",
                periodDays=14,
                nextDueDate="2027-06-01T00:00:00Z",
            )
        ],
        assignments=[],
    )


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    return TestClient(app)


# --- GET /api/chores ---

def test_get_chores_empty_when_no_file(client):
    resp = client.get("/api/chores")
    assert resp.status_code == 200
    data = resp.json()
    assert data["chores"] == []
    assert data["assignments"] == []


def test_get_chores_returns_saved_data(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    save_chores(make_chore_doc())
    c = TestClient(app)
    resp = c.get("/api/chores")
    assert resp.status_code == 200
    assert resp.json()["chores"][0]["id"] == "c1"


# --- POST /api/chores ---

def test_create_chore(client):
    payload = {
        "name": "🪟 Clean windows",
        "emoji": "🪟",
        "periodDays": 365,
        "nextDueDate": "2027-01-01T00:00:00Z",
        "description": "",
    }
    resp = client.post("/api/chores", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "🪟 Clean windows"
    assert data["emoji"] == "🪟"
    assert "id" in data
    get_resp = client.get("/api/chores")
    assert any(c["name"] == "🪟 Clean windows" for c in get_resp.json()["chores"])


# --- PUT /api/chores/{id} ---

def test_update_chore(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    save_chores(make_chore_doc())
    c = TestClient(app)
    resp = c.put("/api/chores/c1", json={"name": "🧹 Sweep floors", "periodDays": 21})
    assert resp.status_code == 204
    get_resp = c.get("/api/chores")
    chore = next(ch for ch in get_resp.json()["chores"] if ch["id"] == "c1")
    assert chore["name"] == "🧹 Sweep floors"
    assert chore["periodDays"] == 21
    assert chore["emoji"] == "🧹"  # unchanged


def test_update_chore_404(client):
    resp = client.put("/api/chores/nonexistent", json={"name": "X"})
    assert resp.status_code == 404


# --- DELETE /api/chores/{id} ---

def test_delete_chore(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    save_chores(make_chore_doc())
    c = TestClient(app)
    resp = c.delete("/api/chores/c1")
    assert resp.status_code == 204
    get_resp = c.get("/api/chores")
    assert get_resp.json()["chores"] == []


def test_delete_chore_404(client):
    resp = client.delete("/api/chores/nonexistent")
    assert resp.status_code == 404


# --- POST /api/chores/{id}/complete ---

def test_complete_chore_advances_next_due(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    save_chores(make_chore_doc())
    c = TestClient(app)
    # Create an assignment so we can verify it also advances
    aid = c.post("/api/assignments", json={"choreId": "c1", "roomId": "r1"}).json()["id"]
    resp = c.post("/api/chores/c1/complete")
    assert resp.status_code == 200
    data = resp.json()
    from datetime import datetime, timezone, timedelta
    new_due = datetime.fromisoformat(data["nextDueDate"].replace("Z", "+00:00"))
    now = datetime.now(timezone.utc)
    expected = now + timedelta(days=14)
    assert abs((new_due - expected).total_seconds()) < 5
    # All assignments should also have their nextDueDate advanced
    assignments = c.get("/api/chores").json()["assignments"]
    a = next(a for a in assignments if a["id"] == aid)
    a_due = datetime.fromisoformat(a["nextDueDate"].replace("Z", "+00:00"))
    assert abs((a_due - expected).total_seconds()) < 5


def test_complete_chore_404(client):
    resp = client.post("/api/chores/nonexistent/complete")
    assert resp.status_code == 404


# --- Assignment routes ---

def test_create_assignment(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    save_chores(make_chore_doc())
    c = TestClient(app)
    resp = c.post("/api/assignments", json={"choreId": "c1", "roomId": "r1", "position": {"x": 3.0, "y": 4.0}})
    assert resp.status_code == 201
    data = resp.json()
    assert data["choreId"] == "c1"
    assert data["roomId"] == "r1"
    assert data["position"]["x"] == 3.0
    assert "id" in data
    # nextDueDate should be inherited from the chore template
    assert data["nextDueDate"] == "2027-06-01T00:00:00Z"


def test_assignment_inherits_next_due_from_chore(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    save_chores(make_chore_doc())
    c = TestClient(app)
    # Create assignment without explicit nextDueDate
    resp = c.post("/api/assignments", json={"choreId": "c1", "roomId": "r2"})
    assert resp.status_code == 201
    assert resp.json()["nextDueDate"] == "2027-06-01T00:00:00Z"
    # Create assignment with explicit nextDueDate overrides chore template
    resp2 = c.post("/api/assignments", json={"choreId": "c1", "roomId": "r3", "nextDueDate": "2028-01-01T00:00:00Z"})
    assert resp2.status_code == 201
    assert resp2.json()["nextDueDate"] == "2028-01-01T00:00:00Z"


def test_create_assignment_house_level(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    save_chores(make_chore_doc())
    c = TestClient(app)
    resp = c.post("/api/assignments", json={"choreId": "c1", "roomId": None, "position": None})
    assert resp.status_code == 201
    assert resp.json()["roomId"] is None
    assert resp.json()["position"] is None


def test_create_assignment_404_unknown_chore(client):
    resp = client.post("/api/assignments", json={"choreId": "nope", "roomId": "r1"})
    assert resp.status_code == 404


def test_update_assignment_position(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    save_chores(make_chore_doc())
    c = TestClient(app)
    create_resp = c.post("/api/assignments", json={"choreId": "c1", "roomId": "r1", "position": {"x": 1.0, "y": 1.0}})
    aid = create_resp.json()["id"]
    put_resp = c.put(f"/api/assignments/{aid}", json={"position": {"x": 5.0, "y": 6.0}})
    assert put_resp.status_code == 204
    assignments = c.get("/api/chores").json()["assignments"]
    a = next(a for a in assignments if a["id"] == aid)
    assert a["position"]["x"] == 5.0


def test_delete_assignment(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    save_chores(make_chore_doc())
    c = TestClient(app)
    aid = c.post("/api/assignments", json={"choreId": "c1", "roomId": "r1"}).json()["id"]
    del_resp = c.delete(f"/api/assignments/{aid}")
    assert del_resp.status_code == 204
    assert c.get("/api/chores").json()["assignments"] == []


def test_delete_chore_cascades_assignments(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    save_chores(make_chore_doc())
    c = TestClient(app)
    c.post("/api/assignments", json={"choreId": "c1", "roomId": "r1"})
    c.delete("/api/chores/c1")
    assert c.get("/api/chores").json()["assignments"] == []


# --- POST /api/assignments/{id}/complete ---

def test_complete_assignment(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    save_chores(make_chore_doc())
    c = TestClient(app)
    aid = c.post("/api/assignments", json={"choreId": "c1", "roomId": "r1"}).json()["id"]
    resp = c.post(f"/api/assignments/{aid}/complete")
    assert resp.status_code == 200
    data = resp.json()
    from datetime import datetime, timezone, timedelta
    new_due = datetime.fromisoformat(data["nextDueDate"].replace("Z", "+00:00"))
    now = datetime.now(timezone.utc)
    expected = now + timedelta(days=14)
    assert abs((new_due - expected).total_seconds()) < 5


def test_complete_assignment_404(client):
    resp = client.post("/api/assignments/nonexistent/complete")
    assert resp.status_code == 404


def test_complete_chore_advances_all_assignments(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    save_chores(make_chore_doc())
    c = TestClient(app)
    aid1 = c.post("/api/assignments", json={"choreId": "c1", "roomId": "r1"}).json()["id"]
    aid2 = c.post("/api/assignments", json={"choreId": "c1", "roomId": "r2"}).json()["id"]
    c.post("/api/chores/c1/complete")
    from datetime import datetime, timezone, timedelta
    assignments = {a["id"]: a for a in c.get("/api/chores").json()["assignments"]}
    now = datetime.now(timezone.utc)
    expected = now + timedelta(days=14)
    for aid in (aid1, aid2):
        due = datetime.fromisoformat(assignments[aid]["nextDueDate"].replace("Z", "+00:00"))
        assert abs((due - expected).total_seconds()) < 5


# --- POST /api/chores/import (mock Donetick) ---

def test_import_from_donetick(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    import respx
    import httpx

    donetick_response = {
        "res": [
            {
                "id": 42,
                "name": "🪟 Clean windows",
                "frequencyType": "interval",
                "frequency": 6,
                "frequencyMetadata": {"unit": "months"},
                "nextDueDate": "2027-01-01T00:00:00Z",
            },
            {
                "id": 43,
                "name": "🧹 Sweep",
                "frequencyType": "weekly",
                "frequency": 2,
                "frequencyMetadata": {"unit": "weeks"},
                "nextDueDate": "2026-07-01T00:00:00Z",
            },
        ]
    }

    with respx.mock:
        respx.get("https://chores.casa.mutualis.com/api/v1/chores/").mock(
            return_value=httpx.Response(200, json=donetick_response)
        )
        c = TestClient(app)
        resp = c.post("/api/chores/import", json={"token": "test-token"})

    assert resp.status_code == 200
    assert resp.json()["imported"] == 2

    # Read back the saved chores using the same tmp_path (DATA_DIR already monkeypatched)
    chores = TestClient(app).get("/api/chores").json()["chores"]
    assert len(chores) == 2
    window = next(c for c in chores if c["donetickId"] == 42)
    assert window["emoji"] == "🪟"
    assert window["periodDays"] == 180  # 6 * 30
    sweep = next(c for c in chores if c["donetickId"] == 43)
    assert sweep["periodDays"] == 14  # 2 * 7


def test_import_is_idempotent(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    import respx
    import httpx

    existing = ChoreDocument(
        chores=[Chore(id="x", donetickId=42, name="🪟 Clean windows", emoji="🪟", periodDays=180, nextDueDate="2027-01-01T00:00:00Z")],
        assignments=[],
    )
    save_chores(existing)

    donetick_response = {"res": [{"id": 42, "name": "🪟 Clean windows", "frequencyType": "interval", "frequency": 6, "frequencyMetadata": {"unit": "months"}, "nextDueDate": "2027-01-01T00:00:00Z"}]}
    with respx.mock:
        respx.get("https://chores.casa.mutualis.com/api/v1/chores/").mock(
            return_value=httpx.Response(200, json=donetick_response)
        )
        c = TestClient(app)
        resp = c.post("/api/chores/import", json={"token": "test-token"})

    assert resp.json()["imported"] == 0
    assert len(TestClient(app).get("/api/chores").json()["chores"]) == 1
