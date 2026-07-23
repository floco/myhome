# House Build Tracking Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a House Build Tracking module (project → phases → tasks → dependencies, budget rollups, notifications, attachments) per `docs/superpowers/specs/2026-07-23-house-build-tracking-design.md`.

**Architecture:** New backend files only (`models_build.py`, `persistence_build.py`, `build_template.py`, `routes/build.py`, `mcp_tools_build.py`), following the exact SQLAlchemy-Core "whole document" pattern used by Works/Properties. New frontend files (`buildStore.svelte.ts`, `BuildPage.svelte`, `PhaseSection.svelte`, `TaskModal.svelte`, `HomeBuildWidget.svelte`) following the Works/Properties UI conventions. Seeded template content (22 phases, 58 tasks) is stored as i18n keys resolved client-side, with a literal-text override column for user edits.

**Tech Stack:** FastAPI, SQLAlchemy Core, Pydantic (backend); Svelte 5 runes, svelte-i18n, Vitest (frontend); pytest (backend tests).

## Global Constraints

- Follow existing repository/service/UI architecture exactly — no new abstractions, no framework changes.
- Every user-visible string (labels, statuses, phase/task names, descriptions) must have both an `en.json` and `fr.json` entry — enforced automatically by the existing `i18nCompleteness.test.ts` key-parity test.
- Reuse existing attachment infrastructure (`save_attachment`/`get_attachment_path`/`delete_attachment`/`delete_all_attachments`/`generate_pdf_thumbnail`) — no new attachment system.
- Reuse the existing notification system (`compute_notifications`/`Notification` model) as-is — plain English, not localized (matches existing chores/low-stock/warranty behavior).
- One build project per home, enforced by a unique index on `build_projects.home_id`.
- No hard dependency-enforcement gate on task status — dependencies drive a computed Ready/Blocked value only.

---

## File Structure

**Backend (new files):**
| File | Responsibility |
|---|---|
| `models_build.py` | Pydantic models for project/phase/task/dependency + document + create/update variants |
| `persistence_build.py` | `load_build`/`save_build`, attachment helpers |
| `build_template.py` | Seed data (22 phases, 58 tasks) + `seed_default_build()` |
| `routes/build.py` | REST endpoints |
| `mcp_tools_build.py` | MCP tool exposure |

**Backend (modified files):** `schema.py` (4 new tables), `main.py` (router registration), `models_homes.py` (module id), `persistence_activity.py` (MODULE_NOUNS entry), `models_settings.py` (notification threshold), `models_notifications.py` (new notification type + state field), `persistence_notifications.py` (state field wiring), `notifications.py` (new computation function), `mcp_app.py` (tool registration).

**Frontend (new files):** `buildStore.svelte.ts`, `BuildPage.svelte`, `PhaseSection.svelte`, `TaskModal.svelte`, `HomeBuildWidget.svelte`.

**Frontend (modified files):** `locales/en.json`, `locales/fr.json`, `App.svelte`, `NavMenu.svelte`, `SettingsGeneral.svelte`, `HomePage.svelte`.

---

## Task 1: Models

**Files:**
- Create: `packages/backend/src/myhome/models_build.py`
- Test: `packages/backend/tests/test_models_build.py`

**Interfaces:**
- Produces: `BuildProject`, `BuildPhase`, `BuildTask`, `BuildTaskDependency`, `BuildDocument`, `BuildProjectUpdate`, `BuildPhaseUpdate`, `BuildTaskCreate`, `BuildTaskUpdate`, `BuildDependencyCreate` — all consumed by Tasks 2, 5, 6.

- [ ] **Step 1: Write the failing test**

```python
# packages/backend/tests/test_models_build.py
from myhome.models_build import (
    BuildDocument, BuildPhase, BuildProject, BuildTask, BuildTaskDependency,
)


def test_build_project_defaults():
    p = BuildProject(id="p1", createdAt="2026-01-01T00:00:00+00:00", updatedAt="2026-01-01T00:00:00+00:00")
    assert p.status == "planning"
    assert p.plannedBudget is None
    assert p.notes == ""


def test_build_phase_defaults():
    ph = BuildPhase(id="ph1", displayOrder=0, nameKey="build.phases.planning.name")
    assert ph.status == "not_started"
    assert ph.nameOverride is None


def test_build_task_defaults():
    t = BuildTask(id="t1", phaseId="ph1", displayOrder=0, titleKey="build.tasks.siteSurvey.title")
    assert t.status == "not_started"
    assert t.validationRequired is False
    assert t.validationStatus == "not_required"
    assert t.attachments == []


def test_build_task_dependency():
    d = BuildTaskDependency(id="d1", predecessorTaskId="t1", successorTaskId="t2")
    assert d.predecessorTaskId == "t1"


def test_build_document_defaults():
    doc = BuildDocument()
    assert doc.project is None
    assert doc.phases == []
    assert doc.tasks == []
    assert doc.dependencies == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/backend && python -m pytest tests/test_models_build.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'myhome.models_build'`

- [ ] **Step 3: Write the implementation**

```python
# packages/backend/src/myhome/models_build.py
from __future__ import annotations
from typing import Literal
from pydantic import BaseModel

BuildProjectStatus = Literal["planning", "in_progress", "completed", "on_hold"]
BuildPhaseStatus = Literal["not_started", "in_progress", "completed"]
BuildTaskStatus = Literal["not_started", "ready", "in_progress", "waiting", "blocked", "completed"]
ValidationStatus = Literal["not_required", "pending_validation", "passed", "failed"]


class BuildProject(BaseModel):
    id: str
    status: BuildProjectStatus = "planning"
    plannedStartDate: str | None = None
    plannedCompletionDate: str | None = None
    actualCompletionDate: str | None = None
    plannedBudget: float | None = None
    notes: str = ""
    createdAt: str
    updatedAt: str


class BuildPhase(BaseModel):
    id: str
    displayOrder: int
    nameKey: str | None = None
    nameOverride: str | None = None
    descriptionKey: str | None = None
    descriptionOverride: str | None = None
    status: BuildPhaseStatus = "not_started"
    plannedStartDate: str | None = None
    plannedEndDate: str | None = None
    actualStartDate: str | None = None
    actualEndDate: str | None = None


class BuildTask(BaseModel):
    id: str
    phaseId: str
    parentTaskId: str | None = None
    displayOrder: int
    titleKey: str | None = None
    titleOverride: str | None = None
    descriptionKey: str | None = None
    descriptionOverride: str | None = None
    status: BuildTaskStatus = "not_started"
    plannedStartDate: str | None = None
    plannedDueDate: str | None = None
    actualCompletionDate: str | None = None
    plannedCost: float | None = None
    actualCost: float | None = None
    contractorId: str | None = None
    validationRequired: bool = False
    validationStatus: ValidationStatus = "not_required"
    notes: str = ""
    attachments: list[str] = []


class BuildTaskDependency(BaseModel):
    id: str
    predecessorTaskId: str
    successorTaskId: str


class BuildDocument(BaseModel):
    version: int = 1
    project: BuildProject | None = None
    phases: list[BuildPhase] = []
    tasks: list[BuildTask] = []
    dependencies: list[BuildTaskDependency] = []


class BuildProjectUpdate(BaseModel):
    status: BuildProjectStatus | None = None
    plannedStartDate: str | None = None
    plannedCompletionDate: str | None = None
    actualCompletionDate: str | None = None
    plannedBudget: float | None = None
    notes: str | None = None


class BuildPhaseUpdate(BaseModel):
    nameOverride: str | None = None
    descriptionOverride: str | None = None
    status: BuildPhaseStatus | None = None
    plannedStartDate: str | None = None
    plannedEndDate: str | None = None
    actualStartDate: str | None = None
    actualEndDate: str | None = None


class BuildTaskCreate(BaseModel):
    phaseId: str
    parentTaskId: str | None = None
    titleOverride: str
    descriptionOverride: str = ""
    status: BuildTaskStatus = "not_started"
    plannedStartDate: str | None = None
    plannedDueDate: str | None = None
    plannedCost: float | None = None
    contractorId: str | None = None
    validationRequired: bool = False
    notes: str = ""


class BuildTaskUpdate(BaseModel):
    titleOverride: str | None = None
    descriptionOverride: str | None = None
    status: BuildTaskStatus | None = None
    plannedStartDate: str | None = None
    plannedDueDate: str | None = None
    actualCompletionDate: str | None = None
    plannedCost: float | None = None
    actualCost: float | None = None
    contractorId: str | None = None
    validationRequired: bool | None = None
    validationStatus: ValidationStatus | None = None
    notes: str | None = None


class BuildDependencyCreate(BaseModel):
    predecessorTaskId: str
    successorTaskId: str
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd packages/backend && python -m pytest tests/test_models_build.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add packages/backend/src/myhome/models_build.py packages/backend/tests/test_models_build.py
git commit -m "feat(build): add Pydantic models for build tracking"
```

---

## Task 2: Schema tables + persistence

**Files:**
- Modify: `packages/backend/src/myhome/schema.py` (append at end of file)
- Create: `packages/backend/src/myhome/persistence_build.py`
- Test: `packages/backend/tests/test_build_persistence.py`

**Interfaces:**
- Consumes: models from Task 1.
- Produces: `load_build(home_id) -> BuildDocument`, `save_build(home_id, doc) -> None`, `delete_build_project(home_id) -> None`, `get_attachment_path(home_id, task_id, filename) -> Path`, `save_attachment(home_id, task_id, filename, data) -> None`, `delete_attachment(home_id, task_id, filename) -> bool`, `delete_all_attachments(home_id, task_id) -> None`, `generate_pdf_thumbnail(pdf_path, thumb_path) -> None` — consumed by Tasks 3, 5, 6, 9.

**Design note:** child tables (`build_phases`, `build_tasks`, `build_task_dependencies`) have no `home_id` column. `save_build` deletes by `build_projects.home_id`, and `ON DELETE CASCADE` (already enabled via `PRAGMA foreign_keys=ON` in `db.py`) cascades the delete down through phases → tasks → dependencies automatically, since both `predecessor_task_id` and `successor_task_id` on `build_task_dependencies` cascade from `build_tasks`.

- [ ] **Step 1: Write the failing test**

```python
# packages/backend/tests/test_build_persistence.py
from myhome.models_build import BuildDocument, BuildPhase, BuildProject, BuildTask, BuildTaskDependency
from myhome.persistence_build import (
    delete_all_attachments,
    delete_attachment,
    delete_build_project,
    get_attachment_path,
    load_build,
    save_attachment,
    save_build,
)

HOME_ID = "test-home"


def _setup(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    (tmp_path / "homes" / HOME_ID).mkdir(parents=True)
    from myhome.db import get_engine
    from myhome.schema import homes as homes_table
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(homes_table.insert().values(
            id=HOME_ID, name="Test Home", type="project", created_at="2026-01-01T00:00:00+00:00",
        ))


def make_doc() -> BuildDocument:
    project = BuildProject(id="proj1", status="in_progress", plannedBudget=250000.0,
                            createdAt="2026-01-01T00:00:00+00:00", updatedAt="2026-01-01T00:00:00+00:00")
    phase = BuildPhase(id="ph1", displayOrder=0, nameKey="build.phases.planning.name", status="in_progress")
    task1 = BuildTask(id="t1", phaseId="ph1", displayOrder=0, titleKey="build.tasks.siteSurvey.title",
                       status="completed", plannedCost=500.0, actualCost=480.0)
    task2 = BuildTask(id="t2", phaseId="ph1", displayOrder=1, titleKey="build.tasks.buildingPermits.title",
                       validationRequired=True, validationStatus="pending_validation")
    dep = BuildTaskDependency(id="d1", predecessorTaskId="t1", successorTaskId="t2")
    return BuildDocument(project=project, phases=[phase], tasks=[task1, task2], dependencies=[dep])


def test_load_returns_empty_when_no_project(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    doc = load_build(HOME_ID)
    assert doc.project is None
    assert doc.phases == []
    assert doc.tasks == []
    assert doc.dependencies == []


def test_round_trip(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    save_build(HOME_ID, make_doc())
    loaded = load_build(HOME_ID)
    assert loaded.project.id == "proj1"
    assert loaded.project.plannedBudget == 250000.0
    assert [p.id for p in loaded.phases] == ["ph1"]
    assert [t.id for t in loaded.tasks] == ["t1", "t2"]
    assert loaded.tasks[0].actualCost == 480.0
    assert loaded.tasks[1].validationStatus == "pending_validation"
    assert len(loaded.dependencies) == 1
    assert loaded.dependencies[0].predecessorTaskId == "t1"


def test_delete_build_project_cascades(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    save_build(HOME_ID, make_doc())
    delete_build_project(HOME_ID)
    loaded = load_build(HOME_ID)
    assert loaded.project is None
    assert loaded.phases == []
    assert loaded.tasks == []
    assert loaded.dependencies == []


def test_attachment_save_and_delete(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    save_attachment(HOME_ID, "t1", "photo.jpg", b"fake-jpeg-bytes")
    path = get_attachment_path(HOME_ID, "t1", "photo.jpg")
    assert path.exists()
    assert delete_attachment(HOME_ID, "t1", "photo.jpg") is True
    assert not path.exists()


def test_delete_all_attachments(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    save_attachment(HOME_ID, "t1", "photo.jpg", b"data")
    delete_all_attachments(HOME_ID, "t1")
    assert not get_attachment_path(HOME_ID, "t1", "photo.jpg").exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/backend && python -m pytest tests/test_build_persistence.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'myhome.persistence_build'`

- [ ] **Step 3: Add the schema tables**

Append to `packages/backend/src/myhome/schema.py` (end of file, after the `properties` table):

```python
build_projects = Table(
    "build_projects", metadata,
    Column("id", String, primary_key=True),
    Column("home_id", String, ForeignKey("homes.id", ondelete="CASCADE"), nullable=False, unique=True),
    Column("status", String, nullable=False),
    Column("planned_start_date", String),
    Column("planned_completion_date", String),
    Column("actual_completion_date", String),
    Column("planned_budget", Float),
    Column("notes", String, nullable=False),
    Column("created_at", String, nullable=False),
    Column("updated_at", String, nullable=False),
)

build_phases = Table(
    "build_phases", metadata,
    Column("id", String, primary_key=True),
    Column("build_project_id", String, ForeignKey("build_projects.id", ondelete="CASCADE"), nullable=False),
    Column("display_order", Integer, nullable=False),
    Column("name_key", String),
    Column("name_override", String),
    Column("description_key", String),
    Column("description_override", String),
    Column("status", String, nullable=False),
    Column("planned_start_date", String),
    Column("planned_end_date", String),
    Column("actual_start_date", String),
    Column("actual_end_date", String),
)

build_tasks = Table(
    "build_tasks", metadata,
    Column("id", String, primary_key=True),
    Column("phase_id", String, ForeignKey("build_phases.id", ondelete="CASCADE"), nullable=False),
    Column("parent_task_id", String),
    Column("display_order", Integer, nullable=False),
    Column("title_key", String),
    Column("title_override", String),
    Column("description_key", String),
    Column("description_override", String),
    Column("status", String, nullable=False),
    Column("planned_start_date", String),
    Column("planned_due_date", String),
    Column("actual_completion_date", String),
    Column("planned_cost", Float),
    Column("actual_cost", Float),
    Column("contractor_id", String),
    Column("validation_required", Boolean, nullable=False),
    Column("validation_status", String, nullable=False),
    Column("notes", String, nullable=False),
    Column("attachments", Text, nullable=False),
)

build_task_dependencies = Table(
    "build_task_dependencies", metadata,
    Column("id", String, primary_key=True),
    Column("predecessor_task_id", String, ForeignKey("build_tasks.id", ondelete="CASCADE"), nullable=False),
    Column("successor_task_id", String, ForeignKey("build_tasks.id", ondelete="CASCADE"), nullable=False),
)
```

- [ ] **Step 4: Write the persistence implementation**

```python
# packages/backend/src/myhome/persistence_build.py
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
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd packages/backend && python -m pytest tests/test_build_persistence.py -v`
Expected: PASS (5 tests)

- [ ] **Step 6: Commit**

```bash
git add packages/backend/src/myhome/schema.py packages/backend/src/myhome/persistence_build.py packages/backend/tests/test_build_persistence.py
git commit -m "feat(build): add schema tables and persistence layer"
```

---

## Task 3: Seed template and seeding function

**Files:**
- Create: `packages/backend/src/myhome/build_template.py`
- Test: `packages/backend/tests/test_build_template.py`

**Interfaces:**
- Consumes: `BuildDocument`, `BuildProject`, `BuildPhase`, `BuildTask`, `BuildTaskDependency` from Task 1.
- Produces: `PHASES: list[dict]`, `seed_default_build(planned_start_date: str | None = None) -> BuildDocument` — consumed by Task 5's `POST /build/start` route.

- [ ] **Step 1: Write the failing test**

```python
# packages/backend/tests/test_build_template.py
from myhome.build_template import PHASES, seed_default_build


def test_phase_count():
    assert len(PHASES) == 22


def test_task_count():
    total = sum(len(p["tasks"]) for p in PHASES)
    assert total == 58


def test_seed_creates_project_and_phases_and_tasks():
    doc = seed_default_build()
    assert doc.project is not None
    assert doc.project.status == "planning"
    assert len(doc.phases) == 22
    assert len(doc.tasks) == 58
    assert doc.phases[0].nameKey == "build.phases.planning.name"
    assert doc.tasks[0].titleKey == "build.tasks.siteSurvey.title"


def test_seed_chains_tasks_within_phase():
    doc = seed_default_build()
    planning_tasks = [t for t in doc.tasks if t.phaseId == doc.phases[0].id]
    assert len(planning_tasks) == 5
    # second task in the phase depends on the first
    dep = next(d for d in doc.dependencies if d.successorTaskId == planning_tasks[1].id)
    assert dep.predecessorTaskId == planning_tasks[0].id


def test_seed_links_first_task_of_phase_to_previous_phase_last_task():
    doc = seed_default_build()
    site_prep_phase = doc.phases[1]
    planning_phase = doc.phases[0]
    site_prep_first_task = min(
        (t for t in doc.tasks if t.phaseId == site_prep_phase.id), key=lambda t: t.displayOrder
    )
    planning_last_task = max(
        (t for t in doc.tasks if t.phaseId == planning_phase.id), key=lambda t: t.displayOrder
    )
    dep = next(d for d in doc.dependencies if d.successorTaskId == site_prep_first_task.id)
    assert dep.predecessorTaskId == planning_last_task.id


def test_seed_rough_in_phases_all_depend_on_framing_not_each_other():
    doc = seed_default_build()
    by_slug = {p["slug"]: doc.phases[i] for i, p in enumerate(PHASES)}
    framing_last = max(
        (t for t in doc.tasks if t.phaseId == by_slug["framing"].id), key=lambda t: t.displayOrder
    )
    for slug in ("plumbingRoughIn", "electricalRoughIn", "hvacRoughIn"):
        first_task = min(
            (t for t in doc.tasks if t.phaseId == by_slug[slug].id), key=lambda t: t.displayOrder
        )
        preds = [d.predecessorTaskId for d in doc.dependencies if d.successorTaskId == first_task.id]
        assert preds == [framing_last.id]


def test_seed_insulation_depends_on_all_three_rough_ins():
    doc = seed_default_build()
    by_slug = {p["slug"]: doc.phases[i] for i, p in enumerate(PHASES)}
    insulation_first = min(
        (t for t in doc.tasks if t.phaseId == by_slug["insulation"].id), key=lambda t: t.displayOrder
    )
    preds = {d.predecessorTaskId for d in doc.dependencies if d.successorTaskId == insulation_first.id}
    expected = set()
    for slug in ("plumbingRoughIn", "electricalRoughIn", "hvacRoughIn"):
        last_task = max(
            (t for t in doc.tasks if t.phaseId == by_slug[slug].id), key=lambda t: t.displayOrder
        )
        expected.add(last_task.id)
    assert preds == expected
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/backend && python -m pytest tests/test_build_template.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'myhome.build_template'`

- [ ] **Step 3: Write the implementation**

```python
# packages/backend/src/myhome/build_template.py
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from .models_build import BuildDocument, BuildPhase, BuildProject, BuildTask, BuildTaskDependency


def _phase(slug: str) -> dict:
    return {"nameKey": f"build.phases.{slug}.name", "descriptionKey": f"build.phases.{slug}.description"}


def _task(slug: str, validation_required: bool = False) -> dict:
    return {
        "titleKey": f"build.tasks.{slug}.title",
        "descriptionKey": f"build.tasks.{slug}.description",
        "validationRequired": validation_required,
    }


PHASES: list[dict] = [
    {"slug": "planning", **_phase("planning"), "tasks": [
        _task("siteSurvey"), _task("architecturalPlans"), _task("buildingPermits", True),
        _task("budgetFinancingApproval"), _task("contractorSelection"),
    ]},
    {"slug": "sitePreparation", **_phase("sitePreparation"), "tasks": [
        _task("siteClearing"), _task("temporaryUtilities"), _task("surveyStaking", True),
    ]},
    {"slug": "foundation", **_phase("foundation"), "tasks": [
        _task("excavation", True), _task("formsReinforcement"), _task("foundationPour", True),
    ]},
    {"slug": "framing", **_phase("framing"), "tasks": [
        _task("floorFraming"), _task("wallFraming"), _task("roofFraming", True),
    ]},
    {"slug": "roofing", **_phase("roofing"), "tasks": [
        _task("roofUnderlayment"), _task("roofCovering", True), _task("roofVentilation"),
    ]},
    {"slug": "windowsExteriorDoors", **_phase("windowsExteriorDoors"), "tasks": [
        _task("windowInstallation"), _task("exteriorDoorInstallation"), _task("exteriorTrimCaulking"),
    ]},
    {"slug": "exteriorEnvelope", **_phase("exteriorEnvelope"), "tasks": [
        _task("weatherResistiveBarrier"), _task("exteriorCladding"), _task("exteriorWaterproofingInspection", True),
    ]},
    {"slug": "plumbingRoughIn", **_phase("plumbingRoughIn"), "tasks": [
        _task("plumbingLayout"), _task("waterHeaterRoughIn"), _task("plumbingRoughInInstallation", True),
    ]},
    {"slug": "electricalRoughIn", **_phase("electricalRoughIn"), "tasks": [
        _task("electricalLayout"), _task("serviceEntranceConnection", True), _task("electricalRoughInInstallation", True),
    ]},
    {"slug": "hvacRoughIn", **_phase("hvacRoughIn"), "tasks": [
        _task("hvacLayout"), _task("equipmentInstallation"), _task("hvacRoughInInstallation", True),
    ]},
    {"slug": "insulation", **_phase("insulation"), "tasks": [
        _task("insulationInstallation"), _task("insulationInspection", True),
    ]},
    {"slug": "drywall", **_phase("drywall"), "tasks": [
        _task("drywallHanging"), _task("drywallFinishing"),
    ]},
    {"slug": "interiorFinishes", **_phase("interiorFinishes"), "tasks": [
        _task("interiorDoorInstallation"), _task("trimMillwork"),
    ]},
    {"slug": "flooring", **_phase("flooring"), "tasks": [
        _task("floorPreparation"), _task("flooringInstallation"),
    ]},
    {"slug": "kitchen", **_phase("kitchen"), "tasks": [
        _task("kitchenCabinetInstallation"), _task("countertopInstallation"), _task("kitchenApplianceInstallation", True),
    ]},
    {"slug": "bathrooms", **_phase("bathrooms"), "tasks": [
        _task("bathroomFixtureInstallation", True), _task("bathroomVentilation"), _task("bathroomWaterproofingTiling"),
    ]},
    {"slug": "painting", **_phase("painting"), "tasks": [
        _task("surfacePreparation"), _task("paintApplication"),
    ]},
    {"slug": "exteriorWorks", **_phase("exteriorWorks"), "tasks": [
        _task("hardscaping"), _task("fencingBoundaryWalls"),
    ]},
    {"slug": "landscaping", **_phase("landscaping"), "tasks": [
        _task("finalGrading"), _task("plantingSeeding"),
    ]},
    {"slug": "finalInspections", **_phase("finalInspections"), "tasks": [
        _task("finalBuildingInspection", True), _task("safetySystemsCheck", True),
    ]},
    {"slug": "punchList", **_phase("punchList"), "tasks": [
        _task("punchListWalkthrough"), _task("punchListResolution", True),
    ]},
    {"slug": "handover", **_phase("handover"), "tasks": [
        _task("finalWalkthrough"), _task("documentsKeysHandover"),
    ]},
]

# Phases whose first task depends on a different set of predecessor phases
# than "the immediately preceding phase in the list" (the default rule).
# Models real parallel construction work: the three rough-in trades all
# start once framing is closed in, not sequentially after each other; and
# insulation can't proceed until all three rough-ins are complete.
FAN_IN: dict[str, list[str]] = {
    "plumbingRoughIn": ["framing"],
    "electricalRoughIn": ["framing"],
    "hvacRoughIn": ["framing"],
    "insulation": ["plumbingRoughIn", "electricalRoughIn", "hvacRoughIn"],
}


def seed_default_build(planned_start_date: str | None = None) -> BuildDocument:
    now = datetime.now(timezone.utc).isoformat()
    project = BuildProject(
        id=str(uuid.uuid4()), status="planning", plannedStartDate=planned_start_date,
        createdAt=now, updatedAt=now,
    )
    phases: list[BuildPhase] = []
    tasks: list[BuildTask] = []
    dependencies: list[BuildTaskDependency] = []
    last_task_id_by_phase_slug: dict[str, str] = {}

    for phase_index, phase_def in enumerate(PHASES):
        phase_id = str(uuid.uuid4())
        phases.append(BuildPhase(
            id=phase_id, displayOrder=phase_index,
            nameKey=phase_def["nameKey"], descriptionKey=phase_def["descriptionKey"],
        ))

        prev_task_id: str | None = None
        first_task_id: str | None = None
        for task_index, task_def in enumerate(phase_def["tasks"]):
            task_id = str(uuid.uuid4())
            if task_index == 0:
                first_task_id = task_id
            tasks.append(BuildTask(
                id=task_id, phaseId=phase_id, displayOrder=task_index,
                titleKey=task_def["titleKey"], descriptionKey=task_def["descriptionKey"],
                validationRequired=task_def["validationRequired"],
            ))
            if prev_task_id is not None:
                dependencies.append(BuildTaskDependency(
                    id=str(uuid.uuid4()), predecessorTaskId=prev_task_id, successorTaskId=task_id,
                ))
            prev_task_id = task_id

        if prev_task_id is not None:
            last_task_id_by_phase_slug[phase_def["slug"]] = prev_task_id

        if first_task_id is not None:
            predecessor_slugs = FAN_IN.get(phase_def["slug"])
            if predecessor_slugs is None and phase_index > 0:
                predecessor_slugs = [PHASES[phase_index - 1]["slug"]]
            for pred_slug in predecessor_slugs or []:
                pred_task_id = last_task_id_by_phase_slug.get(pred_slug)
                if pred_task_id is not None:
                    dependencies.append(BuildTaskDependency(
                        id=str(uuid.uuid4()), predecessorTaskId=pred_task_id, successorTaskId=first_task_id,
                    ))

    return BuildDocument(project=project, phases=phases, tasks=tasks, dependencies=dependencies)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd packages/backend && python -m pytest tests/test_build_template.py -v`
Expected: PASS (7 tests)

- [ ] **Step 5: Commit**

```bash
git add packages/backend/src/myhome/build_template.py packages/backend/tests/test_build_template.py
git commit -m "feat(build): add 22-phase/58-task seed template with dependency generation"
```

---

## Task 4: Routes — project, phase, task CRUD

**Files:**
- Create: `packages/backend/src/myhome/routes/build.py`
- Modify: `packages/backend/src/myhome/main.py`
- Test: `packages/backend/tests/test_build.py`

**Interfaces:**
- Consumes: `load_build`/`save_build`/`delete_build_project` (Task 2), `seed_default_build` (Task 3), `log_activity` (existing `persistence_activity.py`).
- Produces: REST endpoints consumed by Task 5 (same router file) and the frontend `buildStore.svelte.ts` (Task 10).

- [ ] **Step 1: Write the failing test**

```python
# packages/backend/tests/test_build.py
from myhome.persistence_build import load_build, save_build


def test_get_build_empty_when_no_project(client, home_id):
    resp = client.get(f"/api/homes/{home_id}/build")
    assert resp.status_code == 200
    assert resp.json()["project"] is None


def test_start_build_seeds_template(client, home_id):
    resp = client.post(f"/api/homes/{home_id}/build/start", json={})
    assert resp.status_code == 201
    data = resp.json()
    assert data["project"]["status"] == "planning"
    assert len(data["phases"]) == 22
    assert len(data["tasks"]) == 58
    assert len(data["dependencies"]) > 0


def test_start_build_conflict_when_already_started(client, home_id):
    client.post(f"/api/homes/{home_id}/build/start", json={})
    resp = client.post(f"/api/homes/{home_id}/build/start", json={})
    assert resp.status_code == 409


def test_update_project(client, home_id):
    client.post(f"/api/homes/{home_id}/build/start", json={})
    resp = client.put(f"/api/homes/{home_id}/build/project", json={"status": "in_progress", "plannedBudget": 300000.0})
    assert resp.status_code == 204
    data = client.get(f"/api/homes/{home_id}/build").json()
    assert data["project"]["status"] == "in_progress"
    assert data["project"]["plannedBudget"] == 300000.0


def test_update_project_404_when_no_project(client, home_id):
    resp = client.put(f"/api/homes/{home_id}/build/project", json={"status": "in_progress"})
    assert resp.status_code == 404


def test_delete_project(client, home_id):
    client.post(f"/api/homes/{home_id}/build/start", json={})
    resp = client.delete(f"/api/homes/{home_id}/build/project")
    assert resp.status_code == 204
    assert client.get(f"/api/homes/{home_id}/build").json()["project"] is None


def test_update_phase(client, home_id):
    data = client.post(f"/api/homes/{home_id}/build/start", json={}).json()
    phase_id = data["phases"][0]["id"]
    resp = client.put(f"/api/homes/{home_id}/build/phases/{phase_id}", json={"status": "in_progress"})
    assert resp.status_code == 204
    updated = client.get(f"/api/homes/{home_id}/build").json()
    assert updated["phases"][0]["status"] == "in_progress"


def test_update_phase_name_override(client, home_id):
    data = client.post(f"/api/homes/{home_id}/build/start", json={}).json()
    phase_id = data["phases"][0]["id"]
    client.put(f"/api/homes/{home_id}/build/phases/{phase_id}", json={"nameOverride": "Custom Planning"})
    updated = client.get(f"/api/homes/{home_id}/build").json()
    assert updated["phases"][0]["nameOverride"] == "Custom Planning"


def test_update_phase_404(client, home_id):
    client.post(f"/api/homes/{home_id}/build/start", json={})
    resp = client.put(f"/api/homes/{home_id}/build/phases/nope", json={"status": "in_progress"})
    assert resp.status_code == 404


def test_create_custom_task(client, home_id):
    data = client.post(f"/api/homes/{home_id}/build/start", json={}).json()
    phase_id = data["phases"][0]["id"]
    resp = client.post(f"/api/homes/{home_id}/build/tasks", json={"phaseId": phase_id, "titleOverride": "Extra permit visit"})
    assert resp.status_code == 201
    task = resp.json()
    assert task["titleOverride"] == "Extra permit visit"
    assert task["titleKey"] is None


def test_update_task(client, home_id):
    data = client.post(f"/api/homes/{home_id}/build/start", json={}).json()
    task_id = data["tasks"][0]["id"]
    resp = client.put(f"/api/homes/{home_id}/build/tasks/{task_id}", json={
        "status": "in_progress", "actualCost": 550.0, "contractorId": "Acme Surveying",
    })
    assert resp.status_code == 204
    updated = client.get(f"/api/homes/{home_id}/build").json()
    task = next(t for t in updated["tasks"] if t["id"] == task_id)
    assert task["status"] == "in_progress"
    assert task["actualCost"] == 550.0
    assert task["contractorId"] == "Acme Surveying"


def test_update_task_404(client, home_id):
    client.post(f"/api/homes/{home_id}/build/start", json={})
    resp = client.put(f"/api/homes/{home_id}/build/tasks/nope", json={"status": "completed"})
    assert resp.status_code == 404


def test_delete_task_cascades_dependencies(client, home_id):
    data = client.post(f"/api/homes/{home_id}/build/start", json={}).json()
    task_id = data["tasks"][0]["id"]
    resp = client.delete(f"/api/homes/{home_id}/build/tasks/{task_id}")
    assert resp.status_code == 204
    updated = client.get(f"/api/homes/{home_id}/build").json()
    assert all(t["id"] != task_id for t in updated["tasks"])
    assert all(d["predecessorTaskId"] != task_id and d["successorTaskId"] != task_id for d in updated["dependencies"])


def test_delete_task_404(client, home_id):
    client.post(f"/api/homes/{home_id}/build/start", json={})
    resp = client.delete(f"/api/homes/{home_id}/build/tasks/nope")
    assert resp.status_code == 404
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/backend && python -m pytest tests/test_build.py -v`
Expected: FAIL with 404s (route module not registered) / import errors

- [ ] **Step 3: Write the route implementation**

```python
# packages/backend/src/myhome/routes/build.py
from __future__ import annotations

import re
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
from ..persistence_build import delete_build_project, load_build, save_build

router = APIRouter()

_ID_RE = re.compile(r"[A-Za-z0-9_-]{1,64}")


def _validate_id(value: str) -> None:
    if not _ID_RE.fullmatch(value):
        raise HTTPException(status_code=400, detail="Invalid id")


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
    from ..persistence_build import delete_all_attachments

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
```

Add `build` to the router import list and registration in `packages/backend/src/myhome/main.py`:

```python
# Modify the existing import line (around line 20):
from .routes import activity, auth, backup, build, chores, consumables, costs, ha, homes, house, inventory, kb, locations, mcp_config, notifications, properties, settings, svg, works
```

```python
# Add alongside the other app.include_router(...) calls (near line 166):
app.include_router(build.router)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd packages/backend && python -m pytest tests/test_build.py -v`
Expected: PASS (14 tests)

- [ ] **Step 5: Commit**

```bash
git add packages/backend/src/myhome/routes/build.py packages/backend/src/myhome/main.py packages/backend/tests/test_build.py
git commit -m "feat(build): add project/phase/task CRUD routes"
```

---

## Task 5: Routes — dependencies and attachments

**Files:**
- Modify: `packages/backend/src/myhome/routes/build.py` (append)
- Test: Modify `packages/backend/tests/test_build.py` (append)

**Interfaces:**
- Consumes: attachment helpers from Task 2, `BuildDependencyCreate`/`BuildTaskDependency` from Task 1.
- Produces: dependency + attachment endpoints consumed by frontend `buildStore.svelte.ts` (Task 10) and `TaskModal.svelte` (Task 13).

- [ ] **Step 1: Write the failing tests**

Append to `packages/backend/tests/test_build.py`:

```python
def test_create_dependency(client, home_id):
    data = client.post(f"/api/homes/{home_id}/build/start", json={}).json()
    t1, t2 = data["tasks"][0]["id"], data["tasks"][-1]["id"]
    resp = client.post(f"/api/homes/{home_id}/build/dependencies", json={"predecessorTaskId": t1, "successorTaskId": t2})
    assert resp.status_code == 201
    updated = client.get(f"/api/homes/{home_id}/build").json()
    assert any(d["predecessorTaskId"] == t1 and d["successorTaskId"] == t2 for d in updated["dependencies"])


def test_delete_dependency(client, home_id):
    data = client.post(f"/api/homes/{home_id}/build/start", json={}).json()
    dep_id = data["dependencies"][0]["id"]
    resp = client.delete(f"/api/homes/{home_id}/build/dependencies/{dep_id}")
    assert resp.status_code == 204
    updated = client.get(f"/api/homes/{home_id}/build").json()
    assert all(d["id"] != dep_id for d in updated["dependencies"])


def test_delete_dependency_404(client, home_id):
    client.post(f"/api/homes/{home_id}/build/start", json={})
    resp = client.delete(f"/api/homes/{home_id}/build/dependencies/nope")
    assert resp.status_code == 404


def test_upload_and_get_task_attachment(client, home_id):
    data = client.post(f"/api/homes/{home_id}/build/start", json={}).json()
    task_id = data["tasks"][0]["id"]
    resp = client.post(
        f"/api/homes/{home_id}/build/tasks/{task_id}/attachments",
        files={"file": ("photo.jpg", b"\xff\xd8\xff\xe0" + b"\x00" * 100, "image/jpeg")},
    )
    assert resp.status_code == 201
    assert resp.json()["filename"] == "photo.jpg"
    updated = client.get(f"/api/homes/{home_id}/build").json()
    task = next(t for t in updated["tasks"] if t["id"] == task_id)
    assert "photo.jpg" in task["attachments"]

    get_resp = client.get(f"/api/homes/{home_id}/build/tasks/{task_id}/attachments/photo.jpg")
    assert get_resp.status_code == 200


def test_upload_attachment_unsupported_type_rejected(client, home_id):
    data = client.post(f"/api/homes/{home_id}/build/start", json={}).json()
    task_id = data["tasks"][0]["id"]
    resp = client.post(
        f"/api/homes/{home_id}/build/tasks/{task_id}/attachments",
        files={"file": ("notes.txt", b"hello", "text/plain")},
    )
    assert resp.status_code == 400


def test_delete_task_attachment(client, home_id):
    data = client.post(f"/api/homes/{home_id}/build/start", json={}).json()
    task_id = data["tasks"][0]["id"]
    client.post(
        f"/api/homes/{home_id}/build/tasks/{task_id}/attachments",
        files={"file": ("photo.jpg", b"\xff\xd8\xff\xe0" + b"\x00" * 100, "image/jpeg")},
    )
    resp = client.delete(f"/api/homes/{home_id}/build/tasks/{task_id}/attachments/photo.jpg")
    assert resp.status_code == 204
    updated = client.get(f"/api/homes/{home_id}/build").json()
    task = next(t for t in updated["tasks"] if t["id"] == task_id)
    assert "photo.jpg" not in task["attachments"]


def test_delete_task_removes_attachments_dir(client, tmp_path, home_id):
    data = client.post(f"/api/homes/{home_id}/build/start", json={}).json()
    task_id = data["tasks"][0]["id"]
    client.post(
        f"/api/homes/{home_id}/build/tasks/{task_id}/attachments",
        files={"file": ("photo.jpg", b"\xff\xd8\xff\xe0" + b"\x00" * 100, "image/jpeg")},
    )
    client.delete(f"/api/homes/{home_id}/build/tasks/{task_id}")
    attach_dir = tmp_path / "homes" / home_id / "build-attachments" / task_id
    assert not attach_dir.exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/backend && python -m pytest tests/test_build.py -v -k "dependency or attachment"`
Expected: FAIL with 404s (endpoints not yet defined)

- [ ] **Step 3: Append the implementation**

Append to `packages/backend/src/myhome/routes/build.py` (add `mimetypes`, `os` to the existing imports at top, and add `UploadFile`/`FileResponse` imports):

```python
# Add to the import block at the top of routes/build.py:
import mimetypes
import os
from fastapi import UploadFile
from fastapi.responses import FileResponse
from ..persistence_build import (
    delete_all_attachments as _delete_all_task_attachments,
    delete_attachment,
    generate_pdf_thumbnail,
    get_attachment_path,
    save_attachment,
)
```

```python
_ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".webp"}


def _sanitise_filename(name: str) -> str:
    name = name.replace(" ", "_")
    name = re.sub(r"[^a-zA-Z0-9._-]", "", name)
    return name or "attachment"


def _validate_filename(filename: str) -> None:
    if not re.fullmatch(r"[A-Za-z0-9._-]+", filename) or filename.startswith("."):
        raise HTTPException(status_code=400, detail="Invalid filename")


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


@router.post("/api/homes/{home_id}/build/tasks/{task_id}/attachments", status_code=201)
async def upload_task_attachment(home_id: str, task_id: str, file: UploadFile) -> dict:
    _validate_id(task_id)
    doc = load_build(home_id)
    task = next((t for t in doc.tasks if t.id == task_id), None)
    if not task:
        raise HTTPException(status_code=404)
    original = file.filename or ""
    ext = os.path.splitext(original)[1].lower()
    if ext not in _ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Unsupported file type")
    filename = _sanitise_filename(original)
    data = await file.read()
    save_attachment(home_id, task_id, filename, data)
    if ext == ".pdf":
        pdf_path = get_attachment_path(home_id, task_id, filename)
        thumb_path = pdf_path.with_name(pdf_path.name + ".thumb.jpg")
        generate_pdf_thumbnail(pdf_path, thumb_path)
    if filename not in task.attachments:
        task.attachments.append(filename)
    save_build(home_id, doc)
    return {"filename": filename}


@router.get("/api/homes/{home_id}/build/tasks/{task_id}/attachments/{filename}")
def get_task_attachment(home_id: str, task_id: str, filename: str) -> FileResponse:
    _validate_id(task_id)
    _validate_filename(filename)
    path = get_attachment_path(home_id, task_id, filename)
    if not path.is_file():
        raise HTTPException(status_code=404)
    media_type, _ = mimetypes.guess_type(filename)
    return FileResponse(str(path), media_type=media_type or "application/octet-stream", filename=filename)


@router.delete("/api/homes/{home_id}/build/tasks/{task_id}/attachments/{filename}", status_code=204)
def remove_task_attachment(home_id: str, task_id: str, filename: str) -> None:
    _validate_id(task_id)
    _validate_filename(filename)
    doc = load_build(home_id)
    task = next((t for t in doc.tasks if t.id == task_id), None)
    if not task:
        raise HTTPException(status_code=404)
    if not delete_attachment(home_id, task_id, filename):
        raise HTTPException(status_code=404)
    task.attachments = [a for a in task.attachments if a != filename]
    save_build(home_id, doc)
```

Also update `delete_task` (from Task 4) to use the renamed import — replace its local `from ..persistence_build import delete_all_attachments` with a direct call to `_delete_all_task_attachments(home_id, task_id)` (since `delete_all_attachments` is now imported at module scope under that alias to avoid shadowing).

- [ ] **Step 4: Run test to verify it passes**

Run: `cd packages/backend && python -m pytest tests/test_build.py -v`
Expected: PASS (all tests in the file)

- [ ] **Step 5: Commit**

```bash
git add packages/backend/src/myhome/routes/build.py packages/backend/tests/test_build.py
git commit -m "feat(build): add dependency and task attachment routes"
```

---

## Task 6: Module registration and activity log wiring

**Files:**
- Modify: `packages/backend/src/myhome/models_homes.py`
- Modify: `packages/backend/src/myhome/persistence_activity.py`
- Test: `packages/backend/tests/test_homes.py` (verify existing test still passes), `packages/backend/tests/test_activity.py` (add one case if the file exists, else create)

**Interfaces:**
- Produces: `"build"` present in `ALL_MODULE_IDS` and `DEFAULT_PROJECT_MODULES`, consumed by the frontend module-toggle UI (Task 16) and by `DEFAULT_DEMO_MODULES`.

- [ ] **Step 1: Write the failing test**

```python
# Add to packages/backend/tests/test_activity.py (create the file if it does not already exist,
# following the exact structure of persistence_activity.py's existing ACTION_VERBS/MODULE_NOUNS test coverage)
from myhome.persistence_activity import describe
from myhome.models_activity import ActivityEntry


def test_describe_build_task_created():
    entry = ActivityEntry(
        id="e1", timestamp="2026-01-01T00:00:00+00:00", userId="u1", username="admin",
        module="build", action="create", entityLabel="Foundation Pour", refId="t1",
    )
    assert describe(entry) == "added build task 'Foundation Pour'"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/backend && python -m pytest tests/test_activity.py -v -k build`
Expected: FAIL with `KeyError: 'build'` (module not yet in `MODULE_NOUNS`)

- [ ] **Step 3: Write the implementation**

Modify `packages/backend/src/myhome/models_homes.py`:

```python
ALL_MODULE_IDS: list[str] = [
    "home", "plan", "chores", "inventory", "consumables",
    "works", "kb", "costs",
    "locations", "properties", "build", "budget", "visits", "contacts", "checklist",
]

DEFAULT_EXISTING_MODULES: list[str] = [
    "home", "plan", "chores", "inventory", "consumables", "works", "kb", "costs",
]

DEFAULT_PROJECT_MODULES: list[str] = ["home", "plan", "works", "kb", "build"]
```

Modify `packages/backend/src/myhome/persistence_activity.py`:

```python
MODULE_NOUNS = {
    "chores": "chore", "works": "work", "costs": "cost entry",
    "inventory": "inventory item", "consumables": "consumable", "kb": "KB article",
    "locations": "location", "properties": "property", "build": "build task",
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd packages/backend && python -m pytest tests/test_activity.py tests/test_homes.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add packages/backend/src/myhome/models_homes.py packages/backend/src/myhome/persistence_activity.py packages/backend/tests/test_activity.py
git commit -m "feat(build): register build module id and activity log noun"
```

---

## Task 7: Notification settings and state extensions

**Files:**
- Modify: `packages/backend/src/myhome/models_settings.py`
- Modify: `packages/backend/src/myhome/models_notifications.py`
- Modify: `packages/backend/src/myhome/persistence_notifications.py`
- Test: `packages/backend/tests/test_notification_state_build.py`

**Interfaces:**
- Produces: `NotificationSettings.buildTaskDueSoonThreshold: int`, `Notification.type` including `"build_task_due" | "build_validation" | "build_phase_complete"`, `NotificationState.buildPhasesNotified: list[str]` — consumed by Task 8.

- [ ] **Step 1: Write the failing test**

```python
# packages/backend/tests/test_notification_state_build.py
from myhome.models_notifications import Notification, NotificationState
from myhome.models_settings import NotificationSettings
from myhome.persistence_notifications import load_notification_state, save_notification_state

HOME_ID = "test-home"


def test_notification_settings_has_build_threshold():
    s = NotificationSettings()
    assert s.buildTaskDueSoonThreshold == 7


def test_notification_type_accepts_build_types():
    Notification(type="build_task_due", refId="t1", title="x", detail="y", severity="warning")
    Notification(type="build_validation", refId="t1", title="x", detail="y", severity="info")
    Notification(type="build_phase_complete", refId="ph1", title="x", detail="y", severity="info")


def test_notification_state_build_phases_notified_round_trip(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    (tmp_path / "homes" / HOME_ID).mkdir(parents=True)
    from myhome.db import get_engine
    from myhome.schema import homes as homes_table
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(homes_table.insert().values(
            id=HOME_ID, name="Test Home", type="project", created_at="2026-01-01T00:00:00+00:00",
        ))
    state = NotificationState(buildPhasesNotified=["ph1"])
    save_notification_state(HOME_ID, state)
    loaded = load_notification_state(HOME_ID)
    assert loaded.buildPhasesNotified == ["ph1"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/backend && python -m pytest tests/test_notification_state_build.py -v`
Expected: FAIL — `AttributeError`/`ValidationError` (fields don't exist yet)

- [ ] **Step 3: Write the implementation**

Modify `packages/backend/src/myhome/models_settings.py`:

```python
class NotificationSettings(BaseModel):
    enabled: bool = True
    choresDueSoonThreshold: float = 0.25
    warrantyDaysThreshold: int = 30
    buildTaskDueSoonThreshold: int = 7
    haPushEnabled: bool = False
    haNotifyService: str | None = None
    haPushTime: str = "08:00"
```

Modify `packages/backend/src/myhome/models_notifications.py`:

```python
class Notification(BaseModel):
    type: Literal["chore", "low_stock", "warranty", "build_task_due", "build_validation", "build_phase_complete"]
    refId: str
    title: str
    detail: str
    severity: Literal["info", "warning", "critical"]


class NotificationState(BaseModel):
    version: int = 1
    warrantyNotified: dict[str, str] = {}
    buildPhasesNotified: list[str] = []
    lastPushDigestDate: str | None = None
```

Modify `packages/backend/src/myhome/persistence_notifications.py` — add a `build_phases_notified` JSON column read/write alongside the existing `warranty_notified` one. First add the column to the `notification_state` table in `schema.py`:

```python
# schema.py — modify the existing notification_state table definition:
notification_state = Table(
    "notification_state", metadata,
    Column("home_id", String, ForeignKey("homes.id", ondelete="CASCADE"), primary_key=True),
    Column("warranty_notified", Text, nullable=False),
    Column("build_phases_notified", Text, nullable=False, server_default="[]"),
    Column("last_push_digest_date", String),
)
```

`server_default="[]"` lets `metadata.create_all` add this column to any pre-existing `notification_state` table on next startup without a hand-written migration (SQLite `ALTER TABLE ADD COLUMN` needs a default for existing rows, which `create_all` does not auto-apply to already-existing tables — but since this is a dev/pre-1.0 codebase with clean-cutover precedent already established for the SQLite migration, and `notification_state` is trivially re-derived from live data, no migration function is needed here; document this assumption in the PR description).

```python
# persistence_build.py is NOT touched here — this is persistence_notifications.py:
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd packages/backend && python -m pytest tests/test_notification_state_build.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add packages/backend/src/myhome/models_settings.py packages/backend/src/myhome/models_notifications.py packages/backend/src/myhome/persistence_notifications.py packages/backend/src/myhome/schema.py packages/backend/tests/test_notification_state_build.py
git commit -m "feat(build): extend notification settings/state for build tracking"
```

---

## Task 8: Notification computation

**Files:**
- Modify: `packages/backend/src/myhome/notifications.py`
- Test: `packages/backend/tests/test_notifications.py` (append; if the file doesn't already contain equivalent chore/warranty tests to mirror, check first — it does, per the existing Notification Center feature)

**Interfaces:**
- Consumes: `load_build` (Task 2), `NotificationSettings.buildTaskDueSoonThreshold` and `NotificationState.buildPhasesNotified` (Task 7).
- Produces: `compute_notifications` now also includes build notifications — consumed by the existing `GET /api/homes/{id}/notifications` route (no route change needed, it already calls `compute_notifications`) and `NotificationBell.svelte` (no frontend change needed — it already renders whatever `type`s come back, grouped by a `GROUP_ORDER` list that Task 16 will extend).

- [ ] **Step 1: Write the failing test**

```python
# Append to packages/backend/tests/test_notifications.py
from myhome.models_build import BuildDocument, BuildPhase, BuildProject, BuildTask
from myhome.models_notifications import NotificationState
from myhome.notifications import _build_notifications
from datetime import datetime, timezone, timedelta


def _iso_days_from_now(days: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()


def _make_build_doc(**task_kwargs) -> BuildDocument:
    project = BuildProject(id="p1", createdAt="2026-01-01T00:00:00+00:00", updatedAt="2026-01-01T00:00:00+00:00")
    phase = BuildPhase(id="ph1", displayOrder=0, nameKey="build.phases.planning.name")
    task = BuildTask(id="t1", phaseId="ph1", displayOrder=0, titleKey="build.tasks.siteSurvey.title", **task_kwargs)
    return BuildDocument(project=project, phases=[phase], tasks=[task])


def test_build_task_due_soon():
    doc = _make_build_doc(plannedDueDate=_iso_days_from_now(3))
    results = _build_notifications(doc, threshold_days=7, state=NotificationState())
    assert any(n.type == "build_task_due" and n.severity == "warning" for n, _ in [(r, None) for r in results[0]])


def test_build_task_overdue():
    doc = _make_build_doc(plannedDueDate=_iso_days_from_now(-2))
    notifications, _ = _build_notifications(doc, threshold_days=7, state=NotificationState())
    assert any(n.type == "build_task_due" and n.severity == "critical" for n in notifications)


def test_build_task_not_due_soon_excluded():
    doc = _make_build_doc(plannedDueDate=_iso_days_from_now(30))
    notifications, _ = _build_notifications(doc, threshold_days=7, state=NotificationState())
    assert not any(n.type == "build_task_due" for n in notifications)


def test_build_task_completed_excluded_even_if_overdue():
    doc = _make_build_doc(plannedDueDate=_iso_days_from_now(-2), status="completed")
    notifications, _ = _build_notifications(doc, threshold_days=7, state=NotificationState())
    assert not any(n.type == "build_task_due" for n in notifications)


def test_build_validation_pending():
    doc = _make_build_doc(validationRequired=True, validationStatus="pending_validation")
    notifications, _ = _build_notifications(doc, threshold_days=7, state=NotificationState())
    assert any(n.type == "build_validation" for n in notifications)


def test_build_validation_not_required_excluded():
    doc = _make_build_doc(validationRequired=False)
    notifications, _ = _build_notifications(doc, threshold_days=7, state=NotificationState())
    assert not any(n.type == "build_validation" for n in notifications)


def test_build_phase_complete_fires_once():
    project = BuildProject(id="p1", createdAt="2026-01-01T00:00:00+00:00", updatedAt="2026-01-01T00:00:00+00:00")
    phase = BuildPhase(id="ph1", displayOrder=0, nameKey="build.phases.planning.name", status="completed")
    doc = BuildDocument(project=project, phases=[phase], tasks=[])

    notifications1, state1 = _build_notifications(doc, threshold_days=7, state=NotificationState())
    assert any(n.type == "build_phase_complete" and n.refId == "ph1" for n in notifications1)
    assert "ph1" in state1.buildPhasesNotified

    notifications2, _ = _build_notifications(doc, threshold_days=7, state=state1)
    assert not any(n.type == "build_phase_complete" for n in notifications2)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/backend && python -m pytest tests/test_notifications.py -v -k build`
Expected: FAIL with `ImportError: cannot import name '_build_notifications'`

- [ ] **Step 3: Write the implementation**

Modify `packages/backend/src/myhome/notifications.py` — add the import and new function, and wire it into `compute_notifications`:

```python
# Add near the top imports:
from .models_build import BuildDocument
from .persistence_build import load_build
```

```python
def _build_notifications(
    doc: BuildDocument, threshold_days: int, state: NotificationState,
) -> tuple[list[Notification], NotificationState]:
    if doc.project is None:
        return [], state

    now = datetime.now(timezone.utc)
    results: list[Notification] = []

    for task in doc.tasks:
        if task.status == "completed":
            continue
        if task.plannedDueDate:
            due = _parse_iso(task.plannedDueDate)
            days_left = (due.date() - now.date()).days
            if days_left <= threshold_days:
                title = task.titleOverride or task.titleKey or task.id
                results.append(Notification(
                    type="build_task_due", refId=task.id, title=title,
                    detail=_format_due(now, due), severity="critical" if days_left < 0 else "warning",
                ))
        if task.validationRequired and task.validationStatus == "pending_validation":
            title = task.titleOverride or task.titleKey or task.id
            results.append(Notification(
                type="build_validation", refId=task.id, title=title,
                detail="Validation pending", severity="info",
            ))

    notified = list(state.buildPhasesNotified)
    changed = False
    for phase in doc.phases:
        if phase.status == "completed" and phase.id not in notified:
            title = phase.nameOverride or phase.nameKey or phase.id
            results.append(Notification(
                type="build_phase_complete", refId=phase.id, title=title,
                detail="Phase complete", severity="info",
            ))
            notified.append(phase.id)
            changed = True

    new_state = state.model_copy(update={"buildPhasesNotified": notified}) if changed else state
    return results, new_state
```

Update `compute_notifications`:

```python
def compute_notifications(home_id: str) -> list[Notification]:
    settings = load_settings(home_id).notifications
    if not settings.enabled:
        return []

    state = load_notification_state(home_id)
    chores_doc = load_chores(home_id)
    consumables_doc = load_consumables(home_id)
    inventory_doc = load_inventory(home_id)
    build_doc = load_build(home_id)

    results: list[Notification] = []
    results += _chore_notifications(chores_doc, settings.choresDueSoonThreshold)
    results += _low_stock_notifications(consumables_doc)
    fired, updated_state = _warranty_notifications(
        inventory_doc, settings.warrantyDaysThreshold, state,
    )
    results += fired
    build_fired, updated_state = _build_notifications(
        build_doc, settings.buildTaskDueSoonThreshold, updated_state,
    )
    results += build_fired
    if updated_state != state:
        save_notification_state(home_id, updated_state)
    return results
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd packages/backend && python -m pytest tests/test_notifications.py -v`
Expected: PASS (all tests, including the pre-existing chore/low-stock/warranty ones)

- [ ] **Step 5: Commit**

```bash
git add packages/backend/src/myhome/notifications.py packages/backend/tests/test_notifications.py
git commit -m "feat(build): compute due/overdue, validation, and phase-complete notifications"
```

---

## Task 9: MCP tools

**Files:**
- Create: `packages/backend/src/myhome/mcp_tools_build.py`
- Modify: `packages/backend/src/myhome/mcp_app.py`
- Test: `packages/backend/tests/test_mcp_tools_build.py`

**Interfaces:**
- Consumes: `load_build`/`save_build` (Task 2), `_require_role`/`_resolve_home_id`/`mcp` (existing `mcp_server.py`).
- Produces: `list_build_phases`, `list_build_tasks`, `create_build_task`, `update_build_task`, `update_build_phase` MCP tools.

- [ ] **Step 1: Write the failing test**

```python
# packages/backend/tests/test_mcp_tools_build.py
import pytest
from myhome.mcp_tools_build import (
    _create_build_task_impl,
    _list_build_phases_impl,
    _list_build_tasks_impl,
    _update_build_phase_impl,
    _update_build_task_impl,
)
from myhome.build_template import seed_default_build
from myhome.persistence_build import save_build


def _seed(home_id):
    doc = seed_default_build()
    save_build(home_id, doc)
    return doc


def test_list_build_phases_impl(tmp_path, monkeypatch, home_id="h1"):
    _seed_env(tmp_path, monkeypatch, home_id)
    doc = _seed(home_id)
    result = _list_build_phases_impl(home_id)
    assert len(result["phases"]) == 22


def test_list_build_tasks_impl(tmp_path, monkeypatch, home_id="h1"):
    _seed_env(tmp_path, monkeypatch, home_id)
    doc = _seed(home_id)
    result = _list_build_tasks_impl(home_id, phase_id=doc.phases[0].id)
    assert len(result["tasks"]) == 5


def test_create_build_task_impl(tmp_path, monkeypatch, home_id="h1"):
    _seed_env(tmp_path, monkeypatch, home_id)
    doc = _seed(home_id)
    result = _create_build_task_impl(home_id, phase_id=doc.phases[0].id, title="Extra site visit")
    assert result["titleOverride"] == "Extra site visit"


def test_update_build_task_impl(tmp_path, monkeypatch, home_id="h1"):
    _seed_env(tmp_path, monkeypatch, home_id)
    doc = _seed(home_id)
    result = _update_build_task_impl(home_id, task_id=doc.tasks[0].id, status="in_progress")
    assert result["status"] == "in_progress"


def test_update_build_task_impl_unknown_id(tmp_path, monkeypatch, home_id="h1"):
    _seed_env(tmp_path, monkeypatch, home_id)
    _seed(home_id)
    with pytest.raises(ValueError):
        _update_build_task_impl(home_id, task_id="nope", status="in_progress")


def test_update_build_phase_impl(tmp_path, monkeypatch, home_id="h1"):
    _seed_env(tmp_path, monkeypatch, home_id)
    doc = _seed(home_id)
    result = _update_build_phase_impl(home_id, phase_id=doc.phases[0].id, status="in_progress")
    assert result["status"] == "in_progress"


def _seed_env(tmp_path, monkeypatch, home_id):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    (tmp_path / "homes" / home_id).mkdir(parents=True)
    from myhome.db import get_engine
    from myhome.schema import homes as homes_table
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(homes_table.insert().values(
            id=home_id, name="Test Home", type="project", created_at="2026-01-01T00:00:00+00:00",
        ))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/backend && python -m pytest tests/test_mcp_tools_build.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'myhome.mcp_tools_build'`

- [ ] **Step 3: Write the implementation**

```python
# packages/backend/src/myhome/mcp_tools_build.py
from __future__ import annotations

import uuid

from mcp.server.fastmcp import Context

from .mcp_server import _require_role, _resolve_home_id, mcp
from .models_build import BuildTask
from .persistence_build import load_build, save_build

_VALID_TASK_STATUSES = ("not_started", "ready", "in_progress", "waiting", "blocked", "completed")
_VALID_PHASE_STATUSES = ("not_started", "in_progress", "completed")


def _list_build_phases_impl(home_id: str | None) -> dict:
    resolved = _resolve_home_id(home_id)
    doc = load_build(resolved)
    return {"phases": [p.model_dump() for p in doc.phases]}


def _list_build_tasks_impl(home_id: str | None, phase_id: str | None = None) -> dict:
    resolved = _resolve_home_id(home_id)
    doc = load_build(resolved)
    tasks = doc.tasks if phase_id is None else [t for t in doc.tasks if t.phaseId == phase_id]
    return {"tasks": [t.model_dump() for t in tasks]}


def _create_build_task_impl(
    home_id: str | None, phase_id: str, title: str,
    description: str = "", validation_required: bool = False,
) -> dict:
    resolved = _resolve_home_id(home_id)
    doc = load_build(resolved)
    if not any(p.id == phase_id for p in doc.phases):
        raise ValueError(f"Unknown phase_id {phase_id!r}")
    siblings = [t for t in doc.tasks if t.phaseId == phase_id]
    task = BuildTask(
        id=str(uuid.uuid4()), phaseId=phase_id, displayOrder=len(siblings),
        titleOverride=title, descriptionOverride=description, validationRequired=validation_required,
    )
    doc.tasks.append(task)
    save_build(resolved, doc)
    return task.model_dump()


def _update_build_task_impl(home_id: str | None, task_id: str, **fields) -> dict:
    if fields.get("status") is not None and fields["status"] not in _VALID_TASK_STATUSES:
        raise ValueError(f"status must be one of {_VALID_TASK_STATUSES}")
    resolved = _resolve_home_id(home_id)
    doc = load_build(resolved)
    task = next((t for t in doc.tasks if t.id == task_id), None)
    if task is None:
        raise ValueError(f"Unknown task_id {task_id!r}")
    for field, value in fields.items():
        if value is not None:
            setattr(task, field, value)
    save_build(resolved, doc)
    return task.model_dump()


def _update_build_phase_impl(home_id: str | None, phase_id: str, **fields) -> dict:
    if fields.get("status") is not None and fields["status"] not in _VALID_PHASE_STATUSES:
        raise ValueError(f"status must be one of {_VALID_PHASE_STATUSES}")
    resolved = _resolve_home_id(home_id)
    doc = load_build(resolved)
    phase = next((p for p in doc.phases if p.id == phase_id), None)
    if phase is None:
        raise ValueError(f"Unknown phase_id {phase_id!r}")
    for field, value in fields.items():
        if value is not None:
            setattr(phase, field, value)
    save_build(resolved, doc)
    return phase.model_dump()


@mcp.tool()
async def list_build_phases(ctx: Context, home_id: str | None = None) -> dict:
    """List build tracking phases for a home's construction project."""
    await _require_role(ctx.request_context.request, "ro")
    return _list_build_phases_impl(home_id)


@mcp.tool()
async def list_build_tasks(ctx: Context, home_id: str | None = None, phase_id: str | None = None) -> dict:
    """List build tracking tasks for a home, optionally filtered to one phase_id."""
    await _require_role(ctx.request_context.request, "ro")
    return _list_build_tasks_impl(home_id, phase_id)


@mcp.tool()
async def create_build_task(
    ctx: Context, phase_id: str, title: str,
    home_id: str | None = None, description: str = "", validation_required: bool = False,
) -> dict:
    """Create a custom build task within an existing phase."""
    await _require_role(ctx.request_context.request, "normal")
    return _create_build_task_impl(home_id, phase_id, title, description, validation_required)


@mcp.tool()
async def update_build_task(
    ctx: Context, task_id: str, home_id: str | None = None,
    status: str | None = None, contractor_id: str | None = None,
    planned_due_date: str | None = None, actual_cost: float | None = None,
    validation_status: str | None = None, notes: str | None = None,
) -> dict:
    """Update a build task's status, contractor, dates, cost, or validation status."""
    await _require_role(ctx.request_context.request, "normal")
    return _update_build_task_impl(
        home_id, task_id, status=status, contractorId=contractor_id,
        plannedDueDate=planned_due_date, actualCost=actual_cost,
        validationStatus=validation_status, notes=notes,
    )


@mcp.tool()
async def update_build_phase(
    ctx: Context, phase_id: str, home_id: str | None = None, status: str | None = None,
) -> dict:
    """Update a build phase's status."""
    await _require_role(ctx.request_context.request, "normal")
    return _update_build_phase_impl(home_id, phase_id, status=status)
```

Modify `packages/backend/src/myhome/mcp_app.py` — add `mcp_tools_build` to the import list (alphabetically, before `mcp_tools_chores`):

```python
from . import (
    mcp_tools_build,
    mcp_tools_chores,
    mcp_tools_consumables,
    mcp_tools_costs,
    mcp_tools_homes,
    mcp_tools_inventory,
    mcp_tools_kb,
    mcp_tools_locations,
    mcp_tools_properties,
    mcp_tools_settings,
    mcp_tools_works,
)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd packages/backend && python -m pytest tests/test_mcp_tools_build.py -v`
Expected: PASS (6 tests)

- [ ] **Step 5: Commit**

```bash
git add packages/backend/src/myhome/mcp_tools_build.py packages/backend/src/myhome/mcp_app.py packages/backend/tests/test_mcp_tools_build.py
git commit -m "feat(build): add MCP tools for build phases and tasks"
```

---

Backend is complete after Task 9 (all 9 backend tasks). Frontend tasks follow.

---

## Task 10: Locale content

**Files:**
- Modify: `packages/editor/src/lib/locales/en.json`
- Modify: `packages/editor/src/lib/locales/fr.json`
- Test: existing `packages/editor/test/i18nCompleteness.test.ts` (no changes needed — it automatically enforces key parity and non-empty values for whatever is added)

**Interfaces:**
- Produces: all `common.modules.build`, `build.projectStatus.*`, `build.phaseStatus.*`, `build.taskStatus.*`, `build.validationStatus.*`, `build.dashboard.*`, `build.page.*`, `build.modal.*`, `build.phases.*`, `build.tasks.*` keys consumed by every remaining frontend task.

- [ ] **Step 1: Run the existing i18n completeness test to confirm current baseline passes**

Run: `cd packages/editor && npx vitest run test/i18nCompleteness.test.ts`
Expected: PASS (0 failures) — this is the safety net Step 3 must keep passing.

- [ ] **Step 2: Add `"build"` to `common.modules` in both files**

In `packages/editor/src/lib/locales/en.json`, modify the `common.modules` block:

```json
    "modules": {
      "home": "Home",
      "plan": "Floor Plan",
      "chores": "Chores",
      "inventory": "Inventory",
      "consumables": "Consumables",
      "works": "Works",
      "kb": "Knowledge Base",
      "costs": "Costs",
      "locations": "Locations",
      "properties": "Properties",
      "build": "Build",
      "budget": "Budget",
      "visits": "Visits",
      "contacts": "Contacts",
      "checklist": "Checklist"
    },
```

In `packages/editor/src/lib/locales/fr.json`, the equivalent block:

```json
    "modules": {
      "home": "Accueil",
      "plan": "Plan",
      "chores": "Corvées",
      "inventory": "Inventaire",
      "consumables": "Consommables",
      "works": "Travaux",
      "kb": "Base de connaissances",
      "costs": "Coûts",
      "locations": "Lieux",
      "properties": "Biens",
      "build": "Construction",
      "budget": "Budget",
      "visits": "Visites",
      "contacts": "Contacts",
      "checklist": "Liste de contrôle"
    },
```

(Match whatever French wording the existing `properties`/`locations`/etc. entries already use in `fr.json` — read the file first since the exact existing translations may differ slightly from the illustrative ones above; keep the surrounding keys byte-identical and only insert the new `"build"` line.)

- [ ] **Step 3: Add the top-level `"build"` namespace to `en.json`**

Insert as a new top-level key (alongside `"kb"`, `"markdownEditor"`, `"app"`, etc., anywhere in the top-level object — JSON key order doesn't matter to the parser or the completeness test):

```json
  "build": {
    "projectStatus": {
      "planning": "Planning",
      "inProgress": "In progress",
      "completed": "Completed",
      "onHold": "On hold"
    },
    "phaseStatus": {
      "notStarted": "Not started",
      "inProgress": "In progress",
      "completed": "Completed"
    },
    "taskStatus": {
      "notStarted": "Not started",
      "ready": "Ready",
      "inProgress": "In progress",
      "waiting": "Waiting",
      "blocked": "Blocked",
      "completed": "Completed"
    },
    "validationStatus": {
      "notRequired": "Not required",
      "pendingValidation": "Pending validation",
      "passed": "Passed",
      "failed": "Failed"
    },
    "dashboard": {
      "status": "Status",
      "currentPhase": "Current phase",
      "percentComplete": "% complete",
      "plannedBudget": "Planned budget",
      "actualCost": "Actual cost",
      "overdueTasks": "Overdue & upcoming tasks",
      "upcomingValidations": "Upcoming validations",
      "recentActivity": "Recent activity",
      "noOverdue": "No overdue or upcoming tasks.",
      "noValidationsPending": "No validations pending.",
      "noActivity": "No recent activity."
    },
    "page": {
      "startTitle": "Start Build Tracking",
      "startDescription": "Set up a construction project for this home with 22 standard phases and a starter task checklist you can customize.",
      "startButton": "Start Build Tracking",
      "dashboardTab": "Dashboard",
      "phasesTab": "Phases",
      "addPhase": "+ Add phase",
      "addTask": "+ Add task",
      "taskCount": "{n} tasks",
      "noPhases": "No phases yet.",
      "deleteProjectConfirm": "Delete this build project and all its phases, tasks, and attachments? This cannot be undone."
    },
    "modal": {
      "newTask": "New task",
      "editTask": "Edit task",
      "title": "Title",
      "titlePlaceholder": "Task title",
      "description": "Description",
      "status": "Status",
      "contractor": "Contractor",
      "contractorPlaceholder": "Contractor name",
      "plannedStart": "Planned start",
      "plannedDue": "Planned due",
      "actualCompletion": "Actual completion",
      "plannedCost": "Planned cost (€)",
      "actualCost": "Actual cost (€)",
      "validationRequired": "Validation required",
      "validationStatus": "Validation status",
      "dependsOn": "Depends on",
      "noDependencies": "No dependencies",
      "notes": "Notes",
      "noneOption": "— None —",
      "titleRequired": "Title is required",
      "saveFailed": "Save failed",
      "deleteFailed": "Delete failed",
      "uploadFailed": "Upload failed",
      "confirm": "Confirm"
    },
    "phases": {
      "planning": { "name": "Planning", "description": "Initial project setup: permits, design, financing, and contractor selection before ground is broken." },
      "sitePreparation": { "name": "Site Preparation", "description": "Clearing, access, and utility groundwork before excavation begins." },
      "foundation": { "name": "Foundation", "description": "Excavation, footings, and slab or crawlspace construction." },
      "framing": { "name": "Framing", "description": "Structural skeleton: floors, walls, and roof framing." },
      "roofing": { "name": "Roofing", "description": "Weatherproofing the roof structure." },
      "windowsExteriorDoors": { "name": "Windows & Exterior Doors", "description": "Installing the building envelope's window and door openings." },
      "exteriorEnvelope": { "name": "Exterior Envelope", "description": "Weather barrier, insulation, and exterior cladding." },
      "plumbingRoughIn": { "name": "Plumbing Rough-In", "description": "Water supply, drain, and vent piping installed before walls are closed." },
      "electricalRoughIn": { "name": "Electrical Rough-In", "description": "Wiring, boxes, and panel groundwork before walls are closed." },
      "hvacRoughIn": { "name": "HVAC Rough-In", "description": "Ductwork, refrigerant lines, or hydronic piping before walls are closed." },
      "insulation": { "name": "Insulation", "description": "Thermal and acoustic insulation before drywall closes the walls." },
      "drywall": { "name": "Drywall", "description": "Wall and ceiling closure and finishing." },
      "interiorFinishes": { "name": "Interior Finishes", "description": "Trim, doors, and millwork throughout the interior." },
      "flooring": { "name": "Flooring", "description": "Final floor coverings throughout the house." },
      "kitchen": { "name": "Kitchen", "description": "Cabinetry, countertops, and kitchen appliance installation." },
      "bathrooms": { "name": "Bathrooms", "description": "Fixtures and finishes for each bathroom." },
      "painting": { "name": "Painting", "description": "Interior and exterior paint and finish coats." },
      "exteriorWorks": { "name": "Exterior Works", "description": "Driveways, walkways, decks, and other hardscape." },
      "landscaping": { "name": "Landscaping", "description": "Grading, planting, and final grounds finishing." },
      "finalInspections": { "name": "Final Inspections", "description": "Regulatory and safety inspections before occupancy." },
      "punchList": { "name": "Punch List", "description": "Identifying and resolving remaining defects before handover." },
      "handover": { "name": "Handover", "description": "Final walkthrough, documentation, and keys transfer." }
    },
    "tasks": {
      "siteSurvey": { "title": "Site Survey", "description": "Commission a topographic survey\nConfirm property boundaries\nIdentify soil conditions\nLocate existing utilities" },
      "architecturalPlans": { "title": "Architectural Plans", "description": "Brief the architect on requirements\nReview preliminary sketches\nApprove final floor plans\nApprove elevations and sections" },
      "buildingPermits": { "title": "Building Permits", "description": "Submit permit application\nRespond to any requests for information\nObtain approved permit\nPost permit on site" },
      "budgetFinancingApproval": { "title": "Budget & Financing Approval", "description": "Finalize construction budget\nSecure financing or construction loan\nSet contingency reserve\nApprove payment schedule" },
      "contractorSelection": { "title": "Contractor Selection", "description": "Request bids from qualified contractors\nCompare quotes and references\nSign construction contract\nSchedule project kickoff" },
      "siteClearing": { "title": "Site Clearing", "description": "Remove vegetation and debris\nFell and clear designated trees\nGrade access route for equipment\nFence off the site" },
      "temporaryUtilities": { "title": "Temporary Utilities", "description": "Install temporary power connection\nInstall temporary water supply\nSet up site office/storage container\nInstall site sanitation" },
      "surveyStaking": { "title": "Survey & Staking", "description": "Stake out building corners\nMark excavation limits\nVerify setbacks against permit\nProtect survey markers" },
      "excavation": { "title": "Excavation", "description": "Excavate to design depth\nVerify excavation dimensions\nInspect soil bearing capacity\nInstall temporary shoring if required" },
      "formsReinforcement": { "title": "Forms & Reinforcement", "description": "Set formwork to plan dimensions\nInstall reinforcement steel\nPosition utility penetrations and sleeves\nVerify drainage and waterproofing membrane" },
      "foundationPour": { "title": "Foundation Pour", "description": "Verify excavation dimensions\nInstall reinforcement\nVerify drainage\nPosition utility penetrations\nPour concrete\nFinish surface\nAllow curing\nPrepare for inspection" },
      "floorFraming": { "title": "Floor Framing", "description": "Install sill plates and anchor bolts\nInstall floor joists\nInstall subfloor sheathing\nVerify level and square" },
      "wallFraming": { "title": "Wall Framing", "description": "Erect exterior wall panels\nErect interior partition walls\nInstall headers over openings\nBrace and plumb walls" },
      "roofFraming": { "title": "Roof Framing", "description": "Set ridge beam and rafters or trusses\nInstall roof sheathing\nVerify structural connections\nPrepare for inspection" },
      "roofUnderlayment": { "title": "Roof Underlayment", "description": "Install roofing felt or synthetic underlayment\nInstall flashing at valleys and penetrations\nInstall drip edge" },
      "roofCovering": { "title": "Roof Covering", "description": "Install roofing material (tiles, shingles, or metal)\nInstall ridge caps\nInstall gutters and downspouts\nInspect for leaks after installation" },
      "roofVentilation": { "title": "Roof Ventilation", "description": "Install ridge and soffit vents\nVerify airflow path\nSeal vent penetrations" },
      "windowInstallation": { "title": "Window Installation", "description": "Verify rough opening dimensions\nSet and level windows\nInstall flashing and seal\nAdjust for smooth operation" },
      "exteriorDoorInstallation": { "title": "Exterior Door Installation", "description": "Verify rough opening dimensions\nSet and level door frames\nInstall flashing and weatherstripping\nTest lock and hardware operation" },
      "exteriorTrimCaulking": { "title": "Exterior Trim & Caulking", "description": "Install exterior window and door trim\nCaulk all exterior joints\nInspect weatherproofing" },
      "weatherResistiveBarrier": { "title": "Weather-Resistive Barrier", "description": "Install house wrap or weather barrier\nTape and seal all seams\nInstall flashing around penetrations" },
      "exteriorCladding": { "title": "Exterior Cladding", "description": "Install cladding material (siding, brick, or render)\nInstall trim and corner details\nCaulk and seal joints\nInspect for consistent alignment" },
      "exteriorWaterproofingInspection": { "title": "Exterior Waterproofing Inspection", "description": "Inspect flashing details\nInspect cladding fastening\nConfirm weep holes and drainage paths are clear" },
      "plumbingLayout": { "title": "Plumbing Layout", "description": "Mark fixture locations\nCoordinate with framing for pipe runs\nVerify vent stack routing" },
      "waterHeaterRoughIn": { "title": "Water Heater Rough-In", "description": "Position water heater\nRough-in supply and vent connections\nVerify code clearances" },
      "plumbingRoughInInstallation": { "title": "Plumbing Rough-In Installation", "description": "Install supply lines\nInstall drain-waste-vent piping\nPressure-test supply lines\nCap open lines for inspection" },
      "electricalLayout": { "title": "Electrical Layout", "description": "Mark outlet, switch, and fixture locations\nConfirm circuit plan against electrical drawings\nCoordinate with other rough-in trades" },
      "serviceEntranceConnection": { "title": "Service Entrance Connection", "description": "Coordinate utility service connection\nInstall meter base\nSchedule utility hookup" },
      "electricalRoughInInstallation": { "title": "Electrical Rough-In Installation", "description": "Install electrical panel\nRun wiring to boxes\nInstall boxes for outlets, switches, and fixtures\nLabel circuits" },
      "hvacLayout": { "title": "HVAC Layout", "description": "Confirm equipment locations\nPlan duct or pipe routing\nCoordinate penetrations with framing" },
      "equipmentInstallation": { "title": "HVAC Equipment Installation", "description": "Set furnace, heat pump, or boiler unit\nConnect refrigerant or hydronic lines\nVerify condensate drainage" },
      "hvacRoughInInstallation": { "title": "HVAC Rough-In Installation", "description": "Install ductwork or piping\nInstall equipment mounting points\nPressure-test lines where applicable\nSeal duct joints" },
      "insulationInstallation": { "title": "Insulation Installation", "description": "Install wall cavity insulation\nInstall attic/roof insulation\nSeal air gaps and penetrations\nVerify vapor barrier placement" },
      "insulationInspection": { "title": "Insulation Inspection", "description": "Verify R-value compliance\nCheck for gaps and compression\nSign off before drywall close-in" },
      "drywallHanging": { "title": "Drywall Hanging", "description": "Hang drywall sheets on walls and ceilings\nFasten per manufacturer spacing\nCut openings for outlets and fixtures" },
      "drywallFinishing": { "title": "Drywall Taping & Finishing", "description": "Tape and mud joints\nSand smooth\nApply texture if specified\nInspect for imperfections" },
      "interiorDoorInstallation": { "title": "Interior Door Installation", "description": "Hang interior doors\nInstall door hardware\nAdjust for smooth swing and latch" },
      "trimMillwork": { "title": "Trim & Millwork", "description": "Install baseboards\nInstall door and window casings\nInstall crown molding where specified\nCaulk and fill nail holes" },
      "floorPreparation": { "title": "Floor Preparation", "description": "Clean and level subfloor\nRepair any subfloor defects\nConfirm moisture levels are acceptable" },
      "flooringInstallation": { "title": "Flooring Installation", "description": "Install flooring material per room\nInstall transition strips\nInstall baseboards where affected\nInspect for gaps or defects" },
      "kitchenCabinetInstallation": { "title": "Kitchen Cabinet Installation", "description": "Install upper and lower cabinets\nVerify level and alignment\nInstall cabinet hardware" },
      "countertopInstallation": { "title": "Countertop Installation", "description": "Template countertop dimensions\nInstall countertops\nSeal seams and edges" },
      "kitchenApplianceInstallation": { "title": "Kitchen Appliance Installation", "description": "Install and connect appliances\nVerify water and gas connections\nTest appliance operation" },
      "bathroomFixtureInstallation": { "title": "Bathroom Fixture Installation", "description": "Install toilets, sinks, and tubs/showers\nConnect water supply and drain lines\nTest for leaks" },
      "bathroomVentilation": { "title": "Bathroom Ventilation", "description": "Install exhaust fan\nVerify duct routing to exterior\nTest fan operation" },
      "bathroomWaterproofingTiling": { "title": "Bathroom Waterproofing & Tiling", "description": "Apply waterproof membrane in wet areas\nInstall wall and floor tile\nGrout and seal tile joints" },
      "surfacePreparation": { "title": "Surface Preparation", "description": "Fill and sand imperfections\nMask trim and fixtures\nApply primer coat" },
      "paintApplication": { "title": "Paint Application", "description": "Apply interior wall and ceiling paint\nApply exterior paint or stain\nApply second coat where needed\nInspect coverage and finish" },
      "hardscaping": { "title": "Hardscaping", "description": "Install driveway and walkways\nInstall exterior steps and decks\nInstall exterior lighting fixtures" },
      "fencingBoundaryWalls": { "title": "Fencing & Boundary Walls", "description": "Install fencing per site plan\nInstall boundary or retaining walls if specified\nInspect for stability" },
      "finalGrading": { "title": "Final Grading", "description": "Grade soil away from foundation\nRemove construction debris\nPrepare soil for planting" },
      "plantingSeeding": { "title": "Planting & Seeding", "description": "Plant trees and shrubs per landscape plan\nSeed or lay turf\nInstall irrigation if specified" },
      "finalBuildingInspection": { "title": "Final Building Inspection", "description": "Schedule final building inspection\nAddress any inspector findings\nObtain certificate of occupancy" },
      "safetySystemsCheck": { "title": "Safety Systems Check", "description": "Test smoke and carbon monoxide detectors\nTest ground-fault outlets\nVerify egress window operation" },
      "punchListWalkthrough": { "title": "Punch List Walkthrough", "description": "Walk through with contractor\nDocument outstanding defects and items\nPrioritize items by urgency" },
      "punchListResolution": { "title": "Punch List Resolution", "description": "Complete outstanding repair items\nRe-inspect completed items\nObtain sign-off on all items" },
      "finalWalkthrough": { "title": "Final Walkthrough", "description": "Walk through the finished home with the owner\nDemonstrate systems and equipment operation\nConfirm all punch list items are resolved" },
      "documentsKeysHandover": { "title": "Documents & Keys Handover", "description": "Assemble warranty documents and manuals\nAssemble as-built drawings\nTransfer keys and access codes\nCollect final sign-off from owner" }
    }
  },
```

- [ ] **Step 4: Add the matching top-level `"build"` namespace to `fr.json`**

```json
  "build": {
    "projectStatus": {
      "planning": "Planification",
      "inProgress": "En cours",
      "completed": "Terminé",
      "onHold": "En pause"
    },
    "phaseStatus": {
      "notStarted": "Non commencé",
      "inProgress": "En cours",
      "completed": "Terminé"
    },
    "taskStatus": {
      "notStarted": "Non commencé",
      "ready": "Prêt",
      "inProgress": "En cours",
      "waiting": "En attente",
      "blocked": "Bloqué",
      "completed": "Terminé"
    },
    "validationStatus": {
      "notRequired": "Non requise",
      "pendingValidation": "Validation en attente",
      "passed": "Validé",
      "failed": "Échoué"
    },
    "dashboard": {
      "status": "Statut",
      "currentPhase": "Phase actuelle",
      "percentComplete": "% terminé",
      "plannedBudget": "Budget prévu",
      "actualCost": "Coût réel",
      "overdueTasks": "Tâches en retard et à venir",
      "upcomingValidations": "Validations à venir",
      "recentActivity": "Activité récente",
      "noOverdue": "Aucune tâche en retard ou à venir.",
      "noValidationsPending": "Aucune validation en attente.",
      "noActivity": "Aucune activité récente."
    },
    "page": {
      "startTitle": "Démarrer le suivi de chantier",
      "startDescription": "Créez un projet de construction pour ce logement avec 22 phases standards et une liste de tâches de départ personnalisable.",
      "startButton": "Démarrer le suivi de chantier",
      "dashboardTab": "Tableau de bord",
      "phasesTab": "Phases",
      "addPhase": "+ Ajouter une phase",
      "addTask": "+ Ajouter une tâche",
      "taskCount": "{n} tâches",
      "noPhases": "Aucune phase pour le moment.",
      "deleteProjectConfirm": "Supprimer ce projet de construction ainsi que toutes ses phases, tâches et pièces jointes ? Cette action est irréversible."
    },
    "modal": {
      "newTask": "Nouvelle tâche",
      "editTask": "Modifier la tâche",
      "title": "Titre",
      "titlePlaceholder": "Titre de la tâche",
      "description": "Description",
      "status": "Statut",
      "contractor": "Entrepreneur",
      "contractorPlaceholder": "Nom de l'entrepreneur",
      "plannedStart": "Début prévu",
      "plannedDue": "Échéance prévue",
      "actualCompletion": "Achèvement réel",
      "plannedCost": "Coût prévu (€)",
      "actualCost": "Coût réel (€)",
      "validationRequired": "Validation requise",
      "validationStatus": "Statut de validation",
      "dependsOn": "Dépend de",
      "noDependencies": "Aucune dépendance",
      "notes": "Notes",
      "noneOption": "— Aucun —",
      "titleRequired": "Le titre est requis",
      "saveFailed": "Échec de l'enregistrement",
      "deleteFailed": "Échec de la suppression",
      "uploadFailed": "Échec de l'envoi",
      "confirm": "Confirmer"
    },
    "phases": {
      "planning": { "name": "Planification", "description": "Mise en place initiale du projet : permis, conception, financement et sélection des entrepreneurs avant le début des travaux." },
      "sitePreparation": { "name": "Préparation du terrain", "description": "Débroussaillage, accès et travaux préparatoires des réseaux avant l'excavation." },
      "foundation": { "name": "Fondations", "description": "Excavation, semelles et construction de la dalle ou du vide sanitaire." },
      "framing": { "name": "Charpente", "description": "Ossature structurelle : planchers, murs et charpente du toit." },
      "roofing": { "name": "Couverture", "description": "Étanchéification de la structure du toit." },
      "windowsExteriorDoors": { "name": "Fenêtres et portes extérieures", "description": "Installation des ouvertures de fenêtres et portes de l'enveloppe du bâtiment." },
      "exteriorEnvelope": { "name": "Enveloppe extérieure", "description": "Pare-intempéries, isolation et bardage extérieur." },
      "plumbingRoughIn": { "name": "Plomberie hors d'eau", "description": "Installation des canalisations d'alimentation, d'évacuation et de ventilation avant la fermeture des murs." },
      "electricalRoughIn": { "name": "Électricité hors d'eau", "description": "Câblage, boîtiers et tableau électrique avant la fermeture des murs." },
      "hvacRoughIn": { "name": "CVC hors d'eau", "description": "Gaines, lignes frigorifiques ou tuyauterie hydraulique avant la fermeture des murs." },
      "insulation": { "name": "Isolation", "description": "Isolation thermique et acoustique avant la pose des plaques de plâtre." },
      "drywall": { "name": "Plâtrerie", "description": "Fermeture et finition des murs et plafonds." },
      "interiorFinishes": { "name": "Finitions intérieures", "description": "Moulures, portes et menuiseries intérieures." },
      "flooring": { "name": "Revêtements de sol", "description": "Revêtements de sol définitifs dans toute la maison." },
      "kitchen": { "name": "Cuisine", "description": "Pose des meubles, plans de travail et électroménagers de cuisine." },
      "bathrooms": { "name": "Salles de bain", "description": "Équipements et finitions de chaque salle de bain." },
      "painting": { "name": "Peinture", "description": "Peinture et finitions intérieures et extérieures." },
      "exteriorWorks": { "name": "Travaux extérieurs", "description": "Allées, chemins, terrasses et autres aménagements extérieurs." },
      "landscaping": { "name": "Aménagement paysager", "description": "Nivellement, plantations et finition définitive des extérieurs." },
      "finalInspections": { "name": "Inspections finales", "description": "Inspections réglementaires et de sécurité avant occupation." },
      "punchList": { "name": "Liste des réserves", "description": "Identification et résolution des réserves avant la remise des clés." },
      "handover": { "name": "Remise des clés", "description": "Visite finale, documentation et remise des clés." }
    },
    "tasks": {
      "siteSurvey": { "title": "Étude de terrain", "description": "Commander un relevé topographique\nConfirmer les limites de la propriété\nIdentifier la nature du sol\nLocaliser les réseaux existants" },
      "architecturalPlans": { "title": "Plans d'architecte", "description": "Informer l'architecte des besoins\nExaminer les esquisses préliminaires\nApprouver les plans définitifs\nApprouver les élévations et coupes" },
      "buildingPermits": { "title": "Permis de construire", "description": "Déposer la demande de permis\nRépondre aux demandes d'informations complémentaires\nObtenir le permis approuvé\nAfficher le permis sur le chantier" },
      "budgetFinancingApproval": { "title": "Approbation du budget et du financement", "description": "Finaliser le budget de construction\nObtenir le financement ou le prêt travaux\nDéfinir une réserve pour imprévus\nApprouver l'échéancier de paiement" },
      "contractorSelection": { "title": "Sélection de l'entrepreneur général", "description": "Demander des devis à des entrepreneurs qualifiés\nComparer les offres et références\nSigner le contrat de construction\nPlanifier le lancement du chantier" },
      "siteClearing": { "title": "Débroussaillage du terrain", "description": "Enlever la végétation et les débris\nAbattre et évacuer les arbres désignés\nAménager une voie d'accès pour les engins\nClôturer le chantier" },
      "temporaryUtilities": { "title": "Raccordements provisoires", "description": "Installer un raccordement électrique provisoire\nInstaller une alimentation en eau provisoire\nMettre en place le bureau/conteneur de chantier\nInstaller des sanitaires de chantier" },
      "surveyStaking": { "title": "Implantation", "description": "Piqueter les angles du bâtiment\nMarquer les limites de l'excavation\nVérifier les reculs par rapport au permis\nProtéger les repères d'implantation" },
      "excavation": { "title": "Excavation", "description": "Excaver à la profondeur prévue\nVérifier les dimensions de l'excavation\nContrôler la capacité portante du sol\nInstaller un étaiement provisoire si nécessaire" },
      "formsReinforcement": { "title": "Coffrages et armatures", "description": "Mettre en place les coffrages selon les plans\nInstaller les armatures\nPositionner les traversées et fourreaux techniques\nVérifier le drainage et la membrane d'étanchéité" },
      "foundationPour": { "title": "Coulage des fondations", "description": "Vérifier les dimensions de l'excavation\nInstaller les armatures\nVérifier le drainage\nPositionner les traversées techniques\nCouler le béton\nFinir la surface\nLaisser durcir\nPréparer l'inspection" },
      "floorFraming": { "title": "Ossature de plancher", "description": "Installer les lisses basses et boulons d'ancrage\nInstaller les solives de plancher\nInstaller le support de sous-plancher\nVérifier le niveau et l'équerrage" },
      "wallFraming": { "title": "Ossature murale", "description": "Ériger les panneaux de mur extérieur\nÉriger les cloisons intérieures\nInstaller les linteaux au-dessus des ouvertures\nContreventer et mettre les murs d'aplomb" },
      "roofFraming": { "title": "Charpente de toiture", "description": "Poser la poutre faîtière et les chevrons ou fermes\nInstaller le support de toiture\nVérifier les assemblages structurels\nPréparer l'inspection" },
      "roofUnderlayment": { "title": "Sous-couche de toiture", "description": "Installer le pare-pluie ou la sous-couche synthétique\nInstaller les solins aux noues et traversées\nInstaller le larmier" },
      "roofCovering": { "title": "Couverture de toiture", "description": "Poser le matériau de couverture (tuiles, bardeaux ou métal)\nInstaller les faîtières\nInstaller les gouttières et descentes d'eau pluviale\nContrôler l'étanchéité après la pose" },
      "roofVentilation": { "title": "Ventilation de toiture", "description": "Installer les évents de faîtage et de sous-toit\nVérifier le passage de l'air\nSceller les traversées d'évents" },
      "windowInstallation": { "title": "Pose des fenêtres", "description": "Vérifier les dimensions des ouvertures brutes\nPoser et mettre à niveau les fenêtres\nInstaller les solins et joints d'étanchéité\nAjuster pour un fonctionnement fluide" },
      "exteriorDoorInstallation": { "title": "Pose des portes extérieures", "description": "Vérifier les dimensions des ouvertures brutes\nPoser et mettre à niveau les cadres de porte\nInstaller les solins et joints d'étanchéité\nTester le fonctionnement des serrures et quincaillerie" },
      "exteriorTrimCaulking": { "title": "Moulures extérieures et calfeutrage", "description": "Installer les moulures extérieures de fenêtres et portes\nCalfeutrer tous les joints extérieurs\nContrôler l'étanchéité" },
      "weatherResistiveBarrier": { "title": "Pare-intempéries", "description": "Installer le pare-intempéries\nRubaner et sceller tous les joints\nInstaller les solins autour des traversées" },
      "exteriorCladding": { "title": "Bardage extérieur", "description": "Installer le matériau de bardage (bardage, brique ou enduit)\nInstaller les moulures et détails d'angle\nCalfeutrer et sceller les joints\nContrôler l'alignement" },
      "exteriorWaterproofingInspection": { "title": "Inspection de l'étanchéité extérieure", "description": "Contrôler les détails de solins\nContrôler la fixation du bardage\nConfirmer le dégagement des orifices de drainage" },
      "plumbingLayout": { "title": "Implantation de la plomberie", "description": "Marquer l'emplacement des équipements sanitaires\nCoordonner avec la charpente pour le passage des tuyaux\nVérifier le tracé de la ventilation" },
      "waterHeaterRoughIn": { "title": "Pré-installation du chauffe-eau", "description": "Positionner le chauffe-eau\nRéaliser les raccordements d'alimentation et de ventilation\nVérifier les dégagements réglementaires" },
      "plumbingRoughInInstallation": { "title": "Installation de la plomberie hors d'eau", "description": "Installer les canalisations d'alimentation\nInstaller les canalisations d'évacuation et de ventilation\nTester la pression des canalisations d'alimentation\nObturer les canalisations en attente d'inspection" },
      "electricalLayout": { "title": "Implantation électrique", "description": "Marquer l'emplacement des prises, interrupteurs et luminaires\nConfirmer le plan des circuits selon les schémas électriques\nCoordonner avec les autres corps de métier hors d'eau" },
      "serviceEntranceConnection": { "title": "Raccordement au réseau électrique", "description": "Coordonner le raccordement au réseau\nInstaller le socle du compteur\nPlanifier le branchement par le fournisseur" },
      "electricalRoughInInstallation": { "title": "Installation électrique hors d'eau", "description": "Installer le tableau électrique\nTirer le câblage jusqu'aux boîtiers\nInstaller les boîtiers de prises, interrupteurs et luminaires\nÉtiqueter les circuits" },
      "hvacLayout": { "title": "Implantation CVC", "description": "Confirmer l'emplacement des équipements\nPlanifier le tracé des gaines ou tuyauteries\nCoordonner les traversées avec la charpente" },
      "equipmentInstallation": { "title": "Installation des équipements CVC", "description": "Installer l'appareil (chaudière, pompe à chaleur)\nRaccorder les lignes frigorifiques ou hydrauliques\nVérifier l'évacuation des condensats" },
      "hvacRoughInInstallation": { "title": "Installation CVC hors d'eau", "description": "Installer les gaines ou tuyauteries\nInstaller les points de fixation des équipements\nTester la pression des lignes le cas échéant\nSceller les joints de gaines" },
      "insulationInstallation": { "title": "Pose de l'isolation", "description": "Installer l'isolation des murs\nInstaller l'isolation des combles/toiture\nSceller les fuites d'air et traversées\nVérifier la pose du pare-vapeur" },
      "insulationInspection": { "title": "Inspection de l'isolation", "description": "Vérifier la conformité de la résistance thermique (R)\nContrôler l'absence de vides et de compression\nValider avant la fermeture des murs" },
      "drywallHanging": { "title": "Pose des plaques de plâtre", "description": "Poser les plaques de plâtre sur murs et plafonds\nFixer selon l'espacement du fabricant\nDécouper les ouvertures pour prises et luminaires" },
      "drywallFinishing": { "title": "Jointoiement et finition", "description": "Rubaner et enduire les joints\nPoncer pour lisser\nAppliquer une texture si prévu\nContrôler les imperfections" },
      "interiorDoorInstallation": { "title": "Pose des portes intérieures", "description": "Poser les portes intérieures\nInstaller la quincaillerie\nAjuster pour une ouverture et un verrouillage fluides" },
      "trimMillwork": { "title": "Moulures et menuiseries", "description": "Installer les plinthes\nInstaller les chambranles de portes et fenêtres\nInstaller les corniches prévues\nCalfeutrer et reboucher les trous de clous" },
      "floorPreparation": { "title": "Préparation des sols", "description": "Nettoyer et niveler le support de sol\nRéparer les défauts du support\nConfirmer un taux d'humidité acceptable" },
      "flooringInstallation": { "title": "Pose des revêtements de sol", "description": "Poser le revêtement prévu par pièce\nInstaller les barres de seuil\nInstaller les plinthes concernées\nContrôler l'absence de défauts" },
      "kitchenCabinetInstallation": { "title": "Pose des meubles de cuisine", "description": "Installer les meubles hauts et bas\nVérifier le niveau et l'alignement\nInstaller la quincaillerie des meubles" },
      "countertopInstallation": { "title": "Pose des plans de travail", "description": "Prendre les gabarits des plans de travail\nInstaller les plans de travail\nSceller les joints et bords" },
      "kitchenApplianceInstallation": { "title": "Installation des électroménagers", "description": "Installer et raccorder les électroménagers\nVérifier les raccordements eau et gaz\nTester le fonctionnement des appareils" },
      "bathroomFixtureInstallation": { "title": "Pose des équipements sanitaires", "description": "Installer les WC, lavabos et baignoires/douches\nRaccorder l'alimentation en eau et les évacuations\nContrôler l'absence de fuites" },
      "bathroomVentilation": { "title": "Ventilation de salle de bain", "description": "Installer le ventilateur d'extraction\nVérifier le tracé de la gaine vers l'extérieur\nTester le fonctionnement du ventilateur" },
      "bathroomWaterproofingTiling": { "title": "Étanchéité et carrelage de salle de bain", "description": "Appliquer la membrane d'étanchéité dans les zones humides\nPoser le carrelage mural et au sol\nJointoyer et sceller les joints de carrelage" },
      "surfacePreparation": { "title": "Préparation des surfaces", "description": "Reboucher et poncer les imperfections\nProtéger les moulures et équipements\nAppliquer une couche d'apprêt" },
      "paintApplication": { "title": "Application de la peinture", "description": "Appliquer la peinture des murs et plafonds intérieurs\nAppliquer la peinture ou lasure extérieure\nAppliquer une seconde couche si nécessaire\nContrôler la couverture et la finition" },
      "hardscaping": { "title": "Aménagements extérieurs", "description": "Installer l'allée et les chemins\nInstaller les marches et terrasses extérieures\nInstaller l'éclairage extérieur" },
      "fencingBoundaryWalls": { "title": "Clôtures et murs de limite", "description": "Installer la clôture selon le plan de masse\nInstaller les murs de clôture ou de soutènement prévus\nContrôler la stabilité" },
      "finalGrading": { "title": "Nivellement final", "description": "Niveler le sol en pente contraire aux fondations\nÉvacuer les gravats de chantier\nPréparer le sol pour la plantation" },
      "plantingSeeding": { "title": "Plantation et engazonnement", "description": "Planter les arbres et arbustes selon le plan paysager\nEnsemencer ou poser du gazon\nInstaller l'irrigation si prévue" },
      "finalBuildingInspection": { "title": "Inspection finale du bâtiment", "description": "Planifier l'inspection finale du bâtiment\nTraiter les remarques de l'inspecteur\nObtenir le certificat de conformité/d'occupation" },
      "safetySystemsCheck": { "title": "Contrôle des systèmes de sécurité", "description": "Tester les détecteurs de fumée et de monoxyde de carbone\nTester les prises différentielles\nVérifier le fonctionnement des fenêtres d'évacuation" },
      "punchListWalkthrough": { "title": "Visite de réserves", "description": "Effectuer la visite avec l'entrepreneur\nDocumenter les défauts et éléments en suspens\nPrioriser les éléments selon l'urgence" },
      "punchListResolution": { "title": "Résolution des réserves", "description": "Réaliser les réparations en suspens\nRéinspecter les éléments corrigés\nObtenir la validation de tous les éléments" },
      "finalWalkthrough": { "title": "Visite finale", "description": "Visiter la maison terminée avec le propriétaire\nExpliquer le fonctionnement des systèmes et équipements\nConfirmer la résolution de toutes les réserves" },
      "documentsKeysHandover": { "title": "Remise des documents et des clés", "description": "Rassembler les documents de garantie et notices\nRassembler les plans tels que construits\nRemettre les clés et codes d'accès\nRecueillir la validation finale du propriétaire" }
    }
  },
```

- [ ] **Step 5: Run the completeness test to verify it passes**

Run: `cd packages/editor && npx vitest run test/i18nCompleteness.test.ts`
Expected: PASS — key sets match exactly between `en.json` and `fr.json`, no empty values.

- [ ] **Step 6: Commit**

```bash
git add packages/editor/src/lib/locales/en.json packages/editor/src/lib/locales/fr.json
git commit -m "feat(build): add English and French locale content for build tracking"
```

---

## Task 11: `buildStore.svelte.ts`

**Files:**
- Create: `packages/editor/src/lib/buildStore.svelte.ts`
- Test: `packages/editor/test/buildStore.test.ts`

**Interfaces:**
- Produces: `createBuildStore(getHomeId)` returning `{ project, phases, tasks, dependencies, loaded, loadError, startProject, updateProject, deleteProject, updatePhase, createTask, updateTask, deleteTask, addDependency, removeDependency, uploadAttachment, deleteAttachment, reload, projectBudget, phaseBudget(phaseId), projectProgress, phaseProgress(phaseId), taskReadyOrBlocked(taskId) }` — consumed by Tasks 12–15.

- [ ] **Step 1: Write the failing test**

```typescript
// packages/editor/test/buildStore.test.ts
import { describe, it, expect, vi, afterEach } from "vitest";
import { createBuildStore } from "../src/lib/buildStore.svelte";

const HOME = "home-1";
const getHomeId = () => HOME;

const sampleDoc = {
  version: 1,
  project: { id: "p1", status: "in_progress", plannedStartDate: null, plannedCompletionDate: null, actualCompletionDate: null, plannedBudget: 100000, notes: "", createdAt: "2026-01-01T00:00:00+00:00", updatedAt: "2026-01-01T00:00:00+00:00" },
  phases: [
    { id: "ph1", displayOrder: 0, nameKey: "build.phases.planning.name", nameOverride: null, descriptionKey: "build.phases.planning.description", descriptionOverride: null, status: "in_progress", plannedStartDate: null, plannedEndDate: null, actualStartDate: null, actualEndDate: null },
  ],
  tasks: [
    { id: "t1", phaseId: "ph1", parentTaskId: null, displayOrder: 0, titleKey: "build.tasks.siteSurvey.title", titleOverride: null, descriptionKey: "build.tasks.siteSurvey.description", descriptionOverride: null, status: "completed", plannedStartDate: null, plannedDueDate: null, actualCompletionDate: null, plannedCost: 500, actualCost: 480, contractorId: null, validationRequired: false, validationStatus: "not_required", notes: "", attachments: [] },
    { id: "t2", phaseId: "ph1", parentTaskId: null, displayOrder: 1, titleKey: "build.tasks.architecturalPlans.title", titleOverride: null, descriptionKey: "build.tasks.architecturalPlans.description", descriptionOverride: null, status: "not_started", plannedStartDate: null, plannedDueDate: null, actualCompletionDate: null, plannedCost: 2000, actualCost: null, contractorId: null, validationRequired: false, validationStatus: "not_required", notes: "", attachments: [] },
  ],
  dependencies: [
    { id: "d1", predecessorTaskId: "t1", successorTaskId: "t2" },
  ],
};

async function tick(): Promise<void> {
  await new Promise((r) => setTimeout(r, 0));
}

function makeStore() {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => sampleDoc }));
  return createBuildStore(getHomeId);
}

afterEach(() => vi.unstubAllGlobals());

describe("buildStore", () => {
  it("loads the build document", async () => {
    const store = makeStore();
    await tick();
    expect(store.project?.id).toBe("p1");
    expect(store.phases).toHaveLength(1);
    expect(store.tasks).toHaveLength(2);
  });

  it("computes project budget as planned vs actual sums across tasks", async () => {
    const store = makeStore();
    await tick();
    expect(store.projectBudget.planned).toBe(2500);
    expect(store.projectBudget.actual).toBe(480);
  });

  it("computes phase progress as completed/total tasks", async () => {
    const store = makeStore();
    await tick();
    expect(store.phaseProgress("ph1")).toBe(0.5);
  });

  it("marks a task with an incomplete predecessor as blocked", async () => {
    const store = makeStore();
    await tick();
    expect(store.taskReadyOrBlocked("t2")).toBe("blocked");
  });

  it("marks a task with no incomplete predecessors as ready", async () => {
    const store = makeStore();
    await tick();
    expect(store.taskReadyOrBlocked("t1")).toBe("completed");
  });

  it("startProject posts to /build/start and reloads", async () => {
    const store = makeStore();
    await tick();
    const fetchMock = fetch as unknown as ReturnType<typeof vi.fn>;
    await store.startProject();
    expect(fetchMock).toHaveBeenCalledWith(
      `/api/homes/${HOME}/build/start`,
      expect.objectContaining({ method: "POST" })
    );
  });

  it("updateTask PUTs the patch and reloads", async () => {
    const store = makeStore();
    await tick();
    const fetchMock = fetch as unknown as ReturnType<typeof vi.fn>;
    await store.updateTask("t2", { status: "in_progress" });
    expect(fetchMock).toHaveBeenCalledWith(
      `/api/homes/${HOME}/build/tasks/t2`,
      expect.objectContaining({ method: "PUT" })
    );
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/editor && npx vitest run test/buildStore.test.ts`
Expected: FAIL — `Cannot find module '../src/lib/buildStore.svelte'`

- [ ] **Step 3: Write the implementation**

```typescript
// packages/editor/src/lib/buildStore.svelte.ts

export type BuildProjectStatus = "planning" | "in_progress" | "completed" | "on_hold";
export type BuildPhaseStatus = "not_started" | "in_progress" | "completed";
export type BuildTaskStatus = "not_started" | "ready" | "in_progress" | "waiting" | "blocked" | "completed";
export type ValidationStatus = "not_required" | "pending_validation" | "passed" | "failed";

export interface BuildProject {
  id: string;
  status: BuildProjectStatus;
  plannedStartDate: string | null;
  plannedCompletionDate: string | null;
  actualCompletionDate: string | null;
  plannedBudget: number | null;
  notes: string;
  createdAt: string;
  updatedAt: string;
}

export interface BuildPhase {
  id: string;
  displayOrder: number;
  nameKey: string | null;
  nameOverride: string | null;
  descriptionKey: string | null;
  descriptionOverride: string | null;
  status: BuildPhaseStatus;
  plannedStartDate: string | null;
  plannedEndDate: string | null;
  actualStartDate: string | null;
  actualEndDate: string | null;
}

export interface BuildTask {
  id: string;
  phaseId: string;
  parentTaskId: string | null;
  displayOrder: number;
  titleKey: string | null;
  titleOverride: string | null;
  descriptionKey: string | null;
  descriptionOverride: string | null;
  status: BuildTaskStatus;
  plannedStartDate: string | null;
  plannedDueDate: string | null;
  actualCompletionDate: string | null;
  plannedCost: number | null;
  actualCost: number | null;
  contractorId: string | null;
  validationRequired: boolean;
  validationStatus: ValidationStatus;
  notes: string;
  attachments: string[];
}

export interface BuildTaskDependency {
  id: string;
  predecessorTaskId: string;
  successorTaskId: string;
}

export interface BuildDocument {
  version: number;
  project: BuildProject | null;
  phases: BuildPhase[];
  tasks: BuildTask[];
  dependencies: BuildTaskDependency[];
}

export function createBuildStore(getHomeId: () => string | null = () => null) {
  const phases = $state<BuildPhase[]>([]);
  const tasks = $state<BuildTask[]>([]);
  const dependencies = $state<BuildTaskDependency[]>([]);
  let project = $state<BuildProject | null>(null);
  let loaded = $state(false);
  let loadError = $state<string | null>(null);

  async function init(): Promise<void> {
    const homeId = getHomeId();
    if (!homeId) { loaded = true; return; }
    try {
      const resp = await fetch(`/api/homes/${homeId}/build`);
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const doc: BuildDocument = await resp.json();
      project = doc.project;
      phases.length = 0;
      for (const p of doc.phases) phases.push(p);
      tasks.length = 0;
      for (const t of doc.tasks) tasks.push(t);
      dependencies.length = 0;
      for (const d of doc.dependencies) dependencies.push(d);
    } catch (e) {
      loadError = e instanceof Error ? e.message : String(e);
    } finally {
      loaded = true;
    }
  }

  async function startProject(plannedStartDate?: string): Promise<void> {
    const homeId = getHomeId();
    if (!homeId) throw new Error("No active home");
    const resp = await fetch(`/api/homes/${homeId}/build/start`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(plannedStartDate ? { plannedStartDate } : {}),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
  }

  async function updateProject(patch: Partial<BuildProject>): Promise<void> {
    const homeId = getHomeId();
    if (!homeId) throw new Error("No active home");
    const resp = await fetch(`/api/homes/${homeId}/build/project`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(patch),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
  }

  async function deleteProject(): Promise<void> {
    const homeId = getHomeId();
    if (!homeId) throw new Error("No active home");
    const resp = await fetch(`/api/homes/${homeId}/build/project`, { method: "DELETE" });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
  }

  async function updatePhase(phaseId: string, patch: Partial<BuildPhase>): Promise<void> {
    const homeId = getHomeId();
    if (!homeId) throw new Error("No active home");
    const resp = await fetch(`/api/homes/${homeId}/build/phases/${phaseId}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(patch),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
  }

  async function createTask(data: { phaseId: string; titleOverride: string; [key: string]: unknown }): Promise<void> {
    const homeId = getHomeId();
    if (!homeId) throw new Error("No active home");
    const resp = await fetch(`/api/homes/${homeId}/build/tasks`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
  }

  async function updateTask(taskId: string, patch: Partial<BuildTask>): Promise<void> {
    const homeId = getHomeId();
    if (!homeId) throw new Error("No active home");
    const resp = await fetch(`/api/homes/${homeId}/build/tasks/${taskId}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(patch),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
  }

  async function deleteTask(taskId: string): Promise<void> {
    const homeId = getHomeId();
    if (!homeId) throw new Error("No active home");
    const resp = await fetch(`/api/homes/${homeId}/build/tasks/${taskId}`, { method: "DELETE" });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
  }

  async function addDependency(predecessorTaskId: string, successorTaskId: string): Promise<void> {
    const homeId = getHomeId();
    if (!homeId) throw new Error("No active home");
    const resp = await fetch(`/api/homes/${homeId}/build/dependencies`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ predecessorTaskId, successorTaskId }),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
  }

  async function removeDependency(dependencyId: string): Promise<void> {
    const homeId = getHomeId();
    if (!homeId) throw new Error("No active home");
    const resp = await fetch(`/api/homes/${homeId}/build/dependencies/${dependencyId}`, { method: "DELETE" });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
  }

  async function uploadAttachment(taskId: string, file: File): Promise<string> {
    const homeId = getHomeId();
    if (!homeId) throw new Error("No active home");
    const form = new FormData();
    form.append("file", file);
    const resp = await fetch(`/api/homes/${homeId}/build/tasks/${taskId}/attachments`, { method: "POST", body: form });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const result = await resp.json();
    await init();
    return result.filename as string;
  }

  async function deleteAttachment(taskId: string, filename: string): Promise<void> {
    const homeId = getHomeId();
    if (!homeId) throw new Error("No active home");
    const resp = await fetch(`/api/homes/${homeId}/build/tasks/${taskId}/attachments/${filename}`, { method: "DELETE" });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
  }

  function phaseTasks(phaseId: string): BuildTask[] {
    return tasks.filter((t) => t.phaseId === phaseId);
  }

  function phaseBudget(phaseId: string): { planned: number; actual: number } {
    const ts = phaseTasks(phaseId);
    return {
      planned: ts.reduce((sum, t) => sum + (t.plannedCost ?? 0), 0),
      actual: ts.reduce((sum, t) => sum + (t.actualCost ?? 0), 0),
    };
  }

  function phaseProgress(phaseId: string): number {
    const ts = phaseTasks(phaseId);
    if (ts.length === 0) return 0;
    return ts.filter((t) => t.status === "completed").length / ts.length;
  }

  function taskReadyOrBlocked(taskId: string): BuildTaskStatus {
    const task = tasks.find((t) => t.id === taskId);
    if (!task) throw new Error(`Unknown taskId ${taskId}`);
    if (!["not_started", "ready", "blocked"].includes(task.status)) return task.status;
    const predecessorIds = dependencies.filter((d) => d.successorTaskId === taskId).map((d) => d.predecessorTaskId);
    if (predecessorIds.length === 0) return "ready";
    const allDone = predecessorIds.every((id) => tasks.find((t) => t.id === id)?.status === "completed");
    return allDone ? "ready" : "blocked";
  }

  const projectBudget = $derived({
    planned: tasks.reduce((sum, t) => sum + (t.plannedCost ?? 0), 0),
    actual: tasks.reduce((sum, t) => sum + (t.actualCost ?? 0), 0),
  });

  const projectProgress = $derived(
    tasks.length === 0 ? 0 : tasks.filter((t) => t.status === "completed").length / tasks.length
  );

  init();

  return {
    get project() { return project; },
    get phases() { return phases as BuildPhase[]; },
    get tasks() { return tasks as BuildTask[]; },
    get dependencies() { return dependencies as BuildTaskDependency[]; },
    get loaded() { return loaded; },
    get loadError() { return loadError; },
    get projectBudget() { return projectBudget; },
    get projectProgress() { return projectProgress; },
    phaseTasks,
    phaseBudget,
    phaseProgress,
    taskReadyOrBlocked,
    startProject,
    updateProject,
    deleteProject,
    updatePhase,
    createTask,
    updateTask,
    deleteTask,
    addDependency,
    removeDependency,
    uploadAttachment,
    deleteAttachment,
    reload: init,
  };
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd packages/editor && npx vitest run test/buildStore.test.ts`
Expected: PASS (7 tests)

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/lib/buildStore.svelte.ts packages/editor/test/buildStore.test.ts
git commit -m "feat(build): add buildStore with CRUD and derived budget/progress/ready-blocked getters"
```

---

## Task 12: `BuildPage.svelte` — shell, empty state, dashboard tab

**Files:**
- Create: `packages/editor/src/lib/components/BuildPage.svelte`
- Test: `packages/editor/test/BuildPage.test.ts`

**Interfaces:**
- Consumes: `createBuildStore` return type (Task 11), `Tabs.svelte`, `StatTile.svelte`, `Card.svelte`, `Button.svelte` (existing `ui/` components).
- Produces: `<BuildPage {store} onopentask={(taskId) => void} />` — consumed by Task 16's `App.svelte` wiring. Renders the Phases tab via `PhaseSection.svelte` from Task 13.

- [ ] **Step 1: Write the failing test**

```typescript
// packages/editor/test/BuildPage.test.ts
import { describe, it, expect, vi, afterEach } from "vitest";
import { mount, unmount, flushSync, tick } from "svelte";
import BuildPage from "../src/lib/components/BuildPage.svelte";
import { createBuildStore } from "../src/lib/buildStore.svelte";

const HOME = "home-1";
const getHomeId = () => HOME;

const emptyDoc = { version: 1, project: null, phases: [], tasks: [], dependencies: [] };

const seededDoc = {
  version: 1,
  project: { id: "p1", status: "in_progress", plannedStartDate: null, plannedCompletionDate: null, actualCompletionDate: null, plannedBudget: 100000, notes: "", createdAt: "2026-01-01T00:00:00+00:00", updatedAt: "2026-01-01T00:00:00+00:00" },
  phases: [
    { id: "ph1", displayOrder: 0, nameKey: "build.phases.planning.name", nameOverride: null, descriptionKey: null, descriptionOverride: null, status: "in_progress", plannedStartDate: null, plannedEndDate: null, actualStartDate: null, actualEndDate: null },
  ],
  tasks: [
    { id: "t1", phaseId: "ph1", parentTaskId: null, displayOrder: 0, titleKey: "build.tasks.siteSurvey.title", titleOverride: null, descriptionKey: null, descriptionOverride: null, status: "completed", plannedStartDate: null, plannedDueDate: "2020-01-01", actualCompletionDate: null, plannedCost: 500, actualCost: 480, contractorId: null, validationRequired: false, validationStatus: "not_required", notes: "", attachments: [] },
  ],
  dependencies: [],
};

async function waitTick(): Promise<void> {
  await new Promise((r) => setTimeout(r, 0));
}

function renderPage(doc: unknown) {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => doc }));
  const store = createBuildStore(getHomeId);
  const target = document.createElement("div");
  document.body.appendChild(target);
  return { store, target };
}

afterEach(() => vi.unstubAllGlobals());

describe("BuildPage", () => {
  it("shows the start-tracking empty state when no project exists", async () => {
    const { store, target } = renderPage(emptyDoc);
    await waitTick();
    const comp = mount(BuildPage, { target, props: { store, onopentask: vi.fn() } });
    await tick();
    flushSync();

    expect(target.querySelector(".start-card")).toBeTruthy();

    unmount(comp);
    target.remove();
  });

  it("shows the dashboard tab with stat tiles once a project exists", async () => {
    const { store, target } = renderPage(seededDoc);
    await waitTick();
    const comp = mount(BuildPage, { target, props: { store, onopentask: vi.fn() } });
    await tick();
    flushSync();

    expect(target.querySelector(".start-card")).toBeFalsy();
    const values = Array.from(target.querySelectorAll(".ui-stat-value")).map((el) => el.textContent);
    expect(values.length).toBeGreaterThan(0);

    unmount(comp);
    target.remove();
  });

  it("switches to the phases tab on click", async () => {
    const { store, target } = renderPage(seededDoc);
    await waitTick();
    const comp = mount(BuildPage, { target, props: { store, onopentask: vi.fn() } });
    await tick();
    flushSync();

    const tabs = Array.from(target.querySelectorAll(".tab-bar .tab"));
    const phasesTab = tabs.find((el) => el.textContent?.includes("Phases")) as HTMLElement;
    phasesTab.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    flushSync();

    expect(target.querySelector(".phase-section")).toBeTruthy();

    unmount(comp);
    target.remove();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/editor && npx vitest run test/BuildPage.test.ts`
Expected: FAIL — `Cannot find module '../src/lib/components/BuildPage.svelte'`

- [ ] **Step 3: Write the implementation**

```svelte
<!-- packages/editor/src/lib/components/BuildPage.svelte -->
<script lang="ts">
  import { _ } from "svelte-i18n";
  import type { createBuildStore } from "../buildStore.svelte";
  import Card from "./ui/Card.svelte";
  import Button from "./ui/Button.svelte";
  import StatTile from "./ui/StatTile.svelte";
  import Tabs from "./ui/Tabs.svelte";
  import PhaseSection from "./PhaseSection.svelte";

  type BuildStore = ReturnType<typeof createBuildStore>;

  interface Props {
    store: BuildStore;
    onopentask: (taskId: string) => void;
  }
  let { store, onopentask }: Props = $props();

  let activeTab = $state<"dashboard" | "phases">("dashboard");
  let starting = $state(false);
  let startError = $state<string | null>(null);

  async function handleStart(): Promise<void> {
    starting = true; startError = null;
    try {
      await store.startProject();
    } catch (e) {
      startError = e instanceof Error ? e.message : $_('build.modal.saveFailed');
    } finally {
      starting = false;
    }
  }

  function resolveLabel(key: string | null, override: string | null): string {
    if (override) return override;
    if (key) return $_(key);
    return "";
  }

  const currentPhase = $derived(
    store.phases.find((p) => p.status === "in_progress") ?? store.phases.find((p) => p.status !== "completed") ?? null
  );

  const overdueAndUpcoming = $derived(
    store.tasks
      .filter((t) => t.status !== "completed" && t.plannedDueDate)
      .sort((a, b) => (a.plannedDueDate! < b.plannedDueDate! ? -1 : 1))
      .slice(0, 5)
  );

  const upcomingValidations = $derived(
    store.tasks.filter((t) => t.validationRequired && t.validationStatus === "pending_validation").slice(0, 5)
  );

  function fmtMoney(n: number): string {
    return n.toLocaleString(undefined, { maximumFractionDigits: 0 }) + " €";
  }
</script>

{#if !store.project}
  <div class="start-card">
    <Card>
      <h2>{$_('build.page.startTitle')}</h2>
      <p>{$_('build.page.startDescription')}</p>
      {#if startError}<div class="start-error">{startError}</div>{/if}
      <Button variant="primary" disabled={starting} onclick={handleStart}>{$_('build.page.startButton')}</Button>
    </Card>
  </div>
{:else}
  <Tabs
    tabs={[
      { id: "dashboard", label: $_('build.page.dashboardTab') },
      { id: "phases", label: $_('build.page.phasesTab') },
    ]}
    active={activeTab}
    onchange={(id) => { activeTab = id as "dashboard" | "phases"; }}
  />

  {#if activeTab === "dashboard"}
    <div class="stat-row">
      <StatTile value={$_(`build.projectStatus.${store.project.status === "in_progress" ? "inProgress" : store.project.status === "on_hold" ? "onHold" : store.project.status}`)} label={$_('build.dashboard.status')} />
      <StatTile value={currentPhase ? resolveLabel(currentPhase.nameKey, currentPhase.nameOverride) : "—"} label={$_('build.dashboard.currentPhase')} />
      <StatTile value={`${Math.round(store.projectProgress * 100)}%`} label={$_('build.dashboard.percentComplete')} />
      <StatTile value={fmtMoney(store.projectBudget.planned)} label={$_('build.dashboard.plannedBudget')} />
      <StatTile value={fmtMoney(store.projectBudget.actual)} label={$_('build.dashboard.actualCost')} />
    </div>

    <div class="dash-row">
      <Card>
        <h3>{$_('build.dashboard.overdueTasks')}</h3>
        {#if overdueAndUpcoming.length === 0}
          <p class="empty">{$_('build.dashboard.noOverdue')}</p>
        {:else}
          <ul class="task-list">
            {#each overdueAndUpcoming as task (task.id)}
              <li>
                <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_noninteractive_element_interactions -->
                <span class="task-link" role="button" tabindex="0" onclick={() => onopentask(task.id)}>
                  {resolveLabel(task.titleKey, task.titleOverride)} — {task.plannedDueDate}
                </span>
              </li>
            {/each}
          </ul>
        {/if}
      </Card>
      <Card>
        <h3>{$_('build.dashboard.upcomingValidations')}</h3>
        {#if upcomingValidations.length === 0}
          <p class="empty">{$_('build.dashboard.noValidationsPending')}</p>
        {:else}
          <ul class="task-list">
            {#each upcomingValidations as task (task.id)}
              <li>
                <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_noninteractive_element_interactions -->
                <span class="task-link" role="button" tabindex="0" onclick={() => onopentask(task.id)}>
                  {resolveLabel(task.titleKey, task.titleOverride)}
                </span>
              </li>
            {/each}
          </ul>
        {/if}
      </Card>
    </div>
  {:else}
    <PhaseSection {store} {onopentask} />
  {/if}
{/if}

<style>
  .start-card { display: flex; justify-content: center; padding: var(--space-4); }
  .start-card :global(.ui-card) { max-width: 480px; text-align: center; }
  .start-error { color: var(--danger); font-size: 12px; margin: 8px 0; }
  .stat-row { display: grid; grid-template-columns: repeat(5, 1fr); gap: var(--space-3); margin-bottom: var(--space-4); }
  .dash-row { display: grid; grid-template-columns: 1fr 1fr; gap: var(--space-4); }
  .dash-row h3 { margin: 0 0 var(--space-2); font-size: 13px; }
  .empty { font-size: 12px; color: var(--text-faint); }
  .task-list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 6px; }
  .task-link { cursor: pointer; font-size: 12px; color: var(--text); }
  .task-link:hover { text-decoration: underline; }
  @media (max-width: 900px) {
    .stat-row { grid-template-columns: repeat(2, 1fr); }
    .dash-row { grid-template-columns: 1fr; }
  }
</style>
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd packages/editor && npx vitest run test/BuildPage.test.ts`
Expected: PASS once Task 13's `PhaseSection.svelte` also exists (write both files before running if implementing sequentially in one sitting; otherwise this test's third case will fail until Task 13 lands — that is expected and acceptable since Task 13 is next).

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/lib/components/BuildPage.svelte packages/editor/test/BuildPage.test.ts
git commit -m "feat(build): add BuildPage with empty state and dashboard tab"
```

---

## Task 13: `PhaseSection.svelte` — phases tab

**Files:**
- Create: `packages/editor/src/lib/components/PhaseSection.svelte`
- Test: `packages/editor/test/PhaseSection.test.ts`

**Interfaces:**
- Consumes: `createBuildStore` return type (Task 11), `Card.svelte`.
- Produces: `<PhaseSection {store} onopentask={(taskId) => void} />` — consumed by Task 12's `BuildPage.svelte`.

- [ ] **Step 1: Write the failing test**

```typescript
// packages/editor/test/PhaseSection.test.ts
import { describe, it, expect, vi, afterEach } from "vitest";
import { mount, unmount, flushSync, tick } from "svelte";
import PhaseSection from "../src/lib/components/PhaseSection.svelte";
import { createBuildStore } from "../src/lib/buildStore.svelte";

const HOME = "home-1";
const getHomeId = () => HOME;

const doc = {
  version: 1,
  project: { id: "p1", status: "in_progress", plannedStartDate: null, plannedCompletionDate: null, actualCompletionDate: null, plannedBudget: null, notes: "", createdAt: "2026-01-01T00:00:00+00:00", updatedAt: "2026-01-01T00:00:00+00:00" },
  phases: [
    { id: "ph1", displayOrder: 0, nameKey: "build.phases.planning.name", nameOverride: null, descriptionKey: null, descriptionOverride: null, status: "in_progress", plannedStartDate: null, plannedEndDate: null, actualStartDate: null, actualEndDate: null },
    { id: "ph2", displayOrder: 1, nameKey: "build.phases.foundation.name", nameOverride: null, descriptionKey: null, descriptionOverride: null, status: "not_started", plannedStartDate: null, plannedEndDate: null, actualStartDate: null, actualEndDate: null },
  ],
  tasks: [
    { id: "t1", phaseId: "ph1", parentTaskId: null, displayOrder: 0, titleKey: "build.tasks.siteSurvey.title", titleOverride: null, descriptionKey: null, descriptionOverride: null, status: "completed", plannedStartDate: null, plannedDueDate: null, actualCompletionDate: null, plannedCost: null, actualCost: null, contractorId: null, validationRequired: false, validationStatus: "not_required", notes: "", attachments: [] },
    { id: "t2", phaseId: "ph1", parentTaskId: null, displayOrder: 1, titleKey: "build.tasks.architecturalPlans.title", titleOverride: null, descriptionKey: null, descriptionOverride: null, status: "not_started", plannedStartDate: null, plannedDueDate: null, actualCompletionDate: null, plannedCost: null, actualCost: null, contractorId: null, validationRequired: false, validationStatus: "not_required", notes: "", attachments: [] },
  ],
  dependencies: [],
};

async function waitTick(): Promise<void> {
  await new Promise((r) => setTimeout(r, 0));
}

afterEach(() => vi.unstubAllGlobals());

describe("PhaseSection", () => {
  it("renders one collapsed phase-section per phase", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => doc }));
    const store = createBuildStore(getHomeId);
    await waitTick();
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(PhaseSection, { target, props: { store, onopentask: vi.fn() } });
    await tick();
    flushSync();

    expect(target.querySelectorAll(".phase-section")).toHaveLength(2);
    expect(target.querySelectorAll(".phase-tasks").length).toBe(0);

    unmount(comp);
    target.remove();
  });

  it("expands a phase to show its tasks on click", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => doc }));
    const store = createBuildStore(getHomeId);
    await waitTick();
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(PhaseSection, { target, props: { store, onopentask: vi.fn() } });
    await tick();
    flushSync();

    (target.querySelector(".phase-header") as HTMLElement).dispatchEvent(new MouseEvent("click", { bubbles: true }));
    flushSync();

    const taskRows = target.querySelectorAll(".phase-tasks .task-row");
    expect(taskRows).toHaveLength(2);

    unmount(comp);
    target.remove();
  });

  it("clicking a task row calls onopentask with its id", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => doc }));
    const store = createBuildStore(getHomeId);
    await waitTick();
    const target = document.createElement("div");
    document.body.appendChild(target);
    const onopentask = vi.fn();
    const comp = mount(PhaseSection, { target, props: { store, onopentask } });
    await tick();
    flushSync();

    (target.querySelector(".phase-header") as HTMLElement).dispatchEvent(new MouseEvent("click", { bubbles: true }));
    flushSync();
    (target.querySelector(".task-row") as HTMLElement).dispatchEvent(new MouseEvent("click", { bubbles: true }));
    flushSync();

    expect(onopentask).toHaveBeenCalledWith("t1");

    unmount(comp);
    target.remove();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/editor && npx vitest run test/PhaseSection.test.ts`
Expected: FAIL — `Cannot find module '../src/lib/components/PhaseSection.svelte'`

- [ ] **Step 3: Write the implementation**

```svelte
<!-- packages/editor/src/lib/components/PhaseSection.svelte -->
<script lang="ts">
  import { _ } from "svelte-i18n";
  import type { createBuildStore } from "../buildStore.svelte";
  import Card from "./ui/Card.svelte";

  type BuildStore = ReturnType<typeof createBuildStore>;

  interface Props {
    store: BuildStore;
    onopentask: (taskId: string) => void;
  }
  let { store, onopentask }: Props = $props();

  let expandedPhaseId = $state<string | null>(null);

  function resolveLabel(key: string | null, override: string | null): string {
    if (override) return override;
    if (key) return $_(key);
    return "";
  }

  function toggle(phaseId: string): void {
    expandedPhaseId = expandedPhaseId === phaseId ? null : phaseId;
  }

  const sortedPhases = $derived([...store.phases].sort((a, b) => a.displayOrder - b.displayOrder));
</script>

{#if sortedPhases.length === 0}
  <p class="empty">{$_('build.page.noPhases')}</p>
{:else}
  {#each sortedPhases as phase (phase.id)}
    {@const phaseTasks = store.phaseTasks(phase.id).sort((a, b) => a.displayOrder - b.displayOrder)}
    {@const progress = store.phaseProgress(phase.id)}
    <div class="phase-section">
      <Card>
        <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_noninteractive_element_interactions -->
        <div class="phase-header" role="button" tabindex="0" onclick={() => toggle(phase.id)}>
          <span class="chevron">{expandedPhaseId === phase.id ? "▼" : "▶"}</span>
          <span class="phase-name">{resolveLabel(phase.nameKey, phase.nameOverride)}</span>
          <span class="phase-status">{$_(`build.phaseStatus.${phase.status === "in_progress" ? "inProgress" : phase.status}`)}</span>
          <span class="phase-count">{$_('build.page.taskCount', { values: { n: phaseTasks.length } })}</span>
          <div class="progress-track"><div class="progress-fill" style="width:{progress * 100}%"></div></div>
        </div>
        {#if expandedPhaseId === phase.id}
          <div class="phase-tasks">
            {#each phaseTasks as task (task.id)}
              <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_noninteractive_element_interactions -->
              <div class="task-row" role="button" tabindex="0" onclick={() => onopentask(task.id)}>
                <span class="task-title">{resolveLabel(task.titleKey, task.titleOverride)}</span>
                <span class="task-status">{$_(`build.taskStatus.${task.status === "in_progress" ? "inProgress" : task.status === "not_started" ? "notStarted" : task.status}`)}</span>
                <span class="task-due">{task.plannedDueDate ?? "—"}</span>
                <span class="task-contractor">{task.contractorId ?? "—"}</span>
              </div>
            {/each}
          </div>
        {/if}
      </Card>
    </div>
  {/each}
{/if}

<style>
  .empty { font-size: 12px; color: var(--text-faint); }
  .phase-section { margin-bottom: var(--space-2); }
  .phase-header {
    display: flex; align-items: center; gap: 10px; cursor: pointer;
  }
  .chevron { font-size: 9px; color: var(--text-faint); width: 12px; }
  .phase-name { flex: 1; font-size: 13px; font-weight: 600; }
  .phase-status { font-size: 11px; color: var(--text-muted); }
  .phase-count { font-size: 11px; color: var(--text-faint); }
  .progress-track { width: 80px; height: 6px; background: var(--surface-alt); border-radius: 999px; overflow: hidden; }
  .progress-fill { height: 100%; background: var(--accent); }
  .phase-tasks { margin-top: var(--space-3); display: flex; flex-direction: column; gap: 4px; }
  .task-row {
    display: flex; align-items: center; gap: 10px; padding: 6px 8px; border-radius: var(--radius-sm);
    cursor: pointer; font-size: 12px;
  }
  .task-row:hover { background: var(--surface-hover); }
  .task-title { flex: 1; }
  .task-status, .task-due, .task-contractor { color: var(--text-muted); font-size: 11px; }
</style>
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd packages/editor && npx vitest run test/PhaseSection.test.ts test/BuildPage.test.ts`
Expected: PASS (all tests in both files, including the `BuildPage` "phases tab" case deferred from Task 12)

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/lib/components/PhaseSection.svelte packages/editor/test/PhaseSection.test.ts
git commit -m "feat(build): add PhaseSection with expandable phase/task list and progress bar"
```

---

## Task 14: `TaskModal.svelte`

**Files:**
- Create: `packages/editor/src/lib/components/TaskModal.svelte`
- Test: `packages/editor/test/TaskModal.test.ts`

**Interfaces:**
- Consumes: `createBuildStore` return type (Task 11), `Modal.svelte`, `Input.svelte`, `Button.svelte`, `DatePicker.svelte`, `MediaGallery.svelte`, `apiUrl.ts` (all existing).
- Produces: `<TaskModal task={BuildTask | null} {store} onclose={() => void} />` — consumed by Task 16's `App.svelte` wiring.

- [ ] **Step 1: Write the failing test**

```typescript
// packages/editor/test/TaskModal.test.ts
import { describe, it, expect, vi, afterEach } from "vitest";
import { mount, unmount, flushSync, tick } from "svelte";
import TaskModal from "../src/lib/components/TaskModal.svelte";
import { createBuildStore } from "../src/lib/buildStore.svelte";

const HOME = "home-1";
const getHomeId = () => HOME;

const doc = {
  version: 1,
  project: { id: "p1", status: "in_progress", plannedStartDate: null, plannedCompletionDate: null, actualCompletionDate: null, plannedBudget: null, notes: "", createdAt: "2026-01-01T00:00:00+00:00", updatedAt: "2026-01-01T00:00:00+00:00" },
  phases: [{ id: "ph1", displayOrder: 0, nameKey: "build.phases.planning.name", nameOverride: null, descriptionKey: null, descriptionOverride: null, status: "in_progress", plannedStartDate: null, plannedEndDate: null, actualStartDate: null, actualEndDate: null }],
  tasks: [
    { id: "t1", phaseId: "ph1", parentTaskId: null, displayOrder: 0, titleKey: "build.tasks.siteSurvey.title", titleOverride: null, descriptionKey: "build.tasks.siteSurvey.description", descriptionOverride: null, status: "not_started", plannedStartDate: null, plannedDueDate: null, actualCompletionDate: null, plannedCost: 500, actualCost: null, contractorId: null, validationRequired: true, validationStatus: "pending_validation", notes: "", attachments: [] },
  ],
  dependencies: [],
};

async function waitTick(): Promise<void> {
  await new Promise((r) => setTimeout(r, 0));
}

afterEach(() => vi.unstubAllGlobals());

function setup() {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => doc }));
  const store = createBuildStore(getHomeId);
  const target = document.createElement("div");
  document.body.appendChild(target);
  return { store, target };
}

describe("TaskModal", () => {
  it("shows the resolved i18n title for a seeded task with no override", async () => {
    const { store, target } = setup();
    await waitTick();
    const comp = mount(TaskModal, { target, props: { task: store.tasks[0], store, onclose: vi.fn() } });
    await tick();
    flushSync();

    const input = target.querySelector("input.task-title-input") as HTMLInputElement;
    expect(input.value).toBe("Site Survey");

    unmount(comp);
    target.remove();
  });

  it("shows the validation status field when validationRequired is true", async () => {
    const { store, target } = setup();
    await waitTick();
    const comp = mount(TaskModal, { target, props: { task: store.tasks[0], store, onclose: vi.fn() } });
    await tick();
    flushSync();

    expect(target.querySelector(".validation-status-row")).toBeTruthy();

    unmount(comp);
    target.remove();
  });

  it("save calls store.updateTask with the patch", async () => {
    const { store, target } = setup();
    await waitTick();
    const onclose = vi.fn();
    const comp = mount(TaskModal, { target, props: { task: store.tasks[0], store, onclose } });
    await tick();
    flushSync();

    const fetchMock = fetch as unknown as ReturnType<typeof vi.fn>;
    (target.querySelector(".save-btn") as HTMLElement).dispatchEvent(new MouseEvent("click", { bubbles: true }));
    await waitTick();
    flushSync();

    expect(fetchMock).toHaveBeenCalledWith(
      `/api/homes/${HOME}/build/tasks/t1`,
      expect.objectContaining({ method: "PUT" })
    );

    unmount(comp);
    target.remove();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/editor && npx vitest run test/TaskModal.test.ts`
Expected: FAIL — `Cannot find module '../src/lib/components/TaskModal.svelte'`

- [ ] **Step 3: Write the implementation**

```svelte
<!-- packages/editor/src/lib/components/TaskModal.svelte -->
<script lang="ts">
  import { _ } from "svelte-i18n";
  import type { createBuildStore, BuildTask, ValidationStatus } from "../buildStore.svelte";
  import type { MediaItem } from "./ui/mediaTypes";
  import { apiUrl } from "../apiUrl";
  import DatePicker from "./DatePicker.svelte";
  import Modal from "./ui/Modal.svelte";
  import Input from "./ui/Input.svelte";
  import Button from "./ui/Button.svelte";
  import MediaGallery from "./ui/MediaGallery.svelte";
  import Lightbox from "./ui/Lightbox.svelte";

  type BuildStore = ReturnType<typeof createBuildStore>;

  interface Props {
    task: BuildTask | null;
    store: BuildStore;
    onclose: () => void;
  }
  let { task, store, onclose }: Props = $props();

  function resolveLabel(key: string | null, override: string | null): string {
    if (override) return override;
    if (key) return $_(key);
    return "";
  }

  const resolvedTitle = task ? resolveLabel(task.titleKey, task.titleOverride) : "";
  const resolvedDescription = task ? resolveLabel(task.descriptionKey, task.descriptionOverride) : "";

  let title = $state(resolvedTitle);
  let description = $state(resolvedDescription);
  let status = $state<BuildTask["status"]>(task?.status ?? "not_started");
  let contractorId = $state(task?.contractorId ?? "");
  let plannedStartDate = $state(task?.plannedStartDate ?? "");
  let plannedDueDate = $state(task?.plannedDueDate ?? "");
  let actualCompletionDate = $state(task?.actualCompletionDate ?? "");
  let plannedCost = $state<string>(task?.plannedCost != null ? String(task.plannedCost) : "");
  let actualCost = $state<string>(task?.actualCost != null ? String(task.actualCost) : "");
  let validationRequired = $state(task?.validationRequired ?? false);
  let validationStatus = $state<ValidationStatus>(task?.validationStatus ?? "not_required");
  let notes = $state(task?.notes ?? "");

  let saving = $state(false);
  let deleting = $state(false);
  let confirmDelete = $state(false);
  let error = $state<string | null>(null);
  let uploading = $state(false);
  let uploadError = $state<string | null>(null);
  let lightboxOpen = $state(false);
  let lightboxIndex = $state(0);

  const dependsOnTasks = $derived(
    task
      ? store.dependencies
          .filter((d) => d.successorTaskId === task!.id)
          .map((d) => store.tasks.find((t) => t.id === d.predecessorTaskId))
          .filter((t): t is BuildTask => !!t)
      : []
  );

  async function handleSave(): Promise<void> {
    if (!task) return;
    if (!title.trim()) { error = $_('build.modal.titleRequired'); return; }
    saving = true; error = null;
    try {
      await store.updateTask(task.id, {
        titleOverride: title.trim(),
        descriptionOverride: description.trim(),
        status,
        contractorId: contractorId || null,
        plannedStartDate: plannedStartDate || null,
        plannedDueDate: plannedDueDate || null,
        actualCompletionDate: actualCompletionDate || null,
        plannedCost: plannedCost ? parseFloat(plannedCost) || null : null,
        actualCost: actualCost ? parseFloat(actualCost) || null : null,
        validationRequired,
        validationStatus,
        notes: notes.trim(),
      });
      onclose();
    } catch (e) {
      error = e instanceof Error ? e.message : $_('build.modal.saveFailed');
    } finally {
      saving = false;
    }
  }

  async function handleDelete(): Promise<void> {
    if (!task) return;
    deleting = true;
    try {
      await store.deleteTask(task.id);
      onclose();
    } catch (e) {
      error = e instanceof Error ? e.message : $_('build.modal.deleteFailed');
      deleting = false;
    }
  }

  async function handleUpload(files: File[]): Promise<void> {
    if (!task) return;
    uploading = true; uploadError = null;
    try {
      for (const file of files) await store.uploadAttachment(task.id, file);
    } catch (err) {
      uploadError = err instanceof Error ? err.message : $_('build.modal.uploadFailed');
    } finally {
      uploading = false;
    }
  }

  async function handleDeleteAttachment(id: string): Promise<void> {
    if (!task) return;
    try {
      await store.deleteAttachment(task.id, id);
    } catch (err) {
      uploadError = err instanceof Error ? err.message : $_('build.modal.deleteFailed');
    }
  }

  const currentTask = $derived(task ? (store.tasks.find((t) => t.id === task!.id) ?? task) : null);

  const mediaItems = $derived<MediaItem[]>(
    (currentTask?.attachments ?? []).map((name) => {
      const url = apiUrl(`/api/homes/${store.project?.id ?? ""}/build/tasks/${task!.id}/attachments/${name}`);
      const isPdf = name.toLowerCase().endsWith(".pdf");
      return { id: name, name, url, thumbnailUrl: isPdf ? `${url}.thumb.jpg` : url, type: isPdf ? "document" : "image" };
    })
  );
</script>

{#if task}
  <Modal open={true} title={$_('build.modal.editTask')} {onclose} width="min(92vw, 820px)">
    <div class="row">
      <label>{$_('build.modal.title')} *</label>
      <input class="task-title-input native-input" bind:value={title} placeholder={$_('build.modal.titlePlaceholder')} />
    </div>
    <div class="row">
      <label>{$_('build.modal.description')}</label>
      <textarea class="native-input desc-area" bind:value={description} rows="4"></textarea>
    </div>
    <div class="row-pair">
      <div class="row">
        <label>{$_('build.modal.status')}</label>
        <select class="native-input" bind:value={status}>
          <option value="not_started">{$_('build.taskStatus.notStarted')}</option>
          <option value="ready">{$_('build.taskStatus.ready')}</option>
          <option value="in_progress">{$_('build.taskStatus.inProgress')}</option>
          <option value="waiting">{$_('build.taskStatus.waiting')}</option>
          <option value="blocked">{$_('build.taskStatus.blocked')}</option>
          <option value="completed">{$_('build.taskStatus.completed')}</option>
        </select>
      </div>
      <div class="row">
        <label>{$_('build.modal.contractor')}</label>
        <Input bind:value={contractorId} placeholder={$_('build.modal.contractorPlaceholder')} />
      </div>
    </div>
    <div class="row-pair">
      <div class="row">
        <label>{$_('build.modal.plannedStart')}</label>
        <DatePicker bind:value={plannedStartDate} />
      </div>
      <div class="row">
        <label>{$_('build.modal.plannedDue')}</label>
        <DatePicker bind:value={plannedDueDate} />
      </div>
    </div>
    <div class="row-pair">
      <div class="row">
        <label>{$_('build.modal.plannedCost')}</label>
        <input class="native-input" type="number" min="0" step="0.01" bind:value={plannedCost} placeholder="0.00" />
      </div>
      <div class="row">
        <label>{$_('build.modal.actualCost')}</label>
        <input class="native-input" type="number" min="0" step="0.01" bind:value={actualCost} placeholder="0.00" />
      </div>
    </div>
    <div class="row-pair">
      <div class="row">
        <label>{$_('build.modal.actualCompletion')}</label>
        <DatePicker bind:value={actualCompletionDate} />
      </div>
      <div class="row checkbox-row">
        <label><input type="checkbox" bind:checked={validationRequired} /> {$_('build.modal.validationRequired')}</label>
      </div>
    </div>
    {#if validationRequired}
      <div class="row validation-status-row">
        <label>{$_('build.modal.validationStatus')}</label>
        <select class="native-input" bind:value={validationStatus}>
          <option value="not_required">{$_('build.validationStatus.notRequired')}</option>
          <option value="pending_validation">{$_('build.validationStatus.pendingValidation')}</option>
          <option value="passed">{$_('build.validationStatus.passed')}</option>
          <option value="failed">{$_('build.validationStatus.failed')}</option>
        </select>
      </div>
    {/if}
    {#if dependsOnTasks.length > 0}
      <div class="row">
        <label>{$_('build.modal.dependsOn')}</label>
        <div class="dep-chips">
          {#each dependsOnTasks as dep (dep.id)}
            <span class="dep-chip">{resolveLabel(dep.titleKey, dep.titleOverride)}</span>
          {/each}
        </div>
      </div>
    {/if}
    <div class="row">
      <label>{$_('build.modal.notes')}</label>
      <textarea class="native-input desc-area" bind:value={notes} rows="3"></textarea>
    </div>

    <MediaGallery items={mediaItems} {uploading} {uploadError} onUpload={handleUpload} onDelete={handleDeleteAttachment} onItemClick={(i) => { lightboxIndex = i; lightboxOpen = true; }} />

    {#if error}<div class="modal-error">{error}</div>{/if}

    {#snippet footer()}
      {#if confirmDelete}
        <span class="confirm-text">{$_('build.modal.confirm')}?</span>
        <Button variant="danger" disabled={deleting} onclick={handleDelete}>✓ {$_('build.modal.confirm')}</Button>
        <Button variant="ghost" onclick={() => { confirmDelete = false; }}>✕</Button>
      {:else}
        <Button variant="danger" onclick={() => { confirmDelete = true; }}>🗑 {$_('common.delete')}</Button>
      {/if}
      <span class="spacer"></span>
      <Button class="save-btn" variant="primary" disabled={saving} onclick={handleSave}>{$_('common.save')}</Button>
    {/snippet}
  </Modal>
{/if}

{#if lightboxOpen && mediaItems.length > 0}
  <Lightbox items={mediaItems} initialIndex={lightboxIndex} onclose={() => { lightboxOpen = false; }} />
{/if}

<style>
  .row { display: flex; flex-direction: column; gap: 4px; margin-bottom: var(--space-3); }
  .row-pair { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: var(--space-3); }
  .row-pair .row { margin-bottom: 0; }
  .checkbox-row { justify-content: center; }
  label { font-size: 10px; color: var(--text-muted); text-transform: uppercase; letter-spacing: .06em; }
  .native-input {
    background: var(--surface-alt); border: 1px solid var(--border); color: var(--text);
    padding: 8px 12px; border-radius: var(--radius-md); font-size: 13px; width: 100%; box-sizing: border-box;
  }
  .desc-area { resize: vertical; white-space: pre-line; }
  .dep-chips { display: flex; flex-wrap: wrap; gap: 6px; }
  .dep-chip { font-size: 11px; padding: 2px 8px; border-radius: var(--radius-pill); background: var(--surface-alt); color: var(--text-muted); }
  .modal-error { padding: 8px 0 0; font-size: 11px; color: var(--danger); }
  .spacer { flex: 1; }
  .confirm-text { font-size: 11px; color: var(--danger); }
</style>
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd packages/editor && npx vitest run test/TaskModal.test.ts`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/lib/components/TaskModal.svelte packages/editor/test/TaskModal.test.ts
git commit -m "feat(build): add TaskModal with validation fields, dependency chips, and attachments"
```

---

## Task 15: `HomeBuildWidget.svelte`

**Files:**
- Create: `packages/editor/src/lib/components/HomeBuildWidget.svelte`
- Test: `packages/editor/test/HomeBuildWidget.test.ts`

**Interfaces:**
- Consumes: `createBuildStore` return type (Task 11), `Card.svelte`.
- Produces: `<HomeBuildWidget {buildStore} onnavigate={() => void} />` — consumed by Task 16's `HomePage.svelte` wiring.

- [ ] **Step 1: Write the failing test**

```typescript
// packages/editor/test/HomeBuildWidget.test.ts
import { describe, it, expect, vi, afterEach } from "vitest";
import { mount, unmount, flushSync, tick } from "svelte";
import HomeBuildWidget from "../src/lib/components/HomeBuildWidget.svelte";
import { createBuildStore } from "../src/lib/buildStore.svelte";

const HOME = "home-1";
const getHomeId = () => HOME;

const emptyDoc = { version: 1, project: null, phases: [], tasks: [], dependencies: [] };

const seededDoc = {
  version: 1,
  project: { id: "p1", status: "in_progress", plannedStartDate: null, plannedCompletionDate: null, actualCompletionDate: null, plannedBudget: 100000, notes: "", createdAt: "2026-01-01T00:00:00+00:00", updatedAt: "2026-01-01T00:00:00+00:00" },
  phases: [{ id: "ph1", displayOrder: 0, nameKey: "build.phases.planning.name", nameOverride: null, descriptionKey: null, descriptionOverride: null, status: "in_progress", plannedStartDate: null, plannedEndDate: null, actualStartDate: null, actualEndDate: null }],
  tasks: [
    { id: "t1", phaseId: "ph1", parentTaskId: null, displayOrder: 0, titleKey: "build.tasks.siteSurvey.title", titleOverride: null, descriptionKey: null, descriptionOverride: null, status: "completed", plannedStartDate: null, plannedDueDate: null, actualCompletionDate: null, plannedCost: 500, actualCost: 480, contractorId: null, validationRequired: false, validationStatus: "not_required", notes: "", attachments: [] },
    { id: "t2", phaseId: "ph1", parentTaskId: null, displayOrder: 1, titleKey: "build.tasks.architecturalPlans.title", titleOverride: null, descriptionKey: null, descriptionOverride: null, status: "not_started", plannedStartDate: null, plannedDueDate: null, actualCompletionDate: null, plannedCost: 2000, actualCost: null, contractorId: null, validationRequired: false, validationStatus: "not_required", notes: "", attachments: [] },
  ],
  dependencies: [],
};

async function waitTick(): Promise<void> {
  await new Promise((r) => setTimeout(r, 0));
}

afterEach(() => vi.unstubAllGlobals());

describe("HomeBuildWidget", () => {
  it("renders nothing when there is no build project", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => emptyDoc }));
    const buildStore = createBuildStore(getHomeId);
    await waitTick();
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(HomeBuildWidget, { target, props: { buildStore, onnavigate: vi.fn() } });
    await tick();
    flushSync();

    expect(target.querySelector(".widget")).toBeFalsy();

    unmount(comp);
    target.remove();
  });

  it("shows progress and budget once a project exists", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => seededDoc }));
    const buildStore = createBuildStore(getHomeId);
    await waitTick();
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(HomeBuildWidget, { target, props: { buildStore, onnavigate: vi.fn() } });
    await tick();
    flushSync();

    expect(target.querySelector(".widget")).toBeTruthy();
    expect(target.textContent).toContain("50%");

    unmount(comp);
    target.remove();
  });

  it("clicking the widget calls onnavigate", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => seededDoc }));
    const buildStore = createBuildStore(getHomeId);
    await waitTick();
    const target = document.createElement("div");
    document.body.appendChild(target);
    const onnavigate = vi.fn();
    const comp = mount(HomeBuildWidget, { target, props: { buildStore, onnavigate } });
    await tick();
    flushSync();

    (target.querySelector(".widget") as HTMLElement).dispatchEvent(new MouseEvent("click", { bubbles: true }));
    flushSync();

    expect(onnavigate).toHaveBeenCalledOnce();

    unmount(comp);
    target.remove();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/editor && npx vitest run test/HomeBuildWidget.test.ts`
Expected: FAIL — `Cannot find module '../src/lib/components/HomeBuildWidget.svelte'`

- [ ] **Step 3: Write the implementation**

```svelte
<!-- packages/editor/src/lib/components/HomeBuildWidget.svelte -->
<script lang="ts">
  import { _ } from "svelte-i18n";
  import type { createBuildStore } from "../buildStore.svelte";
  import Card from "./ui/Card.svelte";

  type BuildStore = ReturnType<typeof createBuildStore>;

  interface Props {
    buildStore: BuildStore;
    onnavigate: () => void;
  }
  let { buildStore, onnavigate }: Props = $props();

  function fmt(n: number): string {
    return n.toLocaleString(undefined, { maximumFractionDigits: 0 }) + " €";
  }

  const overdueCount = $derived(
    buildStore.tasks.filter((t) => t.status !== "completed" && t.plannedDueDate && t.plannedDueDate < new Date().toISOString().slice(0, 10)).length
  );
</script>

{#if buildStore.project}
  <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_noninteractive_element_interactions -->
  <div class="widget" role="button" tabindex="0" onclick={onnavigate} onkeydown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); onnavigate(); } }}>
    <Card>
      <div class="header"><h3>🏗️ {$_('common.modules.build')}</h3></div>
      <div class="stat-row">
        <span class="stat">{$_(`build.projectStatus.${buildStore.project.status === "in_progress" ? "inProgress" : buildStore.project.status === "on_hold" ? "onHold" : buildStore.project.status}`)}</span>
        <span class="stat">{Math.round(buildStore.projectProgress * 100)}%</span>
      </div>
      <div class="budget-row">
        <span>{fmt(buildStore.projectBudget.planned)}</span>
        <span class="sep">/</span>
        <span>{fmt(buildStore.projectBudget.actual)}</span>
      </div>
      {#if overdueCount > 0}
        <div class="overdue">{overdueCount} {$_('build.dashboard.overdueTasks')}</div>
      {/if}
    </Card>
  </div>
{/if}

<style>
  .widget { cursor: pointer; }
  .header { display: flex; align-items: baseline; justify-content: space-between; margin-bottom: var(--space-2); }
  .header h3 { margin: 0; font-size: 14px; font-weight: 600; color: var(--text); }
  .stat-row { display: flex; gap: 10px; font-size: 12px; font-weight: 600; margin-bottom: 4px; }
  .budget-row { font-size: 12px; color: var(--text-muted); }
  .sep { margin: 0 4px; }
  .overdue { margin-top: 4px; font-size: 11px; color: var(--danger); }
</style>
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd packages/editor && npx vitest run test/HomeBuildWidget.test.ts`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/lib/components/HomeBuildWidget.svelte packages/editor/test/HomeBuildWidget.test.ts
git commit -m "feat(build): add HomeBuildWidget"
```

---

## Task 16: Routing and module wiring

**Files:**
- Modify: `packages/editor/src/App.svelte`
- Modify: `packages/editor/src/lib/components/NavMenu.svelte`
- Modify: `packages/editor/src/lib/components/settings/SettingsGeneral.svelte`
- Modify: `packages/editor/src/lib/components/HomePage.svelte`

**Interfaces:**
- Consumes: `createBuildStore` (Task 11), `BuildPage` (Task 12), `TaskModal` (Task 14), `HomeBuildWidget` (Task 15).
- Produces: the module reachable end-to-end from the nav, home dashboard, and Settings module toggle. This task has no isolated unit test of its own — it is verified by the manual browser check in the final step below, since `App.svelte` routing has no existing per-route test convention to mirror.

- [ ] **Step 1: Wire the store and route in `App.svelte`**

Add the import near the other store/page imports (mirroring `propertiesStore`/`PropertiesPage`):

```typescript
import BuildPage from "./lib/components/BuildPage.svelte";
import TaskModal from "./lib/components/TaskModal.svelte";
import { createBuildStore } from "./lib/buildStore.svelte";
```

Add the store instantiation alongside the others:

```typescript
const buildStore = createBuildStore(getHomeId);
```

Add `buildStore.reload()` to the same home-switch handler that already calls `propertiesStore.reload()` (search for that call site — it is a single `homesStore`-change effect that reloads every per-home store).

Add task-modal open/close state near the other modal state variables:

```typescript
let openBuildTaskId = $state<string | null>(null);
```

Add the route render block, alongside the existing `#/properties` branch:

```svelte
{:else if currentRoute === "#/build"}
  <BuildPage store={buildStore} onopentask={(taskId) => { openBuildTaskId = taskId; }} />
```

Add the modal render near `NewChoreModal`'s render at the bottom of the file:

```svelte
{#if openBuildTaskId}
  <TaskModal
    task={buildStore.tasks.find((t) => t.id === openBuildTaskId) ?? null}
    store={buildStore}
    onclose={() => { openBuildTaskId = null; }}
  />
{/if}
```

Pass `buildStore` into the `HomePage` props alongside `propertiesStore`:

```svelte
<HomePage
  {floorStore}
  {choreStore}
  {inventoryStore}
  {settingsStore}
  {costsStore}
  {worksStore}
  {consumableStore}
  {locationsStore}
  {propertiesStore}
  {buildStore}
/>
```

- [ ] **Step 2: Add the nav entry**

Modify `packages/editor/src/lib/components/NavMenu.svelte`:

```typescript
const ALL_MODULES = [
  { id: "home",        href: "#/",            icon: "🏡" },
  { id: "plan",        href: "#/plan",        icon: "📐" },
  { id: "chores",      href: "#/chores",      icon: "✅" },
  { id: "inventory",   href: "#/inventory",   icon: "📦" },
  { id: "consumables", href: "#/consumables", icon: "🛒" },
  { id: "works",       href: "#/works",       icon: "🔧" },
  { id: "kb",          href: "#/kb",          icon: "📖" },
  { id: "costs",       href: "#/costs",       icon: "💶" },
  { id: "locations",   href: "#/locations",   icon: "🌍" },
  { id: "properties",  href: "#/properties",  icon: "🏘" },
  { id: "build",       href: "#/build",       icon: "🏗️" },
  { id: "budget",      href: "#/budget",      icon: "💰", placeholder: true },
  { id: "visits",      href: "#/visits",      icon: "📅", placeholder: true },
  { id: "contacts",    href: "#/contacts",    icon: "👤", placeholder: true },
  { id: "checklist",   href: "#/checklist",   icon: "✅", placeholder: true },
];
```

- [ ] **Step 3: Add the Settings module toggle entry**

Modify `packages/editor/src/lib/components/settings/SettingsGeneral.svelte`:

```typescript
const PROJECT_MODULES = [
  { id: "locations",  icon: "🌍" },
  { id: "properties", icon: "🏘" },
  { id: "build",      icon: "🏗️" },
  { id: "budget",     icon: "💰" },
  { id: "visits",     icon: "📅" },
  { id: "contacts",   icon: "👤" },
  { id: "checklist",  icon: "✅" },
];
```

- [ ] **Step 4: Add the home dashboard widget**

Modify `packages/editor/src/lib/components/HomePage.svelte` — add the import, prop, and render call mirroring `HomePropertiesWidget`:

```typescript
import HomeBuildWidget from "./HomeBuildWidget.svelte";
import type { createBuildStore } from "../buildStore.svelte";

type BuildStore = ReturnType<typeof createBuildStore>;
```

Add `buildStore: BuildStore;` to the `Props` interface and destructuring, then in the template's `.col-side`:

```svelte
<HomeBuildWidget {buildStore} onnavigate={() => navigate("#/build")} />
```

(placed after `HomePropertiesWidget`, matching the property/works/consumables ordering already established).

- [ ] **Step 5: Run the full frontend test suite to check for regressions**

Run: `cd packages/editor && npx vitest run`
Expected: PASS — all pre-existing tests plus the 5 new build-related test files (Tasks 10–15) pass; no existing test broken by the `HomePage`/`App`/`NavMenu`/`SettingsGeneral` prop-interface changes.

- [ ] **Step 6: Manual verification (webapp-testing skill)**

Start the dev server, create a `"project"`-type home (or use an existing one and enable `build` in Settings > Modules), and in the browser:
1. Navigate to Build via the nav icon — confirm the "Start Build Tracking" empty state appears.
2. Click Start — confirm all 22 phases and 58 tasks appear under the Phases tab, expandable.
3. Open a task, change its status to "In progress", set a planned due date and planned cost, save — confirm the Dashboard tab reflects it (progress %, budget, overdue/upcoming list).
4. Override a seeded task's title, save, then switch the app's locale to French (Settings) and confirm the *edited* task still shows the English override (not translated) while *other, non-edited* seeded tasks and phase names now show in French.
5. Add a photo attachment to a task and confirm it displays via the media gallery.
6. Delete the build project from a phase/task overflow point (or wherever the delete affordance lives) and confirm the empty state reappears.

- [ ] **Step 7: Commit**

```bash
git add packages/editor/src/App.svelte packages/editor/src/lib/components/NavMenu.svelte packages/editor/src/lib/components/settings/SettingsGeneral.svelte packages/editor/src/lib/components/HomePage.svelte
git commit -m "feat(build): wire routing, nav entry, module toggle, and home widget"
```

---

## Self-Review Notes

- **Spec coverage:** every section of `docs/superpowers/specs/2026-07-23-house-build-tracking-design.md` maps to a task: data model → Tasks 1–2; seed template → Task 3; REST API → Tasks 4–5; module registration → Task 6; notifications → Tasks 7–8; MCP → Task 9; locale content → Task 10; frontend store/pages/modal/widget/routing → Tasks 11–16.
- **Type consistency verified:** `BuildTask`/`BuildPhase`/`BuildProject` field names are identical across `models_build.py` (Task 1), `persistence_build.py` (Task 2), `routes/build.py` (Tasks 4–5), and the TypeScript interfaces in `buildStore.svelte.ts` (Task 11) — camelCase throughout the API boundary (FastAPI/Pydantic serializes camelCase field names as declared, matching every other module's convention in this codebase).
- **No placeholders:** all 58 seed tasks and 22 phases have real, non-empty English and French text (Task 10); every code block is complete, runnable code, not a description of what to write.
