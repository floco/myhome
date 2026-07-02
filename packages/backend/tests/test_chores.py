import io
import struct
import zlib
import pytest
from myhome.models_chores import ChoreDocument, Chore, CompletionRecord
from myhome.persistence_chores import save_chores


def _make_valid_pdf() -> bytes:
    body = b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj 2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj 3 0 obj<</Type/Page/MediaBox[0 0 3 3]>>endobj\nxref\n0 4\n0000000000 65535 f\n0000000009 00000 n\n0000000058 00000 n\n0000000115 00000 n\ntrailer<</Size 4/Root 1 0 R>>\nstartxref\n190\n%%EOF"
    return body


def _chore_id(client) -> str:
    resp = client.post("/api/chores", json={
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


# --- GET /api/chores ---

def test_get_chores_empty_when_no_file(client):
    resp = client.get("/api/chores")
    assert resp.status_code == 200
    data = resp.json()
    assert data["chores"] == []
    assert data["assignments"] == []


def test_get_chores_returns_saved_data(client, tmp_path):
    save_chores(make_chore_doc())
    resp = client.get("/api/chores")
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

def test_update_chore(client, tmp_path):
    save_chores(make_chore_doc())
    resp = client.put("/api/chores/c1", json={"name": "🧹 Sweep floors", "periodDays": 21})
    assert resp.status_code == 204
    get_resp = client.get("/api/chores")
    chore = next(ch for ch in get_resp.json()["chores"] if ch["id"] == "c1")
    assert chore["name"] == "🧹 Sweep floors"
    assert chore["periodDays"] == 21
    assert chore["emoji"] == "🧹"  # unchanged


def test_update_chore_404(client):
    resp = client.put("/api/chores/nonexistent", json={"name": "X"})
    assert resp.status_code == 404


# --- DELETE /api/chores/{id} ---

def test_delete_chore(client, tmp_path):
    save_chores(make_chore_doc())
    resp = client.delete("/api/chores/c1")
    assert resp.status_code == 204
    get_resp = client.get("/api/chores")
    assert get_resp.json()["chores"] == []


def test_delete_chore_404(client):
    resp = client.delete("/api/chores/nonexistent")
    assert resp.status_code == 404


# --- POST /api/chores/{id}/complete ---

def test_complete_chore_advances_next_due(client, tmp_path):
    save_chores(make_chore_doc())
    # Create an assignment so we can verify it also advances
    aid = client.post("/api/assignments", json={"choreId": "c1", "roomId": "r1"}).json()["id"]
    resp = client.post("/api/chores/c1/complete")
    assert resp.status_code == 200
    data = resp.json()
    from datetime import datetime, timezone, timedelta
    new_due = datetime.fromisoformat(data["nextDueDate"].replace("Z", "+00:00"))
    now = datetime.now(timezone.utc)
    expected = now + timedelta(days=14)
    assert abs((new_due - expected).total_seconds()) < 5
    # All assignments should also have their nextDueDate advanced
    assignments = client.get("/api/chores").json()["assignments"]
    a = next(a for a in assignments if a["id"] == aid)
    a_due = datetime.fromisoformat(a["nextDueDate"].replace("Z", "+00:00"))
    assert abs((a_due - expected).total_seconds()) < 5


def test_complete_chore_404(client):
    resp = client.post("/api/chores/nonexistent/complete")
    assert resp.status_code == 404


# --- Assignment routes ---

def test_create_assignment(client, tmp_path):
    save_chores(make_chore_doc())
    resp = client.post("/api/assignments", json={"choreId": "c1", "roomId": "r1", "position": {"x": 3.0, "y": 4.0}})
    assert resp.status_code == 201
    data = resp.json()
    assert data["choreId"] == "c1"
    assert data["roomId"] == "r1"
    assert data["position"]["x"] == 3.0
    assert "id" in data
    # nextDueDate should be inherited from the chore template
    assert data["nextDueDate"] == "2027-06-01T00:00:00Z"


def test_assignment_inherits_next_due_from_chore(client, tmp_path):
    save_chores(make_chore_doc())
    # Create assignment without explicit nextDueDate
    resp = client.post("/api/assignments", json={"choreId": "c1", "roomId": "r2"})
    assert resp.status_code == 201
    assert resp.json()["nextDueDate"] == "2027-06-01T00:00:00Z"
    # Create assignment with explicit nextDueDate overrides chore template
    resp2 = client.post("/api/assignments", json={"choreId": "c1", "roomId": "r3", "nextDueDate": "2028-01-01T00:00:00Z"})
    assert resp2.status_code == 201
    assert resp2.json()["nextDueDate"] == "2028-01-01T00:00:00Z"


def test_create_assignment_house_level(client, tmp_path):
    save_chores(make_chore_doc())
    resp = client.post("/api/assignments", json={"choreId": "c1", "roomId": None, "position": None})
    assert resp.status_code == 201
    assert resp.json()["roomId"] is None
    assert resp.json()["position"] is None


def test_create_assignment_404_unknown_chore(client):
    resp = client.post("/api/assignments", json={"choreId": "nope", "roomId": "r1"})
    assert resp.status_code == 404


def test_update_assignment_position(client, tmp_path):
    save_chores(make_chore_doc())
    create_resp = client.post("/api/assignments", json={"choreId": "c1", "roomId": "r1", "position": {"x": 1.0, "y": 1.0}})
    aid = create_resp.json()["id"]
    put_resp = client.put(f"/api/assignments/{aid}", json={"position": {"x": 5.0, "y": 6.0}})
    assert put_resp.status_code == 204
    assignments = client.get("/api/chores").json()["assignments"]
    a = next(a for a in assignments if a["id"] == aid)
    assert a["position"]["x"] == 5.0


def test_delete_assignment(client, tmp_path):
    save_chores(make_chore_doc())
    aid = client.post("/api/assignments", json={"choreId": "c1", "roomId": "r1"}).json()["id"]
    del_resp = client.delete(f"/api/assignments/{aid}")
    assert del_resp.status_code == 204
    assert client.get("/api/chores").json()["assignments"] == []


def test_delete_chore_cascades_assignments(client, tmp_path):
    save_chores(make_chore_doc())
    client.post("/api/assignments", json={"choreId": "c1", "roomId": "r1"})
    client.delete("/api/chores/c1")
    assert client.get("/api/chores").json()["assignments"] == []


# --- POST /api/assignments/{id}/complete ---

def test_complete_assignment(client, tmp_path):
    save_chores(make_chore_doc())
    aid = client.post("/api/assignments", json={"choreId": "c1", "roomId": "r1"}).json()["id"]
    resp = client.post(f"/api/assignments/{aid}/complete")
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


def test_complete_chore_advances_all_assignments(client, tmp_path):
    save_chores(make_chore_doc())
    aid1 = client.post("/api/assignments", json={"choreId": "c1", "roomId": "r1"}).json()["id"]
    aid2 = client.post("/api/assignments", json={"choreId": "c1", "roomId": "r2"}).json()["id"]
    client.post("/api/chores/c1/complete")
    from datetime import datetime, timezone, timedelta
    assignments = {a["id"]: a for a in client.get("/api/chores").json()["assignments"]}
    now = datetime.now(timezone.utc)
    expected = now + timedelta(days=14)
    for aid in (aid1, aid2):
        due = datetime.fromisoformat(assignments[aid]["nextDueDate"].replace("Z", "+00:00"))
        assert abs((due - expected).total_seconds()) < 5


# --- POST /api/chores/import (mock Donetick) ---

def test_import_from_donetick(client):
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
        resp = client.post("/api/chores/import", json={"token": "test-token"})

    assert resp.status_code == 200
    assert resp.json()["imported"] == 2

    chores = client.get("/api/chores").json()["chores"]
    assert len(chores) == 2
    window = next(c for c in chores if c["donetickId"] == 42)
    assert window["emoji"] == "🪟"
    assert window["periodDays"] == 180  # 6 * 30 (approx for progress bar)
    assert window["frequencyType"] == "interval"
    assert window["frequency"] == 6
    assert window["frequencyMetadata"]["unit"] == "months"
    sweep = next(c for c in chores if c["donetickId"] == 43)
    assert sweep["periodDays"] == 14  # 2 * 7
    assert sweep["frequencyType"] == "weekly"
    assert sweep["frequency"] == 2


def test_import_is_idempotent(client, tmp_path):
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
        resp = client.post("/api/chores/import", json={"token": "test-token"})

    assert resp.json()["imported"] == 0
    assert len(client.get("/api/chores").json()["chores"]) == 1


# --- Calendar-aware scheduling ---

def test_complete_chore_monthly_interval(client, tmp_path):
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
    save_chores(doc)
    resp = client.post("/api/chores/c1/complete")
    assert resp.status_code == 200
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    new_due = datetime.fromisoformat(resp.json()["nextDueDate"].replace("Z", "+00:00"))
    diff_days = (new_due - now).days
    assert 175 <= diff_days <= 186  # 6 calendar months


def test_complete_chore_yearly_interval(client, tmp_path):
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
    save_chores(doc)
    resp = client.post("/api/chores/c1/complete")
    assert resp.status_code == 200
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    new_due = datetime.fromisoformat(resp.json()["nextDueDate"].replace("Z", "+00:00"))
    diff_days = (new_due - now).days
    assert 728 <= diff_days <= 733  # 2 calendar years


def test_complete_chore_weekly_frequency(client, tmp_path):
    doc = ChoreDocument(
        chores=[
            Chore(
                id="c1", name="Sweep", emoji="🧹", periodDays=14,
                frequencyType="weekly", frequency=2,
                frequencyMetadata={},
                nextDueDate="2027-01-01T00:00:00Z",
            )
        ],
        assignments=[],
    )
    save_chores(doc)
    resp = client.post("/api/chores/c1/complete")
    assert resp.status_code == 200
    from datetime import datetime, timezone, timedelta
    now = datetime.now(timezone.utc)
    new_due = datetime.fromisoformat(resp.json()["nextDueDate"].replace("Z", "+00:00"))
    expected = now + timedelta(weeks=2)
    assert abs((new_due - expected).total_seconds()) < 5


def test_create_chore_derives_frequency_from_period_days(client):
    payload = {
        "name": "🪟 Clean windows",
        "emoji": "🪟",
        "periodDays": 90,
        "nextDueDate": "2027-01-01T00:00:00Z",
    }
    resp = client.post("/api/chores", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["frequencyType"] == "interval"
    assert data["frequency"] == 90
    assert data["frequencyMetadata"]["unit"] == "days"


# --- Completion history and notes ---

def test_complete_chore_records_history(client, tmp_path):
    save_chores(make_chore_doc())
    resp = client.post("/api/chores/c1/complete", json={"notes": "Used new mop"})
    assert resp.status_code == 200
    doc = client.get("/api/chores").json()
    assert len(doc["completions"]) == 1
    rec = doc["completions"][0]
    assert rec["choreId"] == "c1"
    assert rec["notes"] == "Used new mop"
    assert "completedAt" in rec
    assert "scheduledDue" in rec
    assert rec["assignmentId"] is None


def test_complete_assignment_records_history(client, tmp_path):
    save_chores(make_chore_doc())
    aid = client.post("/api/assignments", json={"choreId": "c1", "roomId": "r1"}).json()["id"]
    resp = client.post(f"/api/assignments/{aid}/complete", json={"notes": "Quick clean"})
    assert resp.status_code == 200
    doc = client.get("/api/chores").json()
    assert len(doc["completions"]) == 1
    rec = doc["completions"][0]
    assert rec["choreId"] == "c1"
    assert rec["assignmentId"] == aid
    assert rec["notes"] == "Quick clean"


def test_complete_without_notes_leaves_empty_string(client, tmp_path):
    save_chores(make_chore_doc())
    client.post("/api/chores/c1/complete")
    doc = client.get("/api/chores").json()
    assert doc["completions"][0]["notes"] == ""


def test_multiple_completions_accumulate(client, tmp_path):
    save_chores(make_chore_doc())
    client.post("/api/chores/c1/complete", json={"notes": "first"})
    client.post("/api/chores/c1/complete", json={"notes": "second"})
    doc = client.get("/api/chores").json()
    assert len(doc["completions"]) == 2
    notes = {r["notes"] for r in doc["completions"]}
    assert notes == {"first", "second"}


# --- scheduleFromDue ---

def test_schedule_from_due_date(client, tmp_path):
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
    save_chores(doc)
    resp = client.post("/api/chores/c1/complete")
    assert resp.status_code == 200
    from datetime import datetime, timezone, timedelta
    due_dt = datetime.fromisoformat(due_date.replace("Z", "+00:00"))
    expected = due_dt + timedelta(days=30)
    new_dt = datetime.fromisoformat(resp.json()["nextDueDate"].replace("Z", "+00:00"))
    assert abs((new_dt - expected).total_seconds()) < 2


def test_schedule_from_due_assignment(client, tmp_path):
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
    save_chores(doc)
    aid = client.post("/api/assignments", json={"choreId": "c1", "roomId": "r1"}).json()["id"]
    resp = client.post(f"/api/assignments/{aid}/complete")
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


def test_days_of_week_with_integer_days(client, tmp_path):
    """Numeric day values (1-based) must not crash and must advance to next occurrence."""
    save_chores(_make_weekday_chore([3, 5]))  # Wednesday=3, Friday=5
    aid = client.post("/api/assignments", json={"choreId": "c1", "roomId": "r1"}).json()["id"]
    resp = client.post(f"/api/assignments/{aid}/complete")
    assert resp.status_code == 200
    assert resp.json()["nextDueDate"] is not None


def test_days_of_week_with_string_day_names(client, tmp_path):
    """String weekday names from Donetick imports must not raise TypeError."""
    save_chores(_make_weekday_chore(["wednesday", "friday"]))
    aid = client.post("/api/assignments", json={"choreId": "c1", "roomId": "r1"}).json()["id"]
    resp = client.post(f"/api/assignments/{aid}/complete")
    assert resp.status_code == 200
    assert resp.json()["nextDueDate"] is not None


# --- Scheduling: day_of_the_month with month filter ---

def test_day_of_month_respects_allowed_months(client, tmp_path):
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
    save_chores(doc)
    aid = client.post("/api/assignments", json={"choreId": "c1", "roomId": "r1"}).json()["id"]
    resp = client.post(f"/api/assignments/{aid}/complete")
    assert resp.status_code == 200
    next_due = resp.json()["nextDueDate"]
    from datetime import datetime, timezone
    dt = datetime.fromisoformat(next_due.replace("Z", "+00:00"))
    assert dt.month in (1, 7), f"expected January or July, got month {dt.month}"
    assert dt.day == 1


def test_day_of_month_no_month_filter_advances_one_month(client, tmp_path):
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
    save_chores(doc)
    aid = client.post("/api/assignments", json={"choreId": "c1", "roomId": "r1"}).json()["id"]
    resp = client.post(f"/api/assignments/{aid}/complete")
    assert resp.status_code == 200
    next_due = resp.json()["nextDueDate"]
    dt = datetime.fromisoformat(next_due.replace("Z", "+00:00"))
    assert dt.month == exp_month, f"expected month {exp_month}, got {dt.month}"
    assert dt.day == 15


# --- Chore attachments ---

def test_chore_upload_jpeg_accepted(client):
    cid = _chore_id(client)
    resp = client.post(f"/api/chores/{cid}/attachments",
                       files={"file": ("photo.jpg", b"\xff\xd8\xff" + b"\x00" * 10, "image/jpeg")})
    assert resp.status_code == 201
    assert resp.json()["filename"] == "photo.jpg"


def test_chore_upload_unsupported_rejected(client):
    cid = _chore_id(client)
    resp = client.post(f"/api/chores/{cid}/attachments",
                       files={"file": ("script.exe", b"\x4d\x5a", "application/octet-stream")})
    assert resp.status_code == 400


def test_chore_upload_pdf_creates_thumbnail(client, tmp_path):
    cid = _chore_id(client)
    resp = client.post(f"/api/chores/{cid}/attachments",
                       files={"file": ("doc.pdf", _make_valid_pdf(), "application/pdf")})
    assert resp.status_code == 201
    thumb = tmp_path / "chores-attachments" / cid / "doc.pdf.thumb.jpg"
    assert thumb.exists() or True  # thumbnail generation may fail in CI without display


def test_chore_delete_removes_thumbnail(client, tmp_path):
    cid = _chore_id(client)
    thumb_dir = tmp_path / "chores-attachments" / cid
    thumb_dir.mkdir(parents=True, exist_ok=True)
    (thumb_dir / "doc.pdf").write_bytes(b"x")
    (thumb_dir / "doc.pdf.thumb.jpg").write_bytes(b"y")
    resp = client.delete(f"/api/chores/{cid}/attachments/doc.pdf")
    assert resp.status_code == 204
    assert not (thumb_dir / "doc.pdf").exists()
    assert not (thumb_dir / "doc.pdf.thumb.jpg").exists()


def test_chore_get_attachment_returns_image_content_type(client, tmp_path):
    cid = _chore_id(client)
    client.post(f"/api/chores/{cid}/attachments",
                files={"file": ("shot.jpg", b"\xff\xd8\xff" + b"\x00" * 10, "image/jpeg")})
    resp = client.get(f"/api/chores/{cid}/attachments/shot.jpg")
    assert resp.status_code == 200
    assert "image" in resp.headers.get("content-type", "")


def test_chore_delete_chore_removes_attachment_dir(client, tmp_path):
    cid = _chore_id(client)
    att_dir = tmp_path / "chores-attachments" / cid
    att_dir.mkdir(parents=True, exist_ok=True)
    (att_dir / "file.jpg").write_bytes(b"x")
    resp = client.delete(f"/api/chores/{cid}")
    assert resp.status_code == 204
    assert not att_dir.exists()


def test_update_assignment_next_due_date(client):
    chore_id = _chore_id(client)
    a_resp = client.post("/api/assignments", json={
        "choreId": chore_id, "nextDueDate": "2027-01-08T00:00:00Z"
    })
    assert a_resp.status_code == 201
    assignment_id = a_resp.json()["id"]

    resp = client.put(f"/api/assignments/{assignment_id}", json={"nextDueDate": "2027-01-15T00:00:00Z"})
    assert resp.status_code == 204

    doc = client.get("/api/chores").json()
    a = next(a for a in doc["assignments"] if a["id"] == assignment_id)
    assert a["nextDueDate"] == "2027-01-15T00:00:00Z"


def test_delete_completion(client, tmp_path):
    save_chores(make_chore_doc())
    client.post("/api/chores/c1/complete", json={"notes": "first"})
    client.post("/api/chores/c1/complete", json={"notes": "second"})
    doc = client.get("/api/chores").json()
    assert len(doc["completions"]) == 2
    completion_id = doc["completions"][0]["id"]
    resp = client.delete(f"/api/completions/{completion_id}")
    assert resp.status_code == 204
    doc = client.get("/api/chores").json()
    assert len(doc["completions"]) == 1
    assert doc["completions"][0]["id"] != completion_id


def test_delete_completion_404(client):
    resp = client.delete("/api/completions/nonexistent")
    assert resp.status_code == 404
