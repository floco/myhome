import json
from pathlib import Path

from sqlalchemy import select

from . import attachment_storage
from .attachment_storage import generate_pdf_thumbnail
from .db import get_engine
from .models_chores import Assignment, Chore, ChoreDocument, CompletionRecord, Position
from .schema import (
    chore_assignments as chore_assignments_table,
    chore_completions as chore_completions_table,
    chores as chores_table,
)

_MODULE = "chores"


def load_chores(home_id: str) -> ChoreDocument:
    engine = get_engine()
    with engine.connect() as conn:
        chore_rows = conn.execute(
            select(chores_table).where(chores_table.c.home_id == home_id).order_by(chores_table.c.order_index)
        ).mappings().all()
        assignment_rows = conn.execute(
            select(chore_assignments_table).where(chore_assignments_table.c.home_id == home_id)
            .order_by(chore_assignments_table.c.order_index)
        ).mappings().all()
        completion_rows = conn.execute(
            select(chore_completions_table).where(chore_completions_table.c.home_id == home_id)
            .order_by(chore_completions_table.c.order_index)
        ).mappings().all()

    chores = [
        Chore(
            id=r["id"], donetickId=r["donetick_id"], name=r["name"], emoji=r["emoji"],
            periodDays=r["period_days"], frequencyType=r["frequency_type"], frequency=r["frequency"],
            frequencyMetadata=json.loads(r["frequency_metadata"]), scheduleFromDue=bool(r["schedule_from_due"]),
            nextDueDate=r["next_due_date"], description=r["description"], attachments=json.loads(r["attachments"]),
        )
        for r in chore_rows
    ]
    assignments = [
        Assignment(
            id=r["id"], choreId=r["chore_id"], roomId=r["room_id"],
            position=Position(x=r["position_x"], y=r["position_y"]) if r["position_x"] is not None else None,
            nextDueDate=r["next_due_date"], label=r["label"],
        )
        for r in assignment_rows
    ]
    completions = [
        CompletionRecord(
            id=r["id"], choreId=r["chore_id"], assignmentId=r["assignment_id"],
            completedAt=r["completed_at"], scheduledDue=r["scheduled_due"], notes=r["notes"],
        )
        for r in completion_rows
    ]
    # Normalization 1: fill in missing assignment nextDueDates from parent chore.
    chore_map = {c.id: c for c in chores}
    for a in assignments:
        if not a.nextDueDate:
            parent = chore_map.get(a.choreId)
            a.nextDueDate = parent.nextDueDate if parent else ""
    # Normalization 2: fill in frequency fields for chores that only have periodDays.
    # Not just legacy-JSON compat -- callers can construct a Chore with just
    # periodDays (frequency/frequencyMetadata left at their Pydantic defaults)
    # and rely on this derivation happening on load.
    for c in chores:
        if c.frequencyType == "interval" and not c.frequencyMetadata:
            c.frequency = max(1, round(c.periodDays))
            c.frequencyMetadata = {"unit": "days"}
    return ChoreDocument(chores=chores, assignments=assignments, completions=completions)


def save_chores(home_id: str, doc: ChoreDocument) -> None:
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(chore_completions_table.delete().where(chore_completions_table.c.home_id == home_id))
        conn.execute(chore_assignments_table.delete().where(chore_assignments_table.c.home_id == home_id))
        conn.execute(chores_table.delete().where(chores_table.c.home_id == home_id))
        if doc.chores:
            conn.execute(chores_table.insert(), [
                {
                    "id": c.id, "home_id": home_id, "order_index": i, "donetick_id": c.donetickId,
                    "name": c.name, "emoji": c.emoji, "period_days": c.periodDays,
                    "frequency_type": c.frequencyType, "frequency": c.frequency,
                    "frequency_metadata": json.dumps(c.frequencyMetadata), "schedule_from_due": c.scheduleFromDue,
                    "next_due_date": c.nextDueDate, "description": c.description,
                    "attachments": json.dumps(c.attachments),
                }
                for i, c in enumerate(doc.chores)
            ])
        if doc.assignments:
            conn.execute(chore_assignments_table.insert(), [
                {
                    "id": a.id, "home_id": home_id, "order_index": i, "chore_id": a.choreId, "room_id": a.roomId,
                    "position_x": a.position.x if a.position else None,
                    "position_y": a.position.y if a.position else None,
                    "next_due_date": a.nextDueDate, "label": a.label,
                }
                for i, a in enumerate(doc.assignments)
            ])
        if doc.completions:
            conn.execute(chore_completions_table.insert(), [
                {
                    "id": c.id, "home_id": home_id, "order_index": i, "chore_id": c.choreId,
                    "assignment_id": c.assignmentId, "completed_at": c.completedAt,
                    "scheduled_due": c.scheduledDue, "notes": c.notes,
                }
                for i, c in enumerate(doc.completions)
            ])


def get_attachment_path(home_id: str, chore_id: str, filename: str) -> Path:
    return attachment_storage.get_attachment_path(home_id, _MODULE, chore_id, filename)


def save_attachment(home_id: str, chore_id: str, filename: str, data: bytes) -> None:
    attachment_storage.save_attachment(home_id, _MODULE, chore_id, filename, data)


def delete_attachment(home_id: str, chore_id: str, filename: str) -> bool:
    return attachment_storage.delete_attachment(home_id, _MODULE, chore_id, filename)


def delete_all_attachments(home_id: str, chore_id: str) -> None:
    attachment_storage.delete_all_attachments(home_id, _MODULE, chore_id)


def reset_chores(home_id: str) -> None:
    save_chores(home_id, ChoreDocument())
    attachment_storage.delete_all_module_attachments(home_id, _MODULE)
