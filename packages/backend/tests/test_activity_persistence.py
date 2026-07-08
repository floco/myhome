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
