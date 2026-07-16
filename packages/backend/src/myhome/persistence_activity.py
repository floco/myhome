import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from .db import get_engine
from .models_activity import ActivityEntry, ActivityLogDocument
from .schema import activity_log_entries as activity_log_entries_table

RETENTION_DAYS = 90

ACTION_VERBS = {
    "create": "added", "update": "updated", "delete": "deleted", "complete": "completed",
    "restore": "restored", "delete_forever": "permanently deleted", "empty_trash": "emptied trash of",
}
MODULE_NOUNS = {
    "chores": "chore", "works": "work", "costs": "cost entry",
    "inventory": "inventory item", "consumables": "consumable", "kb": "KB article",
}


def load_activity_log(home_id: str) -> ActivityLogDocument:
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(
            select(activity_log_entries_table).where(activity_log_entries_table.c.home_id == home_id)
            .order_by(activity_log_entries_table.c.timestamp)
        ).mappings().all()
    return ActivityLogDocument(entries=[
        ActivityEntry(
            id=r["id"], timestamp=r["timestamp"], userId=r["user_id"], username=r["username"],
            module=r["module"], action=r["action"], entityLabel=r["entity_label"], refId=r["ref_id"],
        )
        for r in rows
    ])


def save_activity_log(home_id: str, doc: ActivityLogDocument) -> None:
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(activity_log_entries_table.delete().where(activity_log_entries_table.c.home_id == home_id))
        if doc.entries:
            conn.execute(activity_log_entries_table.insert(), [
                {
                    "id": e.id, "home_id": home_id, "timestamp": e.timestamp, "user_id": e.userId,
                    "username": e.username, "module": e.module, "action": e.action,
                    "entity_label": e.entityLabel, "ref_id": e.refId,
                }
                for e in doc.entries
            ])


def _resolve_username(user_id: str) -> str:
    from .persistence_auth import load_users
    user = next((u for u in load_users().users if u.id == user_id), None)
    return user.username if user else "unknown"


def log_activity(
    home_id: str, user_id: str, module: str, action: str,
    entity_label: str, ref_id: str | None = None,
) -> None:
    doc = load_activity_log(home_id)
    doc.entries.append(ActivityEntry(
        id=str(uuid.uuid4()),
        timestamp=datetime.now(timezone.utc).isoformat(),
        userId=user_id,
        username=_resolve_username(user_id),
        module=module,
        action=action,
        entityLabel=entity_label,
        refId=ref_id,
    ))
    cutoff = datetime.now(timezone.utc) - timedelta(days=RETENTION_DAYS)
    doc.entries = [e for e in doc.entries if datetime.fromisoformat(e.timestamp) >= cutoff]
    save_activity_log(home_id, doc)


def describe(entry: ActivityEntry) -> str:
    return f"{ACTION_VERBS[entry.action]} {MODULE_NOUNS[entry.module]} '{entry.entityLabel}'"
