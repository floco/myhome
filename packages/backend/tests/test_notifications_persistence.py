from myhome.models_notifications import NotificationState
from myhome.persistence_notifications import load_notification_state, save_notification_state


def test_load_notification_state_returns_defaults_when_no_file(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    state = load_notification_state("home-1")
    assert state.warrantyNotified == {}
    assert state.lastPushDigestDate is None


def test_save_and_load_notification_state_round_trips(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    # notification_state FK-references homes.id (for cascade-delete-on-home-
    # delete), so a row must exist there before save_notification_state().
    from myhome.db import get_engine
    from myhome.schema import homes as homes_table
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(homes_table.insert().values(
            id="home-1", name="Test Home", type="existing", created_at="2026-01-01T00:00:00+00:00",
        ))
    save_notification_state("home-1", NotificationState(
        warrantyNotified={"item-1": "2026-08-01T00:00:00Z"},
        lastPushDigestDate="2026-07-06",
    ))
    state = load_notification_state("home-1")
    assert state.warrantyNotified == {"item-1": "2026-08-01T00:00:00Z"}
    assert state.lastPushDigestDate == "2026-07-06"
