from datetime import datetime, timedelta, timezone

import respx
from httpx import Response

from myhome.notification_scheduler import check_and_send_digests
from myhome.persistence_notifications import load_notification_state
from myhome.persistence_settings import load_settings, save_settings


async def test_check_and_send_digests_skips_home_with_push_disabled(client, home_id):
    await check_and_send_digests(now=datetime.now(timezone.utc))
    state = load_notification_state(home_id)
    assert state.lastPushDigestDate is None


async def test_check_and_send_digests_sends_and_marks_date(client, home_id, monkeypatch):
    monkeypatch.setenv("SUPERVISOR_TOKEN", "test-token")
    doc = load_settings(home_id)
    doc.notifications.haPushEnabled = True
    doc.notifications.haNotifyService = "notify.mobile_app_pixel"
    doc.notifications.haPushTime = "08:00"
    save_settings(home_id, doc)
    client.post(f"/api/homes/{home_id}/consumables", json={"name": "Salt", "quantity": 0, "minQuantity": 1})

    now = datetime(2026, 7, 6, 9, 0, tzinfo=timezone.utc)
    with respx.mock:
        route = respx.post("http://supervisor/core/api/services/notify/mobile_app_pixel").mock(
            return_value=Response(200)
        )
        await check_and_send_digests(now=now)
        assert route.called

    state = load_notification_state(home_id)
    assert state.lastPushDigestDate == "2026-07-06"


async def test_check_and_send_digests_skips_before_configured_time(client, home_id, monkeypatch):
    monkeypatch.setenv("SUPERVISOR_TOKEN", "test-token")
    doc = load_settings(home_id)
    doc.notifications.haPushEnabled = True
    doc.notifications.haNotifyService = "notify.mobile_app_pixel"
    doc.notifications.haPushTime = "20:00"
    save_settings(home_id, doc)

    now = datetime(2026, 7, 6, 9, 0, tzinfo=timezone.utc)
    with respx.mock:
        route = respx.post("http://supervisor/core/api/services/notify/mobile_app_pixel").mock(
            return_value=Response(200)
        )
        await check_and_send_digests(now=now)
        assert not route.called
    assert load_notification_state(home_id).lastPushDigestDate is None


async def test_check_and_send_digests_does_not_mark_date_on_ha_failure(client, home_id, monkeypatch):
    monkeypatch.setenv("SUPERVISOR_TOKEN", "test-token")
    doc = load_settings(home_id)
    doc.notifications.haPushEnabled = True
    doc.notifications.haNotifyService = "notify.mobile_app_pixel"
    doc.notifications.haPushTime = "08:00"
    save_settings(home_id, doc)
    client.post(f"/api/homes/{home_id}/consumables", json={"name": "Salt", "quantity": 0, "minQuantity": 1})

    now = datetime(2026, 7, 6, 9, 0, tzinfo=timezone.utc)
    with respx.mock:
        respx.post("http://supervisor/core/api/services/notify/mobile_app_pixel").mock(
            return_value=Response(500)
        )
        await check_and_send_digests(now=now)
    assert load_notification_state(home_id).lastPushDigestDate is None


async def test_check_and_send_digests_skips_already_sent_today(client, home_id, monkeypatch):
    monkeypatch.setenv("SUPERVISOR_TOKEN", "test-token")
    doc = load_settings(home_id)
    doc.notifications.haPushEnabled = True
    doc.notifications.haNotifyService = "notify.mobile_app_pixel"
    doc.notifications.haPushTime = "08:00"
    save_settings(home_id, doc)
    client.post(f"/api/homes/{home_id}/consumables", json={"name": "Salt", "quantity": 0, "minQuantity": 1})

    now = datetime(2026, 7, 6, 9, 0, tzinfo=timezone.utc)
    with respx.mock:
        route = respx.post("http://supervisor/core/api/services/notify/mobile_app_pixel").mock(
            return_value=Response(200)
        )
        await check_and_send_digests(now=now)
        assert route.call_count == 1
        await check_and_send_digests(now=now + timedelta(hours=1))
        assert route.call_count == 1
