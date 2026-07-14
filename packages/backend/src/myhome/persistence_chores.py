import json
import logging
import os
import shutil
from pathlib import Path

from sqlalchemy import select

from .db import get_engine
from .ids import InvalidIdError
from .models_chores import Assignment, Chore, ChoreDocument, CompletionRecord, Position
from .schema import (
    chore_assignments as chore_assignments_table,
    chore_completions as chore_completions_table,
    chores as chores_table,
)

_log = logging.getLogger(__name__)


def _home_dir(home_id: str) -> Path:
    # Normalize lexically (no filesystem access -- Path.resolve() follows
    # symlinks and touches disk, which CodeQL's own path-injection sink set
    # flags even before any check runs) then verify containment within
    # homes_root. This is CodeQL's own recommended py/path-injection
    # sanitizer shape: os.path.normpath + startswith against a safe root.
    homes_root = os.path.normpath(os.path.join(os.environ.get("DATA_DIR", "/data"), "homes"))
    candidate = os.path.normpath(os.path.join(homes_root, home_id))
    if not candidate.startswith(homes_root + os.sep):
        raise InvalidIdError(f"Invalid home_id: {home_id!r}")
    return Path(candidate)


def _attachments_dir(home_id: str, chore_id: str) -> Path:
    # Same inline lexical-normalize-then-verify-containment shape as
    # _home_dir() above -- chore_id is validated at the route layer too, but
    # CodeQL's taint tracker doesn't credit a separate validator function as
    # sanitizing the value used here.
    base = os.path.normpath(str(_home_dir(home_id) / "chores-attachments"))
    candidate = os.path.normpath(os.path.join(base, chore_id))
    if not candidate.startswith(base + os.sep):
        raise InvalidIdError(f"Invalid chore_id: {chore_id!r}")
    return Path(candidate)


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
            nextDueDate=r["next_due_date"],
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
                    "next_due_date": a.nextDueDate,
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
    base = os.path.normpath(str(_attachments_dir(home_id, chore_id)))
    candidate = os.path.normpath(os.path.join(base, filename))
    if not candidate.startswith(base + os.sep):
        raise InvalidIdError(f"Invalid filename: {filename!r}")
    return Path(candidate)


def save_attachment(home_id: str, chore_id: str, filename: str, data: bytes) -> None:
    path = _attachments_dir(home_id, chore_id)
    base = os.path.normpath(str(path))
    candidate = os.path.normpath(os.path.join(base, filename))
    if not candidate.startswith(base + os.sep):
        raise InvalidIdError(f"Invalid filename: {filename!r}")
    path.mkdir(parents=True, exist_ok=True)
    Path(candidate).write_bytes(data)


def delete_attachment(home_id: str, chore_id: str, filename: str) -> bool:
    base = os.path.normpath(str(_attachments_dir(home_id, chore_id)))
    candidate = os.path.normpath(os.path.join(base, filename))
    if not candidate.startswith(base + os.sep):
        raise InvalidIdError(f"Invalid filename: {filename!r}")
    path = Path(candidate)
    if not path.exists():
        return False
    path.unlink()
    thumb = path.with_name(path.name + ".thumb.jpg")
    if thumb.exists():
        thumb.unlink()
    return True


def delete_all_attachments(home_id: str, chore_id: str) -> None:
    att_dir = _attachments_dir(home_id, chore_id)
    if att_dir.exists():
        shutil.rmtree(att_dir)


def generate_pdf_thumbnail(pdf_path: Path, thumb_path: Path) -> None:
    try:
        import fitz
        doc = fitz.open(str(pdf_path))
        page = doc[0]
        mat = fitz.Matrix(1.5, 1.5)
        pix = page.get_pixmap(matrix=mat)
        pix.save(str(thumb_path))
    except Exception as exc:
        _log.warning("PDF thumbnail generation failed for %s: %s", pdf_path, exc)
