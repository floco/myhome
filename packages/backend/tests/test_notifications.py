from datetime import datetime, timedelta, timezone

from myhome.models_chores import Assignment, Chore, ChoreDocument
from myhome.models_consumables import Consumable, ConsumableDocument
from myhome.models_inventory import InventoryDocument, InventoryItem
from myhome.models_notifications import NotificationState
from myhome.notifications import _chore_notifications, _low_stock_notifications, _warranty_notifications


def _iso_days_from_now(days: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")


def _iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def test_chore_notifications_includes_assignment_within_threshold():
    now = datetime.now(timezone.utc)
    doc = ChoreDocument(
        chores=[Chore(id="c1", name="Sweep", emoji="🧹", periodDays=10, nextDueDate=_iso(now))],
        assignments=[Assignment(id="a1", choreId="c1", nextDueDate=_iso(now + timedelta(days=2)))],
    )
    results = _chore_notifications(doc, threshold=0.25)
    assert len(results) == 1
    assert results[0].type == "chore"
    assert results[0].refId == "c1"
    assert results[0].severity == "warning"


def test_chore_notifications_excludes_assignment_outside_threshold():
    now = datetime.now(timezone.utc)
    doc = ChoreDocument(
        chores=[Chore(id="c1", name="Sweep", emoji="🧹", periodDays=10, nextDueDate=_iso(now))],
        assignments=[Assignment(id="a1", choreId="c1", nextDueDate=_iso(now + timedelta(days=9)))],
    )
    results = _chore_notifications(doc, threshold=0.25)
    assert results == []


def test_chore_notifications_marks_overdue_as_critical():
    now = datetime.now(timezone.utc)
    doc = ChoreDocument(
        chores=[Chore(id="c1", name="Sweep", emoji="🧹", periodDays=10, nextDueDate=_iso(now))],
        assignments=[Assignment(id="a1", choreId="c1", nextDueDate=_iso(now - timedelta(days=1)))],
    )
    results = _chore_notifications(doc, threshold=0.25)
    assert len(results) == 1
    assert results[0].severity == "critical"
    assert "overdue" in results[0].detail


def test_chore_notifications_dedupes_by_chore_keeping_most_urgent():
    now = datetime.now(timezone.utc)
    doc = ChoreDocument(
        chores=[Chore(id="c1", name="Sweep", emoji="🧹", periodDays=10, nextDueDate=_iso(now))],
        assignments=[
            Assignment(id="a1", choreId="c1", nextDueDate=_iso(now + timedelta(days=8))),
            Assignment(id="a2", choreId="c1", nextDueDate=_iso(now - timedelta(days=1))),
        ],
    )
    results = _chore_notifications(doc, threshold=0.25)
    assert len(results) == 1
    assert results[0].severity == "critical"


def test_low_stock_notifications_flags_low_and_empty_but_not_ok():
    doc = ConsumableDocument(consumables=[
        Consumable(id="co1", name="Soap", quantity=5, minQuantity=1),
        Consumable(id="co2", name="Salt", quantity=1, minQuantity=2),
        Consumable(id="co3", name="Sugar", quantity=0, minQuantity=1),
    ])
    results = _low_stock_notifications(doc)
    ids = {n.refId for n in results}
    assert ids == {"co2", "co3"}
    empty = next(n for n in results if n.refId == "co3")
    assert empty.severity == "critical"
    low = next(n for n in results if n.refId == "co2")
    assert low.severity == "warning"


def test_warranty_notifications_fires_once_then_suppresses():
    expiry = _iso_days_from_now(10)
    doc = InventoryDocument(items=[
        InventoryItem(id="i1", name="TV", warrantyExpiryDate=expiry),
    ])
    state = NotificationState()

    fired, new_state = _warranty_notifications(doc, days_threshold=30, state=state)
    assert len(fired) == 1
    assert fired[0].refId == "i1"
    assert new_state.warrantyNotified["i1"] == expiry

    fired_again, unchanged_state = _warranty_notifications(doc, days_threshold=30, state=new_state)
    assert fired_again == []
    assert unchanged_state == new_state


def test_warranty_notifications_refires_when_expiry_date_changes():
    doc = InventoryDocument(items=[
        InventoryItem(id="i1", name="TV", warrantyExpiryDate=_iso_days_from_now(10)),
    ])
    state = NotificationState(warrantyNotified={"i1": "2020-01-01T00:00:00Z"})
    fired, new_state = _warranty_notifications(doc, days_threshold=30, state=state)
    assert len(fired) == 1
    assert new_state.warrantyNotified["i1"] != "2020-01-01T00:00:00Z"


def test_warranty_notifications_ignores_items_outside_threshold():
    doc = InventoryDocument(items=[
        InventoryItem(id="i1", name="TV", warrantyExpiryDate=_iso_days_from_now(90)),
    ])
    fired, new_state = _warranty_notifications(doc, days_threshold=30, state=NotificationState())
    assert fired == []
    assert new_state == NotificationState()


def test_warranty_notifications_ignores_items_with_no_expiry_date():
    doc = InventoryDocument(items=[InventoryItem(id="i1", name="Ladder")])
    fired, new_state = _warranty_notifications(doc, days_threshold=30, state=NotificationState())
    assert fired == []


def test_get_notifications_route_combines_all_three_categories(client, home_id):
    chore = client.post(f"/api/homes/{home_id}/chores", json={
        "name": "Sweep", "emoji": "🧹", "periodDays": 10,
        "nextDueDate": (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }).json()
    client.post(f"/api/homes/{home_id}/assignments", json={
        "choreId": chore["id"],
        "nextDueDate": (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ"),
    })
    client.post(f"/api/homes/{home_id}/consumables", json={
        "name": "Salt", "quantity": 0, "minQuantity": 1,
    })
    client.post(f"/api/homes/{home_id}/inventory/items", json={
        "name": "TV", "warrantyExpiryDate": (datetime.now(timezone.utc) + timedelta(days=5)).strftime("%Y-%m-%dT%H:%M:%SZ"),
    })

    resp = client.get(f"/api/homes/{home_id}/notifications")
    assert resp.status_code == 200
    types = {n["type"] for n in resp.json()}
    assert types == {"chore", "low_stock", "warranty"}


def test_get_notifications_route_returns_empty_when_disabled(client, home_id):
    from myhome.persistence_settings import load_settings, save_settings
    doc = load_settings(home_id)
    doc.notifications.enabled = False
    save_settings(home_id, doc)

    client.post(f"/api/homes/{home_id}/consumables", json={"name": "Salt", "quantity": 0, "minQuantity": 1})
    resp = client.get(f"/api/homes/{home_id}/notifications")
    assert resp.json() == []


from myhome.models_build import BuildDocument, BuildPhase, BuildProject, BuildTask
from myhome.notifications import _build_notifications


def _make_build_doc(**task_kwargs) -> BuildDocument:
    project = BuildProject(id="p1", createdAt="2026-01-01T00:00:00+00:00", updatedAt="2026-01-01T00:00:00+00:00")
    phase = BuildPhase(id="ph1", displayOrder=0, nameKey="build.phases.planning.name")
    task = BuildTask(id="t1", phaseId="ph1", displayOrder=0, titleKey="build.tasks.siteSurvey.title", **task_kwargs)
    return BuildDocument(project=project, phases=[phase], tasks=[task])


def test_build_task_due_soon():
    doc = _make_build_doc(plannedDueDate=_iso_days_from_now(3))
    notifications, _ = _build_notifications(doc, threshold_days=7, state=NotificationState())
    assert any(n.type == "build_task_due" and n.severity == "warning" for n in notifications)


def test_build_task_overdue():
    doc = _make_build_doc(plannedDueDate=_iso_days_from_now(-2))
    notifications, _ = _build_notifications(doc, threshold_days=7, state=NotificationState())
    assert any(n.type == "build_task_due" and n.severity == "critical" for n in notifications)


def test_build_task_not_due_soon_excluded():
    doc = _make_build_doc(plannedDueDate=_iso_days_from_now(30))
    notifications, _ = _build_notifications(doc, threshold_days=7, state=NotificationState())
    assert not any(n.type == "build_task_due" for n in notifications)


def test_build_task_completed_excluded_even_if_overdue():
    doc = _make_build_doc(plannedDueDate=_iso_days_from_now(-2), status="completed")
    notifications, _ = _build_notifications(doc, threshold_days=7, state=NotificationState())
    assert not any(n.type == "build_task_due" for n in notifications)


def test_build_validation_pending():
    doc = _make_build_doc(validationRequired=True, validationStatus="pending_validation")
    notifications, _ = _build_notifications(doc, threshold_days=7, state=NotificationState())
    assert any(n.type == "build_validation" for n in notifications)


def test_build_validation_not_required_excluded():
    doc = _make_build_doc(validationRequired=False)
    notifications, _ = _build_notifications(doc, threshold_days=7, state=NotificationState())
    assert not any(n.type == "build_validation" for n in notifications)


def test_build_phase_complete_fires_once():
    project = BuildProject(id="p1", createdAt="2026-01-01T00:00:00+00:00", updatedAt="2026-01-01T00:00:00+00:00")
    phase = BuildPhase(id="ph1", displayOrder=0, nameKey="build.phases.planning.name", status="completed")
    doc = BuildDocument(project=project, phases=[phase], tasks=[])

    notifications1, state1 = _build_notifications(doc, threshold_days=7, state=NotificationState())
    assert any(n.type == "build_phase_complete" and n.refId == "ph1" for n in notifications1)
    assert "ph1" in state1.buildPhasesNotified

    notifications2, _ = _build_notifications(doc, threshold_days=7, state=state1)
    assert not any(n.type == "build_phase_complete" for n in notifications2)
