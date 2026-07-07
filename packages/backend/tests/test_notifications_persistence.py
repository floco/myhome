from myhome.models_notifications import NotificationState
from myhome.persistence_notifications import load_notification_state, save_notification_state


def test_load_notification_state_returns_defaults_when_no_file(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    state = load_notification_state("home-1")
    assert state.warrantyNotified == {}
    assert state.lastPushDigestDate is None


def test_save_and_load_notification_state_round_trips(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    save_notification_state("home-1", NotificationState(
        warrantyNotified={"item-1": "2026-08-01T00:00:00Z"},
        lastPushDigestDate="2026-07-06",
    ))
    state = load_notification_state("home-1")
    assert state.warrantyNotified == {"item-1": "2026-08-01T00:00:00Z"}
    assert state.lastPushDigestDate == "2026-07-06"
