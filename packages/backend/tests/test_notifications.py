from datetime import datetime, timedelta, timezone

from myhome.models_chores import Assignment, Chore, ChoreDocument
from myhome.models_consumables import Consumable, ConsumableDocument
from myhome.notifications import _chore_notifications, _low_stock_notifications


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
