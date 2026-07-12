from __future__ import annotations

import random
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from .demo_content import (
    CHORES,
    CONSUMABLE_CATEGORY_ROOM_HINTS,
    CONSUMABLES,
    INVENTORY_CATEGORY_ROOM_HINTS,
    INVENTORY_ITEMS,
    KB_CLOSERS,
    KB_OPENERS,
    KB_TITLES,
    WORKS,
    generate_demo_settings,
)
from .demo_geometry import generate_demo_house, room_centroid
from . import (
    persistence,
    persistence_chores,
    persistence_consumables,
    persistence_costs,
    persistence_inventory,
    persistence_kb,
    persistence_settings,
    persistence_works,
)
from .models import HouseDocument, Room
from .models_chores import Assignment, ChoreDocument, Chore, CompletionRecord, Position
from .models_costs import CostEntry, CostsDocument
from .models_inventory import InventoryDocument, InventoryItem, InventoryPlacement, InventoryPosition
from .models_consumables import (
    Consumable,
    ConsumableDocument,
    ConsumablePlacement,
    ConsumablePosition,
    ConsumableTransaction,
)
from .models_kb import KBDocument, KBEntry
from .models_settings import SettingsDocument
from .models_works import Work, WorksDocument, WorkPlacement, WorkPosition


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


def generate_demo_works(house: HouseDocument, settings: SettingsDocument, rng: random.Random) -> WorksDocument:
    today = date.today()
    supplier_ids = [s.id for s in settings.suppliers]
    all_rooms = [(f.id, r) for f in house.floors for r in f.rooms]

    shuffled = WORKS[:]
    rng.shuffle(shuffled)
    done_count = round(len(shuffled) * 0.5)
    in_progress_count = round(len(shuffled) * 0.15)

    works: list[Work] = []
    for i, (title, category_id, (cost_min, cost_max)) in enumerate(shuffled):
        floor_id, room = rng.choice(all_rooms)
        cx, cy = room_centroid(room)
        placement = WorkPlacement(
            floorId=floor_id,
            position=WorkPosition(x=cx + rng.uniform(-0.8, 0.8), y=cy + rng.uniform(-0.8, 0.8)),
        )

        if i < done_count:
            status = "done"
            work_date = today - timedelta(days=rng.randint(10, 700))
            total_cost = round(rng.uniform(cost_min, cost_max), 2)
            supplier_id = rng.choice(supplier_ids)
        elif i < done_count + in_progress_count:
            status = "in_progress"
            work_date = today - timedelta(days=rng.randint(0, 30))
            total_cost = round(rng.uniform(cost_min, cost_max) * 0.5, 2)
            supplier_id = rng.choice(supplier_ids)
        else:
            status = "planned"
            work_date = today + timedelta(days=rng.randint(5, 180))
            total_cost = None
            supplier_id = None

        works.append(Work(
            id=str(uuid.uuid4()), title=title, status=status, categoryId=category_id,
            date=work_date.isoformat(), totalCost=total_cost, supplierId=supplier_id,
            placement=placement,
        ))

    return WorksDocument(works=works)


def generate_demo_kb(rng: random.Random) -> KBDocument:
    now = datetime.now(timezone.utc)
    entries: list[KBEntry] = []

    for title in KB_TITLES:
        created = now - timedelta(days=rng.randint(10, 400))
        updated = created + timedelta(days=rng.randint(0, max(1, (now - created).days)))
        content = f"## {title}\n\n{rng.choice(KB_OPENERS)}\n\n{rng.choice(KB_CLOSERS)}"
        entries.append(KBEntry(
            id=str(uuid.uuid4()), title=title, content=content,
            createdAt=created.isoformat(), updatedAt=updated.isoformat(),
        ))

    return KBDocument(entries=entries)


_CONSUMABLE_UNIT_BASELINE = {"L": 2.0, "kg": 2.0, "count": 8.0, "rolls": 6.0, "packs": 5.0}


def _consumable_quantities(unit: str, rng: random.Random) -> tuple[float, float]:
    baseline = _CONSUMABLE_UNIT_BASELINE.get(unit, 8.0)
    min_quantity = round(baseline * rng.uniform(0.2, 0.4), 1)
    quantity = round(min_quantity * rng.uniform(0.3, 3.0), 1)
    return quantity, min_quantity


def _build_consumable_transactions(consumable_id: str, final_quantity: float, rng: random.Random, now: datetime) -> list[ConsumableTransaction]:
    extra = round(rng.uniform(2, 8), 1)
    restocked_qty = round(final_quantity + extra, 1)
    restock_ts = now - timedelta(days=rng.randint(20, 60))
    use_ts = now - timedelta(days=rng.randint(1, 19))
    return [
        ConsumableTransaction(
            id=str(uuid.uuid4()), consumableId=consumable_id,
            delta=restocked_qty, quantityAfter=restocked_qty,
            note="Restocked", timestamp=restock_ts.isoformat(),
        ),
        ConsumableTransaction(
            id=str(uuid.uuid4()), consumableId=consumable_id,
            delta=round(final_quantity - restocked_qty, 1), quantityAfter=final_quantity,
            note="Used", timestamp=use_ts.isoformat(),
        ),
    ]


def generate_demo_consumables(house: HouseDocument, settings: SettingsDocument, rng: random.Random) -> ConsumableDocument:
    now = datetime.now(timezone.utc)
    consumables: list[Consumable] = []
    transactions: list[ConsumableTransaction] = []

    for name, emoji, category_id, unit in CONSUMABLES:
        hints = CONSUMABLE_CATEGORY_ROOM_HINTS.get(category_id, [])
        room_label = rng.choice(hints) if hints else house.floors[0].rooms[0].label
        room = _find_room(house, room_label)
        floor_id = _floor_id_for_room(house, room.id)
        quantity, min_quantity = _consumable_quantities(unit, rng)
        cx, cy = room_centroid(room)

        consumable = Consumable(
            id=str(uuid.uuid4()), name=name, emoji=emoji, unit=unit,
            quantity=quantity, minQuantity=min_quantity, categoryId=category_id,
            placement=ConsumablePlacement(
                floorId=floor_id, roomId=room.id,
                position=ConsumablePosition(x=cx + rng.uniform(-0.8, 0.8), y=cy + rng.uniform(-0.8, 0.8)),
            ),
        )
        consumables.append(consumable)
        transactions.extend(_build_consumable_transactions(consumable.id, quantity, rng, now))

    return ConsumableDocument(consumables=consumables, transactions=transactions)


# ChoreDocument, InventoryDocument, CostsDocument, WorksDocument are already
# imported (unaliased) by the generator functions added above.

_ASSETS_DIR = Path(__file__).parent / "demo_assets"


def _attach_placeholder(*, save_attachment, get_attachment_path, generate_pdf_thumbnail, home_id: str, record_id: str, src: Path, dest_name: str) -> None:
    data = src.read_bytes()
    save_attachment(home_id, record_id, dest_name, data)
    if dest_name.endswith(".pdf"):
        pdf_path = get_attachment_path(home_id, record_id, dest_name)
        thumb_path = pdf_path.with_name(pdf_path.name + ".thumb.jpg")
        generate_pdf_thumbnail(pdf_path, thumb_path)


def attach_demo_files(
    home_id: str,
    chores_doc: ChoreDocument,
    inventory_doc: InventoryDocument,
    costs_doc: CostsDocument,
    works_doc: WorksDocument,
    rng: random.Random,
) -> None:
    photo_files = [_ASSETS_DIR / "placeholder-photo-1.png", _ASSETS_DIR / "placeholder-photo-2.png"]

    chore_subset = rng.sample(chores_doc.chores, k=max(1, round(len(chores_doc.chores) * 0.3)))
    for chore in chore_subset:
        photo = rng.choice(photo_files)
        _attach_placeholder(
            save_attachment=persistence_chores.save_attachment,
            get_attachment_path=persistence_chores.get_attachment_path,
            generate_pdf_thumbnail=persistence_chores.generate_pdf_thumbnail,
            home_id=home_id, record_id=chore.id, src=photo, dest_name=photo.name,
        )
        chore.attachments.append(photo.name)

    inventory_subset = rng.sample(inventory_doc.items, k=max(1, round(len(inventory_doc.items) * 0.3)))
    manual = _ASSETS_DIR / "placeholder-manual.pdf"
    for item in inventory_subset:
        _attach_placeholder(
            save_attachment=persistence_inventory.save_attachment,
            get_attachment_path=persistence_inventory.get_attachment_path,
            generate_pdf_thumbnail=persistence_inventory.generate_pdf_thumbnail,
            home_id=home_id, record_id=item.id, src=manual, dest_name=manual.name,
        )
        item.attachments.append(manual.name)

    costs_subset = rng.sample(costs_doc.entries, k=max(1, round(len(costs_doc.entries) * 0.3)))
    receipt = _ASSETS_DIR / "placeholder-receipt.pdf"
    for entry in costs_subset:
        _attach_placeholder(
            save_attachment=persistence_costs.save_attachment,
            get_attachment_path=persistence_costs.get_attachment_path,
            generate_pdf_thumbnail=persistence_costs.generate_pdf_thumbnail,
            home_id=home_id, record_id=entry.id, src=receipt, dest_name=receipt.name,
        )
        entry.attachments.append(receipt.name)

    done_works = [w for w in works_doc.works if w.status == "done"]
    works_subset = rng.sample(done_works, k=max(1, round(len(done_works) * 0.3))) if done_works else []
    warranty = _ASSETS_DIR / "placeholder-warranty.pdf"
    for work in works_subset:
        _attach_placeholder(
            save_attachment=persistence_works.save_attachment,
            get_attachment_path=persistence_works.get_attachment_path,
            generate_pdf_thumbnail=persistence_works.generate_pdf_thumbnail,
            home_id=home_id, record_id=work.id, src=warranty, dest_name=warranty.name,
        )
        work.attachments.append(warranty.name)


def seed_demo_home(home_id: str) -> None:
    rng = random.Random()

    house = generate_demo_house()
    settings = generate_demo_settings()
    chores_doc = generate_demo_chores(house, rng)
    inventory_doc = generate_demo_inventory(house, settings, rng)
    costs_doc = generate_demo_costs(settings, rng)
    works_doc = generate_demo_works(house, settings, rng)
    kb_doc = generate_demo_kb(rng)
    consumables_doc = generate_demo_consumables(house, settings, rng)

    persistence_settings.save_settings(home_id, settings)
    persistence.save_house(home_id, house)
    persistence_chores.save_chores(home_id, chores_doc)
    persistence_inventory.save_inventory(home_id, inventory_doc)
    persistence_costs.save_costs(home_id, costs_doc)
    persistence_works.save_works(home_id, works_doc)
    for entry in kb_doc.entries:
        persistence_kb.save_entry(home_id, entry)
    persistence_consumables.save_consumables(home_id, consumables_doc)

    attach_demo_files(home_id, chores_doc, inventory_doc, costs_doc, works_doc, rng)
    persistence_chores.save_chores(home_id, chores_doc)
    persistence_inventory.save_inventory(home_id, inventory_doc)
    persistence_costs.save_costs(home_id, costs_doc)
    persistence_works.save_works(home_id, works_doc)
