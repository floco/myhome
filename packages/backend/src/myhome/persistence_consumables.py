# packages/backend/src/myhome/persistence_consumables.py
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select

from .db import get_engine
from .models_consumables import (
    Consumable,
    ConsumableDocument,
    ConsumablePlacement,
    ConsumablePosition,
    ConsumableTransaction,
)
from .schema import consumable_transactions as consumable_transactions_table, consumables as consumables_table


def load_consumables(home_id: str) -> ConsumableDocument:
    engine = get_engine()
    with engine.connect() as conn:
        consumable_rows = conn.execute(
            select(consumables_table).where(consumables_table.c.home_id == home_id)
            .order_by(consumables_table.c.order_index)
        ).mappings().all()
        transaction_rows = conn.execute(
            select(consumable_transactions_table).where(consumable_transactions_table.c.home_id == home_id)
            .order_by(consumable_transactions_table.c.order_index)
        ).mappings().all()

    consumables = [
        Consumable(
            id=r["id"], name=r["name"], emoji=r["emoji"], unit=r["unit"], quantity=r["quantity"],
            minQuantity=r["min_quantity"], categoryId=r["category_id"], description=r["description"],
            placement=(
                ConsumablePlacement(
                    floorId=r["placement_floor_id"], roomId=r["placement_room_id"],
                    position=ConsumablePosition(x=r["placement_x"], y=r["placement_y"]),
                )
                if r["placement_floor_id"] is not None else None
            ),
        )
        for r in consumable_rows
    ]
    transactions = [
        ConsumableTransaction(
            id=r["id"], consumableId=r["consumable_id"], delta=r["delta"],
            quantityAfter=r["quantity_after"], note=r["note"], timestamp=r["timestamp"],
            costEntryId=r["cost_entry_id"],
        )
        for r in transaction_rows
    ]
    return ConsumableDocument(consumables=consumables, transactions=transactions)


def save_consumables(home_id: str, doc: ConsumableDocument) -> None:
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(consumable_transactions_table.delete().where(consumable_transactions_table.c.home_id == home_id))
        conn.execute(consumables_table.delete().where(consumables_table.c.home_id == home_id))
        if doc.consumables:
            conn.execute(consumables_table.insert(), [
                {
                    "id": c.id, "home_id": home_id, "order_index": i, "name": c.name, "emoji": c.emoji,
                    "unit": c.unit, "quantity": c.quantity, "min_quantity": c.minQuantity,
                    "category_id": c.categoryId, "description": c.description,
                    "placement_floor_id": c.placement.floorId if c.placement else None,
                    "placement_room_id": c.placement.roomId if c.placement else None,
                    "placement_x": c.placement.position.x if c.placement else None,
                    "placement_y": c.placement.position.y if c.placement else None,
                }
                for i, c in enumerate(doc.consumables)
            ])
        if doc.transactions:
            conn.execute(consumable_transactions_table.insert(), [
                {
                    "id": t.id, "home_id": home_id, "order_index": i, "consumable_id": t.consumableId,
                    "delta": t.delta, "quantity_after": t.quantityAfter, "note": t.note, "timestamp": t.timestamp,
                    "cost_entry_id": t.costEntryId,
                }
                for i, t in enumerate(doc.transactions)
            ])


def reset_consumables(home_id: str) -> None:
    save_consumables(home_id, ConsumableDocument())


def apply_cost_linked_delta(
    doc: ConsumableDocument, consumable_id: str, delta: float, note: str, cost_entry_id: str,
) -> None:
    """Record a stock transaction on behalf of a linked cost entry.

    Mutates `doc` in place; the caller is responsible for saving it. Silently
    no-ops if the consumable no longer exists (e.g. deleted after linking).
    """
    item = next((c for c in doc.consumables if c.id == consumable_id), None)
    if item is None:
        return
    item.quantity += delta
    doc.transactions.append(ConsumableTransaction(
        id=str(uuid.uuid4()), consumableId=consumable_id, delta=delta,
        quantityAfter=item.quantity, note=note, timestamp=datetime.now(timezone.utc).isoformat(),
        costEntryId=cost_entry_id,
    ))


def reverse_cost_linked_transactions(doc: ConsumableDocument, cost_entry_id: str) -> None:
    """Undo any stock transactions previously recorded for `cost_entry_id`.

    Mutates `doc` in place; the caller is responsible for saving it.
    """
    linked = [t for t in doc.transactions if t.costEntryId == cost_entry_id]
    for tx in linked:
        item = next((c for c in doc.consumables if c.id == tx.consumableId), None)
        if item is not None:
            item.quantity -= tx.delta
    doc.transactions = [t for t in doc.transactions if t.costEntryId != cost_entry_id]
