from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from ..deps import get_current_user_id
from ..build_template import seed_default_build
from ..models_build import (
    BuildDependencyCreate, BuildDocument, BuildPhaseUpdate, BuildProjectUpdate,
    BuildTask, BuildTaskCreate, BuildTaskDependency, BuildTaskUpdate,
)
from ..persistence_activity import log_activity
from ..persistence_build import (
    delete_all_attachments,
    delete_build_project,
    load_build,
    save_build,
)

router = APIRouter()


class _StartBuildBody(BuildProjectUpdate):
    pass


@router.get("/api/homes/{home_id}/build", response_model=BuildDocument)
def get_build(home_id: str) -> BuildDocument:
    return load_build(home_id)


@router.post("/api/homes/{home_id}/build/start", response_model=BuildDocument, status_code=201)
def start_build(
    home_id: str, body: _StartBuildBody,
    current_user_id: str = Depends(get_current_user_id),
) -> BuildDocument:
    existing = load_build(home_id)
    if existing.project is not None:
        raise HTTPException(status_code=409, detail="Build project already started")
    doc = seed_default_build(planned_start_date=body.plannedStartDate)
    save_build(home_id, doc)
    log_activity(home_id, current_user_id, "build", "create", "Build project", doc.project.id)
    return doc


@router.put("/api/homes/{home_id}/build/project", status_code=204)
def update_project(
    home_id: str, body: BuildProjectUpdate,
    current_user_id: str = Depends(get_current_user_id),
) -> None:
    doc = load_build(home_id)
    if doc.project is None:
        raise HTTPException(status_code=404)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(doc.project, field, value)
    doc.project.updatedAt = datetime.now(timezone.utc).isoformat()
    save_build(home_id, doc)
    log_activity(home_id, current_user_id, "build", "update", "Build project", doc.project.id)


@router.delete("/api/homes/{home_id}/build/project", status_code=204)
def delete_project(
    home_id: str,
    current_user_id: str = Depends(get_current_user_id),
) -> None:
    doc = load_build(home_id)
    if doc.project is None:
        raise HTTPException(status_code=404)
    delete_build_project(home_id)
    log_activity(home_id, current_user_id, "build", "delete", "Build project", doc.project.id)


@router.put("/api/homes/{home_id}/build/phases/{phase_id}", status_code=204)
def update_phase(
    home_id: str, phase_id: str, body: BuildPhaseUpdate,
    current_user_id: str = Depends(get_current_user_id),
) -> None:
    doc = load_build(home_id)
    phase = next((p for p in doc.phases if p.id == phase_id), None)
    if phase is None:
        raise HTTPException(status_code=404)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(phase, field, value)
    save_build(home_id, doc)
    log_activity(home_id, current_user_id, "build", "update", phase.nameOverride or phase.nameKey or "phase", phase_id)


@router.post("/api/homes/{home_id}/build/tasks", response_model=BuildTask, status_code=201)
def create_task(
    home_id: str, body: BuildTaskCreate,
    current_user_id: str = Depends(get_current_user_id),
) -> BuildTask:
    doc = load_build(home_id)
    if doc.project is None:
        raise HTTPException(status_code=404)
    if not any(p.id == body.phaseId for p in doc.phases):
        raise HTTPException(status_code=400, detail="Unknown phaseId")
    siblings = [t for t in doc.tasks if t.phaseId == body.phaseId]
    task = BuildTask(
        id=str(uuid.uuid4()), displayOrder=len(siblings),
        validationStatus="not_required", **body.model_dump(),
    )
    doc.tasks.append(task)
    save_build(home_id, doc)
    log_activity(home_id, current_user_id, "build", "create", task.titleOverride or "task", task.id)
    return task


@router.put("/api/homes/{home_id}/build/tasks/{task_id}", status_code=204)
def update_task(
    home_id: str, task_id: str, body: BuildTaskUpdate,
    current_user_id: str = Depends(get_current_user_id),
) -> None:
    doc = load_build(home_id)
    task = next((t for t in doc.tasks if t.id == task_id), None)
    if task is None:
        raise HTTPException(status_code=404)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(task, field, value)
    save_build(home_id, doc)
    log_activity(home_id, current_user_id, "build", "update", task.titleOverride or task.titleKey or "task", task_id)


@router.delete("/api/homes/{home_id}/build/tasks/{task_id}", status_code=204)
def delete_task(
    home_id: str, task_id: str,
    current_user_id: str = Depends(get_current_user_id),
) -> None:
    doc = load_build(home_id)
    task = next((t for t in doc.tasks if t.id == task_id), None)
    if task is None:
        raise HTTPException(status_code=404)
    doc.tasks = [t for t in doc.tasks if t.id != task_id]
    doc.dependencies = [
        d for d in doc.dependencies if d.predecessorTaskId != task_id and d.successorTaskId != task_id
    ]
    save_build(home_id, doc)
    delete_all_attachments(home_id, task_id)
    log_activity(home_id, current_user_id, "build", "delete", task.titleOverride or task.titleKey or "task", task_id)


@router.post("/api/homes/{home_id}/build/dependencies", response_model=BuildTaskDependency, status_code=201)
def create_dependency(
    home_id: str, body: BuildDependencyCreate,
    current_user_id: str = Depends(get_current_user_id),
) -> BuildTaskDependency:
    doc = load_build(home_id)
    task_ids = {t.id for t in doc.tasks}
    if body.predecessorTaskId not in task_ids or body.successorTaskId not in task_ids:
        raise HTTPException(status_code=400, detail="Unknown task id")
    dep = BuildTaskDependency(id=str(uuid.uuid4()), **body.model_dump())
    doc.dependencies.append(dep)
    save_build(home_id, doc)
    log_activity(home_id, current_user_id, "build", "create", "dependency", dep.id)
    return dep


@router.delete("/api/homes/{home_id}/build/dependencies/{dependency_id}", status_code=204)
def delete_dependency(
    home_id: str, dependency_id: str,
    current_user_id: str = Depends(get_current_user_id),
) -> None:
    doc = load_build(home_id)
    dep = next((d for d in doc.dependencies if d.id == dependency_id), None)
    if dep is None:
        raise HTTPException(status_code=404)
    doc.dependencies = [d for d in doc.dependencies if d.id != dependency_id]
    save_build(home_id, doc)
    log_activity(home_id, current_user_id, "build", "delete", "dependency", dependency_id)
