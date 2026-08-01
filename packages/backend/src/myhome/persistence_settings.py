# packages/backend/src/myhome/persistence_settings.py
from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from .db import get_engine
from .models_settings import (
    ConsumableCategory,
    CostCategory,
    CostCategoryPlacement,
    CostCategoryPosition,
    InventoryCategory,
    InsuranceCategory,
    NotificationSettings,
    Owner,
    SettingsDocument,
    Store,
    ContactType,
    WorkCategory,
    _default_cost_categories,
    _default_consumable_units,
    _default_inventory_categories,
    _default_work_categories,
    _default_contact_types,
    _default_insurance_categories,
)
from .schema import (
    consumable_categories as consumable_categories_table,
    cost_categories as cost_categories_table,
    inventory_categories as inventory_categories_table,
    owners as owners_table,
    settings as settings_table,
    contact_types as contact_types_table,
    stores as stores_table,
    work_categories as work_categories_table,
    insurance_categories as insurance_categories_table,
)


def load_settings(home_id: str) -> SettingsDocument:
    engine = get_engine()
    with engine.connect() as conn:
        row = conn.execute(select(settings_table).where(settings_table.c.home_id == home_id)).mappings().first()
        if row is None:
            return SettingsDocument(
                costCategories=_default_cost_categories(),
                inventoryCategories=_default_inventory_categories(),
                workCategories=_default_work_categories(),
                consumableUnits=_default_consumable_units(),
                contactTypes=_default_contact_types(),
                insuranceCategories=_default_insurance_categories(),
            )
        cost_rows = conn.execute(
            select(cost_categories_table).where(cost_categories_table.c.home_id == home_id)
            .order_by(cost_categories_table.c.order_index)
        ).mappings().all()
        inv_rows = conn.execute(
            select(inventory_categories_table).where(inventory_categories_table.c.home_id == home_id)
            .order_by(inventory_categories_table.c.order_index)
        ).mappings().all()
        work_rows = conn.execute(
            select(work_categories_table).where(work_categories_table.c.home_id == home_id)
            .order_by(work_categories_table.c.order_index)
        ).mappings().all()
        contact_type_rows = conn.execute(
            select(contact_types_table).where(contact_types_table.c.home_id == home_id)
            .order_by(contact_types_table.c.order_index)
        ).mappings().all()
        consumable_cat_rows = conn.execute(
            select(consumable_categories_table).where(consumable_categories_table.c.home_id == home_id)
            .order_by(consumable_categories_table.c.order_index)
        ).mappings().all()
        insurance_cat_rows = conn.execute(
            select(insurance_categories_table).where(insurance_categories_table.c.home_id == home_id)
            .order_by(insurance_categories_table.c.order_index)
        ).mappings().all()
        owner_rows = conn.execute(
            select(owners_table).where(owners_table.c.home_id == home_id)
            .order_by(owners_table.c.order_index)
        ).mappings().all()
        store_rows = conn.execute(
            select(stores_table).where(stores_table.c.home_id == home_id)
            .order_by(stores_table.c.order_index)
        ).mappings().all()

    return SettingsDocument(
        costCategories=[
            CostCategory(
                id=r["id"], name=r["name"], emoji=r["emoji"], unit=r["unit"], color=r["color"],
                placement=(
                    CostCategoryPlacement(
                        floorId=r["placement_floor_id"],
                        position=CostCategoryPosition(x=r["placement_x"], y=r["placement_y"]),
                    )
                    if r["placement_floor_id"] is not None else None
                ),
            )
            for r in cost_rows
        ],
        inventoryCategories=[InventoryCategory(id=r["id"], name=r["name"]) for r in inv_rows],
        workCategories=[WorkCategory(id=r["id"], name=r["name"], emoji=r["emoji"]) for r in work_rows],
        contactTypes=[ContactType(id=r["id"], name=r["name"]) for r in contact_type_rows],
        consumableUnits=json.loads(row["consumable_units"]) or _default_consumable_units(),
        consumableCategories=[
            ConsumableCategory(id=r["id"], name=r["name"], emoji=r["emoji"]) for r in consumable_cat_rows
        ],
        insuranceCategories=[
            InsuranceCategory(id=r["id"], name=r["name"], emoji=r["emoji"]) for r in insurance_cat_rows
        ],
        owners=[Owner(id=r["id"], name=r["name"]) for r in owner_rows],
        stores=[Store(id=r["id"], name=r["name"]) for r in store_rows],
        notifications=NotificationSettings(
            enabled=bool(row["notif_enabled"]),
            choresDueSoonThreshold=row["notif_chores_due_soon_threshold"],
            warrantyDaysThreshold=row["notif_warranty_days_threshold"],
            haPushEnabled=bool(row["notif_ha_push_enabled"]),
            haNotifyService=row["notif_ha_notify_service"],
            haPushTime=row["notif_ha_push_time"],
        ),
    )


def save_settings(home_id: str, doc: SettingsDocument) -> None:
    engine = get_engine()
    with engine.begin() as conn:
        stmt = sqlite_insert(settings_table).values(
            home_id=home_id,
            consumable_units=json.dumps(doc.consumableUnits),
            notif_enabled=doc.notifications.enabled,
            notif_chores_due_soon_threshold=doc.notifications.choresDueSoonThreshold,
            notif_warranty_days_threshold=doc.notifications.warrantyDaysThreshold,
            notif_ha_push_enabled=doc.notifications.haPushEnabled,
            notif_ha_notify_service=doc.notifications.haNotifyService,
            notif_ha_push_time=doc.notifications.haPushTime,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=[settings_table.c.home_id],
            set_={
                "consumable_units": stmt.excluded.consumable_units,
                "notif_enabled": stmt.excluded.notif_enabled,
                "notif_chores_due_soon_threshold": stmt.excluded.notif_chores_due_soon_threshold,
                "notif_warranty_days_threshold": stmt.excluded.notif_warranty_days_threshold,
                "notif_ha_push_enabled": stmt.excluded.notif_ha_push_enabled,
                "notif_ha_notify_service": stmt.excluded.notif_ha_notify_service,
                "notif_ha_push_time": stmt.excluded.notif_ha_push_time,
            },
        )
        conn.execute(stmt)

        conn.execute(cost_categories_table.delete().where(cost_categories_table.c.home_id == home_id))
        if doc.costCategories:
            conn.execute(cost_categories_table.insert(), [
                {
                    "id": c.id, "home_id": home_id, "order_index": i, "name": c.name, "emoji": c.emoji,
                    "unit": c.unit, "color": c.color,
                    "placement_floor_id": c.placement.floorId if c.placement else None,
                    "placement_x": c.placement.position.x if c.placement else None,
                    "placement_y": c.placement.position.y if c.placement else None,
                }
                for i, c in enumerate(doc.costCategories)
            ])

        conn.execute(inventory_categories_table.delete().where(inventory_categories_table.c.home_id == home_id))
        if doc.inventoryCategories:
            conn.execute(inventory_categories_table.insert(), [
                {"id": c.id, "home_id": home_id, "order_index": i, "name": c.name}
                for i, c in enumerate(doc.inventoryCategories)
            ])

        conn.execute(work_categories_table.delete().where(work_categories_table.c.home_id == home_id))
        if doc.workCategories:
            conn.execute(work_categories_table.insert(), [
                {"id": c.id, "home_id": home_id, "order_index": i, "name": c.name, "emoji": c.emoji}
                for i, c in enumerate(doc.workCategories)
            ])

        conn.execute(contact_types_table.delete().where(contact_types_table.c.home_id == home_id))
        if doc.contactTypes:
            conn.execute(contact_types_table.insert(), [
                {"id": t.id, "home_id": home_id, "order_index": i, "name": t.name}
                for i, t in enumerate(doc.contactTypes)
            ])

        conn.execute(consumable_categories_table.delete().where(consumable_categories_table.c.home_id == home_id))
        if doc.consumableCategories:
            conn.execute(consumable_categories_table.insert(), [
                {"id": c.id, "home_id": home_id, "order_index": i, "name": c.name, "emoji": c.emoji}
                for i, c in enumerate(doc.consumableCategories)
            ])

        conn.execute(insurance_categories_table.delete().where(insurance_categories_table.c.home_id == home_id))
        if doc.insuranceCategories:
            conn.execute(insurance_categories_table.insert(), [
                {"id": c.id, "home_id": home_id, "order_index": i, "name": c.name, "emoji": c.emoji}
                for i, c in enumerate(doc.insuranceCategories)
            ])

        conn.execute(owners_table.delete().where(owners_table.c.home_id == home_id))
        if doc.owners:
            conn.execute(owners_table.insert(), [
                {"id": o.id, "home_id": home_id, "order_index": i, "name": o.name}
                for i, o in enumerate(doc.owners)
            ])

        conn.execute(stores_table.delete().where(stores_table.c.home_id == home_id))
        if doc.stores:
            conn.execute(stores_table.insert(), [
                {"id": s.id, "home_id": home_id, "order_index": i, "name": s.name}
                for i, s in enumerate(doc.stores)
            ])
