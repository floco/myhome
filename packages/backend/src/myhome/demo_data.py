from __future__ import annotations

import random
import uuid
from datetime import date, datetime, timedelta, timezone

from .demo_content import CHORES, INVENTORY_CATEGORY_ROOM_HINTS, INVENTORY_ITEMS
from .demo_geometry import room_centroid
from .models import HouseDocument, Room
from .models_chores import Assignment, ChoreDocument, Chore, CompletionRecord, Position
from .models_costs import CostEntry, CostsDocument
from .models_inventory import InventoryDocument, InventoryItem, InventoryPlacement, InventoryPosition
from .models_settings import SettingsDocument


def _find_room(house: HouseDocument, label: str) -> Room:
    for floor in house.floors:
        for room in floor.rooms:
            if room.label == label:
                return room
    # Fall back to any room so a typo'd hint never crashes generation.
    return house.floors[0].rooms[0]


def _floor_id_for_room(house: HouseDocument, room_id: str) -> str:
    for floor in house.floors:
        if any(r.id == room_id for r in floor.rooms):
            return floor.id
    return house.floors[0].id


def _jittered_position(room: Room, rng: random.Random) -> Position:
    cx, cy = room_centroid(room)
    return Position(x=cx + rng.uniform(-0.8, 0.8), y=cy + rng.uniform(-0.8, 0.8))


def generate_demo_chores(house: HouseDocument, rng: random.Random) -> ChoreDocument:
    now = datetime.now(timezone.utc)
    chores: list[Chore] = []
    assignments: list[Assignment] = []
    completions: list[CompletionRecord] = []

    shuffled = CHORES[:]
    rng.shuffle(shuffled)
    overdue_count = round(len(shuffled) * 0.2)
    due_soon_count = round(len(shuffled) * 0.3)

    for i, (name, emoji, period_days, room_hint) in enumerate(shuffled):
        jitter = rng.uniform(0.8, 1.2)
        period = round(period_days * jitter, 1)

        if i < overdue_count:
            due = now - timedelta(days=rng.randint(1, 30))
        elif i < overdue_count + due_soon_count:
            due = now + timedelta(days=rng.randint(0, 7))
        else:
            due = now + timedelta(days=rng.randint(8, max(9, int(period))))

        chore = Chore(
            id=str(uuid.uuid4()),
            name=name,
            emoji=emoji,
            periodDays=period,
            frequency=max(1, round(period)),
            frequencyMetadata={"unit": "days"},
            nextDueDate=due.isoformat(),
        )
        chores.append(chore)

        for _ in range(rng.randint(0, 4)):
            completed_at = now - timedelta(days=rng.randint(1, 90))
            scheduled_due = completed_at - timedelta(days=rng.randint(0, 5))
            completions.append(CompletionRecord(
                id=str(uuid.uuid4()), choreId=chore.id,
                completedAt=completed_at.isoformat(),
                scheduledDue=scheduled_due.isoformat(),
            ))

        if i < 20:
            room = _find_room(house, room_hint)
            assignments.append(Assignment(
                id=str(uuid.uuid4()), choreId=chore.id, roomId=room.id,
                position=_jittered_position(room, rng), nextDueDate=due.isoformat(),
            ))

    return ChoreDocument(chores=chores, assignments=assignments, completions=completions)


def generate_demo_inventory(house: HouseDocument, settings: SettingsDocument, rng: random.Random) -> InventoryDocument:
    today = date.today()
    items: list[InventoryItem] = []

    for name, emoji, category_id, (price_min, price_max) in INVENTORY_ITEMS:
        hints = INVENTORY_CATEGORY_ROOM_HINTS.get(category_id, [])
        room_label = rng.choice(hints) if hints else house.floors[0].rooms[0].label
        room = _find_room(house, room_label)
        floor_id = _floor_id_for_room(house, room.id)

        purchase_days_ago = rng.randint(30, 5 * 365)
        purchase_date = today - timedelta(days=purchase_days_ago)
        warranty_days = rng.randint(365, 3 * 365)
        warranty_expiry = purchase_date + timedelta(days=warranty_days)
        cx, cy = room_centroid(room)

        items.append(InventoryItem(
            id=str(uuid.uuid4()),
            name=name,
            emoji=emoji,
            category=category_id,
            purchaseDate=purchase_date.isoformat(),
            purchasePrice=round(rng.uniform(price_min, price_max), 2),
            warrantyExpiryDate=warranty_expiry.isoformat(),
            placement=InventoryPlacement(
                floorId=floor_id, roomId=room.id,
                position=InventoryPosition(x=cx + rng.uniform(-0.8, 0.8), y=cy + rng.uniform(-0.8, 0.8)),
            ),
        ))

    return InventoryDocument(items=items)


def _months_ago(base: date, n: int) -> date:
    month_index = base.month - 1 - n
    year = base.year + month_index // 12
    month = month_index % 12 + 1
    day = min(base.day, 28)
    return date(year, month, day)


def generate_demo_costs(settings: SettingsDocument, rng: random.Random) -> CostsDocument:
    today = date.today()
    entries: list[CostEntry] = []
    supplier_ids = [s.id for s in settings.suppliers]

    for i in range(12):
        entries.append(CostEntry(
            id=str(uuid.uuid4()), categoryId="cat-mortgage",
            date=_months_ago(today, i).isoformat(),
            totalAmount=round(rng.uniform(1200, 1800), 2), notes="Monthly mortgage payment",
        ))
    for i in range(12):
        entries.append(CostEntry(
            id=str(uuid.uuid4()), categoryId="cat-electricity",
            date=_months_ago(today, i).isoformat(),
            totalAmount=round(rng.uniform(60, 180), 2), notes="Electricity bill",
        ))
    for i in range(4):
        entries.append(CostEntry(
            id=str(uuid.uuid4()), categoryId="cat-water",
            date=_months_ago(today, i * 3).isoformat(),
            totalAmount=round(rng.uniform(80, 150), 2), notes="Quarterly water bill",
        ))
    entries.append(CostEntry(
        id=str(uuid.uuid4()), categoryId="cat-insurance",
        date=(today - timedelta(days=rng.randint(30, 300))).isoformat(),
        totalAmount=round(rng.uniform(800, 1500), 2), notes="Annual home insurance premium",
    ))
    for note in ["Furnace repair", "Gutter cleaning", "Pest control treatment"]:
        entries.append(CostEntry(
            id=str(uuid.uuid4()), categoryId="cat-maintenance",
            date=(today - timedelta(days=rng.randint(1, 365))).isoformat(),
            totalAmount=round(rng.uniform(100, 600), 2), notes=note,
            supplierId=rng.choice(supplier_ids),
        ))
    for note in ["Streaming subscription bundle", "Home theater setup"]:
        entries.append(CostEntry(
            id=str(uuid.uuid4()), categoryId="cat-entertainment",
            date=(today - timedelta(days=rng.randint(1, 365))).isoformat(),
            totalAmount=round(rng.uniform(20, 150), 2), notes=note,
        ))
    entries.append(CostEntry(
        id=str(uuid.uuid4()), categoryId="cat-groceries",
        date=(today - timedelta(days=rng.randint(1, 365))).isoformat(),
        totalAmount=round(rng.uniform(300, 600), 2), notes="Monthly grocery restock",
    ))

    return CostsDocument(entries=entries)
