# House Build Tracking Module — Design Spec

**Date:** 2026-07-23
**Status:** Approved

## Overview

Tracks the construction of a single new house associated with a home, from
planning through handover: a project → phases → tasks hierarchy with task
dependencies, budget rollups, attachments, and notifications. One build
project per home. Reserved nav slot `build` (icon 🏗️), opt-in via
Settings > Modules like Properties/Works/Consumables, and part of
`DEFAULT_PROJECT_MODULES` since the `"project"` home type already means "new
house under construction."

Out of scope for this pass (explicitly deferred, no schema changes needed
later): contractor management module, dedicated inspections entity,
milestone tracking, Gantt view, weather delays, change orders,
warranty/maintenance handoff, equipment records, critical-path analysis.

---

## 1. Data Model

SQLite via SQLAlchemy Core, following the existing `schema.py`/
`persistence_x.py` "whole document, delete-all-then-reinsert per save"
pattern (same as Works/Properties/Locations).

### `build_projects` (one row per home)

```
id:                        str
home_id:                   str   (unique index — enforces one project per home)
status:                    Literal["planning", "in_progress", "completed", "on_hold"]
planned_start_date:        str | None
planned_completion_date:   str | None
actual_completion_date:    str | None
planned_budget:            float | None
notes:                     str
created_at:                str
updated_at:                str
```

No stored `actual_cost` column. It is a **derived rollup**
(`sum(task.actualCost)` across all tasks), computed at read time alongside
phase- and project-level budget summaries — not persisted, so it can never
drift from the tasks it's summarizing.

### `build_phases`

```
id:                  str
build_project_id:    str
display_order:       int
name_key:            str | None   # i18n key, e.g. "build.phases.foundation.name"
name_override:       str | None   # literal text once user edits
description_key:     str | None
description_override: str | None
status:              Literal["not_started", "in_progress", "completed"]
planned_start_date:  str | None
planned_end_date:    str | None
actual_start_date:   str | None
actual_end_date:     str | None
```

22 default phases seeded on project start, in this order: Planning, Site
Preparation, Foundation, Framing, Roofing, Windows & Exterior Doors,
Exterior Envelope, Plumbing Rough-In, Electrical Rough-In, HVAC Rough-In,
Insulation, Drywall, Interior Finishes, Flooring, Kitchen, Bathrooms,
Painting, Exterior Works, Landscaping, Final Inspections, Punch List,
Handover.

### `build_tasks`

```
id:                     str
phase_id:               str
parent_task_id:         str | None   # self-FK, optional sub-task nesting
display_order:          int
title_key:              str | None
title_override:         str | None
description_key:        str | None
description_override:   str | None
status:                 Literal["not_started", "ready", "in_progress", "waiting", "blocked", "completed"]
planned_start_date:     str | None
planned_due_date:       str | None
actual_completion_date: str | None
planned_cost:           float | None
actual_cost:            float | None
contractor_id:          str | None   # free text for now, see below
validation_required:    bool
validation_status:      Literal["not_required", "pending_validation", "passed", "failed"]
notes:                  str
attachments:            list[str]   # JSON column
```

`contractor_id` is exposed in the UI as a plain free-text field (no
Contractor module exists yet) — whatever the user types is stored verbatim,
the same way Properties' free-text `contact` field works. When a real
Contractor module ships, this becomes a real dropdown/FK against the same
column with no schema change, just a change in what values get written.

`status` is fully user-settable — no hard dependency gate. Dependencies
instead drive a **computed** Ready/Blocked value (Ready = all predecessor
tasks Completed) used for display/filtering and as a suggested default, not
an enforced one. There is no config/override mechanism for enforcement
because none exists in the app today, and per-spec this is acceptable for an
initial implementation.

### `build_task_dependencies`

```
id:                    str
home_id:                str   # scoping for cascade-delete, mirrors location_ratings
predecessor_task_id:    str
successor_task_id:      str
```

### `name_key`/`title_key`/`description_key` mechanics

The backend has no locale awareness anywhere (locale is a browser-only
`localStorage` setting via `svelte-i18n`; even Locations' default criteria
are hardcoded English text with no translation). To give the seeded
template real English *and* French content without teaching the backend
about locale:

- Seeded rows get a nullable `*_key` pointing into the existing locale JSON
  files (`en.json`/`fr.json`), resolved client-side via `svelte-i18n`.
- If the user edits a seeded phase/task's name or description, the edit is
  saved into the paired `*_override` column as literal text, and that row
  stops translating (same as any other user-edited free text elsewhere in
  the app).
- User-added custom phases/tasks always use `*_override` only (no key) —
  same as any other user-authored content in the app, never translated.
- Frontend resolution rule: show `override` if set, else resolve `key` via
  `$_(key)`, else empty string.

This keeps translation content in one place (the locale files) rather than
duplicating it per database row, and requires no backend locale logic.

---

## 2. Backend

New files, following the Works/Properties pattern of "new files only, no
changes to shared persistence internals":

| File | Purpose |
|------|---------|
| `models_build.py` | `BuildProject`, `BuildPhase`, `BuildTask`, `BuildTaskDependency`, `BuildDocument` (wraps all four), plus `*Create`/`*Update` variants for phase/task/dependency |
| `persistence_build.py` | `load_build(home_id) -> BuildDocument` / `save_build(home_id, doc)` (same delete-all-then-reinsert-per-table transaction as `persistence_works.py`), plus attachment helpers (`build-attachments/{task_id}/...`) reusing the exact `save_attachment`/`get_attachment_path`/`delete_attachment`/`delete_all_attachments`/`generate_pdf_thumbnail` shape used by every other attachment-bearing module |
| `build_template.py` | Seed data: 22 phases each with 3–5 tasks (title/description i18n keys, `validationRequired`, optional `plannedDurationDays`), and the dependency-chain generation rule (see §4) |
| `build_calc.py` | Budget rollups (task/phase/project) and Ready/Blocked derivation — pure functions over a `BuildDocument`, not persisted |
| `routes/build.py` | REST routes below |
| `mcp_tools_build.py` | `list_build_phases`, `list_build_tasks`, `create_build_task`, `update_build_task`, `update_build_phase`, mirroring `mcp_tools_works.py`'s `_*_impl` + `@mcp.tool()` pattern, role-gated the same way (`ro` for list, `normal` for mutations); added to `mcp_app.py`'s import list |

### REST API

```
GET    /api/homes/{id}/build                          → full BuildDocument (project + phases + tasks + deps); empty-shaped if no project yet
POST   /api/homes/{id}/build/start                     → creates BuildProject + seeds all phases/tasks/dependencies from template

PUT    /api/homes/{id}/build/project                   → update project (status, dates, budget, notes)
DELETE /api/homes/{id}/build/project                   → delete project + all phases/tasks/deps + attachments

PUT    /api/homes/{id}/build/phases/{phaseId}          → update phase (status/dates; name/description edits go through name_override/description_override via this same route)

POST   /api/homes/{id}/build/tasks                     → create custom task (override-only, no key)
PUT    /api/homes/{id}/build/tasks/{taskId}            → update task
DELETE /api/homes/{id}/build/tasks/{taskId}            → delete task + cascade-delete its dependencies + attachments

POST   /api/homes/{id}/build/dependencies              → { predecessorTaskId, successorTaskId }
DELETE /api/homes/{id}/build/dependencies/{depId}

POST   /api/homes/{id}/build/tasks/{taskId}/attachments
GET    /api/homes/{id}/build/tasks/{taskId}/attachments/{filename}
DELETE /api/homes/{id}/build/tasks/{taskId}/attachments/{filename}
```

Every mutating route calls `log_activity(home_id, user_id, "build", action,
label, ref_id)`, reusing the existing cross-module activity log
(`persistence_activity.py`) — `"build"` added to its `MODULE_NOUNS` dict.
This feeds the Dashboard's "recent activity" panel with no new
infrastructure.

### Module registration

- `models_homes.py`: `"build"` added to `ALL_MODULE_IDS` and to
  `DEFAULT_PROJECT_MODULES` (project-type homes = new-build houses; this
  module is exactly what that home type exists for).
- `NavMenu.svelte`: new non-placeholder entry `{ id: "build", href: "#/build", icon: "🏗️" }`.
- `SettingsGeneral.svelte`: `"build"` added to the `PROJECT_MODULES` toggle
  list (icon 🏗️).

### Notifications

Extends the existing `compute_notifications()`/`Notification` model
as-is — plain English `title`/`detail` computed server-side, not localized,
matching the current behavior of chores/low-stock/warranty notifications
(a pre-existing app-wide gap between the notification system and the i18n
effort; not something this module fixes).

- **`build_task_due`** — task's `planned_due_date` is within a new
  `buildTaskDueSoonThreshold: int = 7` (days) setting on `NotificationSettings`
  (same day-count shape as `warrantyDaysThreshold`), or already past it.
  Severity `warning`/`critical`.
- **`build_validation`** — task has `validation_required=true` and
  `validation_status=pending_validation`. Stateless — appears/disappears
  with current state, like low-stock.
- **`build_phase_complete`** — fires once when a phase's status transitions
  to `completed`. Tracked via a new `buildPhasesNotified: list[str]` field
  on the existing per-home `NotificationState`, same fire-once mechanics as
  `warrantyNotified`.

---

## 3. Frontend

**`buildStore.svelte.ts`** — fetches/caches the full `BuildDocument`; CRUD
methods mirroring the REST routes (`startProject`, `updateProject`,
`deleteProject`, `updatePhase`, `createTask`/`updateTask`/`deleteTask`,
`addDependency`/`removeDependency`, `uploadAttachment`/`deleteAttachment`);
derived getters for per-phase/per-project budget rollups and Ready/Blocked
status (client-side, mirroring how `locationsStore` derives weighted
scores rather than the backend computing them).

**`BuildPage.svelte`** (route `#/build`, replaces `PlaceholderPage`) — two
tabs via the shared `Tabs.svelte`:

- **Dashboard tab**: `StatTile` row (status, current phase, % complete,
  planned vs actual budget), two `Card`s side by side ("Overdue & upcoming
  tasks" and "Upcoming validations" — small sortable lists, row click opens
  `TaskModal`), and a "Recent activity" `Card` reading the per-home activity
  log filtered to `module === "build"`.
- **Phases tab**: one expandable `Card` per phase in `display_order` —
  header shows status chip, date range, plain CSS progress bar
  (% tasks completed), task count; expanding reveals its tasks (title,
  status chip, due date, contractor); row click opens `TaskModal`. "+ Add
  phase" / "+ Add task" affordances for custom additions.

**`TaskModal.svelte`** — structurally mirrors `WorkModal`/`PropertyModal`:
title + description (rendered `white-space: pre-line` for seeded tasks —
each bullet its own line in the source text; becomes an editable textarea
once the user overrides it), status select, contractor free-text input,
planned start/due dates (`DatePicker`), actual completion date, planned/
actual cost, validation-required toggle + validation-status select (hidden/
disabled when not required), a read-only "depends on" chip list resolved
from `build_task_dependencies`, notes textarea, `MediaGallery` for
attachments, Save/Delete/Cancel.

**`HomeBuildWidget.svelte`** — added to `HomePage.svelte`'s side column,
shown when the module is enabled and a project exists: header "🏗️ Build",
status + % complete, budget planned vs actual, overdue-task count. Click →
`#/build`. Mirrors `HomePropertiesWidget.svelte`.

**Empty state**: visiting `#/build` with no project yet shows a centered
"Start Build Tracking" `Card` (short blurb + button) calling
`POST /build/start`.

---

## 4. Seed Template

`build_template.py` holds, per phase: `nameKey`, `descriptionKey`, and a
list of tasks each with `titleKey`, `descriptionKey`, `validationRequired`,
and an optional `plannedDurationDays` (used only to pre-fill a suggested
`planned_due_date` offset from the project's `planned_start_date` at seed
time — not stored as its own column).

**Depth**: 22 phases, averaging **3–5 tasks per phase** (~80–90 tasks
total) — a genuinely useful starting checklist without ballooning into an
exhaustive contractor-grade work-breakdown structure. Indicative counts:
Planning (5: permits, architect plans, financing/budget approval,
contractor selection, site survey), Site Preparation (3), Foundation (3:
excavation, forms & reinforcement, pour & cure), Framing (3), Roofing (2),
Plumbing/Electrical/HVAC Rough-In (2 each), Punch List (2: generate list,
resolve items), Handover (2: final walkthrough, keys & documents handover).
Exact per-phase lists finalized during implementation.

**Dependencies**: generated mechanically, not hand-specified per pair —
each phase's tasks chain sequentially, and the first task of phase *N*
depends on the last task of phase *N−1*. Phases 8–10 (Plumbing/Electrical/
HVAC Rough-In) are the one exception: all three depend on Framing's last
task but not on each other, modeling real parallel work.

**Locale files**: new top-level `build` namespace in `en.json`/`fr.json`,
e.g.:

```json
"build": {
  "phases": {
    "foundation": { "name": "Foundation", "description": "Excavation, footings, and slab or crawlspace construction." }
  },
  "tasks": {
    "foundationPour": {
      "title": "Foundation Pour",
      "description": "Verify excavation dimensions\nInstall reinforcement\nVerify drainage\nPosition utility penetrations\nPour concrete\nFinish surface\nAllow curing\nPrepare for inspection"
    }
  }
}
```

---

## 5. Testing

**Backend**: CRUD for project/phase/task/dependency; cascade-deletes
(project → phases/tasks/deps/attachments, task → deps/attachments); budget
rollups at all 3 levels; Ready/Blocked derivation; seed-from-template
correctness (counts, dependency chain including the rough-in fan-out);
notification generation (due-soon/overdue/validation-pending/
phase-complete fire-once); MCP tool coverage.

**Frontend**: store CRUD; dashboard stat/rollup rendering; phase accordion
expand + progress bar; task modal save/delete + dependency chip display;
key-vs-override resolution (seeded name shows translated text in both
locales, edited name shows literal override in both); widget hidden-when-
disabled/empty; empty-state "Start Build Tracking" seeding flow.

**Manual verification** (webapp-testing skill, before calling this done):
enable Build on a project home, start tracking, confirm all 22 phases/
tasks seeded, edit a task's status/dates/cost, override a seeded task's
title and confirm it stops translating on locale switch, add a photo
attachment, switch to French and confirm all seeded phase/task text
translates, confirm dashboard rollups and the home widget reflect current
data.
