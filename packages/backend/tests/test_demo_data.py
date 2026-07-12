import random

from myhome.demo_geometry import generate_demo_house
from myhome.demo_data import generate_demo_chores


def test_generate_demo_chores_has_at_least_32_chores():
    house = generate_demo_house()
    doc = generate_demo_chores(house, random.Random(42))
    assert len(doc.chores) >= 32


def test_generate_demo_chores_assignments_reference_valid_rooms():
    house = generate_demo_house()
    doc = generate_demo_chores(house, random.Random(42))
    room_ids = {r.id for f in house.floors for r in f.rooms}
    chore_ids = {c.id for c in doc.chores}
    assert len(doc.assignments) > 0
    for a in doc.assignments:
        assert a.choreId in chore_ids
        assert a.roomId in room_ids


def test_generate_demo_chores_has_some_overdue_and_some_upcoming():
    from datetime import datetime, timezone
    house = generate_demo_house()
    doc = generate_demo_chores(house, random.Random(42))
    now = datetime.now(timezone.utc)
    due_dates = [datetime.fromisoformat(c.nextDueDate) for c in doc.chores]
    assert any(d < now for d in due_dates)
    assert any(d >= now for d in due_dates)


def test_generate_demo_chores_completions_reference_valid_chores():
    chore_ids_seen = set()
    house = generate_demo_house()
    doc = generate_demo_chores(house, random.Random(42))
    chore_ids = {c.id for c in doc.chores}
    assert len(doc.completions) > 0
    for comp in doc.completions:
        assert comp.choreId in chore_ids
        chore_ids_seen.add(comp.choreId)


def test_generate_demo_chores_is_deterministic_for_a_given_seed():
    house = generate_demo_house()
    doc1 = generate_demo_chores(house, random.Random(7))
    doc2 = generate_demo_chores(house, random.Random(7))
    assert [c.name for c in doc1.chores] == [c.name for c in doc2.chores]
    assert [c.periodDays for c in doc1.chores] == [c.periodDays for c in doc2.chores]
    # Compare date (not full microsecond timestamp) since "now" is captured
    # independently by each call and ticks forward by a fraction of a second
    # between them -- the whole-day offset driven by the rng seed is what's
    # actually deterministic here.
    assert [c.nextDueDate[:10] for c in doc1.chores] == [c.nextDueDate[:10] for c in doc2.chores]
