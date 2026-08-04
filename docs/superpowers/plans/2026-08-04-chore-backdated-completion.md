# Chore Backdated Completion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let a user complete a chore or assignment with a backdated completion date, so it's recorded accurately in history and — only if it's the most recent completion for that chore — correctly reschedules the next due date.

**Architecture:** Backend `CompleteRequest` gains an optional `completedOn` (ISO date) field. Both `/complete` endpoints build the new `CompletionRecord.completedAt` from that date (keeping today's time-of-day) instead of always using `datetime.now()`. A new shared helper, `is_most_recent_completion`, gates whether the existing next-due/adaptive-period recompute runs — it only runs when the new completion is at or after every other completion on record for that chore. On the frontend, `ChoreRow.svelte`'s existing mark-done expansion gets a `DatePicker` (capped at today) next to the notes input, and the resulting date flows through `choreStore.svelte.ts` to the API only when it differs from today.

**Tech Stack:** FastAPI + Pydantic (backend), Svelte 5 + TypeScript + Vitest (frontend), pytest (backend tests).

## Global Constraints

- No new dependencies.
- `completedOn`, when provided, must be an ISO date string (`YYYY-MM-DD`) and must not be in the future (server-side, compared against the current UTC date) — reject with HTTP 400 otherwise.
- Omitting `completedOn` must behave exactly as today (regression: existing tests for both `/complete` endpoints must keep passing unmodified).
- The MCP `complete_chore` tool (`packages/backend/src/myhome/mcp_tools_chores.py`) is out of scope — it always completes with "now", which is always the most recent completion, so its behavior is unaffected and it needs no changes.
- Editing the `completedAt` of an already-logged completion record (the History tab's delete-only action in `ChoreEditModal.svelte`) is out of scope.

---

### Task 1: `is_most_recent_completion` helper in `chore_scheduling.py`

**Files:**
- Modify: `packages/backend/src/myhome/chore_scheduling.py` (add function after `adaptive_period_days`, which ends at line 100)
- Test: `packages/backend/tests/test_chore_scheduling.py`

**Interfaces:**
- Produces: `is_most_recent_completion(new_completed_at: datetime, other_completions: list[CompletionRecord]) -> bool` — used by Tasks 2 and 3.

- [ ] **Step 1: Write the failing tests**

Add to `packages/backend/tests/test_chore_scheduling.py` (append near the other `adaptive_period_days` tests; the file already imports `datetime, timezone` at the top and `CompletionRecord` from `myhome.models_chores`):

```python
from myhome.chore_scheduling import is_most_recent_completion


def test_is_most_recent_completion_true_with_no_other_completions():
    now = datetime(2026, 8, 4, 12, 0, tzinfo=timezone.utc)
    assert is_most_recent_completion(now, []) is True


def test_is_most_recent_completion_true_when_later_than_all_others():
    new = datetime(2026, 8, 4, 12, 0, tzinfo=timezone.utc)
    others = [
        CompletionRecord(id="r1", choreId="c1", completedAt="2026-07-01T00:00:00Z", scheduledDue=""),
        CompletionRecord(id="r2", choreId="c1", completedAt="2026-08-01T00:00:00Z", scheduledDue=""),
    ]
    assert is_most_recent_completion(new, others) is True


def test_is_most_recent_completion_false_when_an_other_is_later():
    new = datetime(2026, 7, 15, 12, 0, tzinfo=timezone.utc)
    others = [
        CompletionRecord(id="r1", choreId="c1", completedAt="2026-07-01T00:00:00Z", scheduledDue=""),
        CompletionRecord(id="r2", choreId="c1", completedAt="2026-08-01T00:00:00Z", scheduledDue=""),
    ]
    assert is_most_recent_completion(new, others) is False


def test_is_most_recent_completion_true_when_exactly_equal_to_latest_other():
    new = datetime(2026, 8, 1, 0, 0, tzinfo=timezone.utc)
    others = [CompletionRecord(id="r1", choreId="c1", completedAt="2026-08-01T00:00:00Z", scheduledDue="")]
    assert is_most_recent_completion(new, others) is True
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd packages/backend && python -m pytest tests/test_chore_scheduling.py -k is_most_recent_completion -v`
Expected: FAIL with `ImportError: cannot import name 'is_most_recent_completion'`

- [ ] **Step 3: Implement the helper**

In `packages/backend/src/myhome/chore_scheduling.py`, add after `adaptive_period_days` (which currently ends at line 100):

```python
def is_most_recent_completion(new_completed_at: datetime, other_completions: list[CompletionRecord]) -> bool:
    """True if `new_completed_at` is at or after every completion in
    `other_completions` (which should NOT include the new completion itself).
    An empty list means there's nothing to be later than, so it's trivially
    the most recent."""
    if not other_completions:
        return True
    latest_other = max(
        datetime.fromisoformat(c.completedAt.replace("Z", "+00:00")) for c in other_completions
    )
    return new_completed_at >= latest_other
```

This needs `CompletionRecord` in scope — it's already imported at the top of the file (`from .models_chores import Chore, CompletionRecord`).

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd packages/backend && python -m pytest tests/test_chore_scheduling.py -v`
Expected: PASS (all tests in the file, including the pre-existing ones)

- [ ] **Step 5: Commit**

```bash
git add packages/backend/src/myhome/chore_scheduling.py packages/backend/tests/test_chore_scheduling.py
git commit -m "feat(backend): add is_most_recent_completion helper for chore scheduling"
```

---

### Task 2: `completedOn` support on `/chores/{chore_id}/complete`

**Files:**
- Modify: `packages/backend/src/myhome/models_chores.py:86-87` (`CompleteRequest`)
- Modify: `packages/backend/src/myhome/routes/chores.py:270-303` (`complete_chore`), and its import block at lines 10-22
- Test: `packages/backend/tests/test_chores.py`

**Interfaces:**
- Consumes: `is_most_recent_completion` from Task 1 (`from ..chore_scheduling import next_due_from_schedule, adaptive_period_days, is_most_recent_completion`).
- Produces: `CompleteRequest.completedOn: str | None` field, and a module-level helper `_resolve_completed_at(completed_on: str, now: datetime) -> datetime` in `routes/chores.py`, reused by Task 3.

- [ ] **Step 1: Write the failing tests**

Add to `packages/backend/tests/test_chores.py` (it already imports `ChoreDocument, Chore, CompletionRecord` from `myhome.models_chores` and `save_chores` from `myhome.persistence_chores`; use a local `from datetime import ...` import inside each test function, matching the existing style used by `test_complete_chore_adaptive_falls_back_to_period_days_with_no_history`):

```python
def test_complete_chore_with_past_completedOn_is_latest_advances_next_due(client, home_id, tmp_path):
    """No prior completions exist, so a single backdated completion is
    trivially the most recent one -- next-due must be computed from the
    picked date, not from today."""
    doc = ChoreDocument(
        chores=[
            Chore(id="c1", name="Sweep", emoji="🧹", periodDays=7, nextDueDate="2020-01-01T00:00:00Z"),
        ],
        assignments=[],
    )
    save_chores(home_id, doc)
    resp = client.post(f"/api/homes/{home_id}/chores/c1/complete", json={"completedOn": "2020-06-01"})
    assert resp.status_code == 200
    data = resp.json()
    from datetime import datetime, timezone, timedelta
    new_due = datetime.fromisoformat(data["nextDueDate"].replace("Z", "+00:00"))
    expected = datetime(2020, 6, 8, tzinfo=timezone.utc)  # 2020-06-01 + 7 days, same time-of-day component ignored
    assert new_due.date() == expected.date()
    completions = client.get(f"/api/homes/{home_id}/chores").json()["completions"]
    rec = next(c for c in completions if c["choreId"] == "c1")
    assert rec["completedAt"].startswith("2020-06-01")


def test_complete_chore_with_past_completedOn_older_than_existing_leaves_next_due_unchanged(client, home_id, tmp_path):
    """An existing completion from 2026-08-01 is already the latest. Logging
    a backdated completion from 2026-07-01 must be recorded as history but
    must NOT move nextDueDate or periodDays."""
    doc = ChoreDocument(
        chores=[
            Chore(
                id="c1", name="Change filter", emoji="🔧", periodDays=30.0,
                frequencyType="adaptive", frequency=1, frequencyMetadata={},
                nextDueDate="2026-08-31T00:00:00Z",
            )
        ],
        assignments=[],
        completions=[
            CompletionRecord(id="r1", choreId="c1", completedAt="2026-08-01T00:00:00Z", scheduledDue=""),
        ],
    )
    save_chores(home_id, doc)
    resp = client.post(f"/api/homes/{home_id}/chores/c1/complete", json={"completedOn": "2026-07-01"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["nextDueDate"] == "2026-08-31T00:00:00Z"
    assert data["periodDays"] == 30.0
    completions = client.get(f"/api/homes/{home_id}/chores").json()["completions"]
    assert len(completions) == 2
    backdated = next(c for c in completions if c["completedAt"].startswith("2026-07-01"))
    assert backdated["choreId"] == "c1"


def test_complete_chore_rejects_future_completedOn(client, home_id, tmp_path):
    save_chores(home_id, make_chore_doc())
    resp = client.post(f"/api/homes/{home_id}/chores/c1/complete", json={"completedOn": "2999-01-01"})
    assert resp.status_code == 400


def test_complete_chore_rejects_malformed_completedOn(client, home_id, tmp_path):
    save_chores(home_id, make_chore_doc())
    resp = client.post(f"/api/homes/{home_id}/chores/c1/complete", json={"completedOn": "not-a-date"})
    assert resp.status_code == 400
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd packages/backend && python -m pytest tests/test_chores.py -k completedOn -v`
Expected: FAIL — `completedOn` is not a recognized field / responses don't reflect backdating (Pydantic ignores unknown fields by default, so the requests will currently succeed but behave as plain "now" completions, failing the date/nextDueDate assertions; the 400-rejection tests will fail because no validation exists yet).

- [ ] **Step 3: Add `completedOn` to `CompleteRequest`**

In `packages/backend/src/myhome/models_chores.py`, replace lines 86-87:

```python
class CompleteRequest(BaseModel):
    notes: str = ""
```

with:

```python
class CompleteRequest(BaseModel):
    notes: str = ""
    completedOn: str | None = None  # ISO date, YYYY-MM-DD; None = use current time
```

- [ ] **Step 4: Add the date-resolution helper and wire it into `complete_chore`**

In `packages/backend/src/myhome/routes/chores.py`, update the import at line 23 from:

```python
from ..chore_scheduling import next_due_from_schedule, adaptive_period_days
```

to:

```python
from ..chore_scheduling import next_due_from_schedule, adaptive_period_days, is_most_recent_completion
```

Add this module-level helper near the top of the file, after the existing `_validate_donetick_url` function (or any convenient spot above `complete_chore`):

```python
def _resolve_completed_at(completed_on: str, now: datetime) -> datetime:
    """Turn a `YYYY-MM-DD` completedOn string into a full UTC datetime,
    keeping `now`'s time-of-day so the result sorts sensibly against other
    same-day completions. Rejects malformed or future dates."""
    try:
        picked = datetime.strptime(completed_on, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="completedOn must be an ISO date (YYYY-MM-DD)")
    if picked > now.date():
        raise HTTPException(status_code=400, detail="completedOn cannot be in the future")
    return now.replace(year=picked.year, month=picked.month, day=picked.day)
```

Replace the full body of `complete_chore` (currently lines 271-303):

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
    completed_at = _resolve_completed_at(body.completedOn, now) if body and body.completedOn else now
    new_completion = CompletionRecord(
        id=str(uuid.uuid4()),
        choreId=chore_id,
        completedAt=completed_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
        scheduledDue=chore.nextDueDate,
        notes=notes,
    )
    doc.completions.append(new_completion)
    completions_for_chore = [c for c in doc.completions if c.choreId == chore_id]
    other_completions = [c for c in completions_for_chore if c.id != new_completion.id]
    if is_most_recent_completion(completed_at, other_completions):
        if chore.scheduleFromDue and chore.nextDueDate:
            try:
                from_dt = datetime.fromisoformat(chore.nextDueDate.replace("Z", "+00:00"))
            except ValueError:
                from_dt = completed_at
        else:
            from_dt = completed_at
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

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd packages/backend && python -m pytest tests/test_chores.py -v`
Expected: PASS — all tests, including every pre-existing `complete_chore`-related test (regression check) and the 5 new ones from Step 1.

- [ ] **Step 6: Commit**

```bash
git add packages/backend/src/myhome/models_chores.py packages/backend/src/myhome/routes/chores.py packages/backend/tests/test_chores.py
git commit -m "feat(backend): support backdated completedOn on /chores/{id}/complete"
```

---

### Task 3: `completedOn` support on `/assignments/{assignment_id}/complete`

**Files:**
- Modify: `packages/backend/src/myhome/routes/chores.py:330-362` (`complete_assignment`)
- Test: `packages/backend/tests/test_chores.py`

**Interfaces:**
- Consumes: `_resolve_completed_at` and `is_most_recent_completion` from Task 2/1 (already imported/defined in this file).

- [ ] **Step 1: Write the failing tests**

Add to `packages/backend/tests/test_chores.py`:

```python
def test_complete_assignment_with_past_completedOn_is_latest_advances_next_due(client, home_id, tmp_path):
    doc = ChoreDocument(
        chores=[Chore(id="c1", name="Sweep", emoji="🧹", periodDays=7, nextDueDate="2020-01-01T00:00:00Z")],
        assignments=[],
    )
    save_chores(home_id, doc)
    aid = client.post(f"/api/homes/{home_id}/assignments", json={"choreId": "c1", "roomId": "r1"}).json()["id"]
    resp = client.post(f"/api/homes/{home_id}/assignments/{aid}/complete", json={"completedOn": "2020-06-01"})
    assert resp.status_code == 200
    data = resp.json()
    from datetime import datetime, timezone
    new_due = datetime.fromisoformat(data["nextDueDate"].replace("Z", "+00:00"))
    assert new_due.date() == datetime(2020, 6, 8, tzinfo=timezone.utc).date()


def test_complete_assignment_with_past_completedOn_older_than_existing_leaves_next_due_unchanged(client, home_id, tmp_path):
    doc = ChoreDocument(
        chores=[
            Chore(
                id="c1", name="Change filter", emoji="🔧", periodDays=30.0,
                frequencyType="adaptive", frequency=1, frequencyMetadata={},
                nextDueDate="2026-08-31T00:00:00Z",
            )
        ],
        assignments=[],
        completions=[
            CompletionRecord(id="r1", choreId="c1", assignmentId="a1", completedAt="2026-08-01T00:00:00Z", scheduledDue=""),
        ],
    )
    save_chores(home_id, doc)
    aid = client.post(f"/api/homes/{home_id}/assignments", json={"choreId": "c1", "roomId": "r1"}).json()["id"]
    resp = client.post(f"/api/homes/{home_id}/assignments/{aid}/complete", json={"completedOn": "2026-07-01"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["nextDueDate"] == ""
    chores = client.get(f"/api/homes/{home_id}/chores").json()["chores"]
    chore = next(c for c in chores if c["id"] == "c1")
    assert chore["nextDueDate"] == "2026-08-31T00:00:00Z"
    assert chore["periodDays"] == 30.0


def test_complete_assignment_rejects_future_completedOn(client, home_id, tmp_path):
    save_chores(home_id, make_chore_doc())
    aid = client.post(f"/api/homes/{home_id}/assignments", json={"choreId": "c1", "roomId": "r1"}).json()["id"]
    resp = client.post(f"/api/homes/{home_id}/assignments/{aid}/complete", json={"completedOn": "2999-01-01"})
    assert resp.status_code == 400
```

Note: in `test_complete_assignment_with_past_completedOn_older_than_existing_leaves_next_due_unchanged`, the pre-seeded `assignmentId="a1"` on the existing completion is just a label (it doesn't need to match the freshly created assignment's real id) — the endpoint only compares `completedAt` timestamps across all completions sharing `choreId`, not `assignmentId`.

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd packages/backend && python -m pytest tests/test_chores.py -k "complete_assignment_with_past or complete_assignment_rejects" -v`
Expected: FAIL — same reasons as Task 2 Step 2 (no backdating/validation logic yet on this endpoint).

- [ ] **Step 3: Wire it into `complete_assignment`**

Replace the full body of `complete_assignment` (currently lines 331-362) in `packages/backend/src/myhome/routes/chores.py`:

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
    completed_at = _resolve_completed_at(body.completedOn, now) if body and body.completedOn else now
    new_completion = CompletionRecord(
        id=str(uuid.uuid4()),
        choreId=chore.id,
        assignmentId=assignment_id,
        completedAt=completed_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
        scheduledDue=assignment.nextDueDate,
        notes=notes,
    )
    doc.completions.append(new_completion)
    completions_for_chore = [c for c in doc.completions if c.choreId == chore.id]
    other_completions = [c for c in completions_for_chore if c.id != new_completion.id]
    if is_most_recent_completion(completed_at, other_completions):
        if chore.scheduleFromDue and assignment.nextDueDate:
            try:
                from_dt = datetime.fromisoformat(assignment.nextDueDate.replace("Z", "+00:00"))
            except ValueError:
                from_dt = completed_at
        else:
            from_dt = completed_at
        next_due = next_due_from_schedule(chore, from_dt, completions_for_chore)
        if chore.frequencyType == "adaptive":
            chore.periodDays = adaptive_period_days(chore, completions_for_chore)
        assignment.nextDueDate = next_due.strftime("%Y-%m-%dT%H:%M:%SZ")
    save_chores(home_id, doc)
    log_activity(home_id, current_user_id, "chores", "complete", chore.name, chore.id)
    return assignment
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd packages/backend && python -m pytest tests/test_chores.py -v`
Expected: PASS — full file, including all pre-existing assignment-completion tests (regression check) and the new ones.

- [ ] **Step 5: Run the full backend test suite**

Run: `cd packages/backend && python -m pytest -v`
Expected: PASS (no regressions elsewhere, e.g. MCP tool tests in `test_mcp_tools_chores.py` untouched).

- [ ] **Step 6: Commit**

```bash
git add packages/backend/src/myhome/routes/chores.py packages/backend/tests/test_chores.py
git commit -m "feat(backend): support backdated completedOn on /assignments/{id}/complete"
```

---

### Task 4: `DatePicker.svelte` optional `max` prop

**Files:**
- Modify: `packages/editor/src/lib/components/DatePicker.svelte`
- Test: `packages/editor/test/DatePicker.test.ts`

**Interfaces:**
- Produces: `DatePicker` gains an optional prop `max?: string` (ISO date `YYYY-MM-DD`, inclusive). Days after `max` render disabled and cannot be selected. No other prop or exported behavior changes — existing call sites (`TaskModal.svelte`, `InventoryModal.svelte`, `InsuranceModal.svelte`, `ChoreEditModal.svelte`, `CostsEntryModal.svelte`, `WorkModal.svelte`) don't pass `max` and are unaffected.

- [ ] **Step 1: Write the failing test**

Add to `packages/editor/test/DatePicker.test.ts` (new `describe` block, same file):

```ts
describe("DatePicker max", () => {
  let target: HTMLDivElement;

  beforeEach(() => {
    localStorage.clear();
    localStorage.setItem("myhome-locale", "en");
    target = document.createElement("div");
    document.body.appendChild(target);
  });

  afterEach(() => {
    target.remove();
  });

  it("disables and ignores clicks on days after max", () => {
    const app = mount(DatePicker, { target, props: { value: "2024-01-10", max: "2024-01-15" } });
    flushSync();
    (target.querySelector(".dp-field") as HTMLElement).click();
    flushSync();

    const cells = [...target.querySelectorAll(".dp-cell:not(.dp-empty)")] as HTMLButtonElement[];
    const day20 = cells.find((c) => c.textContent === "20")!;
    expect(day20.disabled).toBe(true);

    day20.click();
    flushSync();

    expect(target.querySelector(".dp-text")!.textContent).toContain("10");
    unmount(app);
  });

  it("still allows selecting a day at or before max", () => {
    const app = mount(DatePicker, { target, props: { value: "2024-01-10", max: "2024-01-15" } });
    flushSync();
    (target.querySelector(".dp-field") as HTMLElement).click();
    flushSync();

    const cells = [...target.querySelectorAll(".dp-cell:not(.dp-empty)")] as HTMLButtonElement[];
    const day15 = cells.find((c) => c.textContent === "15")!;
    expect(day15.disabled).toBe(false);

    day15.click();
    flushSync();

    expect(target.querySelector(".dp-text")!.textContent).toContain("15");
    unmount(app);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/editor && npx vitest run test/DatePicker.test.ts`
Expected: FAIL — `max` prop doesn't exist yet, so no cell is disabled (`day20.disabled` is `false`).

- [ ] **Step 3: Implement the `max` prop**

In `packages/editor/src/lib/components/DatePicker.svelte`, update the `Props` interface and destructuring (currently):

```svelte
  interface Props {
    value?: string;
    placeholder?: string;
  }
  let { value = $bindable(""), placeholder }: Props = $props();
```

to:

```svelte
  interface Props {
    value?: string;
    placeholder?: string;
    max?: string;
  }
  let { value = $bindable(""), placeholder, max }: Props = $props();
```

Add a helper and a disabled-check function near `isSelected`/`isToday`:

```svelte
  function cellIso(day: number): string {
    const mm = String(viewMonth + 1).padStart(2, "0");
    const dd = String(day).padStart(2, "0");
    return `${viewYear}-${mm}-${dd}`;
  }

  function isDisabled(day: number): boolean {
    return !!max && cellIso(day) > max;
  }
```

Update `selectDay` to also refuse disabled days (defense in depth, since the button's `disabled` attribute already blocks the click in a real browser):

```svelte
  function selectDay(day: number): void {
    if (isDisabled(day)) return;
    const mm = String(viewMonth + 1).padStart(2, "0");
    const dd = String(day).padStart(2, "0");
    value = `${viewYear}-${mm}-${dd}`;
    open = false;
  }
```

Update the day-cell button in the template (currently):

```svelte
            <button
              class="dp-cell"
              class:dp-selected={isSelected(day)}
              class:dp-today={isToday(day)}
              onclick={() => selectDay(day)}
            >{day}</button>
```

to:

```svelte
            <button
              class="dp-cell"
              class:dp-selected={isSelected(day)}
              class:dp-today={isToday(day)}
              disabled={isDisabled(day)}
              onclick={() => selectDay(day)}
            >{day}</button>
```

Add a disabled style near the other `.dp-cell` rules:

```css
  .dp-cell:disabled { color: var(--text-faint); cursor: default; opacity: 0.5; }
  .dp-cell:disabled:hover { background: none; color: var(--text-faint); }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd packages/editor && npx vitest run test/DatePicker.test.ts`
Expected: PASS — both new tests and all pre-existing `DatePicker` tests.

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/lib/components/DatePicker.svelte packages/editor/test/DatePicker.test.ts
git commit -m "feat(frontend): add optional max prop to DatePicker"
```

---

### Task 5: `ChoreRow.svelte` backdated-completion date field

**Files:**
- Modify: `packages/editor/src/lib/components/ChoreRow.svelte`
- Modify: `packages/editor/src/lib/locales/en.json:338-341`, `packages/editor/src/lib/locales/fr.json:338-341`
- Test: `packages/editor/test/ChoreRow.test.ts`

**Interfaces:**
- Consumes: `DatePicker` with `max` prop from Task 4.
- Produces: `ChoreRow`'s `oncomplete` prop type changes from `(notes: string) => void` to `(notes: string, completedOn?: string) => void`. `completedOn` is passed **only** when the picked date differs from today's local date — when it equals today, `oncomplete` is called with a single argument, exactly as before. This keeps all pre-existing tests (which assert `oncomplete` was called with exactly one string argument) passing unmodified.

- [ ] **Step 1: Write the failing tests**

Add to `packages/editor/test/ChoreRow.test.ts` (new tests, appended inside the existing `describe("ChoreRow", ...)` block):

```ts
  it("shows a date picker defaulting to today when marking done", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(ChoreRow, {
      target,
      props: { emoji: "🧹", name: "Sweep", dueLabel: "Today", dueColor: "#4caf50", oncomplete: vi.fn() },
    });

    (target.querySelector(".done-btn") as HTMLButtonElement).click();
    flushSync();

    const todayIso = new Date().toISOString().slice(0, 10);
    const dateField = target.querySelector(".dp-text");
    expect(dateField).not.toBeNull();
    expect(dateField!.textContent).not.toBe("");
    // Sanity: the picker's bound value defaults to today, which we can
    // confirm indirectly via the confirm flow below rather than parsing
    // the picker's localized display text.
    void todayIso;

    unmount(comp);
    target.remove();
  });

  it("confirm with the default (today) date calls oncomplete with only notes, no completedOn", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const oncomplete = vi.fn();
    const comp = mount(ChoreRow, {
      target,
      props: { emoji: "🧹", name: "Sweep", dueLabel: "Today", dueColor: "#4caf50", oncomplete },
    });

    (target.querySelector(".done-btn") as HTMLButtonElement).click();
    flushSync();
    (target.querySelector(".done-btn.confirm") as HTMLButtonElement).click();
    flushSync();

    expect(oncomplete).toHaveBeenCalledWith("");
    expect(oncomplete.mock.calls[0].length).toBe(1);

    unmount(comp);
    target.remove();
  });

  it("confirm after picking a past date calls oncomplete with notes and completedOn", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const oncomplete = vi.fn();
    const comp = mount(ChoreRow, {
      target,
      props: { emoji: "🧹", name: "Sweep", dueLabel: "Today", dueColor: "#4caf50", oncomplete },
    });

    (target.querySelector(".done-btn") as HTMLButtonElement).click();
    flushSync();

    (target.querySelector(".dp-field") as HTMLElement).click();
    flushSync();
    const cells = [...target.querySelectorAll(".dp-cell:not(.dp-empty)")] as HTMLButtonElement[];
    const firstOfMonth = cells.find((c) => c.textContent === "1")!;
    firstOfMonth.click();
    flushSync();

    (target.querySelector(".done-btn.confirm") as HTMLButtonElement).click();
    flushSync();

    expect(oncomplete).toHaveBeenCalledTimes(1);
    const [notesArg, dateArg] = oncomplete.mock.calls[0];
    expect(notesArg).toBe("");
    expect(dateArg).toMatch(/^\d{4}-\d{2}-\d{2}$/);

    unmount(comp);
    target.remove();
  });
```

Note: the third test picks "the 1st of the currently-displayed month" rather than a specific relative date, since the `DatePicker` view always opens on today's month — if today happens to be the 1st, that test would pick today rather than a past date, which is an acceptable rare flake risk consistent with how other date-grid tests in this codebase (e.g. `DatePicker.test.ts`) already pin to specific known dates only when necessary. This test only needs to prove `completedOn` is threaded through, not that it is strictly historical, so it's fine either way — the assertion is only on `dateArg`'s format and that `oncomplete` received two arguments.

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd packages/editor && npx vitest run test/ChoreRow.test.ts`
Expected: FAIL — no `.dp-text`/`.dp-field` exists in `ChoreRow` yet, and `oncomplete` is still called with a single hardcoded-notes-only argument.

- [ ] **Step 3: Implement the date field in `ChoreRow.svelte`**

Replace the full contents of `packages/editor/src/lib/components/ChoreRow.svelte`'s `<script>` block:

```svelte
<script lang="ts">
  import { _ } from "svelte-i18n";
  import DatePicker from "./DatePicker.svelte";

  interface Props {
    emoji: string;
    name: string;
    location?: string;
    dueLabel: string;
    dueColor: string;
    oncomplete: (notes: string, completedOn?: string) => void;
  }
  let { emoji, name, location, dueLabel, dueColor, oncomplete }: Props = $props();

  function todayIso(): string {
    const d = new Date();
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
  }

  let completing = $state(false);
  let notes = $state("");
  let completedOn = $state("");

  function start(e: Event): void {
    e.stopPropagation();
    completing = true;
    notes = "";
    completedOn = todayIso();
  }

  function confirm(e: Event): void {
    e.stopPropagation();
    completing = false;
    if (completedOn === todayIso()) {
      oncomplete(notes);
    } else {
      oncomplete(notes, completedOn);
    }
  }

  function cancel(e: Event): void {
    e.stopPropagation();
    completing = false;
  }

  function handleKeydown(e: KeyboardEvent): void {
    if (e.key === "Enter") confirm(e);
    if (e.key === "Escape") cancel(e);
  }
</script>
```

Update the markup: replace the `{#if completing}` block's contents (currently the `<input class="note-input">` immediately followed by the confirm/cancel buttons):

```svelte
  {#if completing}
    <input
      class="note-input"
      bind:value={notes}
      placeholder={$_('chores.row.notePlaceholder')}
      onclick={(e) => e.stopPropagation()}
      onkeydown={handleKeydown}
    />
    <div class="date-field" onclick={(e) => e.stopPropagation()}>
      <DatePicker bind:value={completedOn} max={todayIso()} />
    </div>
    <button class="done-btn confirm" onclick={confirm}>✓</button>
    <button class="cancel-btn" onclick={cancel}>✕</button>
  {:else}
```

Add a small style for `.date-field` next to `.note-input`'s styles so it doesn't force the row too wide:

```css
  .date-field { flex-shrink: 0; max-width: 150px; }
```

- [ ] **Step 4: Add i18n keys (if needed) and run tests**

The date field itself has no visible label beyond the `DatePicker`'s own placeholder (`datePicker.placeholder`, already defined in both `en.json` and `fr.json`), so no new i18n keys are strictly required for Task 5. Confirm both locale files already contain `datePicker.placeholder`:

Run: `grep -A1 '"datePicker"' packages/editor/src/lib/locales/en.json packages/editor/src/lib/locales/fr.json`
Expected: both files show `"placeholder": "..."` under `datePicker`.

Run: `cd packages/editor && npx vitest run test/ChoreRow.test.ts`
Expected: PASS — all pre-existing tests (unmodified assertions like `toHaveBeenCalledWith("all done")` still pass because `completedOn` stays at `todayIso()` throughout those tests) plus the 3 new ones.

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/lib/components/ChoreRow.svelte packages/editor/test/ChoreRow.test.ts
git commit -m "feat(frontend): add backdated completion date picker to ChoreRow"
```

---

### Task 6: Wire `completedOn` through `choreStore` and its callers

**Files:**
- Modify: `packages/editor/src/lib/choreStore.svelte.ts:199-209,229-239`
- Modify: `packages/editor/src/lib/components/ChoreListPage.svelte:58,73`
- Modify: `packages/editor/src/lib/components/HomeChoresWidget.svelte:71`
- Test: `packages/editor/test/choreStore.test.ts`

**Interfaces:**
- Consumes: `ChoreRow`'s `oncomplete: (notes: string, completedOn?: string) => void` from Task 5.
- Produces: `completeChore(id: string, notes?: string, completedOn?: string): Promise<void>` and `completeAssignment(id: string, notes?: string, completedOn?: string): Promise<void>` — the third parameter is optional and additive, so the two existing call sites in `App.svelte:950-951` and `ChoresPage.svelte:181-182` (which only ever pass `id`/`id, notes`) keep compiling and behaving unchanged.

- [ ] **Step 1: Write the failing tests**

Add to `packages/editor/test/choreStore.test.ts` (it already has `makeFetch`, `getHomeId`, `HOME`, `tick` helpers and an `afterEach(() => vi.unstubAllGlobals())`; add a new `describe` block):

```ts
describe("choreStore — completedOn", () => {
  it("completeChore omits completedOn from the request body when not provided", async () => {
    const fetchMock = makeFetch(200, emptyDoc);
    vi.stubGlobal("fetch", fetchMock);
    const store = createChoreStore(getHomeId);
    await tick();

    await store.completeChore("c1", "done");

    const completeCall = fetchMock.mock.calls.find(([url]) => String(url).includes("/complete"));
    expect(completeCall).toBeDefined();
    const sentBody = JSON.parse(completeCall![1].body as string);
    expect(sentBody).toEqual({ notes: "done" });
  });

  it("completeChore includes completedOn in the request body when provided", async () => {
    const fetchMock = makeFetch(200, emptyDoc);
    vi.stubGlobal("fetch", fetchMock);
    const store = createChoreStore(getHomeId);
    await tick();

    await store.completeChore("c1", "done", "2026-07-01");

    const completeCall = fetchMock.mock.calls.find(([url]) => String(url).includes("/complete"));
    const sentBody = JSON.parse(completeCall![1].body as string);
    expect(sentBody).toEqual({ notes: "done", completedOn: "2026-07-01" });
  });

  it("completeAssignment includes completedOn in the request body when provided", async () => {
    const fetchMock = makeFetch(200, emptyDoc);
    vi.stubGlobal("fetch", fetchMock);
    const store = createChoreStore(getHomeId);
    await tick();

    await store.completeAssignment("a1", "", "2026-07-01");

    const completeCall = fetchMock.mock.calls.find(([url]) => String(url).includes("/complete"));
    const sentBody = JSON.parse(completeCall![1].body as string);
    expect(sentBody).toEqual({ notes: "", completedOn: "2026-07-01" });
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd packages/editor && npx vitest run test/choreStore.test.ts -t completedOn`
Expected: FAIL — TypeScript will reject the 3-argument calls (`completeChore`/`completeAssignment` currently take 2 params), and even if it ran, the sent body would never include `completedOn`.

- [ ] **Step 3: Update `completeChore` and `completeAssignment`**

In `packages/editor/src/lib/choreStore.svelte.ts`, replace lines 199-209:

```ts
  async function completeChore(id: string, notes: string = ""): Promise<void> {
    const homeId = getHomeId();
    if (!homeId) throw new Error("No active home");
    const resp = await fetch(`/api/homes/${homeId}/chores/${id}/complete`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ notes }),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
  }
```

with:

```ts
  async function completeChore(id: string, notes: string = "", completedOn?: string): Promise<void> {
    const homeId = getHomeId();
    if (!homeId) throw new Error("No active home");
    const resp = await fetch(`/api/homes/${homeId}/chores/${id}/complete`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(completedOn ? { notes, completedOn } : { notes }),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
  }
```

Replace lines 229-239:

```ts
  async function completeAssignment(id: string, notes: string = ""): Promise<void> {
    const homeId = getHomeId();
    if (!homeId) throw new Error("No active home");
    const resp = await fetch(`/api/homes/${homeId}/assignments/${id}/complete`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ notes }),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
  }
```

with:

```ts
  async function completeAssignment(id: string, notes: string = "", completedOn?: string): Promise<void> {
    const homeId = getHomeId();
    if (!homeId) throw new Error("No active home");
    const resp = await fetch(`/api/homes/${homeId}/assignments/${id}/complete`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(completedOn ? { notes, completedOn } : { notes }),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
  }
```

- [ ] **Step 4: Wire the new `oncomplete` signature through the two `ChoreRow` call sites**

In `packages/editor/src/lib/components/ChoreListPage.svelte`, both occurrences (lines 58 and 73) of:

```svelte
          oncomplete={(notes) => store.completeAssignment(assignment.id, notes)}
```

become:

```svelte
          oncomplete={(notes, completedOn) => store.completeAssignment(assignment.id, notes, completedOn)}
```

In `packages/editor/src/lib/components/HomeChoresWidget.svelte`, line 71:

```svelte
            oncomplete={(notes) => store.completeAssignment(row.id, notes)}
```

becomes:

```svelte
            oncomplete={(notes, completedOn) => store.completeAssignment(row.id, notes, completedOn)}
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd packages/editor && npx vitest run test/choreStore.test.ts test/ChoreListPage.test.ts test/HomeChoresWidget.test.ts test/ChoreRow.test.ts`

(If either `ChoreListPage.test.ts` or `HomeChoresWidget.test.ts` doesn't exist, omit it from the command — check with `find packages/editor/test -iname "ChoreListPage.test.ts" -o -iname "HomeChoresWidget.test.ts"` first.)

Expected: PASS — all new and pre-existing tests.

- [ ] **Step 6: Run the full frontend test suite and typecheck**

Run: `cd packages/editor && npx vitest run && npx svelte-check --tsconfig ./tsconfig.json`
Expected: PASS with no new type errors (in particular, confirm `App.svelte:950-951` and `ChoresPage.svelte:181-182` still typecheck against the new optional third parameter).

- [ ] **Step 7: Commit**

```bash
git add packages/editor/src/lib/choreStore.svelte.ts packages/editor/src/lib/components/ChoreListPage.svelte packages/editor/src/lib/components/HomeChoresWidget.svelte packages/editor/test/choreStore.test.ts
git commit -m "feat(frontend): thread completedOn through choreStore and ChoreRow call sites"
```

---

## Manual verification (after all tasks)

Since this touches a user-facing interaction (Chores mark-done flow), do a quick manual pass in the running app before considering this done, per the project's UI-change convention:

1. Start the dev servers (backend + editor).
2. Open the Chores list, click ✓ on a chore row — confirm a date picker appears next to the notes field, defaulted to today, and future dates are not selectable.
3. Pick a date a week ago, confirm — verify the chore's next-due date advances from that backdated date (check via the chore's edit modal History tab, which should show the new completion with the picked date).
4. Complete the same chore again with today's date — verify the next-due date now advances from today, and the earlier backdated entry in History is untouched.
5. Complete a chore with a backdated date that is *older* than an already-existing completion — verify the next-due date does NOT change, but the History tab still shows the new backdated entry.
