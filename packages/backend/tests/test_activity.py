from myhome.persistence_activity import describe
from myhome.models_activity import ActivityEntry


def test_describe_build_task_created():
    entry = ActivityEntry(
        id="e1", timestamp="2026-01-01T00:00:00+00:00", userId="u1", username="admin",
        module="build", action="create", entityLabel="Foundation Pour", refId="t1",
    )
    assert describe(entry) == "added build task 'Foundation Pour'"
