from datetime import datetime, timedelta, timezone

from myhome.models_property_search import PropertySearch, PropertySearchRun
from myhome.property_search_schedule import is_due, latest_slot, local_now

UTC = timezone.utc


def _s(**kw):
    base = dict(id="s1", name="n", prompt="p", createdAt="2026-11-01T00:00:00+00:00", time="08:00")
    base.update(kw)
    return PropertySearch(**base)


def _run(slot, status):
    return PropertySearchRun(id="r", searchId="s1", slot=slot, startedAt=slot, status=status)


def test_slot_before_creation_not_due():
    now = datetime(2026, 11, 8, 11, 0, tzinfo=UTC)
    s = _s(createdAt=datetime(2026, 11, 8, 10, 0, tzinfo=UTC).isoformat())
    assert latest_slot(s, now) is None
    assert is_due(s, [], now) == (False, None)


def test_daily_due_after_time():
    now = datetime(2026, 11, 8, 9, 0, tzinfo=UTC)
    due, slot = is_due(_s(), [], now)
    assert due is True and slot == datetime(2026, 11, 8, 8, 0, tzinfo=UTC).isoformat()


def test_daily_before_time_uses_yesterday_slot():
    now = datetime(2026, 11, 8, 7, 0, tzinfo=UTC)
    assert latest_slot(_s(), now) == datetime(2026, 11, 7, 8, 0, tzinfo=UTC)


def test_not_due_when_slot_succeeded():
    now = datetime(2026, 11, 8, 9, 0, tzinfo=UTC)
    slot = datetime(2026, 11, 8, 8, 0, tzinfo=UTC).isoformat()
    assert is_due(_s(), [_run(slot, "succeeded")], now) == (False, None)
    assert is_due(_s(), [_run(slot, "failed")], now) == (False, None)
    assert is_due(_s(), [_run(slot, "running")], now) == (False, None)


def test_usage_limited_retries_capped_at_3():
    now = datetime(2026, 11, 8, 9, 0, tzinfo=UTC)
    slot = datetime(2026, 11, 8, 8, 0, tzinfo=UTC).isoformat()
    assert is_due(_s(), [_run(slot, "usage_limited")] * 2, now)[0] is True
    assert is_due(_s(), [_run(slot, "usage_limited")] * 3, now) == (False, None)


def test_weekly_missed_slot_caught_up():
    # 2026-11-05 is a Thursday (isoweekday 4); now is Sunday 2026-11-08.
    now = datetime(2026, 11, 8, 9, 0, tzinfo=UTC)
    s = _s(frequency="weekly", dayOfWeek=4)
    due, slot = is_due(s, [], now)
    assert due is True and slot == datetime(2026, 11, 5, 8, 0, tzinfo=UTC).isoformat()


def test_monthly_slot():
    now = datetime(2026, 11, 20, 9, 0, tzinfo=UTC)
    s = _s(frequency="monthly", dayOfMonth=15)
    assert latest_slot(s, now) == datetime(2026, 11, 15, 8, 0, tzinfo=UTC)


def test_disabled_not_due():
    now = datetime(2026, 11, 8, 9, 0, tzinfo=UTC)
    assert is_due(_s(enabled=False), [], now) == (False, None)


def test_run_requested_overrides_disabled():
    now = datetime(2026, 11, 8, 9, 0, tzinfo=UTC)
    s = _s(enabled=False, runRequestedAt="2026-11-08T08:55:00+00:00")
    assert is_due(s, [], now) == (True, "manual:2026-11-08T08:55:00+00:00")


def test_run_requested_not_due_while_manual_running():
    now = datetime(2026, 11, 8, 9, 0, tzinfo=UTC)
    s = _s(runRequestedAt="2026-11-08T08:55:00+00:00")
    assert is_due(s, [_run("manual:2026-11-08T08:55:00+00:00", "running")], now) == (False, None)


def test_local_now_uses_tz_env(monkeypatch):
    monkeypatch.setenv("TZ", "Europe/Brussels")
    assert local_now().utcoffset() in (timedelta(hours=1), timedelta(hours=2))


def test_local_now_falls_back_to_utc(monkeypatch):
    monkeypatch.setenv("TZ", "Not/AZone")
    assert local_now().utcoffset() == timedelta(0)
    monkeypatch.delenv("TZ")
    assert local_now().utcoffset() == timedelta(0)


def test_stale_failed_run_is_retryable():
    now = datetime(2026, 11, 8, 9, 0, tzinfo=UTC)
    slot = datetime(2026, 11, 8, 8, 0, tzinfo=UTC).isoformat()
    stale = PropertySearchRun(id="r", searchId="s1", slot=slot, startedAt=slot, status="failed", error="stale: no result after 2 h")
    assert is_due(_s(), [stale], now)[0] is True
    assert is_due(_s(), [stale] * 3, now) == (False, None)
