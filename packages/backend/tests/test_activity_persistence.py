from myhome.models_activity import ActivityEntry, ActivityLogDocument


def test_activity_entry_requires_fields():
    entry = ActivityEntry(
        id="e1", timestamp="2026-07-08T12:00:00+00:00",
        userId="u1", username="alice",
        module="chores", action="complete", entityLabel="Sweep kitchen",
    )
    assert entry.refId is None


def test_activity_log_document_defaults_to_empty():
    assert ActivityLogDocument().entries == []


from datetime import datetime, timedelta, timezone

from myhome.models_auth import User, UserDocument
from myhome.persistence_activity import describe, load_activity_log, log_activity, save_activity_log
from myhome.persistence_auth import save_users


def _make_user(tmp_path, monkeypatch, user_id="u1", username="alice"):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    save_users(UserDocument(users=[
        User(id=user_id, username=username, role="admin", created_at="2026-01-01T00:00:00+00:00"),
    ]))


def test_log_activity_appends_entry_with_resolved_username(tmp_path, monkeypatch):
    _make_user(tmp_path, monkeypatch)
    log_activity("home-1", "u1", "chores", "complete", "Sweep kitchen", "chore-1")
    entries = load_activity_log("home-1").entries
    assert len(entries) == 1
    assert entries[0].username == "alice"
    assert entries[0].module == "chores"
    assert entries[0].action == "complete"
    assert entries[0].entityLabel == "Sweep kitchen"
    assert entries[0].refId == "chore-1"


def test_log_activity_resolves_unknown_user_gracefully(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    log_activity("home-1", "ghost", "works", "create", "Fix boiler")
    entries = load_activity_log("home-1").entries
    assert entries[0].username == "unknown"


def test_log_activity_prunes_entries_older_than_90_days(tmp_path, monkeypatch):
    _make_user(tmp_path, monkeypatch)
    old_timestamp = (datetime.now(timezone.utc) - timedelta(days=91)).isoformat()
    doc = load_activity_log("home-1")
    doc.entries = [
        ActivityEntry(
            id="old-1", timestamp=old_timestamp, userId="u1", username="alice",
            module="chores", action="create", entityLabel="Old chore",
        )
    ]
    save_activity_log("home-1", doc)

    log_activity("home-1", "u1", "chores", "create", "New chore")

    entries = load_activity_log("home-1").entries
    assert len(entries) == 1
    assert entries[0].entityLabel == "New chore"


def test_describe_builds_expected_sentence():
    entry = ActivityEntry(
        id="e1", timestamp="2026-07-08T12:00:00+00:00", userId="u1", username="alice",
        module="costs", action="create", entityLabel="Electricity",
    )
    assert describe(entry) == "added cost entry 'Electricity'"
