from __future__ import annotations

import json
import logging
import os
import shutil
from pathlib import Path

from sqlalchemy import select

from .db import get_engine
from .ids import InvalidIdError
from .models_build import BuildDocument, BuildPhase, BuildProject, BuildTask, BuildTaskDependency
from .schema import (
    build_phases as build_phases_table,
    build_projects as build_projects_table,
    build_task_dependencies as build_task_dependencies_table,
    build_tasks as build_tasks_table,
)

_log = logging.getLogger(__name__)


def _home_dir(home_id: str) -> Path:
    homes_root = os.path.normpath(os.path.join(os.environ.get("DATA_DIR", "/data"), "homes"))
    candidate = os.path.normpath(os.path.join(homes_root, home_id))
    if not candidate.startswith(homes_root + os.sep):
        raise InvalidIdError(f"Invalid home_id: {home_id!r}")
    return Path(candidate)


def _attachments_dir(home_id: str, task_id: str) -> Path:
    base = os.path.normpath(str(_home_dir(home_id) / "build-attachments"))
    candidate = os.path.normpath(os.path.join(base, task_id))
    if not candidate.startswith(base + os.sep):
        raise InvalidIdError(f"Invalid task_id: {task_id!r}")
    return Path(candidate)


def load_build(home_id: str) -> BuildDocument:
    engine = get_engine()
    with engine.connect() as conn:
        project_row = conn.execute(
            select(build_projects_table).where(build_projects_table.c.home_id == home_id)
        ).mappings().first()
        if project_row is None:
            return BuildDocument()

        project_id = project_row["id"]
        phase_rows = conn.execute(
            select(build_phases_table).where(build_phases_table.c.build_project_id == project_id)
            .order_by(build_phases_table.c.display_order)
        ).mappings().all()
        phase_ids = [r["id"] for r in phase_rows]

        task_rows = []
        if phase_ids:
            task_rows = conn.execute(
                select(build_tasks_table).where(build_tasks_table.c.phase_id.in_(phase_ids))
                .order_by(build_tasks_table.c.display_order)
            ).mappings().all()
        task_ids = [r["id"] for r in task_rows]

        dep_rows = []
        if task_ids:
            dep_rows = conn.execute(
                select(build_task_dependencies_table).where(
                    build_task_dependencies_table.c.successor_task_id.in_(task_ids)
                )
            ).mappings().all()

    project = BuildProject(
        id=project_row["id"], status=project_row["status"],
        plannedStartDate=project_row["planned_start_date"], plannedCompletionDate=project_row["planned_completion_date"],
        actualCompletionDate=project_row["actual_completion_date"], plannedBudget=project_row["planned_budget"],
        notes=project_row["notes"], createdAt=project_row["created_at"], updatedAt=project_row["updated_at"],
    )
    phases = [
        BuildPhase(
            id=r["id"], displayOrder=r["display_order"], nameKey=r["name_key"], nameOverride=r["name_override"],
            descriptionKey=r["description_key"], descriptionOverride=r["description_override"], status=r["status"],
            plannedStartDate=r["planned_start_date"], plannedEndDate=r["planned_end_date"],
            actualStartDate=r["actual_start_date"], actualEndDate=r["actual_end_date"],
        )
        for r in phase_rows
    ]
    tasks = [
        BuildTask(
            id=r["id"], phaseId=r["phase_id"], parentTaskId=r["parent_task_id"], displayOrder=r["display_order"],
            titleKey=r["title_key"], titleOverride=r["title_override"], descriptionKey=r["description_key"],
            descriptionOverride=r["description_override"], status=r["status"],
            plannedStartDate=r["planned_start_date"], plannedDueDate=r["planned_due_date"],
            actualCompletionDate=r["actual_completion_date"], plannedCost=r["planned_cost"], actualCost=r["actual_cost"],
            contractorId=r["contractor_id"], validationRequired=r["validation_required"],
            validationStatus=r["validation_status"], notes=r["notes"], attachments=json.loads(r["attachments"]),
        )
        for r in task_rows
    ]
    dependencies = [
        BuildTaskDependency(id=r["id"], predecessorTaskId=r["predecessor_task_id"], successorTaskId=r["successor_task_id"])
        for r in dep_rows
    ]
    return BuildDocument(project=project, phases=phases, tasks=tasks, dependencies=dependencies)


def save_build(home_id: str, doc: BuildDocument) -> None:
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(build_projects_table.delete().where(build_projects_table.c.home_id == home_id))
        if doc.project is None:
            return
        p = doc.project
        conn.execute(build_projects_table.insert(), {
            "id": p.id, "home_id": home_id, "status": p.status,
            "planned_start_date": p.plannedStartDate, "planned_completion_date": p.plannedCompletionDate,
            "actual_completion_date": p.actualCompletionDate, "planned_budget": p.plannedBudget,
            "notes": p.notes, "created_at": p.createdAt, "updated_at": p.updatedAt,
        })
        if doc.phases:
            conn.execute(build_phases_table.insert(), [
                {
                    "id": ph.id, "build_project_id": p.id, "display_order": ph.displayOrder,
                    "name_key": ph.nameKey, "name_override": ph.nameOverride,
                    "description_key": ph.descriptionKey, "description_override": ph.descriptionOverride,
                    "status": ph.status, "planned_start_date": ph.plannedStartDate, "planned_end_date": ph.plannedEndDate,
                    "actual_start_date": ph.actualStartDate, "actual_end_date": ph.actualEndDate,
                }
                for ph in doc.phases
            ])
        if doc.tasks:
            conn.execute(build_tasks_table.insert(), [
                {
                    "id": t.id, "phase_id": t.phaseId, "parent_task_id": t.parentTaskId, "display_order": t.displayOrder,
                    "title_key": t.titleKey, "title_override": t.titleOverride,
                    "description_key": t.descriptionKey, "description_override": t.descriptionOverride,
                    "status": t.status, "planned_start_date": t.plannedStartDate, "planned_due_date": t.plannedDueDate,
                    "actual_completion_date": t.actualCompletionDate, "planned_cost": t.plannedCost, "actual_cost": t.actualCost,
                    "contractor_id": t.contractorId, "validation_required": t.validationRequired,
                    "validation_status": t.validationStatus, "notes": t.notes, "attachments": json.dumps(t.attachments),
                }
                for t in doc.tasks
            ])
        if doc.dependencies:
            conn.execute(build_task_dependencies_table.insert(), [
                {"id": d.id, "predecessor_task_id": d.predecessorTaskId, "successor_task_id": d.successorTaskId}
                for d in doc.dependencies
            ])


def delete_build_project(home_id: str) -> None:
    save_build(home_id, BuildDocument())
    attachments_root = _home_dir(home_id) / "build-attachments"
    if attachments_root.exists():
        shutil.rmtree(attachments_root)


def get_attachment_path(home_id: str, task_id: str, filename: str) -> Path:
    base = os.path.normpath(str(_attachments_dir(home_id, task_id)))
    candidate = os.path.normpath(os.path.join(base, filename))
    if not candidate.startswith(base + os.sep):
        raise InvalidIdError(f"Invalid filename: {filename!r}")
    return Path(candidate)


def save_attachment(home_id: str, task_id: str, filename: str, data: bytes) -> None:
    path = _attachments_dir(home_id, task_id)
    base = os.path.normpath(str(path))
    candidate = os.path.normpath(os.path.join(base, filename))
    if not candidate.startswith(base + os.sep):
        raise InvalidIdError(f"Invalid filename: {filename!r}")
    path.mkdir(parents=True, exist_ok=True)
    Path(candidate).write_bytes(data)


def delete_attachment(home_id: str, task_id: str, filename: str) -> bool:
    base = os.path.normpath(str(_attachments_dir(home_id, task_id)))
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


def delete_all_attachments(home_id: str, task_id: str) -> None:
    path = _attachments_dir(home_id, task_id)
    if path.exists():
        shutil.rmtree(path)


def generate_pdf_thumbnail(pdf_path: Path, thumb_path: Path) -> None:
    try:
        import fitz  # pymupdf
        doc = fitz.open(str(pdf_path))
        page = doc[0]
        mat = fitz.Matrix(1.5, 1.5)
        pix = page.get_pixmap(matrix=mat)
        pix.save(str(thumb_path))
    except Exception as exc:
        _log.warning("PDF thumbnail generation failed for %s: %s", pdf_path, exc)
