# packages/backend/src/myhome/persistence_notifications.py
import json

from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from .db import get_engine
from .models_notifications import NotificationState
from .schema import notification_state as notification_state_table


def load_notification_state(home_id: str) -> NotificationState:
    engine = get_engine()
    with engine.connect() as conn:
        row = conn.execute(
            select(notification_state_table).where(notification_state_table.c.home_id == home_id)
        ).mappings().first()
    if row is None:
        return NotificationState()
    return NotificationState(
        warrantyNotified=json.loads(row["warranty_notified"]),
        buildPhasesNotified=json.loads(row["build_phases_notified"]),
        lastPushDigestDate=row["last_push_digest_date"],
    )


def save_notification_state(home_id: str, state: NotificationState) -> None:
    engine = get_engine()
    with engine.begin() as conn:
        stmt = sqlite_insert(notification_state_table).values(
            home_id=home_id, warranty_notified=json.dumps(state.warrantyNotified),
            build_phases_notified=json.dumps(state.buildPhasesNotified),
            last_push_digest_date=state.lastPushDigestDate,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=[notification_state_table.c.home_id],
            set_={
                "warranty_notified": stmt.excluded.warranty_notified,
                "build_phases_notified": stmt.excluded.build_phases_notified,
                "last_push_digest_date": stmt.excluded.last_push_digest_date,
            },
        )
        conn.execute(stmt)
