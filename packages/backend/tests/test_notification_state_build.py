from myhome.models_notifications import Notification, NotificationState
from myhome.models_settings import NotificationSettings
from myhome.persistence_notifications import load_notification_state, save_notification_state

HOME_ID = "test-home"


def test_notification_settings_has_build_threshold():
    s = NotificationSettings()
    assert s.buildTaskDueSoonThreshold == 7


def test_notification_type_accepts_build_types():
    Notification(type="build_task_due", refId="t1", title="x", detail="y", severity="warning")
    Notification(type="build_validation", refId="t1", title="x", detail="y", severity="info")
    Notification(type="build_phase_complete", refId="ph1", title="x", detail="y", severity="info")


def test_notification_state_build_phases_notified_round_trip(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    (tmp_path / "homes" / HOME_ID).mkdir(parents=True)
    from myhome.db import get_engine
    from myhome.schema import homes as homes_table
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(homes_table.insert().values(
            id=HOME_ID, name="Test Home", type="project", created_at="2026-01-01T00:00:00+00:00",
        ))
    state = NotificationState(buildPhasesNotified=["ph1"])
    save_notification_state(HOME_ID, state)
    loaded = load_notification_state(HOME_ID)
    assert loaded.buildPhasesNotified == ["ph1"]
