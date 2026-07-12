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


from datetime import date

from myhome.demo_content import generate_demo_settings
from myhome.demo_data import generate_demo_inventory


def test_generate_demo_inventory_has_at_least_32_items():
    house = generate_demo_house()
    settings = generate_demo_settings()
    doc = generate_demo_inventory(house, settings, random.Random(42))
    assert len(doc.items) >= 32


def test_generate_demo_inventory_items_have_valid_category_and_placement():
    house = generate_demo_house()
    settings = generate_demo_settings()
    doc = generate_demo_inventory(house, settings, random.Random(42))
    category_ids = {c.id for c in settings.inventoryCategories}
    floor_ids = {f.id for f in house.floors}
    room_ids = {r.id for f in house.floors for r in f.rooms}
    for item in doc.items:
        assert item.category in category_ids
        assert item.placement is not None
        assert item.placement.floorId in floor_ids
        assert item.placement.roomId in room_ids
        assert item.purchasePrice > 0


def test_generate_demo_inventory_some_warranties_already_expired():
    house = generate_demo_house()
    settings = generate_demo_settings()
    doc = generate_demo_inventory(house, settings, random.Random(42))
    today = date.today().isoformat()
    expired = [i for i in doc.items if i.warrantyExpiryDate and i.warrantyExpiryDate < today]
    assert len(expired) > 0


from myhome.demo_data import generate_demo_costs


def test_generate_demo_costs_has_at_least_32_entries():
    settings = generate_demo_settings()
    doc = generate_demo_costs(settings, random.Random(42))
    assert len(doc.entries) >= 32


def test_generate_demo_costs_entries_reference_valid_categories_and_suppliers():
    settings = generate_demo_settings()
    doc = generate_demo_costs(settings, random.Random(42))
    category_ids = {c.id for c in settings.costCategories}
    supplier_ids = {s.id for s in settings.suppliers}
    for entry in doc.entries:
        assert entry.categoryId in category_ids
        assert entry.totalAmount > 0
        if entry.supplierId is not None:
            assert entry.supplierId in supplier_ids


def test_generate_demo_costs_spread_across_last_12_months():
    from datetime import date, timedelta
    settings = generate_demo_settings()
    doc = generate_demo_costs(settings, random.Random(42))
    cutoff = (date.today() - timedelta(days=370)).isoformat()
    assert all(e.date >= cutoff for e in doc.entries)
    assert len({e.date[:7] for e in doc.entries}) >= 6  # spans several distinct months


from myhome.demo_data import generate_demo_works


def test_generate_demo_works_has_at_least_32_entries():
    house = generate_demo_house()
    settings = generate_demo_settings()
    doc = generate_demo_works(house, settings, random.Random(42))
    assert len(doc.works) >= 32


def test_generate_demo_works_has_a_mix_of_statuses():
    house = generate_demo_house()
    settings = generate_demo_settings()
    doc = generate_demo_works(house, settings, random.Random(42))
    statuses = {w.status for w in doc.works}
    assert statuses == {"planned", "in_progress", "done"}
    done = [w for w in doc.works if w.status == "done"]
    assert all(w.totalCost is not None for w in done)
    planned = [w for w in doc.works if w.status == "planned"]
    assert all(w.totalCost is None for w in planned)


def test_generate_demo_works_reference_valid_categories_and_floors():
    house = generate_demo_house()
    settings = generate_demo_settings()
    doc = generate_demo_works(house, settings, random.Random(42))
    category_ids = {c.id for c in settings.workCategories}
    floor_ids = {f.id for f in house.floors}
    for w in doc.works:
        assert w.categoryId in category_ids
        assert w.placement is not None
        assert w.placement.floorId in floor_ids
