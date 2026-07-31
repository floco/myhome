# Chore Scheduling: Rich Recurrence, NL Quick-Add, Adaptive Scheduling Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let chores be manually created/edited with the same rich recurrence types the backend already supports for Donetick imports (daily, custom interval, weekly-on-specific-days, monthly-on-a-day, yearly, and a new adaptive type), plus an English/French natural-language quick-add that pre-fills that same picker.

**Architecture:** A new shared `ScheduleEditor.svelte` component (bound via `frequencyType`/`frequency`/`frequencyMetadata`/`periodDays`) replaces the interval-only UI in `NewChoreModal.svelte` and the plain-number UI in `ChoreEditModal.svelte`. A new `scheduleParser.ts` (pure TS, regex-based, no LLM) turns a sentence into the same structured shape for the quick-add box. A new `adaptive` `frequencyType` reuses the existing `periodDays` column as both its seed value and its running average — no new DB columns anywhere.

**Tech Stack:** FastAPI + Pydantic (backend), Svelte 5 runes + svelte-i18n + Vitest (frontend), pytest (backend tests).

## Global Constraints

- Full design at `docs/superpowers/specs/2026-07-31-chore-scheduling-design.md` — read it if anything below is ambiguous.
- Date-only due dates everywhere (no time-of-day) — out of scope, do not add it.
- `scheduleFromDue` (due-date vs. completion-date anchoring) is unrelated and untouched — do not modify its logic.
- **Correction (found mid-execution):** the premise that this codebase has no Svelte component-render tests was wrong — an earlier research pass only looked under `src/lib` and missed the package's actual test directory, `packages/editor/test/`, which has 115+ files, both `mount()`/`unmount()`/`flushSync()`-based component tests (e.g. `test/ChoresPage.test.ts`, `test/ChoreEditModal.test.ts`) *and* pure-logic tests (e.g. `test/choreFormat.test.ts`). **Every test file this plan adds — component or pure-logic — belongs under `packages/editor/test/`, never under `src/lib`.** (A stray `src/lib/choreStore.test.ts` this plan's author created before catching this was merged into `test/choreStore.test.ts` and deleted; `scheduleParser.test.ts` likewise goes in `test/`, not next to `scheduleParser.ts`.)
- Follow existing i18n key naming (`chores.schedule.*`, `chores.newModal.*`, `chores.editModal.*`) for all new keys; add every new key to **both** `en.json` and `fr.json` in the same task that introduces it.
- Run `cd /projects/myhome && pytest packages/backend` and `cd /projects/myhome/packages/editor && npx vitest run` before any commit that touches backend/frontend code respectively, to confirm nothing else broke.

---

### Task 1: Backend — explicit `daily` advance + adaptive scheduling core

**Files:**
- Modify: `packages/backend/src/myhome/chore_scheduling.py`
- Test: `packages/backend/tests/test_chore_scheduling.py`

**Interfaces:**
- Produces: `adaptive_period_days(chore: Chore, completions_for_chore: list[CompletionRecord]) -> float` (exported from `myhome.chore_scheduling`, used by Tasks 2 and 3).
- Produces: `next_due_from_schedule(chore: Chore, from_dt: datetime, completions: list[CompletionRecord] | None = None) -> datetime` — same name, new optional third parameter (existing call sites that don't pass it are unaffected).

- [ ] **Step 1: Write the failing tests**

Append to `packages/backend/tests/test_chore_scheduling.py`:

```python
from myhome.chore_scheduling import adaptive_period_days
from myhome.models_chores import CompletionRecord


def test_daily_advances_by_one_day():
    chore = _chore(frequencyType="daily", frequency=1, frequencyMetadata={})
    from_dt = datetime(2026, 7, 4, tzinfo=timezone.utc)
    result = next_due_from_schedule(chore, from_dt)
    assert result == datetime(2026, 7, 5, tzinfo=timezone.utc)


def test_adaptive_period_days_falls_back_to_period_days_with_no_completions():
    chore = _chore(frequencyType="adaptive", periodDays=21.0, frequencyMetadata={})
    assert adaptive_period_days(chore, []) == 21.0


def test_adaptive_period_days_falls_back_to_period_days_with_one_completion():
    chore = _chore(frequencyType="adaptive", periodDays=21.0, frequencyMetadata={})
    completions = [CompletionRecord(id="r1", choreId="c1", completedAt="2026-06-01T00:00:00Z", scheduledDue="")]
    assert adaptive_period_days(chore, completions) == 21.0


def test_adaptive_period_days_averages_last_five_gaps():
    chore = _chore(frequencyType="adaptive", periodDays=21.0, frequencyMetadata={})
    # Gaps between consecutive completions: 10, 20, 30, 40, 50, 60 days.
    # Only the last 5 (20, 30, 40, 50, 60) should count -- average = 40.
    completions = [
        CompletionRecord(id="r1", choreId="c1", completedAt="2026-01-01T00:00:00Z", scheduledDue=""),
        CompletionRecord(id="r2", choreId="c1", completedAt="2026-01-11T00:00:00Z", scheduledDue=""),
        CompletionRecord(id="r3", choreId="c1", completedAt="2026-01-31T00:00:00Z", scheduledDue=""),
        CompletionRecord(id="r4", choreId="c1", completedAt="2026-03-02T00:00:00Z", scheduledDue=""),
        CompletionRecord(id="r5", choreId="c1", completedAt="2026-04-11T00:00:00Z", scheduledDue=""),
        CompletionRecord(id="r6", choreId="c1", completedAt="2026-05-31T00:00:00Z", scheduledDue=""),
        CompletionRecord(id="r7", choreId="c1", completedAt="2026-07-30T00:00:00Z", scheduledDue=""),
    ]
    assert adaptive_period_days(chore, completions) == 40.0


def test_adaptive_next_due_uses_averaged_gap():
    chore = _chore(frequencyType="adaptive", periodDays=21.0, frequencyMetadata={})
    completions = [
        CompletionRecord(id="r1", choreId="c1", completedAt="2026-01-01T00:00:00Z", scheduledDue=""),
        CompletionRecord(id="r2", choreId="c1", completedAt="2026-01-11T00:00:00Z", scheduledDue=""),
        CompletionRecord(id="r3", choreId="c1", completedAt="2026-01-31T00:00:00Z", scheduledDue=""),
        CompletionRecord(id="r4", choreId="c1", completedAt="2026-03-02T00:00:00Z", scheduledDue=""),
        CompletionRecord(id="r5", choreId="c1", completedAt="2026-04-11T00:00:00Z", scheduledDue=""),
        CompletionRecord(id="r6", choreId="c1", completedAt="2026-05-31T00:00:00Z", scheduledDue=""),
        CompletionRecord(id="r7", choreId="c1", completedAt="2026-07-30T00:00:00Z", scheduledDue=""),
    ]
    from_dt = datetime(2026, 7, 30, tzinfo=timezone.utc)
    result = next_due_from_schedule(chore, from_dt, completions)
    assert result == datetime(2026, 9, 8, tzinfo=timezone.utc)  # 2026-07-30 + 40 days
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /projects/myhome && pytest packages/backend/tests/test_chore_scheduling.py -v`
Expected: the 5 new tests FAIL (`test_daily_advances_by_one_day` falls through to the `periodDays` fallback and gets the wrong date; the `adaptive_period_days` tests fail with `ImportError`/`AttributeError` since the function doesn't exist yet).

- [ ] **Step 3: Implement**

In `packages/backend/src/myhome/chore_scheduling.py`, change the import line and add the new helper + branches:

```python
from .models_chores import Chore, CompletionRecord
```

Add this function after `to_weekday_num` and before `next_due_from_schedule`:

```python
def adaptive_period_days(chore: Chore, completions_for_chore: list[CompletionRecord]) -> float:
    """Average of the gaps (in days) between the chore's last 5 completions.

    Falls back to the chore's current `periodDays` (its seed value at
    creation, or whatever this function last computed it to be) when there
    are fewer than 2 completions to derive a gap from.
    """
    if len(completions_for_chore) < 2:
        return chore.periodDays
    ordered = sorted(completions_for_chore, key=lambda c: c.completedAt)
    timestamps = [datetime.fromisoformat(c.completedAt.replace("Z", "+00:00")) for c in ordered]
    gaps = [(timestamps[i] - timestamps[i - 1]).total_seconds() / 86400 for i in range(1, len(timestamps))]
    recent = gaps[-5:]
    return sum(recent) / len(recent)
```

Change the signature of `next_due_from_schedule` and add the `daily`/`adaptive` branches:

```python
def next_due_from_schedule(chore: Chore, from_dt: datetime, completions: list[CompletionRecord] | None = None) -> datetime:
    ft = chore.frequencyType
    freq = chore.frequency
    meta: dict = chore.frequencyMetadata or {}
    unit = meta.get("unit", "days")
    if ft == "day_of_the_month":
        allowed_months: set[int] = set(meta.get("months") or range(1, 13))
        next_m = add_months(from_dt.replace(day=1), 1)
        for _ in range(12):
            if next_m.month in allowed_months:
                break
            next_m = add_months(next_m, 1)
        day = min(freq, calendar.monthrange(next_m.year, next_m.month)[1])
        return next_m.replace(day=day)
    if ft == "days_of_the_week":
        days = sorted((to_weekday_num(d) - 1) % 7 for d in (meta.get("days") or []))
        if not days:
            return from_dt + timedelta(weeks=1)
        wd = from_dt.weekday()
        for d in days:
            if d > wd:
                return from_dt + timedelta(days=d - wd)
        return from_dt + timedelta(days=7 - wd + days[0])
    if ft == "daily":
        return from_dt + timedelta(days=1)
    # Donetick's own scheduler always advances "daily"/"weekly"/"monthly"/"yearly"
    # chores by exactly 1 unit and ignores `frequency` for them entirely -- that
    # multiplier only applies to the "interval" type (see upstream
    # internal/chore/scheduler.go). A chore imported with a stray `frequency`
    # value on one of these literal types must not be multiplied.
    if ft == "weekly":
        return from_dt + timedelta(weeks=1)
    if ft in ("monthly", "month"):
        return add_months(from_dt, 1)
    if ft in ("yearly", "year"):
        return add_years(from_dt, 1)
    if ft == "interval":
        if unit == "years":
            return add_years(from_dt, freq)
        if unit == "months":
            return add_months(from_dt, freq)
        if unit == "weeks":
            return from_dt + timedelta(weeks=freq)
        return from_dt + timedelta(days=freq)
    if ft == "adaptive":
        return from_dt + timedelta(days=adaptive_period_days(chore, completions or []))
    return from_dt + timedelta(days=chore.periodDays)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /projects/myhome && pytest packages/backend/tests/test_chore_scheduling.py -v`
Expected: all tests PASS (8 total: 3 pre-existing + 5 new).

- [ ] **Step 5: Commit**

```bash
cd /projects/myhome
git add packages/backend/src/myhome/chore_scheduling.py packages/backend/tests/test_chore_scheduling.py
git commit -m "feat(chores): add daily and adaptive scheduling to next_due_from_schedule"
```

---

### Task 2: Backend — refresh `periodDays` on completion, fix `year`/`yearly` alias

**Files:**
- Modify: `packages/backend/src/myhome/routes/chores.py`
- Test: `packages/backend/tests/test_chores.py`

**Interfaces:**
- Consumes: `adaptive_period_days(chore, completions_for_chore)` and `next_due_from_schedule(chore, from_dt, completions)` from Task 1.

- [ ] **Step 1: Write the failing tests**

Append to `packages/backend/tests/test_chores.py`:

```python
# --- Adaptive scheduling ---

def test_complete_chore_adaptive_falls_back_to_period_days_with_no_history(client, home_id, tmp_path):
    doc = ChoreDocument(
        chores=[
            Chore(
                id="c1", name="Change filter", emoji="🔧", periodDays=30.0,
                frequencyType="adaptive", frequency=1, frequencyMetadata={},
                nextDueDate="2027-01-01T00:00:00Z",
            )
        ],
        assignments=[],
    )
    save_chores(home_id, doc)
    resp = client.post(f"/api/homes/{home_id}/chores/c1/complete")
    assert resp.status_code == 200
    data = resp.json()
    assert data["periodDays"] == 30.0
    from datetime import datetime, timezone, timedelta
    now = datetime.now(timezone.utc)
    new_due = datetime.fromisoformat(data["nextDueDate"].replace("Z", "+00:00"))
    expected = now + timedelta(days=30)
    assert abs((new_due - expected).total_seconds()) < 5


def test_complete_chore_adaptive_recomputes_period_days_from_history(client, home_id, tmp_path):
    """Two completions 10 days apart are already recorded; completing a third
    time now should average in the new gap and refresh periodDays to reflect
    it, rather than leaving the original 30.0 seed value stale."""
    doc = ChoreDocument(
        chores=[
            Chore(
                id="c1", name="Change filter", emoji="🔧", periodDays=30.0,
                frequencyType="adaptive", frequency=1, frequencyMetadata={},
                nextDueDate="2026-07-30T00:00:00Z",
            )
        ],
        assignments=[],
        completions=[
            CompletionRecord(id="r1", choreId="c1", completedAt="2026-07-01T00:00:00Z", scheduledDue=""),
            CompletionRecord(id="r2", choreId="c1", completedAt="2026-07-11T00:00:00Z", scheduledDue=""),
        ],
    )
    save_chores(home_id, doc)
    resp = client.post(f"/api/homes/{home_id}/chores/c1/complete")
    assert resp.status_code == 200
    assert resp.json()["periodDays"] != 30.0


def test_complete_chore_non_adaptive_does_not_change_period_days(client, home_id, tmp_path):
    save_chores(home_id, make_chore_doc())
    resp = client.post(f"/api/homes/{home_id}/chores/c1/complete")
    assert resp.status_code == 200
    assert resp.json()["periodDays"] == 14


def test_complete_assignment_adaptive_recomputes_period_days(client, home_id, tmp_path):
    doc = ChoreDocument(
        chores=[
            Chore(
                id="c1", name="Change filter", emoji="🔧", periodDays=30.0,
                frequencyType="adaptive", frequency=1, frequencyMetadata={},
                nextDueDate="2026-07-30T00:00:00Z",
            )
        ],
        assignments=[],
        completions=[
            CompletionRecord(id="r1", choreId="c1", completedAt="2026-07-01T00:00:00Z", scheduledDue=""),
            CompletionRecord(id="r2", choreId="c1", completedAt="2026-07-11T00:00:00Z", scheduledDue=""),
        ],
    )
    save_chores(home_id, doc)
    aid = client.post(f"/api/homes/{home_id}/assignments", json={"choreId": "c1", "roomId": "r1"}).json()["id"]
    resp = client.post(f"/api/homes/{home_id}/assignments/{aid}/complete")
    assert resp.status_code == 200
    chores = client.get(f"/api/homes/{home_id}/chores").json()["chores"]
    chore = next(c for c in chores if c["id"] == "c1")
    assert chore["periodDays"] != 30.0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /projects/myhome && pytest packages/backend/tests/test_chores.py -v -k adaptive`
Expected: FAIL — `periodDays` stays `30.0` in all cases since nothing recomputes it yet.

- [ ] **Step 3: Implement**

In `packages/backend/src/myhome/routes/chores.py`, update the import:

```python
from ..chore_scheduling import next_due_from_schedule, adaptive_period_days
```

Fix the `_period_days` alias (find `elif freq_type == "yearly":` and change to):

```python
    elif freq_type in ("yearly", "year"):
        return 365.0
```

Replace `complete_chore` with (reorders the completion-append before computing `next_due` so the just-recorded completion counts toward the adaptive average, and refreshes `periodDays` for adaptive chores):

```python
@router.post("/api/homes/{home_id}/chores/{chore_id}/complete", response_model=Chore)
def complete_chore(
    home_id: str, chore_id: str, body: CompleteRequest | None = None,
    current_user_id: str = Depends(get_current_user_id),
) -> Chore:
    doc = load_chores(home_id)
    chore = next((c for c in doc.chores if c.id == chore_id), None)
    if chore is None:
        raise HTTPException(status_code=404, detail="Chore not found")
    notes = body.notes if body else ""
    now = datetime.now(timezone.utc)
    if chore.scheduleFromDue and chore.nextDueDate:
        try:
            from_dt = datetime.fromisoformat(chore.nextDueDate.replace("Z", "+00:00"))
        except ValueError:
            from_dt = now
    else:
        from_dt = now
    doc.completions.append(CompletionRecord(
        id=str(uuid.uuid4()),
        choreId=chore_id,
        completedAt=now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        scheduledDue=chore.nextDueDate,
        notes=notes,
    ))
    completions_for_chore = [c for c in doc.completions if c.choreId == chore_id]
    next_due = next_due_from_schedule(chore, from_dt, completions_for_chore)
    next_due_str = next_due.strftime("%Y-%m-%dT%H:%M:%SZ")
    if chore.frequencyType == "adaptive":
        chore.periodDays = adaptive_period_days(chore, completions_for_chore)
    for a in doc.assignments:
        if a.choreId == chore_id:
            a.nextDueDate = next_due_str
    chore.nextDueDate = next_due_str
    save_chores(home_id, doc)
    log_activity(home_id, current_user_id, "chores", "complete", chore.name, chore_id)
    return chore
```

Replace `complete_assignment` with the same pattern:

```python
@router.post("/api/homes/{home_id}/assignments/{assignment_id}/complete", response_model=Assignment)
def complete_assignment(
    home_id: str, assignment_id: str, body: CompleteRequest | None = None,
    current_user_id: str = Depends(get_current_user_id),
) -> Assignment:
    doc = load_chores(home_id)
    assignment = next((a for a in doc.assignments if a.id == assignment_id), None)
    if assignment is None:
        raise HTTPException(status_code=404, detail="Assignment not found")
    chore = next((c for c in doc.chores if c.id == assignment.choreId), None)
    if chore is None:
        raise HTTPException(status_code=404, detail="Chore not found")
    notes = body.notes if body else ""
    now = datetime.now(timezone.utc)
    if chore.scheduleFromDue and assignment.nextDueDate:
        try:
            from_dt = datetime.fromisoformat(assignment.nextDueDate.replace("Z", "+00:00"))
        except ValueError:
            from_dt = now
    else:
        from_dt = now
    doc.completions.append(CompletionRecord(
        id=str(uuid.uuid4()),
        choreId=chore.id,
        assignmentId=assignment_id,
        completedAt=now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        scheduledDue=assignment.nextDueDate,
        notes=notes,
    ))
    completions_for_chore = [c for c in doc.completions if c.choreId == chore.id]
    next_due = next_due_from_schedule(chore, from_dt, completions_for_chore)
    if chore.frequencyType == "adaptive":
        chore.periodDays = adaptive_period_days(chore, completions_for_chore)
    assignment.nextDueDate = next_due.strftime("%Y-%m-%dT%H:%M:%SZ")
    save_chores(home_id, doc)
    log_activity(home_id, current_user_id, "chores", "complete", chore.name, chore.id)
    return assignment
```

Note: keep the exact route decorators (`@router.post(...)`) already on these two functions unchanged — only the function bodies above change.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /projects/myhome && pytest packages/backend/tests/test_chores.py -v`
Expected: all tests in the file PASS (including the 4 new adaptive ones and every pre-existing test — the reordering must not change behavior for non-adaptive chores).

- [ ] **Step 5: Commit**

```bash
cd /projects/myhome
git add packages/backend/src/myhome/routes/chores.py packages/backend/tests/test_chores.py
git commit -m "feat(chores): refresh periodDays for adaptive chores after each completion"
```

---

### Task 3: Backend — MCP `complete_chore` tool gets the same adaptive refresh

**Files:**
- Modify: `packages/backend/src/myhome/mcp_tools_chores.py`
- Test: `packages/backend/tests/test_mcp_tools_chores.py`

**Interfaces:**
- Consumes: `adaptive_period_days`, `next_due_from_schedule` from Task 1 (same as Task 2, applied to the MCP tool implementation instead of the REST route).

- [ ] **Step 1: Write the failing test**

Append to `packages/backend/tests/test_mcp_tools_chores.py`:

```python
def test_complete_chore_adaptive_falls_back_to_period_days_with_no_history(home_id):
    from myhome.mcp_tools_chores import _complete_chore_impl, _create_chore_impl
    chore = _create_chore_impl(
        home_id, "Change filter", "🔧", 30.0, "2026-07-30T00:00:00Z",
        frequency_type="adaptive", frequency=1, frequency_metadata={},
    )
    result = _complete_chore_impl(home_id, chore["id"])
    assert result["periodDays"] == 30.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /projects/myhome && pytest packages/backend/tests/test_mcp_tools_chores.py -v -k adaptive`
Expected: FAIL if `_complete_chore_impl` errors on the new `next_due_from_schedule` signature, or PASS-but-for-the-wrong-reason if it silently ignores adaptive — check by temporarily asserting `result["periodDays"] == 999` first if unsure; either way, proceed to Step 3 since the goal is to lock in the refresh behavior, not merely reach a passing assertion.

- [ ] **Step 3: Implement**

In `packages/backend/src/myhome/mcp_tools_chores.py`, update the import (find the existing `from .chore_scheduling import next_due_from_schedule` line):

```python
from .chore_scheduling import next_due_from_schedule, adaptive_period_days
```

Replace `_complete_chore_impl` with:

```python
def _complete_chore_impl(home_id: str | None, chore_id: str, notes: str = "") -> dict:
    resolved = _resolve_home_id(home_id)
    doc = load_chores(resolved)
    chore = next((c for c in doc.chores if c.id == chore_id), None)
    if chore is None:
        raise ValueError(f"Unknown chore_id {chore_id!r}")
    now = datetime.now(timezone.utc)
    if chore.scheduleFromDue and chore.nextDueDate:
        try:
            from_dt = datetime.fromisoformat(chore.nextDueDate.replace("Z", "+00:00"))
        except ValueError:
            from_dt = now
    else:
        from_dt = now
    doc.completions.append(CompletionRecord(
        id=str(uuid.uuid4()),
        choreId=chore_id,
        completedAt=now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        scheduledDue=chore.nextDueDate,
        notes=notes,
    ))
    completions_for_chore = [c for c in doc.completions if c.choreId == chore_id]
    next_due = next_due_from_schedule(chore, from_dt, completions_for_chore)
    next_due_str = next_due.strftime("%Y-%m-%dT%H:%M:%SZ")
    if chore.frequencyType == "adaptive":
        chore.periodDays = adaptive_period_days(chore, completions_for_chore)
    for a in doc.assignments:
        if a.choreId == chore_id:
            a.nextDueDate = next_due_str
    chore.nextDueDate = next_due_str
    save_chores(resolved, doc)
    return chore.model_dump()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /projects/myhome && pytest packages/backend/tests/test_mcp_tools_chores.py -v`
Expected: all tests in the file PASS.

- [ ] **Step 5: Run the full backend suite**

Run: `cd /projects/myhome && pytest packages/backend -q`
Expected: all tests PASS (no regressions from Tasks 1-3).

- [ ] **Step 6: Commit**

```bash
cd /projects/myhome
git add packages/backend/src/myhome/mcp_tools_chores.py packages/backend/tests/test_mcp_tools_chores.py
git commit -m "feat(chores): refresh periodDays for adaptive chores in the MCP complete_chore tool"
```

---

### Task 4: Frontend — new i18n keys (English + French)

**Files:**
- Modify: `packages/editor/src/lib/locales/en.json`
- Modify: `packages/editor/src/lib/locales/fr.json`

**Interfaces:**
- Produces: `chores.schedule.adaptive`, `chores.schedule.adaptiveDays` (used by Task 5); `chores.scheduleEditor.*` (used by Task 8); `chores.quickAdd.*` (used by Task 9). Every key below must exist in both files under exactly these paths before later tasks run.

- [ ] **Step 1: Edit `en.json`**

Find (inside `chores.schedule`):
```json
      "daily": "Daily",
      "quarterly": "Quarterly",
      "everyNDays": "Every {n} days"
    },
```
Replace with:
```json
      "daily": "Daily",
      "quarterly": "Quarterly",
      "everyNDays": "Every {n} days",
      "adaptive": "Adaptive",
      "adaptiveDays": "Adaptive (~{n} days)"
    },
```

Find (the end of `chores.newModal`, immediately before the closing brace of `chores`):
```json
      "creating": "Creating…",
      "failedToCreate": "Failed to create"
    }
  },
```
Replace with:
```json
      "creating": "Creating…",
      "failedToCreate": "Failed to create"
    },
    "scheduleEditor": {
      "category": "Recurrence",
      "categoryInterval": "Custom interval",
      "categoryDaily": "Daily",
      "categoryWeekly": "Weekly on specific day(s)",
      "categoryMonthly": "Monthly on a specific day",
      "categoryYearly": "Yearly",
      "categoryAdaptive": "Adaptive (learns from history)",
      "dayOfMonth": "Day of month",
      "restrictMonths": "Restrict to specific months",
      "periodDays": "Period (days)",
      "periodDaysHint": "Adjusts automatically after each completion",
      "selectAtLeastOneDay": "Select at least one day"
    },
    "quickAdd": {
      "label": "Quick add",
      "placeholder": "e.g. \"Change water filter every 6 months\"",
      "parse": "Parse"
    }
  },
```

- [ ] **Step 2: Edit `fr.json`**

Find (inside `chores.schedule`):
```json
      "daily": "Quotidien",
      "quarterly": "Trimestriel",
      "everyNDays": "Tous les {n} jours"
    },
```
Replace with:
```json
      "daily": "Quotidien",
      "quarterly": "Trimestriel",
      "everyNDays": "Tous les {n} jours",
      "adaptive": "Adaptatif",
      "adaptiveDays": "Adaptatif (~{n} jours)"
    },
```

Find (the end of `chores.newModal`, immediately before the closing brace of `chores`):
```json
      "creating": "Création…",
      "failedToCreate": "Échec de la création"
    }
```
Replace with:
```json
      "creating": "Création…",
      "failedToCreate": "Échec de la création"
    },
    "scheduleEditor": {
      "category": "Récurrence",
      "categoryInterval": "Intervalle personnalisé",
      "categoryDaily": "Quotidien",
      "categoryWeekly": "Hebdomadaire, jour(s) précis",
      "categoryMonthly": "Mensuel, jour précis",
      "categoryYearly": "Annuel",
      "categoryAdaptive": "Adaptatif (apprend de l'historique)",
      "dayOfMonth": "Jour du mois",
      "restrictMonths": "Restreindre à des mois précis",
      "periodDays": "Période (jours)",
      "periodDaysHint": "S'ajuste automatiquement après chaque réalisation",
      "selectAtLeastOneDay": "Sélectionnez au moins un jour"
    },
    "quickAdd": {
      "label": "Ajout rapide",
      "placeholder": "ex. « Changer le filtre à eau tous les 6 mois »",
      "parse": "Analyser"
    }
```

(This must land immediately before whatever closing brace already followed `"failedToCreate": "Échec de la création"` in the original file — do not change that brace itself, only insert the new siblings before it.)

- [ ] **Step 3: Verify both files are valid JSON and the test suite still loads them**

Run: `cd /projects/myhome/packages/editor && node -e "JSON.parse(require('fs').readFileSync('src/lib/locales/en.json'))" && node -e "JSON.parse(require('fs').readFileSync('src/lib/locales/fr.json'))" && echo OK`
Expected: prints `OK` (both files parse).

Run: `cd /projects/myhome/packages/editor && npx vitest run`
Expected: all existing tests still PASS — `test/setup.ts` loads both locale files at startup, so a JSON syntax error here would fail every single test in the suite.

- [ ] **Step 4: Commit**

```bash
cd /projects/myhome
git add packages/editor/src/lib/locales/en.json packages/editor/src/lib/locales/fr.json
git commit -m "feat(chores): add i18n keys for adaptive scheduling, ScheduleEditor, and quick-add"
```

---

### Task 5: Frontend — `scheduleLabel` gets an `adaptive` branch

**Files:**
- Modify: `packages/editor/src/lib/choreStore.svelte.ts`
- Test: `packages/editor/src/lib/choreStore.test.ts`

**Interfaces:**
- Consumes: `chores.schedule.adaptiveDays` i18n key from Task 4.

- [ ] **Step 1: Write the failing test**

Append to the `describe("scheduleLabel", ...)` block in `packages/editor/src/lib/choreStore.test.ts`:

```ts
  it("shows the current period for an adaptive chore", () => {
    const chore = makeChore({ frequencyType: "adaptive", frequency: 1, frequencyMetadata: {}, periodDays: 42 });
    expect(scheduleLabel(chore)).toBe("Adaptive (~42 days)");
  });
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /projects/myhome/packages/editor && npx vitest run src/lib/choreStore.test.ts`
Expected: FAIL — the `chore.periodDays}d` fallback returns `"42d"`, not `"Adaptive (~42 days)"`.

- [ ] **Step 3: Implement**

In `packages/editor/src/lib/choreStore.svelte.ts`, find:
```ts
    return t("chores.schedule.everyNDays", { values: { n } });
  }
  return `${chore.periodDays}d`;
}
```
Replace with:
```ts
    return t("chores.schedule.everyNDays", { values: { n } });
  }
  if (ft === "adaptive") return t("chores.schedule.adaptiveDays", { values: { n: Math.round(chore.periodDays) } });
  return `${chore.periodDays}d`;
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /projects/myhome/packages/editor && npx vitest run src/lib/choreStore.test.ts`
Expected: all 6 tests PASS.

- [ ] **Step 5: Commit**

```bash
cd /projects/myhome
git add packages/editor/src/lib/choreStore.svelte.ts packages/editor/src/lib/choreStore.test.ts
git commit -m "feat(chores): render adaptive schedules in scheduleLabel"
```

---

### Task 6: Frontend — `ChoresPage.svelte` schedule filter recognizes `daily` and `adaptive`

**Files:**
- Modify: `packages/editor/src/lib/components/ChoresPage.svelte`

**Interfaces:**
- Consumes: `chores.schedule.adaptive` i18n key from Task 4.

- [ ] **Step 1: Implement**

Find (the `scheduleCategory` function):
```ts
  function scheduleCategory(chore: Chore): string {
    const { frequencyType: ft, frequency: n, frequencyMetadata: meta } = chore;
    const unit = (meta as Record<string, string>)?.unit ?? "days";
    if (ft === "days_of_the_week" || ft === "weekly") return "weekly";
    if (ft === "day_of_the_month" || ft === "monthly") return "monthly";
    if (ft === "yearly") return "yearly";
    if (ft === "interval") {
```
Replace with:
```ts
  function scheduleCategory(chore: Chore): string {
    const { frequencyType: ft, frequency: n, frequencyMetadata: meta } = chore;
    const unit = (meta as Record<string, string>)?.unit ?? "days";
    if (ft === "daily") return "daily";
    if (ft === "adaptive") return "adaptive";
    if (ft === "days_of_the_week" || ft === "weekly") return "weekly";
    if (ft === "day_of_the_month" || ft === "monthly") return "monthly";
    if (ft === "yearly") return "yearly";
    if (ft === "interval") {
```

Find (the schedule filter `<select>`):
```svelte
      <select class="native-input" bind:value={scheduleFilter}>
        <option value="">{$_('chores.page.allSchedules')}</option>
        <option value="daily">{$_('chores.schedule.daily')}</option>
        <option value="weekly">{$_('chores.schedule.weekly')}</option>
        <option value="monthly">{$_('chores.schedule.monthly')}</option>
        <option value="yearly">{$_('chores.schedule.yearly')}</option>
      </select>
```
Replace with:
```svelte
      <select class="native-input" bind:value={scheduleFilter}>
        <option value="">{$_('chores.page.allSchedules')}</option>
        <option value="daily">{$_('chores.schedule.daily')}</option>
        <option value="weekly">{$_('chores.schedule.weekly')}</option>
        <option value="monthly">{$_('chores.schedule.monthly')}</option>
        <option value="yearly">{$_('chores.schedule.yearly')}</option>
        <option value="adaptive">{$_('chores.schedule.adaptive')}</option>
      </select>
```

- [ ] **Step 2: Typecheck**

Run: `cd /projects/myhome/packages/editor && npx svelte-check --tsconfig ./tsconfig.json 2>&1 | tail -20`
Expected: no new errors introduced by this change (pre-existing warnings in unrelated files are fine — this codebase already has some, per prior work).

- [ ] **Step 3: Commit**

```bash
cd /projects/myhome
git add packages/editor/src/lib/components/ChoresPage.svelte
git commit -m "fix(chores): recognize literal daily chores and adaptive chores in the schedule filter"
```

---

### Task 7: Frontend — natural-language schedule parser (English + French)

**Files:**
- Create: `packages/editor/src/lib/scheduleParser.ts`
- Test: `packages/editor/test/scheduleParser.test.ts`

**Interfaces:**
- Produces: `parseScheduleText(text: string, loc: "en" | "fr"): ParsedSchedule | null` where `ParsedSchedule = { name: string; schedule: { frequencyType: string; frequency: number; frequencyMetadata: Record<string, unknown> } }`. Used by Task 9.

- [ ] **Step 1: Write the failing tests**

Create `packages/editor/test/scheduleParser.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import { parseScheduleText } from "./scheduleParser";

describe("parseScheduleText (English)", () => {
  it("parses a custom interval in months", () => {
    const result = parseScheduleText("Change water filter every 6 months", "en");
    expect(result).toEqual({
      name: "Change water filter",
      schedule: { frequencyType: "interval", frequency: 6, frequencyMetadata: { unit: "months" } },
    });
  });

  it("parses a custom interval in days", () => {
    const result = parseScheduleText("Clean the gutters every 14 days", "en");
    expect(result).toEqual({
      name: "Clean the gutters",
      schedule: { frequencyType: "interval", frequency: 14, frequencyMetadata: { unit: "days" } },
    });
  });

  it("parses specific weekdays, ignoring an unparsed trailing time", () => {
    const result = parseScheduleText("Take the trash out every Monday and Tuesday at 6:15 pm", "en");
    expect(result).toEqual({
      name: "Take the trash out at 6:15 pm",
      schedule: { frequencyType: "days_of_the_week", frequency: 1, frequencyMetadata: { days: [1, 2] } },
    });
  });

  it("parses daily", () => {
    const result = parseScheduleText("Water the plants every day", "en");
    expect(result).toEqual({
      name: "Water the plants",
      schedule: { frequencyType: "daily", frequency: 1, frequencyMetadata: {} },
    });
  });

  it("parses yearly", () => {
    const result = parseScheduleText("Pay the property tax every year", "en");
    expect(result).toEqual({
      name: "Pay the property tax",
      schedule: { frequencyType: "yearly", frequency: 1, frequencyMetadata: {} },
    });
  });

  it("parses a specific day of the month", () => {
    const result = parseScheduleText("Pay rent on the 1st of every month", "en");
    expect(result).toEqual({
      name: "Pay rent",
      schedule: { frequencyType: "day_of_the_month", frequency: 1, frequencyMetadata: {} },
    });
  });

  it("falls back to a bare day interval when no unit is recognized", () => {
    const result = parseScheduleText("Rotate the mattress every 90", "en");
    expect(result).toEqual({
      name: "Rotate the mattress",
      schedule: { frequencyType: "interval", frequency: 90, frequencyMetadata: { unit: "days" } },
    });
  });

  it("returns null when nothing recurrence-like is found", () => {
    expect(parseScheduleText("Buy milk", "en")).toBeNull();
  });

  it("returns null for empty input", () => {
    expect(parseScheduleText("   ", "en")).toBeNull();
  });
});

describe("parseScheduleText (French)", () => {
  it("parses a custom interval in months", () => {
    const result = parseScheduleText("Changer le filtre à eau tous les 6 mois", "fr");
    expect(result).toEqual({
      name: "Changer le filtre à eau",
      schedule: { frequencyType: "interval", frequency: 6, frequencyMetadata: { unit: "months" } },
    });
  });

  it("parses specific weekdays", () => {
    const result = parseScheduleText("Sortir la poubelle tous les lundis et mardis", "fr");
    expect(result).toEqual({
      name: "Sortir la poubelle",
      schedule: { frequencyType: "days_of_the_week", frequency: 1, frequencyMetadata: { days: [1, 2] } },
    });
  });

  it("parses daily", () => {
    const result = parseScheduleText("Arroser les plantes tous les jours", "fr");
    expect(result).toEqual({
      name: "Arroser les plantes",
      schedule: { frequencyType: "daily", frequency: 1, frequencyMetadata: {} },
    });
  });

  it("parses yearly", () => {
    const result = parseScheduleText("Payer la taxe foncière chaque année", "fr");
    expect(result).toEqual({
      name: "Payer la taxe foncière",
      schedule: { frequencyType: "yearly", frequency: 1, frequencyMetadata: {} },
    });
  });

  it("parses a specific day of the month", () => {
    const result = parseScheduleText("Payer le loyer le 1 de chaque mois", "fr");
    expect(result).toEqual({
      name: "Payer le loyer",
      schedule: { frequencyType: "day_of_the_month", frequency: 1, frequencyMetadata: {} },
    });
  });

  it("returns null when nothing recurrence-like is found", () => {
    expect(parseScheduleText("Acheter du lait", "fr")).toBeNull();
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /projects/myhome/packages/editor && npx vitest run test/scheduleParser.test.ts`
Expected: FAIL with a module-not-found error (`scheduleParser.ts` doesn't exist yet).

- [ ] **Step 3: Implement**

Create `packages/editor/src/lib/scheduleParser.ts`:

```ts
export interface ParsedSchedule {
  name: string;
  schedule: {
    frequencyType: string;
    frequency: number;
    frequencyMetadata: Record<string, unknown>;
  };
}

const WEEKDAY_NUM: Record<string, number> = {
  monday: 1, tuesday: 2, wednesday: 3, thursday: 4, friday: 5, saturday: 6, sunday: 7,
  lundi: 1, mardi: 2, mercredi: 3, jeudi: 4, vendredi: 5, samedi: 6, dimanche: 7,
};

const UNIT_WORDS: Record<string, "days" | "weeks" | "months" | "years"> = {
  day: "days", days: "days", jour: "days", jours: "days",
  week: "weeks", weeks: "weeks", semaine: "weeks", semaines: "weeks",
  month: "months", months: "months", mois: "months",
  year: "years", years: "years", an: "years", ans: "years",
  année: "years", annee: "years", années: "years", annees: "years",
};

function normalizeDayToken(token: string): number | null {
  const clean = token.trim().toLowerCase().replace(/s$/, "");
  return WEEKDAY_NUM[clean] ?? null;
}

function stripMatch(text: string, match: RegExpMatchArray): string {
  const idx = match.index ?? 0;
  const before = text.slice(0, idx);
  const after = text.slice(idx + match[0].length);
  const cleaned = (before + " " + after).replace(/\s+/g, " ").trim().replace(/[,.;:]+$/, "");
  return cleaned.length > 0 ? cleaned : text.trim();
}

export function parseScheduleText(text: string, loc: "en" | "fr"): ParsedSchedule | null {
  const trimmed = text.trim();
  if (!trimmed) return null;

  const dailyRe = loc === "fr" ? /\btous\s+les\s+jours\b|\bquotidien(?:nement)?\b/i : /\bevery\s+day\b|\bdaily\b/i;
  const dailyMatch = trimmed.match(dailyRe);
  if (dailyMatch) {
    return { name: stripMatch(trimmed, dailyMatch), schedule: { frequencyType: "daily", frequency: 1, frequencyMetadata: {} } };
  }

  const yearlyRe = loc === "fr"
    ? /\bchaque\s+ann[ée]e\b|\btous\s+les\s+ans\b|\bannuellement\b/i
    : /\bevery\s+year\b|\byearly\b|\bannually\b/i;
  const yearlyMatch = trimmed.match(yearlyRe);
  if (yearlyMatch) {
    return { name: stripMatch(trimmed, yearlyMatch), schedule: { frequencyType: "yearly", frequency: 1, frequencyMetadata: {} } };
  }

  const dayNames = loc === "fr"
    ? "lundis?|mardis?|mercredis?|jeudis?|vendredis?|samedis?|dimanches?"
    : "mondays?|tuesdays?|wednesdays?|thursdays?|fridays?|saturdays?|sundays?";
  const dayListRe = `(?:${dayNames})(?:\\s*(?:,|${loc === "fr" ? "et" : "and"})\\s*(?:${dayNames}))*`;
  const weekdayRe = loc === "fr"
    ? new RegExp(`\\b(?:tous\\s+les|chaque)\\s+(${dayListRe})`, "i")
    : new RegExp(`\\b(?:every|each)\\s+(${dayListRe})`, "i");
  const weekdayMatch = trimmed.match(weekdayRe);
  if (weekdayMatch) {
    const splitRe = loc === "fr" ? /,|et/i : /,|and/i;
    const days = weekdayMatch[1]
      .split(splitRe)
      .map((t) => normalizeDayToken(t))
      .filter((n): n is number => n !== null)
      .sort((a, b) => a - b);
    if (days.length > 0) {
      return { name: stripMatch(trimmed, weekdayMatch), schedule: { frequencyType: "days_of_the_week", frequency: 1, frequencyMetadata: { days } } };
    }
  }

  const domRe = loc === "fr"
    ? /\ble\s+(\d{1,2})(?:er)?\s+de\s+chaque\s+mois\b/i
    : /\bon\s+the\s+(\d{1,2})(?:st|nd|rd|th)?\s+of\s+every\s+month\b/i;
  const domMatch = trimmed.match(domRe);
  if (domMatch) {
    const day = Math.min(31, Math.max(1, parseInt(domMatch[1], 10)));
    return { name: stripMatch(trimmed, domMatch), schedule: { frequencyType: "day_of_the_month", frequency: day, frequencyMetadata: {} } };
  }

  const unitWords = Object.keys(UNIT_WORDS).join("|");
  const intervalRe = loc === "fr"
    ? new RegExp(`\\btous\\s+les\\s+(\\d+)\\s+(${unitWords})\\b`, "i")
    : new RegExp(`\\bevery\\s+(\\d+)\\s+(${unitWords})\\b`, "i");
  const intervalMatch = trimmed.match(intervalRe);
  if (intervalMatch) {
    const n = Math.max(1, parseInt(intervalMatch[1], 10));
    const unit = UNIT_WORDS[intervalMatch[2].toLowerCase()] ?? "days";
    return { name: stripMatch(trimmed, intervalMatch), schedule: { frequencyType: "interval", frequency: n, frequencyMetadata: { unit } } };
  }

  const bareRe = loc === "fr" ? /\btous\s+les\s+(\d+)\b/i : /\bevery\s+(\d+)\b/i;
  const bareMatch = trimmed.match(bareRe);
  if (bareMatch) {
    const n = Math.max(1, parseInt(bareMatch[1], 10));
    return { name: stripMatch(trimmed, bareMatch), schedule: { frequencyType: "interval", frequency: n, frequencyMetadata: { unit: "days" } } };
  }

  return null;
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /projects/myhome/packages/editor && npx vitest run test/scheduleParser.test.ts`
Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
cd /projects/myhome
git add packages/editor/src/lib/scheduleParser.ts packages/editor/test/scheduleParser.test.ts
git commit -m "feat(chores): add EN/FR natural-language schedule parser"
```

---

### Task 8: Frontend — new `ScheduleEditor.svelte` component

**Files:**
- Create: `packages/editor/src/lib/components/ScheduleEditor.svelte`

**Interfaces:**
- Consumes: `chores.scheduleEditor.*`, `chores.schedule.dayAbbrev.*`, `chores.newModal.unit*` i18n keys (Task 4 and pre-existing).
- Produces: a component with bindable props `frequencyType: string`, `frequency: number`, `frequencyMetadata: Record<string, unknown>`, `periodDays: number`, `valid: boolean` (default `true`). Used by Tasks 9 and 10. Gets a real `test/ScheduleEditor.test.ts` component test (see Global Constraints correction above) plus the Task 11 manual browser pass.

- [ ] **Step 1: Implement**

Create `packages/editor/src/lib/components/ScheduleEditor.svelte`:

```svelte
<script lang="ts">
  import { _, locale } from "svelte-i18n";

  type Category = "interval" | "daily" | "days_of_the_week" | "day_of_the_month" | "yearly" | "adaptive";

  interface Props {
    frequencyType: string;
    frequency: number;
    frequencyMetadata: Record<string, unknown>;
    periodDays: number;
    valid?: boolean;
  }

  let {
    frequencyType = $bindable(),
    frequency = $bindable(),
    frequencyMetadata = $bindable(),
    periodDays = $bindable(),
    valid = $bindable(true),
  }: Props = $props();

  const UNIT_DAYS: Record<string, number> = { days: 1, weeks: 7, months: 30, years: 365 };
  const DAY_KEYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"];

  function categoryFor(ft: string): Category {
    if (ft === "days_of_the_week") return "days_of_the_week";
    if (ft === "day_of_the_month") return "day_of_the_month";
    if (ft === "yearly") return "yearly";
    if (ft === "adaptive") return "adaptive";
    if (ft === "daily") return "daily";
    return "interval";
  }

  const initialDays = (frequencyMetadata?.days as number[] | undefined) ?? [];
  const initialMonths = (frequencyMetadata?.months as number[] | undefined) ?? [];

  let cat = $state<Category>(categoryFor(frequencyType));
  let intervalN = $state(frequencyType === "interval" ? frequency : 30);
  let intervalUnit = $state<"days" | "weeks" | "months" | "years">(
    (frequencyMetadata?.unit as "days" | "weeks" | "months" | "years" | undefined) ?? "days"
  );
  let selectedDays = $state<number[]>(frequencyType === "days_of_the_week" ? initialDays : []);
  let dayOfMonth = $state(frequencyType === "day_of_the_month" ? frequency : 1);
  let restrictMonths = $state(frequencyType === "day_of_the_month" && initialMonths.length > 0);
  let selectedMonths = $state<number[]>(frequencyType === "day_of_the_month" ? initialMonths : []);
  let adaptivePeriod = $state(frequencyType === "adaptive" ? periodDays : 30);

  function monthNames(loc: string): string[] {
    return Array.from({ length: 12 }, (_unused, i) =>
      new Intl.DateTimeFormat(loc, { month: "long" }).format(new Date(2000, i, 1))
    );
  }
  const MONTH_NAMES = $derived(monthNames($locale ?? "en"));

  function toggleDay(d: number): void {
    selectedDays = selectedDays.includes(d) ? selectedDays.filter((x) => x !== d) : [...selectedDays, d].sort((a, b) => a - b);
  }
  function toggleMonth(m: number): void {
    selectedMonths = selectedMonths.includes(m) ? selectedMonths.filter((x) => x !== m) : [...selectedMonths, m].sort((a, b) => a - b);
  }

  $effect(() => {
    if (cat === "interval") {
      frequencyType = "interval";
      frequency = intervalN;
      frequencyMetadata = { unit: intervalUnit };
      periodDays = intervalN * UNIT_DAYS[intervalUnit];
      valid = intervalN >= 1;
    } else if (cat === "daily") {
      frequencyType = "daily";
      frequency = 1;
      frequencyMetadata = {};
      periodDays = 1;
      valid = true;
    } else if (cat === "days_of_the_week") {
      frequencyType = "days_of_the_week";
      frequency = 1;
      frequencyMetadata = { days: selectedDays };
      periodDays = 7;
      valid = selectedDays.length > 0;
    } else if (cat === "day_of_the_month") {
      frequencyType = "day_of_the_month";
      frequency = dayOfMonth;
      frequencyMetadata = restrictMonths && selectedMonths.length > 0 ? { months: selectedMonths } : {};
      periodDays = 30;
      valid = dayOfMonth >= 1 && dayOfMonth <= 31;
    } else if (cat === "yearly") {
      frequencyType = "yearly";
      frequency = 1;
      frequencyMetadata = {};
      periodDays = 365;
      valid = true;
    } else {
      frequencyType = "adaptive";
      frequency = 1;
      frequencyMetadata = {};
      periodDays = adaptivePeriod;
      valid = adaptivePeriod >= 1;
    }
  });
</script>

<div class="schedule-editor">
  <div class="field">
    <label for="se-category">{$_('chores.scheduleEditor.category')}</label>
    <select id="se-category" class="native-input" bind:value={cat}>
      <option value="interval">{$_('chores.scheduleEditor.categoryInterval')}</option>
      <option value="daily">{$_('chores.scheduleEditor.categoryDaily')}</option>
      <option value="days_of_the_week">{$_('chores.scheduleEditor.categoryWeekly')}</option>
      <option value="day_of_the_month">{$_('chores.scheduleEditor.categoryMonthly')}</option>
      <option value="yearly">{$_('chores.scheduleEditor.categoryYearly')}</option>
      <option value="adaptive">{$_('chores.scheduleEditor.categoryAdaptive')}</option>
    </select>
  </div>

  {#if cat === "interval"}
    <div class="field freq-row">
      <input type="number" class="native-input freq-n" bind:value={intervalN} min="1" />
      <select class="native-input" bind:value={intervalUnit}>
        <option value="days">{$_('chores.newModal.unitDays')}</option>
        <option value="weeks">{$_('chores.newModal.unitWeeks')}</option>
        <option value="months">{$_('chores.newModal.unitMonths')}</option>
        <option value="years">{$_('chores.newModal.unitYears')}</option>
      </select>
    </div>
  {:else if cat === "days_of_the_week"}
    <div class="field">
      <div class="day-toggles">
        {#each DAY_KEYS as key, i (key)}
          <button
            type="button"
            class="day-toggle"
            class:active={selectedDays.includes(i + 1)}
            onclick={() => toggleDay(i + 1)}
          >{$_(`chores.schedule.dayAbbrev.${key}`)}</button>
        {/each}
      </div>
      {#if selectedDays.length === 0}<div class="hint-error">{$_('chores.scheduleEditor.selectAtLeastOneDay')}</div>{/if}
    </div>
  {:else if cat === "day_of_the_month"}
    <div class="field">
      <label for="se-dom">{$_('chores.scheduleEditor.dayOfMonth')}</label>
      <input id="se-dom" type="number" class="native-input freq-n" bind:value={dayOfMonth} min="1" max="31" />
    </div>
    <div class="field-row">
      <input type="checkbox" id="se-restrict" bind:checked={restrictMonths} />
      <label for="se-restrict" class="checkbox-label">{$_('chores.scheduleEditor.restrictMonths')}</label>
    </div>
    {#if restrictMonths}
      <div class="month-toggles">
        {#each MONTH_NAMES as name, i (name)}
          <button
            type="button"
            class="day-toggle"
            class:active={selectedMonths.includes(i + 1)}
            onclick={() => toggleMonth(i + 1)}
          >{name}</button>
        {/each}
      </div>
    {/if}
  {:else if cat === "adaptive"}
    <div class="field">
      <label for="se-adaptive">{$_('chores.scheduleEditor.periodDays')}</label>
      <input id="se-adaptive" type="number" class="native-input freq-n" bind:value={adaptivePeriod} min="1" />
      <span class="hint">{$_('chores.scheduleEditor.periodDaysHint')}</span>
    </div>
  {/if}
</div>

<style>
  .schedule-editor { display: flex; flex-direction: column; gap: var(--space-3); }
  .field { display: flex; flex-direction: column; gap: 4px; }
  .field label { font-size: 11px; color: var(--text-muted); }
  .field-row { display: flex; align-items: center; gap: 8px; }
  .checkbox-label { font-size: 12px; color: var(--text-muted); cursor: pointer; }
  .native-input {
    background: var(--surface-alt); border: 1px solid var(--border); color: var(--text);
    padding: 8px 12px; border-radius: var(--radius-md);
    font-size: 13px; font-family: var(--font-sans); width: 100%; box-sizing: border-box;
  }
  .native-input:focus { outline: none; border-color: var(--accent); }
  select.native-input { cursor: pointer; }
  .freq-row { flex-direction: row; gap: 8px; }
  .freq-n { width: 80px; }
  .freq-row select { flex: 1; }
  .day-toggles, .month-toggles { display: flex; flex-wrap: wrap; gap: 6px; }
  .day-toggle {
    padding: 6px 10px; border: 1px solid var(--border); border-radius: var(--radius-sm);
    background: var(--surface-alt); color: var(--text); font-size: 12px; cursor: pointer;
  }
  .day-toggle.active { background: var(--accent); color: var(--accent-contrast); }
  .hint { font-size: 11px; color: var(--text-faint); }
  .hint-error { font-size: 11px; color: var(--danger); }
</style>
```

- [ ] **Step 2: Typecheck**

Run: `cd /projects/myhome/packages/editor && npx svelte-check --tsconfig ./tsconfig.json 2>&1 | tail -30`
Expected: no new type errors from `ScheduleEditor.svelte` (it isn't imported anywhere yet, but it must still typecheck standalone).

- [ ] **Step 3: Commit**

```bash
cd /projects/myhome
git add packages/editor/src/lib/components/ScheduleEditor.svelte
git commit -m "feat(chores): add ScheduleEditor component with all recurrence categories"
```

---

### Task 9: Frontend — wire `ScheduleEditor` + quick-add into `NewChoreModal.svelte`

**Files:**
- Modify: `packages/editor/src/lib/components/NewChoreModal.svelte`

**Interfaces:**
- Consumes: `ScheduleEditor` (Task 8), `parseScheduleText` (Task 7), `chores.quickAdd.*` i18n keys (Task 4).

- [ ] **Step 1: Implement**

Replace the entire `<script>` block of `packages/editor/src/lib/components/NewChoreModal.svelte` with:

```svelte
<script lang="ts">
  import { _, locale } from "svelte-i18n";
  import type { createChoreStore } from "../choreStore.svelte";
  import Modal from "./ui/Modal.svelte";
  import Button from "./ui/Button.svelte";
  import EmojiPicker from "./ui/EmojiPicker.svelte";
  import ScheduleEditor from "./ScheduleEditor.svelte";
  import { parseScheduleText } from "../scheduleParser";

  type ChoreStore = ReturnType<typeof createChoreStore>;

  interface Props {
    open: boolean;
    store: ChoreStore;
    onclose: () => void;
  }

  let { open, store, onclose }: Props = $props();

  let name = $state("");
  let emoji = $state("📋");
  let quickAddText = $state("");
  let frequencyType = $state("interval");
  let frequency = $state(30);
  let frequencyMetadata = $state<Record<string, unknown>>({ unit: "days" });
  let periodDays = $state(30);
  let scheduleValid = $state(true);
  let resetKey = $state(0);
  let nextDue = $state(new Date(Date.now() + 30 * 86400000).toISOString().slice(0, 10));
  let scheduleFromDue = $state(false);
  let saving = $state(false);
  let error = $state("");

  function handleParse(): void {
    const loc = ($locale ?? "en").startsWith("fr") ? "fr" : "en";
    const result = parseScheduleText(quickAddText, loc);
    if (!result) {
      name = quickAddText.trim();
      return;
    }
    name = result.name;
    frequencyType = result.schedule.frequencyType;
    frequency = result.schedule.frequency;
    frequencyMetadata = result.schedule.frequencyMetadata;
    resetKey += 1;
  }

  async function handleCreate(): Promise<void> {
    if (!name.trim() || !scheduleValid) return;
    saving = true;
    error = "";
    try {
      await store.createChore({
        name: name.trim(),
        emoji: emoji.trim() || "📋",
        periodDays,
        frequencyType,
        frequency,
        frequencyMetadata,
        scheduleFromDue,
        nextDueDate: new Date(nextDue).toISOString(),
        description: "",
        donetickId: null,
      });
      reset();
      onclose();
    } catch (e) {
      error = e instanceof Error ? e.message : $_('chores.newModal.failedToCreate');
    } finally {
      saving = false;
    }
  }

  function reset(): void {
    name = ""; emoji = "📋"; quickAddText = "";
    frequencyType = "interval"; frequency = 30; frequencyMetadata = { unit: "days" }; periodDays = 30;
    resetKey += 1;
    nextDue = new Date(Date.now() + 30 * 86400000).toISOString().slice(0, 10);
    scheduleFromDue = false; error = "";
  }

  function handleClose(): void {
    reset();
    onclose();
  }

  function handleFormKeydown(e: KeyboardEvent): void {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleCreate(); }
  }
</script>
```

Replace the template body (everything inside `<Modal ...> ... </Modal>`) with:

```svelte
<Modal {open} title={$_('chores.newModal.title')} onclose={handleClose} width="360px">
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <div class="chore-form" onkeydown={handleFormKeydown} role="presentation">
    <div class="field">
      <label for="chore-quickadd">{$_('chores.quickAdd.label')}</label>
      <div class="quickadd-row">
        <!-- svelte-ignore a11y_autofocus -->
        <input id="chore-quickadd" class="native-input" bind:value={quickAddText} placeholder={$_('chores.quickAdd.placeholder')} autofocus />
        <Button variant="secondary" onclick={handleParse}>{$_('chores.quickAdd.parse')}</Button>
      </div>
    </div>

    <div class="field">
      <label for="chore-name">{$_('chores.editModal.name')}</label>
      <input id="chore-name" class="native-input" bind:value={name} placeholder={$_('chores.editModal.choreName')} />
    </div>

    <div class="field">
      <label for="chore-emoji">{$_('chores.editModal.emoji')}</label>
      <EmojiPicker bind:value={emoji} />
    </div>

    {#key resetKey}
      <ScheduleEditor
        bind:frequencyType
        bind:frequency
        bind:frequencyMetadata
        bind:periodDays
        bind:valid={scheduleValid}
      />
    {/key}

    <div class="field">
      <label for="chore-due">{$_('chores.newModal.firstDue')}</label>
      <input id="chore-due" type="date" class="native-input" bind:value={nextDue} />
    </div>

    <div class="field-row">
      <input type="checkbox" id="sfd" bind:checked={scheduleFromDue} />
      <label for="sfd" class="checkbox-label" title={$_('chores.newModal.scheduleFromDueTitle')}>
        {$_('chores.editModal.scheduleFromDue')}
      </label>
    </div>

    {#if error}<div class="error">{error}</div>{/if}
  </div>

  {#snippet footer()}
    <Button variant="secondary" onclick={handleClose}>{$_('common.cancel')}</Button>
    <Button variant="primary" disabled={!name.trim() || !scheduleValid || saving} onclick={handleCreate}>
      {saving ? $_('chores.newModal.creating') : $_('settings.security.create')}
    </Button>
  {/snippet}
</Modal>
```

In the `<style>` block, add (right after the existing `.field-row` rule):

```css
  .quickadd-row { display: flex; gap: 8px; align-items: center; }
  .quickadd-row .native-input { flex: 1; }
```

Also remove the now-unused `.freq-row`/`.freq-n` rules from this file's `<style>` block if nothing else in the file references them (they move into `ScheduleEditor.svelte`'s own scoped styles from Task 8) — check with a search of the rest of the file before deleting.

- [ ] **Step 2: Typecheck**

Run: `cd /projects/myhome/packages/editor && npx svelte-check --tsconfig ./tsconfig.json 2>&1 | tail -30`
Expected: no new errors.

- [ ] **Step 3: Run the full frontend suite**

Run: `cd /projects/myhome/packages/editor && npx vitest run`
Expected: all tests PASS (this file has no dedicated test suite, but the change must not break anything that imports `choreStore.svelte.ts` or the locale files).

- [ ] **Step 4: Commit**

```bash
cd /projects/myhome
git add packages/editor/src/lib/components/NewChoreModal.svelte
git commit -m "feat(chores): wire ScheduleEditor and NL quick-add into NewChoreModal"
```

---

### Task 10: Frontend — wire `ScheduleEditor` into `ChoreEditModal.svelte`

**Files:**
- Modify: `packages/editor/src/lib/components/ChoreEditModal.svelte`

**Interfaces:**
- Consumes: `ScheduleEditor` (Task 8).

- [ ] **Step 1: Implement**

Add the import (alongside the other component imports):

```ts
  import ScheduleEditor from "./ScheduleEditor.svelte";
```

Add draft state (alongside the existing `draftPeriodDays` etc. declarations):

```ts
  let draftFrequencyType = $state("interval");
  let draftFrequency = $state(1);
  let draftFrequencyMetadata = $state<Record<string, unknown>>({});
  let draftScheduleValid = $state(true);
```

In the `$effect` that resets draft state when `chore` changes, find:
```ts
  $effect(() => {
    if (chore) {
      draftName = chore.name;
      draftEmoji = chore.emoji;
      draftPeriodDays = chore.periodDays;
      draftNextDue = chore.nextDueDate.slice(0, 10);
      draftScheduleFromDue = chore.scheduleFromDue;
      draftDescription = chore.description ?? "";
      activeTab = "info";
      error = null;
    }
  });
```
Replace with:
```ts
  $effect(() => {
    if (chore) {
      draftName = chore.name;
      draftEmoji = chore.emoji;
      draftPeriodDays = chore.periodDays;
      draftFrequencyType = chore.frequencyType;
      draftFrequency = chore.frequency;
      draftFrequencyMetadata = chore.frequencyMetadata;
      draftNextDue = chore.nextDueDate.slice(0, 10);
      draftScheduleFromDue = chore.scheduleFromDue;
      draftDescription = chore.description ?? "";
      activeTab = "info";
      error = null;
    }
  });
```

In `handleSave`, find:
```ts
      await store.updateChore(chore.id, {
        name: draftName.trim(),
        emoji: draftEmoji.trim() || "📋",
        periodDays: draftPeriodDays,
        nextDueDate: draftNextDue ? new Date(draftNextDue).toISOString() : chore.nextDueDate,
        scheduleFromDue: draftScheduleFromDue,
        description: draftDescription,
      });
```
Replace with:
```ts
      await store.updateChore(chore.id, {
        name: draftName.trim(),
        emoji: draftEmoji.trim() || "📋",
        periodDays: draftPeriodDays,
        frequencyType: draftFrequencyType,
        frequency: draftFrequency,
        frequencyMetadata: draftFrequencyMetadata,
        nextDueDate: draftNextDue ? new Date(draftNextDue).toISOString() : chore.nextDueDate,
        scheduleFromDue: draftScheduleFromDue,
        description: draftDescription,
      });
```

Also guard the top of `handleSave` — find:
```ts
    if (!chore) return;
    if (!draftName.trim()) { error = $_('chores.editModal.nameEmpty'); return; }
```
Replace with:
```ts
    if (!chore) return;
    if (!draftName.trim()) { error = $_('chores.editModal.nameEmpty'); return; }
    if (!draftScheduleValid) return;
```

In the template, find:
```svelte
        <label>{$_('chores.editModal.periodDays')}
          <input class="native-input" type="number" bind:value={draftPeriodDays} min="1" />
        </label>
```
Replace with:
```svelte
        {#key chore.id}
          <ScheduleEditor
            bind:frequencyType={draftFrequencyType}
            bind:frequency={draftFrequency}
            bind:frequencyMetadata={draftFrequencyMetadata}
            bind:periodDays={draftPeriodDays}
            bind:valid={draftScheduleValid}
          />
        {/key}
```

Finally, disable the Save button when the schedule is invalid — find:
```svelte
        <Button variant="primary" disabled={saving} onclick={handleSave}>
          {saving ? $_('settings.security.saving') : $_('common.save')}
        </Button>
```
Replace with:
```svelte
        <Button variant="primary" disabled={saving || !draftScheduleValid} onclick={handleSave}>
          {saving ? $_('settings.security.saving') : $_('common.save')}
        </Button>
```

- [ ] **Step 2: Typecheck**

Run: `cd /projects/myhome/packages/editor && npx svelte-check --tsconfig ./tsconfig.json 2>&1 | tail -30`
Expected: no new errors.

- [ ] **Step 3: Run the full frontend suite**

Run: `cd /projects/myhome/packages/editor && npx vitest run`
Expected: all tests PASS.

- [ ] **Step 4: Commit**

```bash
cd /projects/myhome
git add packages/editor/src/lib/components/ChoreEditModal.svelte
git commit -m "feat(chores): wire ScheduleEditor into ChoreEditModal"
```

---

### Task 11: Manual browser verification

**Files:** none (verification only).

- [ ] **Step 1: Start the dev environment**

Use whatever this project's existing dev-server recipe is (check `docs/superpowers/plans/` or prior session notes for the isolated-instance recipe — there is a known stray-vite-on-5173 / `PYTHONPATH` gotcha documented from the demo-home work; avoid colliding with any already-running instance). Confirm the app loads and you can log in.

- [ ] **Step 2: Verify each new recurrence category end-to-end**

For each of: Daily, Every N days/weeks/months/years, Weekly on specific day(s), Monthly on a day (with and without restricting to specific months), Yearly, Adaptive:
1. Click ＋ Add chore, pick that category in the new recurrence picker, fill in a name, save.
2. Confirm the chore appears in the list with a sensible "Schedule" column value (matches `scheduleLabel`'s wording for that type).
3. Open it via the edit modal, confirm the picker shows the same category/values you set (not reset to "Custom interval").
4. Change its category to something else, save, confirm the list updates.
5. Click "Mark done" once; confirm `nextDueDate` advances sensibly for that category, and for the Adaptive chore specifically, complete it 2-3 times a few (real) minutes apart and confirm its periodDays/label updates to reflect a computed average rather than staying at the seed value.

- [ ] **Step 3: Verify the schedule filter dropdown**

In the Chores page toolbar, filter by each of Daily/Weekly/Monthly/Yearly/Adaptive and confirm the chores you created in Step 2 show up under the right filter (this exercises the `scheduleCategory` fix from Task 6).

- [ ] **Step 4: Verify natural-language quick-add in both languages**

Switch the app language to English, open ＋ Add chore, type `Change water filter every 6 months` into the quick-add box, click Parse, confirm the name field fills with "Change water filter" and the recurrence picker switches to "Custom interval" / 6 / months. Repeat with a French phrase (`Changer le filtre à eau tous les 6 mois`) after switching the app language to French.

- [ ] **Step 5: Report results**

Note any visual or behavioral issues found. Since this codebase has no automated component tests for this UI, this manual pass is the only verification of the actual rendered behavior — do not skip it or claim the feature works without having done it.
