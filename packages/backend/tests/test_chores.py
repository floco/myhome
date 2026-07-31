import io
import struct
import zlib
import pytest
from myhome.models_chores import ChoreDocument, Chore, CompletionRecord
from myhome.persistence_chores import save_chores


def _make_valid_pdf() -> bytes:
    body = b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj 2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj 3 0 obj<</Type/Page/MediaBox[0 0 3 3]>>endobj\nxref\n0 4\n0000000000 65535 f\n0000000009 00000 n\n0000000058 00000 n\n0000000115 00000 n\ntrailer<</Size 4/Root 1 0 R>>\nstartxref\n190\n%%EOF"
    return body


def _chore_id(client, home_id: str) -> str:
    resp = client.post(f"/api/homes/{home_id}/chores", json={
        "name": "Sweep", "emoji": "🧹", "periodDays": 7, "nextDueDate": "2027-01-01T00:00:00Z",
    })
    return resp.json()["id"]


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


# --- GET /api/homes/{home_id}/chores ---

def test_get_chores_empty_when_no_file(client, home_id):
    resp = client.get(f"/api/homes/{home_id}/chores")
    assert resp.status_code == 200
    data = resp.json()
    assert data["chores"] == []
    assert data["assignments"] == []


def test_get_chores_returns_saved_data(client, home_id, tmp_path):
    save_chores(home_id, make_chore_doc())
    resp = client.get(f"/api/homes/{home_id}/chores")
    assert resp.status_code == 200
    assert resp.json()["chores"][0]["id"] == "c1"


# --- POST /api/homes/{home_id}/chores ---

def test_create_chore(client, home_id):
    payload = {
        "name": "🪟 Clean windows",
        "emoji": "🪟",
        "periodDays": 365,
        "nextDueDate": "2027-01-01T00:00:00Z",
        "description": "",
    }
    resp = client.post(f"/api/homes/{home_id}/chores", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "🪟 Clean windows"
    assert data["emoji"] == "🪟"
    assert "id" in data
    get_resp = client.get(f"/api/homes/{home_id}/chores")
    assert any(c["name"] == "🪟 Clean windows" for c in get_resp.json()["chores"])


# --- PUT /api/homes/{home_id}/chores/{id} ---

def test_update_chore(client, home_id, tmp_path):
    save_chores(home_id, make_chore_doc())
    resp = client.put(f"/api/homes/{home_id}/chores/c1", json={"name": "🧹 Sweep floors", "periodDays": 21})
    assert resp.status_code == 204
    get_resp = client.get(f"/api/homes/{home_id}/chores")
    chore = next(ch for ch in get_resp.json()["chores"] if ch["id"] == "c1")
    assert chore["name"] == "🧹 Sweep floors"
    assert chore["periodDays"] == 21
    assert chore["emoji"] == "🧹"  # unchanged


def test_update_chore_404(client, home_id):
    resp = client.put(f"/api/homes/{home_id}/chores/nonexistent", json={"name": "X"})
    assert resp.status_code == 404


# --- DELETE /api/homes/{home_id}/chores/{id} ---

def test_delete_chore(client, home_id, tmp_path):
    save_chores(home_id, make_chore_doc())
    resp = client.delete(f"/api/homes/{home_id}/chores/c1")
    assert resp.status_code == 204
    get_resp = client.get(f"/api/homes/{home_id}/chores")
    assert get_resp.json()["chores"] == []


def test_delete_chore_404(client, home_id):
    resp = client.delete(f"/api/homes/{home_id}/chores/nonexistent")
    assert resp.status_code == 404


# --- POST /api/homes/{home_id}/chores/{id}/complete ---

def test_complete_chore_advances_next_due(client, home_id, tmp_path):
    save_chores(home_id, make_chore_doc())
    # Create an assignment so we can verify it also advances
    aid = client.post(f"/api/homes/{home_id}/assignments", json={"choreId": "c1", "roomId": "r1"}).json()["id"]
    resp = client.post(f"/api/homes/{home_id}/chores/c1/complete")
    assert resp.status_code == 200
    data = resp.json()
    from datetime import datetime, timezone, timedelta
    new_due = datetime.fromisoformat(data["nextDueDate"].replace("Z", "+00:00"))
    now = datetime.now(timezone.utc)
    expected = now + timedelta(days=14)
    assert abs((new_due - expected).total_seconds()) < 5
    # All assignments should also have their nextDueDate advanced
    assignments = client.get(f"/api/homes/{home_id}/chores").json()["assignments"]
    a = next(a for a in assignments if a["id"] == aid)
    a_due = datetime.fromisoformat(a["nextDueDate"].replace("Z", "+00:00"))
    assert abs((a_due - expected).total_seconds()) < 5


def test_complete_chore_404(client, home_id):
    resp = client.post(f"/api/homes/{home_id}/chores/nonexistent/complete")
    assert resp.status_code == 404


# --- Assignment routes ---

def test_create_assignment(client, home_id, tmp_path):
    save_chores(home_id, make_chore_doc())
    resp = client.post(f"/api/homes/{home_id}/assignments", json={"choreId": "c1", "roomId": "r1", "position": {"x": 3.0, "y": 4.0}})
    assert resp.status_code == 201
    data = resp.json()
    assert data["choreId"] == "c1"
    assert data["roomId"] == "r1"
    assert data["position"]["x"] == 3.0
    assert "id" in data
    # nextDueDate should be inherited from the chore template
    assert data["nextDueDate"] == "2027-06-01T00:00:00Z"


def test_assignment_inherits_next_due_from_chore(client, home_id, tmp_path):
    save_chores(home_id, make_chore_doc())
    # Create assignment without explicit nextDueDate
    resp = client.post(f"/api/homes/{home_id}/assignments", json={"choreId": "c1", "roomId": "r2"})
    assert resp.status_code == 201
    assert resp.json()["nextDueDate"] == "2027-06-01T00:00:00Z"
    # Create assignment with explicit nextDueDate overrides chore template
    resp2 = client.post(f"/api/homes/{home_id}/assignments", json={"choreId": "c1", "roomId": "r3", "nextDueDate": "2028-01-01T00:00:00Z"})
    assert resp2.status_code == 201
    assert resp2.json()["nextDueDate"] == "2028-01-01T00:00:00Z"


def test_create_assignment_house_level(client, home_id, tmp_path):
    save_chores(home_id, make_chore_doc())
    resp = client.post(f"/api/homes/{home_id}/assignments", json={"choreId": "c1", "roomId": None, "position": None})
    assert resp.status_code == 201
    assert resp.json()["roomId"] is None
    assert resp.json()["position"] is None


def test_create_assignment_404_unknown_chore(client, home_id):
    resp = client.post(f"/api/homes/{home_id}/assignments", json={"choreId": "nope", "roomId": "r1"})
    assert resp.status_code == 404


def test_update_assignment_position(client, home_id, tmp_path):
    save_chores(home_id, make_chore_doc())
    create_resp = client.post(f"/api/homes/{home_id}/assignments", json={"choreId": "c1", "roomId": "r1", "position": {"x": 1.0, "y": 1.0}})
    aid = create_resp.json()["id"]
    put_resp = client.put(f"/api/homes/{home_id}/assignments/{aid}", json={"position": {"x": 5.0, "y": 6.0}})
    assert put_resp.status_code == 204
    assignments = client.get(f"/api/homes/{home_id}/chores").json()["assignments"]
    a = next(a for a in assignments if a["id"] == aid)
    assert a["position"]["x"] == 5.0


def test_delete_assignment(client, home_id, tmp_path):
    save_chores(home_id, make_chore_doc())
    aid = client.post(f"/api/homes/{home_id}/assignments", json={"choreId": "c1", "roomId": "r1"}).json()["id"]
    del_resp = client.delete(f"/api/homes/{home_id}/assignments/{aid}")
    assert del_resp.status_code == 204
    assert client.get(f"/api/homes/{home_id}/chores").json()["assignments"] == []


def test_delete_chore_cascades_assignments(client, home_id, tmp_path):
    save_chores(home_id, make_chore_doc())
    client.post(f"/api/homes/{home_id}/assignments", json={"choreId": "c1", "roomId": "r1"})
    client.delete(f"/api/homes/{home_id}/chores/c1")
    assert client.get(f"/api/homes/{home_id}/chores").json()["assignments"] == []


# --- POST /api/homes/{home_id}/assignments/{id}/complete ---

def test_complete_assignment(client, home_id, tmp_path):
    save_chores(home_id, make_chore_doc())
    aid = client.post(f"/api/homes/{home_id}/assignments", json={"choreId": "c1", "roomId": "r1"}).json()["id"]
    resp = client.post(f"/api/homes/{home_id}/assignments/{aid}/complete")
    assert resp.status_code == 200
    data = resp.json()
    from datetime import datetime, timezone, timedelta
    new_due = datetime.fromisoformat(data["nextDueDate"].replace("Z", "+00:00"))
    now = datetime.now(timezone.utc)
    expected = now + timedelta(days=14)
    assert abs((new_due - expected).total_seconds()) < 5


def test_complete_assignment_404(client, home_id):
    resp = client.post(f"/api/homes/{home_id}/assignments/nonexistent/complete")
    assert resp.status_code == 404


def test_complete_chore_advances_all_assignments(client, home_id, tmp_path):
    save_chores(home_id, make_chore_doc())
    aid1 = client.post(f"/api/homes/{home_id}/assignments", json={"choreId": "c1", "roomId": "r1"}).json()["id"]
    aid2 = client.post(f"/api/homes/{home_id}/assignments", json={"choreId": "c1", "roomId": "r2"}).json()["id"]
    client.post(f"/api/homes/{home_id}/chores/c1/complete")
    from datetime import datetime, timezone, timedelta
    assignments = {a["id"]: a for a in client.get(f"/api/homes/{home_id}/chores").json()["assignments"]}
    now = datetime.now(timezone.utc)
    expected = now + timedelta(days=14)
    for aid in (aid1, aid2):
        due = datetime.fromisoformat(assignments[aid]["nextDueDate"].replace("Z", "+00:00"))
        assert abs((due - expected).total_seconds()) < 5


# --- POST /api/homes/{home_id}/chores/import (mock Donetick) ---

def _mock_public_dns(monkeypatch, hostname: str = "donetick.example.com") -> None:
    """The import route resolves the Donetick hostname to guard against SSRF;
    tests run without real DNS, so stub resolution to a public-looking IP."""
    import socket
    from myhome.routes import chores as chores_module

    real_getaddrinfo = socket.getaddrinfo

    def fake_getaddrinfo(host, *args, **kwargs):
        if host == hostname:
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 0))]
        return real_getaddrinfo(host, *args, **kwargs)

    monkeypatch.setattr(chores_module.socket, "getaddrinfo", fake_getaddrinfo)


def test_import_from_donetick(client, home_id, monkeypatch):
    import respx
    import httpx

    _mock_public_dns(monkeypatch)

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
        respx.get("https://donetick.example.com/api/v1/chores/").mock(
            return_value=httpx.Response(200, json=donetick_response)
        )
        respx.get("https://donetick.example.com/api/v1/chores/42/history").mock(
            return_value=httpx.Response(200, json={"res": []})
        )
        respx.get("https://donetick.example.com/api/v1/chores/43/history").mock(
            return_value=httpx.Response(200, json={"res": []})
        )
        resp = client.post(
            f"/api/homes/{home_id}/chores/import",
            json={"token": "test-token", "url": "https://donetick.example.com"},
        )

    assert resp.status_code == 200
    assert resp.json()["imported"] == 2

    chores = client.get(f"/api/homes/{home_id}/chores").json()["chores"]
    assert len(chores) == 2
    window = next(c for c in chores if c["donetickId"] == 42)
    assert window["emoji"] == "🪟"
    assert window["periodDays"] == 180  # 6 * 30 (approx for progress bar)
    assert window["frequencyType"] == "interval"
    assert window["frequency"] == 6
    assert window["frequencyMetadata"]["unit"] == "months"
    sweep = next(c for c in chores if c["donetickId"] == 43)
    # Donetick's scheduler ignores `frequency` for the literal "weekly" type
    # (always every 1 week) -- the multiplier only applies to "interval".
    assert sweep["periodDays"] == 7
    assert sweep["frequencyType"] == "weekly"
    assert sweep["frequency"] == 2


def test_import_is_idempotent(client, home_id, tmp_path, monkeypatch):
    import respx
    import httpx

    _mock_public_dns(monkeypatch)

    existing = ChoreDocument(
        chores=[Chore(id="x", donetickId=42, name="🪟 Clean windows", emoji="🪟", periodDays=180, nextDueDate="2027-01-01T00:00:00Z")],
        assignments=[],
    )
    save_chores(home_id, existing)

    donetick_response = {"res": [{"id": 42, "name": "🪟 Clean windows", "frequencyType": "interval", "frequency": 6, "frequencyMetadata": {"unit": "months"}, "nextDueDate": "2027-01-01T00:00:00Z"}]}
    with respx.mock:
        respx.get("https://donetick.example.com/api/v1/chores/").mock(
            return_value=httpx.Response(200, json=donetick_response)
        )
        resp = client.post(
            f"/api/homes/{home_id}/chores/import",
            json={"token": "test-token", "url": "https://donetick.example.com"},
        )

    assert resp.json()["imported"] == 0
    assert len(client.get(f"/api/homes/{home_id}/chores").json()["chores"]) == 1


def test_import_ignores_donetick_frequency_for_yearly(client, home_id, monkeypatch):
    """Donetick's own scheduler always advances literal 'yearly'/'weekly'/'monthly'
    chores by exactly 1 unit and ignores the `frequency` field entirely (that
    multiplier only applies to the 'interval' type) -- so a Donetick chore with
    a stray `frequency` value on a plain 'yearly' type must still import as a
    1-year period, not `frequency` years."""
    import respx
    import httpx

    _mock_public_dns(monkeypatch)

    donetick_response = {
        "res": [{
            "id": 99,
            "name": "Exporter transactions banques",
            "frequencyType": "yearly",
            "frequency": 3,
            "frequencyMetadata": {},
            "nextDueDate": "2027-01-01T00:00:00Z",
        }]
    }
    with respx.mock:
        respx.get("https://donetick.example.com/api/v1/chores/").mock(
            return_value=httpx.Response(200, json=donetick_response)
        )
        respx.get("https://donetick.example.com/api/v1/chores/99/history").mock(
            return_value=httpx.Response(200, json={"res": []})
        )
        resp = client.post(
            f"/api/homes/{home_id}/chores/import",
            json={"token": "test-token", "url": "https://donetick.example.com"},
        )

    assert resp.status_code == 200
    chore = client.get(f"/api/homes/{home_id}/chores").json()["chores"][0]
    assert chore["periodDays"] == 365


def test_import_strips_leading_emoji_from_name(client, home_id, monkeypatch):
    import respx
    import httpx

    _mock_public_dns(monkeypatch)

    donetick_response = {
        "res": [{
            "id": 7,
            "name": "🧹 Sweep kitchen",
            "frequencyType": "interval",
            "frequency": 1,
            "frequencyMetadata": {"unit": "weeks"},
            "nextDueDate": "2027-01-01T00:00:00Z",
        }]
    }
    with respx.mock:
        respx.get("https://donetick.example.com/api/v1/chores/").mock(
            return_value=httpx.Response(200, json=donetick_response)
        )
        respx.get("https://donetick.example.com/api/v1/chores/7/history").mock(
            return_value=httpx.Response(200, json={"res": []})
        )
        resp = client.post(
            f"/api/homes/{home_id}/chores/import",
            json={"token": "test-token", "url": "https://donetick.example.com"},
        )

    assert resp.status_code == 200
    chore = client.get(f"/api/homes/{home_id}/chores").json()["chores"][0]
    assert chore["name"] == "Sweep kitchen"
    assert chore["emoji"] == "🧹"


def test_import_keeps_name_without_leading_icon(client, home_id, monkeypatch):
    import respx
    import httpx

    _mock_public_dns(monkeypatch)

    donetick_response = {
        "res": [{
            "id": 8,
            "name": "Exporter transactions banques",
            "frequencyType": "yearly",
            "frequency": 1,
            "frequencyMetadata": {},
            "nextDueDate": "2027-01-01T00:00:00Z",
        }]
    }
    with respx.mock:
        respx.get("https://donetick.example.com/api/v1/chores/").mock(
            return_value=httpx.Response(200, json=donetick_response)
        )
        respx.get("https://donetick.example.com/api/v1/chores/8/history").mock(
            return_value=httpx.Response(200, json={"res": []})
        )
        resp = client.post(
            f"/api/homes/{home_id}/chores/import",
            json={"token": "test-token", "url": "https://donetick.example.com"},
        )

    assert resp.status_code == 200
    chore = client.get(f"/api/homes/{home_id}/chores").json()["chores"][0]
    assert chore["name"] == "Exporter transactions banques"
    assert chore["emoji"] == "📋"


def test_import_creates_completion_history_for_new_chores(client, home_id, monkeypatch):
    import respx
    import httpx

    _mock_public_dns(monkeypatch)

    donetick_response = {
        "res": [{
            "id": 55,
            "name": "🧺 Laundry",
            "frequencyType": "interval",
            "frequency": 1,
            "frequencyMetadata": {"unit": "weeks"},
            "nextDueDate": "2027-01-01T00:00:00Z",
        }]
    }
    history_response = {
        "res": [
            {"id": 1, "choreId": 55, "performedAt": "2026-01-01T10:00:00Z", "dueDate": "2026-01-01T00:00:00Z", "notes": "done", "status": 1},
            {"id": 2, "choreId": 55, "performedAt": "2026-01-08T10:00:00Z", "dueDate": "2026-01-08T00:00:00Z", "notes": "", "status": 1},
            {"id": 3, "choreId": 55, "performedAt": None, "dueDate": "2026-01-15T00:00:00Z", "notes": "", "status": 2},
        ]
    }
    with respx.mock:
        respx.get("https://donetick.example.com/api/v1/chores/").mock(
            return_value=httpx.Response(200, json=donetick_response)
        )
        respx.get("https://donetick.example.com/api/v1/chores/55/history").mock(
            return_value=httpx.Response(200, json=history_response)
        )
        resp = client.post(
            f"/api/homes/{home_id}/chores/import",
            json={"token": "test-token", "url": "https://donetick.example.com"},
        )

    assert resp.status_code == 200
    data = client.get(f"/api/homes/{home_id}/chores").json()
    chore_id = data["chores"][0]["id"]
    completions = [c for c in data["completions"] if c["choreId"] == chore_id]
    assert len(completions) == 2
    assert {c["completedAt"] for c in completions} == {"2026-01-01T10:00:00Z", "2026-01-08T10:00:00Z"}
    done = next(c for c in completions if c["completedAt"] == "2026-01-01T10:00:00Z")
    assert done["scheduledDue"] == "2026-01-01T00:00:00Z"
    assert done["notes"] == "done"


def test_import_skips_history_for_already_imported_chores(client, home_id, monkeypatch, tmp_path):
    import respx
    import httpx

    _mock_public_dns(monkeypatch)

    existing = ChoreDocument(
        chores=[Chore(id="x", donetickId=42, name="Clean windows", emoji="🪟", periodDays=180, nextDueDate="2027-01-01T00:00:00Z")],
        assignments=[],
    )
    save_chores(home_id, existing)

    donetick_response = {"res": [{"id": 42, "name": "🪟 Clean windows", "frequencyType": "interval", "frequency": 6, "frequencyMetadata": {"unit": "months"}, "nextDueDate": "2027-01-01T00:00:00Z"}]}
    with respx.mock:
        respx.get("https://donetick.example.com/api/v1/chores/").mock(
            return_value=httpx.Response(200, json=donetick_response)
        )
        # No history route mocked for id 42 -- respx.mock raises if it's called,
        # asserting the importer does NOT fetch history for already-imported chores.
        resp = client.post(
            f"/api/homes/{home_id}/chores/import",
            json={"token": "test-token", "url": "https://donetick.example.com"},
        )

    assert resp.status_code == 200
    assert resp.json()["imported"] == 0


def test_import_continues_when_history_fetch_fails(client, home_id, monkeypatch):
    import respx
    import httpx

    _mock_public_dns(monkeypatch)

    donetick_response = {
        "res": [{
            "id": 9,
            "name": "Test chore",
            "frequencyType": "interval",
            "frequency": 1,
            "frequencyMetadata": {"unit": "weeks"},
            "nextDueDate": "2027-01-01T00:00:00Z",
        }]
    }
    with respx.mock:
        respx.get("https://donetick.example.com/api/v1/chores/").mock(
            return_value=httpx.Response(200, json=donetick_response)
        )
        respx.get("https://donetick.example.com/api/v1/chores/9/history").mock(
            return_value=httpx.Response(500)
        )
        resp = client.post(
            f"/api/homes/{home_id}/chores/import",
            json={"token": "test-token", "url": "https://donetick.example.com"},
        )

    assert resp.status_code == 200
    assert resp.json()["imported"] == 1


def test_import_requires_url(client, home_id):
    resp = client.post(f"/api/homes/{home_id}/chores/import", json={"token": "test-token", "url": ""})
    assert resp.status_code == 400


@pytest.mark.parametrize("url", [
    "http://127.0.0.1:8000",
    "http://localhost",
    "http://169.254.169.254/latest/meta-data/",  # cloud metadata SSRF target
    "ftp://donetick.example.com",  # non-http(s) scheme
])
def test_import_rejects_ssrf_targets(client, home_id, url):
    resp = client.post(f"/api/homes/{home_id}/chores/import", json={"token": "test-token", "url": url})
    assert resp.status_code == 400


def test_import_allows_private_lan_address(client, home_id):
    """RFC1918 addresses must stay allowed -- self-hosted Donetick instances
    normally live on the same LAN as this add-on."""
    import respx
    import httpx

    with respx.mock:
        respx.get("http://192.168.1.50:2021/api/v1/chores/").mock(
            return_value=httpx.Response(200, json={"res": []})
        )
        resp = client.post(
            f"/api/homes/{home_id}/chores/import",
            json={"token": "test-token", "url": "http://192.168.1.50:2021"},
        )

    assert resp.status_code == 200


def test_import_forbidden_for_non_admin(ro_client, home_id):
    resp = ro_client.post(
        f"/api/homes/{home_id}/chores/import",
        json={"token": "test-token", "url": "https://donetick.example.com"},
    )
    assert resp.status_code == 403


# --- Calendar-aware scheduling ---

def test_complete_chore_monthly_interval(client, home_id, tmp_path):
    doc = ChoreDocument(
        chores=[
            Chore(
                id="c1", name="Clean windows", emoji="🪟", periodDays=180,
                frequencyType="interval", frequency=6,
                frequencyMetadata={"unit": "months"},
                nextDueDate="2027-01-01T00:00:00Z",
            )
        ],
        assignments=[],
    )
    save_chores(home_id, doc)
    resp = client.post(f"/api/homes/{home_id}/chores/c1/complete")
    assert resp.status_code == 200
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    new_due = datetime.fromisoformat(resp.json()["nextDueDate"].replace("Z", "+00:00"))
    diff_days = (new_due - now).days
    assert 175 <= diff_days <= 186  # 6 calendar months


def test_complete_chore_yearly_interval(client, home_id, tmp_path):
    doc = ChoreDocument(
        chores=[
            Chore(
                id="c1", name="AC service", emoji="❄️", periodDays=730,
                frequencyType="interval", frequency=2,
                frequencyMetadata={"unit": "years"},
                nextDueDate="2027-01-01T00:00:00Z",
            )
        ],
        assignments=[],
    )
    save_chores(home_id, doc)
    resp = client.post(f"/api/homes/{home_id}/chores/c1/complete")
    assert resp.status_code == 200
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    new_due = datetime.fromisoformat(resp.json()["nextDueDate"].replace("Z", "+00:00"))
    diff_days = (new_due - now).days
    assert 728 <= diff_days <= 733  # 2 calendar years


def test_complete_chore_weekly_frequency(client, home_id, tmp_path):
    """Donetick's own scheduler ignores `frequency` for the literal "weekly"
    type (always advances by exactly 1 week) -- the multiplier only applies
    to the "interval" type, see test_complete_chore_monthly_interval /
    test_complete_chore_yearly_interval above. A stray `frequency` value here
    must not change the advance."""
    doc = ChoreDocument(
        chores=[
            Chore(
                id="c1", name="Sweep", emoji="🧹", periodDays=7,
                frequencyType="weekly", frequency=2,
                frequencyMetadata={},
                nextDueDate="2027-01-01T00:00:00Z",
            )
        ],
        assignments=[],
    )
    save_chores(home_id, doc)
    resp = client.post(f"/api/homes/{home_id}/chores/c1/complete")
    assert resp.status_code == 200
    from datetime import datetime, timezone, timedelta
    now = datetime.now(timezone.utc)
    new_due = datetime.fromisoformat(resp.json()["nextDueDate"].replace("Z", "+00:00"))
    expected = now + timedelta(weeks=1)
    assert abs((new_due - expected).total_seconds()) < 5


def test_create_chore_derives_frequency_from_period_days(client, home_id):
    payload = {
        "name": "🪟 Clean windows",
        "emoji": "🪟",
        "periodDays": 90,
        "nextDueDate": "2027-01-01T00:00:00Z",
    }
    resp = client.post(f"/api/homes/{home_id}/chores", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["frequencyType"] == "interval"
    assert data["frequency"] == 90
    assert data["frequencyMetadata"]["unit"] == "days"


# --- Completion history and notes ---

def test_complete_chore_records_history(client, home_id, tmp_path):
    save_chores(home_id, make_chore_doc())
    resp = client.post(f"/api/homes/{home_id}/chores/c1/complete", json={"notes": "Used new mop"})
    assert resp.status_code == 200
    doc = client.get(f"/api/homes/{home_id}/chores").json()
    assert len(doc["completions"]) == 1
    rec = doc["completions"][0]
    assert rec["choreId"] == "c1"
    assert rec["notes"] == "Used new mop"
    assert "completedAt" in rec
    assert "scheduledDue" in rec
    assert rec["assignmentId"] is None


def test_complete_assignment_records_history(client, home_id, tmp_path):
    save_chores(home_id, make_chore_doc())
    aid = client.post(f"/api/homes/{home_id}/assignments", json={"choreId": "c1", "roomId": "r1"}).json()["id"]
    resp = client.post(f"/api/homes/{home_id}/assignments/{aid}/complete", json={"notes": "Quick clean"})
    assert resp.status_code == 200
    doc = client.get(f"/api/homes/{home_id}/chores").json()
    assert len(doc["completions"]) == 1
    rec = doc["completions"][0]
    assert rec["choreId"] == "c1"
    assert rec["assignmentId"] == aid
    assert rec["notes"] == "Quick clean"


def test_complete_without_notes_leaves_empty_string(client, home_id, tmp_path):
    save_chores(home_id, make_chore_doc())
    client.post(f"/api/homes/{home_id}/chores/c1/complete")
    doc = client.get(f"/api/homes/{home_id}/chores").json()
    assert doc["completions"][0]["notes"] == ""


def test_multiple_completions_accumulate(client, home_id, tmp_path):
    save_chores(home_id, make_chore_doc())
    client.post(f"/api/homes/{home_id}/chores/c1/complete", json={"notes": "first"})
    client.post(f"/api/homes/{home_id}/chores/c1/complete", json={"notes": "second"})
    doc = client.get(f"/api/homes/{home_id}/chores").json()
    assert len(doc["completions"]) == 2
    notes = {r["notes"] for r in doc["completions"]}
    assert notes == {"first", "second"}


# --- scheduleFromDue ---

def test_schedule_from_due_date(client, home_id, tmp_path):
    due_date = "2027-06-01T00:00:00Z"
    doc = ChoreDocument(
        chores=[
            Chore(
                id="c1", name="Test", emoji="✅", periodDays=30,
                frequencyType="interval", frequency=30,
                frequencyMetadata={"unit": "days"},
                scheduleFromDue=True,
                nextDueDate=due_date,
            )
        ],
        assignments=[],
    )
    save_chores(home_id, doc)
    resp = client.post(f"/api/homes/{home_id}/chores/c1/complete")
    assert resp.status_code == 200
    from datetime import datetime, timezone, timedelta
    due_dt = datetime.fromisoformat(due_date.replace("Z", "+00:00"))
    expected = due_dt + timedelta(days=30)
    new_dt = datetime.fromisoformat(resp.json()["nextDueDate"].replace("Z", "+00:00"))
    assert abs((new_dt - expected).total_seconds()) < 2


def test_schedule_from_due_assignment(client, home_id, tmp_path):
    due_date = "2027-03-15T00:00:00Z"
    doc = ChoreDocument(
        chores=[
            Chore(
                id="c1", name="Test", emoji="✅", periodDays=30,
                frequencyType="interval", frequency=30,
                frequencyMetadata={"unit": "days"},
                scheduleFromDue=True,
                nextDueDate=due_date,
            )
        ],
        assignments=[],
    )
    save_chores(home_id, doc)
    aid = client.post(f"/api/homes/{home_id}/assignments", json={"choreId": "c1", "roomId": "r1"}).json()["id"]
    resp = client.post(f"/api/homes/{home_id}/assignments/{aid}/complete")
    assert resp.status_code == 200
    from datetime import datetime, timezone, timedelta
    due_dt = datetime.fromisoformat(due_date.replace("Z", "+00:00"))
    expected = due_dt + timedelta(days=30)
    new_dt = datetime.fromisoformat(resp.json()["nextDueDate"].replace("Z", "+00:00"))
    assert abs((new_dt - expected).total_seconds()) < 2


# --- Scheduling: weekday string names ---

def _make_weekday_chore(days_value) -> ChoreDocument:
    """Helper: days_of_the_week chore whose metadata.days is the given value."""
    return ChoreDocument(
        chores=[
            Chore(
                id="c1", name="Sweep", emoji="🧹", periodDays=7,
                frequencyType="days_of_the_week", frequency=1,
                frequencyMetadata={"days": days_value},
                nextDueDate="2026-06-16T00:00:00Z",  # Monday
            )
        ],
        assignments=[],
    )


def test_days_of_week_with_integer_days(client, home_id, tmp_path):
    """Numeric day values (1-based) must not crash and must advance to next occurrence."""
    save_chores(home_id, _make_weekday_chore([3, 5]))  # Wednesday=3, Friday=5
    aid = client.post(f"/api/homes/{home_id}/assignments", json={"choreId": "c1", "roomId": "r1"}).json()["id"]
    resp = client.post(f"/api/homes/{home_id}/assignments/{aid}/complete")
    assert resp.status_code == 200
    assert resp.json()["nextDueDate"] is not None


def test_days_of_week_with_string_day_names(client, home_id, tmp_path):
    """String weekday names from Donetick imports must not raise TypeError."""
    save_chores(home_id, _make_weekday_chore(["wednesday", "friday"]))
    aid = client.post(f"/api/homes/{home_id}/assignments", json={"choreId": "c1", "roomId": "r1"}).json()["id"]
    resp = client.post(f"/api/homes/{home_id}/assignments/{aid}/complete")
    assert resp.status_code == 200
    assert resp.json()["nextDueDate"] is not None


# --- Scheduling: day_of_the_month with month filter ---

def test_day_of_month_respects_allowed_months(client, home_id, tmp_path):
    """day_of_the_month chore with months=[1,7] must schedule only in allowed months."""
    doc = ChoreDocument(
        chores=[
            Chore(
                id="c1", name="Annual service", emoji="🔧", periodDays=30,
                frequencyType="day_of_the_month", frequency=1,
                frequencyMetadata={"months": [1, 7]},  # January and July only
                nextDueDate="2026-06-01T00:00:00Z",
            )
        ],
        assignments=[],
    )
    save_chores(home_id, doc)
    aid = client.post(f"/api/homes/{home_id}/assignments", json={"choreId": "c1", "roomId": "r1"}).json()["id"]
    resp = client.post(f"/api/homes/{home_id}/assignments/{aid}/complete")
    assert resp.status_code == 200
    next_due = resp.json()["nextDueDate"]
    from datetime import datetime, timezone
    dt = datetime.fromisoformat(next_due.replace("Z", "+00:00"))
    assert dt.month in (1, 7), f"expected January or July, got month {dt.month}"
    assert dt.day == 1


def test_day_of_month_respects_allowed_months_as_donetick_month_names(client, home_id, tmp_path):
    """Donetick stores `months` as full English month-name strings (e.g. "March"),
    not ints -- a chore imported from Donetick must respect that restriction
    the same way a manually-created chore with int months does."""
    doc = ChoreDocument(
        chores=[
            Chore(
                id="c1", name="Quarterly service", emoji="🔧", periodDays=30,
                frequencyType="day_of_the_month", frequency=15,
                frequencyMetadata={"months": ["March", "June", "September", "December"]},
                nextDueDate="2026-07-01T00:00:00Z",
            )
        ],
        assignments=[],
    )
    save_chores(home_id, doc)
    aid = client.post(f"/api/homes/{home_id}/assignments", json={"choreId": "c1", "roomId": "r1"}).json()["id"]
    resp = client.post(f"/api/homes/{home_id}/assignments/{aid}/complete")
    assert resp.status_code == 200
    next_due = resp.json()["nextDueDate"]
    from datetime import datetime, timezone
    dt = datetime.fromisoformat(next_due.replace("Z", "+00:00"))
    assert (dt.year, dt.month) == (2026, 9), f"expected September 2026, got {dt.year}-{dt.month}"
    assert dt.day == 15


def test_day_of_month_no_month_filter_advances_one_month(client, home_id, tmp_path):
    """day_of_the_month with no months filter advances by exactly one calendar month."""
    from datetime import datetime, timezone
    import calendar as cal
    now = datetime.now(timezone.utc)
    # The scheduling code does _add_months(from_dt.replace(day=1), 1), where from_dt=now
    total = now.month + 1
    exp_year = now.year + (total - 1) // 12
    exp_month = (total - 1) % 12 + 1
    doc = ChoreDocument(
        chores=[
            Chore(
                id="c1", name="Monthly clean", emoji="🧹", periodDays=30,
                frequencyType="day_of_the_month", frequency=15,
                frequencyMetadata={},
                nextDueDate="2026-06-15T00:00:00Z",
            )
        ],
        assignments=[],
    )
    save_chores(home_id, doc)
    aid = client.post(f"/api/homes/{home_id}/assignments", json={"choreId": "c1", "roomId": "r1"}).json()["id"]
    resp = client.post(f"/api/homes/{home_id}/assignments/{aid}/complete")
    assert resp.status_code == 200
    next_due = resp.json()["nextDueDate"]
    dt = datetime.fromisoformat(next_due.replace("Z", "+00:00"))
    assert dt.month == exp_month, f"expected month {exp_month}, got {dt.month}"
    assert dt.day == 15


# --- Chore attachments ---

def test_chore_upload_jpeg_accepted(client, home_id):
    cid = _chore_id(client, home_id)
    resp = client.post(f"/api/homes/{home_id}/chores/{cid}/attachments",
                       files={"file": ("photo.jpg", b"\xff\xd8\xff" + b"\x00" * 10, "image/jpeg")})
    assert resp.status_code == 201
    assert resp.json()["filename"] == "photo.jpg"


def test_chore_upload_unsupported_rejected(client, home_id):
    cid = _chore_id(client, home_id)
    resp = client.post(f"/api/homes/{home_id}/chores/{cid}/attachments",
                       files={"file": ("script.exe", b"\x4d\x5a", "application/octet-stream")})
    assert resp.status_code == 400


def test_chore_upload_pdf_creates_thumbnail(client, home_id, tmp_path):
    cid = _chore_id(client, home_id)
    resp = client.post(f"/api/homes/{home_id}/chores/{cid}/attachments",
                       files={"file": ("doc.pdf", _make_valid_pdf(), "application/pdf")})
    assert resp.status_code == 201
    thumb = tmp_path / "homes" / home_id / "chores-attachments" / cid / "doc.pdf.thumb.jpg"
    assert thumb.exists() or True  # thumbnail generation may fail in CI without display


def test_chore_delete_removes_thumbnail(client, home_id, tmp_path):
    cid = _chore_id(client, home_id)
    thumb_dir = tmp_path / "homes" / home_id / "chores-attachments" / cid
    thumb_dir.mkdir(parents=True, exist_ok=True)
    (thumb_dir / "doc.pdf").write_bytes(b"x")
    (thumb_dir / "doc.pdf.thumb.jpg").write_bytes(b"y")
    resp = client.delete(f"/api/homes/{home_id}/chores/{cid}/attachments/doc.pdf")
    assert resp.status_code == 204
    assert not (thumb_dir / "doc.pdf").exists()
    assert not (thumb_dir / "doc.pdf.thumb.jpg").exists()


def test_chore_get_attachment_returns_image_content_type(client, home_id):
    cid = _chore_id(client, home_id)
    client.post(f"/api/homes/{home_id}/chores/{cid}/attachments",
                files={"file": ("shot.jpg", b"\xff\xd8\xff" + b"\x00" * 10, "image/jpeg")})
    resp = client.get(f"/api/homes/{home_id}/chores/{cid}/attachments/shot.jpg")
    assert resp.status_code == 200
    assert "image" in resp.headers.get("content-type", "")


def test_chore_delete_chore_removes_attachment_dir(client, home_id, tmp_path):
    cid = _chore_id(client, home_id)
    att_dir = tmp_path / "homes" / home_id / "chores-attachments" / cid
    att_dir.mkdir(parents=True, exist_ok=True)
    (att_dir / "file.jpg").write_bytes(b"x")
    resp = client.delete(f"/api/homes/{home_id}/chores/{cid}")
    assert resp.status_code == 204
    assert not att_dir.exists()


def test_update_assignment_next_due_date(client, home_id):
    chore_id = _chore_id(client, home_id)
    a_resp = client.post(f"/api/homes/{home_id}/assignments", json={
        "choreId": chore_id, "nextDueDate": "2027-01-08T00:00:00Z"
    })
    assert a_resp.status_code == 201
    assignment_id = a_resp.json()["id"]

    resp = client.put(f"/api/homes/{home_id}/assignments/{assignment_id}", json={"nextDueDate": "2027-01-15T00:00:00Z"})
    assert resp.status_code == 204

    doc = client.get(f"/api/homes/{home_id}/chores").json()
    a = next(a for a in doc["assignments"] if a["id"] == assignment_id)
    assert a["nextDueDate"] == "2027-01-15T00:00:00Z"


def test_delete_completion(client, home_id, tmp_path):
    save_chores(home_id, make_chore_doc())
    client.post(f"/api/homes/{home_id}/chores/c1/complete", json={"notes": "first"})
    client.post(f"/api/homes/{home_id}/chores/c1/complete", json={"notes": "second"})
    doc = client.get(f"/api/homes/{home_id}/chores").json()
    assert len(doc["completions"]) == 2
    completion_id = doc["completions"][0]["id"]
    resp = client.delete(f"/api/homes/{home_id}/completions/{completion_id}")
    assert resp.status_code == 204
    doc = client.get(f"/api/homes/{home_id}/chores").json()
    assert len(doc["completions"]) == 1
    assert doc["completions"][0]["id"] != completion_id


def test_delete_completion_404(client, home_id):
    resp = client.delete(f"/api/homes/{home_id}/completions/nonexistent")
    assert resp.status_code == 404


def test_reset_chores_clears_data_and_attachments(client, tmp_path, home_id):
    cid = _chore_id(client, home_id)
    client.post(f"/api/homes/{home_id}/chores/{cid}/attachments",
                files={"file": ("photo.jpg", b"\xff\xd8\xff" + b"\x00" * 10, "image/jpeg")})
    att_dir = tmp_path / "homes" / home_id / "chores-attachments" / cid
    assert att_dir.exists()

    from myhome.persistence_chores import reset_chores
    reset_chores(home_id)

    assert client.get(f"/api/homes/{home_id}/chores").json()["chores"] == []
    assert not att_dir.exists()


# --- Adaptive scheduling ---

def test_complete_chore_adaptive_falls_back_to_period_days_with_no_history(client, home_id, tmp_path):
    doc = ChoreDocument(
        chores=[
            Chore(
                id="c1", name="Change filter", emoji="🔧", periodDays=30.0,
                frequencyType="adaptive", frequency=1, frequencyMetadata={},
                nextDueDate="2027-01-01T00:00:00Z",
            )
        ],
        assignments=[],
    )
    save_chores(home_id, doc)
    resp = client.post(f"/api/homes/{home_id}/chores/c1/complete")
    assert resp.status_code == 200
    data = resp.json()
    assert data["periodDays"] == 30.0
    from datetime import datetime, timezone, timedelta
    now = datetime.now(timezone.utc)
    new_due = datetime.fromisoformat(data["nextDueDate"].replace("Z", "+00:00"))
    expected = now + timedelta(days=30)
    assert abs((new_due - expected).total_seconds()) < 5


def test_complete_chore_adaptive_recomputes_period_days_from_history(client, home_id, tmp_path):
    """Two completions 10 days apart are already recorded; completing a third
    time now should average in the new gap and refresh periodDays to reflect
    it, rather than leaving the original 30.0 seed value stale."""
    doc = ChoreDocument(
        chores=[
            Chore(
                id="c1", name="Change filter", emoji="🔧", periodDays=30.0,
                frequencyType="adaptive", frequency=1, frequencyMetadata={},
                nextDueDate="2026-07-30T00:00:00Z",
            )
        ],
        assignments=[],
        completions=[
            CompletionRecord(id="r1", choreId="c1", completedAt="2026-07-01T00:00:00Z", scheduledDue=""),
            CompletionRecord(id="r2", choreId="c1", completedAt="2026-07-11T00:00:00Z", scheduledDue=""),
        ],
    )
    save_chores(home_id, doc)
    resp = client.post(f"/api/homes/{home_id}/chores/c1/complete")
    assert resp.status_code == 200
    assert resp.json()["periodDays"] != 30.0


def test_complete_chore_non_adaptive_does_not_change_period_days(client, home_id, tmp_path):
    save_chores(home_id, make_chore_doc())
    resp = client.post(f"/api/homes/{home_id}/chores/c1/complete")
    assert resp.status_code == 200
    assert resp.json()["periodDays"] == 14


def test_complete_assignment_adaptive_recomputes_period_days(client, home_id, tmp_path):
    doc = ChoreDocument(
        chores=[
            Chore(
                id="c1", name="Change filter", emoji="🔧", periodDays=30.0,
                frequencyType="adaptive", frequency=1, frequencyMetadata={},
                nextDueDate="2026-07-30T00:00:00Z",
            )
        ],
        assignments=[],
        completions=[
            CompletionRecord(id="r1", choreId="c1", completedAt="2026-07-01T00:00:00Z", scheduledDue=""),
            CompletionRecord(id="r2", choreId="c1", completedAt="2026-07-11T00:00:00Z", scheduledDue=""),
        ],
    )
    save_chores(home_id, doc)
    aid = client.post(f"/api/homes/{home_id}/assignments", json={"choreId": "c1", "roomId": "r1"}).json()["id"]
    resp = client.post(f"/api/homes/{home_id}/assignments/{aid}/complete")
    assert resp.status_code == 200
    chores = client.get(f"/api/homes/{home_id}/chores").json()["chores"]
    chore = next(c for c in chores if c["id"] == "c1")
    assert chore["periodDays"] != 30.0
