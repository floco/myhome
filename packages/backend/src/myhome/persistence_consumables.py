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
            initialQuantity=r["initial_quantity"],
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
                    "initial_quantity": c.initialQuantity,
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


def recompute_consumable_transactions(doc: ConsumableDocument, consumable_id: str) -> None:
    """Recompute delta/quantityAfter for one consumable's transactions in true
    chronological (date) order, and update its live quantity to match.

    Needed because transactions can be backdated -- a cost entry linked to a
    stock increase can carry any date -- so insertion order no longer matches
    chronological order. The running total must walk transactions oldest to
    newest rather than trusting whatever was computed at insertion time.

    Ground truth differs by transaction type:
    - Cost-linked transactions (costEntryId set): `delta` is ground truth
      (the quantity from the cost entry); `quantityAfter` is derived.
    - Manual stock updates (costEntryId is None): `quantityAfter` is ground
      truth (the absolute value the user set); `delta` is derived as the gap
      needed to reconcile with the true prior running total -- which also
      naturally captures real-world usage/loss between manual readings.

    Mutates `doc` in place; the caller is responsible for saving it.
    """
    item = next((c for c in doc.consumables if c.id == consumable_id), None)
    if item is None:
        return
    txs = sorted(
        (t for t in doc.transactions if t.consumableId == consumable_id),
        key=lambda t: t.timestamp,
    )
    running = item.initialQuantity
    for tx in txs:
        if tx.costEntryId is not None:
            running += tx.delta
            tx.quantityAfter = running
        else:
            tx.delta = tx.quantityAfter - running
            running = tx.quantityAfter
    item.quantity = running


def apply_cost_linked_delta(
    doc: ConsumableDocument, consumable_id: str, delta: float, note: str, cost_entry_id: str,
    timestamp: str | None = None,
) -> None:
    """Record a stock transaction on behalf of a linked cost entry.

    Mutates `doc` in place; the caller is responsible for saving it. Silently
    no-ops if the consumable no longer exists (e.g. deleted after linking).
    `timestamp` lets the caller backdate the transaction to the cost entry's
    own date instead of the moment it was saved -- defaults to now.
    """
    item = next((c for c in doc.consumables if c.id == consumable_id), None)
    if item is None:
        return
    doc.transactions.append(ConsumableTransaction(
        id=str(uuid.uuid4()), consumableId=consumable_id, delta=delta,
        quantityAfter=0.0, note=note,
        timestamp=timestamp or datetime.now(timezone.utc).isoformat(),
        costEntryId=cost_entry_id,
    ))
    recompute_consumable_transactions(doc, consumable_id)


def reverse_cost_linked_transactions(doc: ConsumableDocument, cost_entry_id: str) -> None:
    """Undo any stock transactions previously recorded for `cost_entry_id`.

    Mutates `doc` in place; the caller is responsible for saving it.
    """
    affected = {t.consumableId for t in doc.transactions if t.costEntryId == cost_entry_id}
    doc.transactions = [t for t in doc.transactions if t.costEntryId != cost_entry_id]
    for consumable_id in affected:
        recompute_consumable_transactions(doc, consumable_id)
