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
