# Chores Module Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix four issues in the Chores module: history mislabels room-wide completions as "whole house," the Planning column mislabels month-restricted schedules as "Monthly," the KPI/chart summary isn't clickable, and the floor-plan pin popup can't set a per-assignment label.

**Architecture:** Four independent, separately-committable fixes touching the existing Chores backend (`packages/backend/src/myhome/routes/chores.py`) and frontend (`packages/editor/src/lib/components/ChoresPage.svelte`, `BadgePopup.svelte`, `HorizontalBarChart.svelte`, `ui/StatTile.svelte`, `choreStore.svelte.ts`). No new files, no new endpoints, no new dependencies.

**Tech Stack:** FastAPI + Pydantic (backend), Svelte 5 + TypeScript + Vitest (frontend), svelte-i18n for en/fr strings.

## Global Constraints

- Every new user-facing string needs both an `en.json` and `fr.json` entry in `packages/editor/src/lib/locales/`.
- Svelte 5 runes only (`$state`, `$derived`, `$props`) — no legacy `export let`.
- Component tests: `mount()`/`unmount()`/`flushSync()` from `"svelte"`, target appended to `document.body` before mounting and removed after. `blur` events are not part of Svelte 5's delegated event set and work with a plain `new Event("blur")` (no `bubbles: true` needed) — this is already the pattern in `ChoreEditModal.test.ts`'s label-blur test. `click` events dispatched via `.click()` on the element work directly.
- No new dependencies, no new API endpoints — reuse `PUT /api/homes/{home_id}/assignments/{assignment_id}` (already supports a `label` patch) and the existing `POST /api/homes/{home_id}/chores/{chore_id}/complete`.

---

### Task 1: Backend — one completion record per assignment on chore-level complete

Fixes the root cause of the "toute la maison" history bug: `POST /chores/{chore_id}/complete` (used by "Mark all done" in the list and "✓ All done" in the floor-plan popup) currently writes a single `CompletionRecord` with `assignmentId=None`, so history always falls back to the whole-house label. This task makes it write one record per assignment, correctly tagged.

**Files:**
- Modify: `packages/backend/src/myhome/routes/chores.py:283-323` (the `complete_chore` function)
- Test: `packages/backend/tests/test_chores.py`

**Interfaces:**
- Consumes: `CompletionRecord(id, choreId, assignmentId, completedAt, scheduledDue, notes)` (existing model, `models_chores.py:25-31`); `doc.assignments: list[Assignment]` where `Assignment.choreId`/`Assignment.id` already exist.
- Produces: no change to `complete_chore`'s signature, request/response shape, or the `Chore` it returns — only how many `CompletionRecord`s land in `doc.completions` and what `assignmentId` each carries. Later tasks don't depend on this one.

- [ ] **Step 1: Write the failing tests**

Add these two tests right after `test_complete_chore_advances_all_assignments` (around line 378) in `packages/backend/tests/test_chores.py`:

```python
def test_complete_chore_creates_one_completion_per_assignment(client, home_id, tmp_path):
    save_chores(home_id, make_chore_doc())
    aid = client.post(f"/api/homes/{home_id}/assignments", json={"choreId": "c1", "roomId": "r1"}).json()["id"]
    resp = client.post(f"/api/homes/{home_id}/chores/c1/complete")
    assert resp.status_code == 200
    doc = client.get(f"/api/homes/{home_id}/chores").json()
    assert len(doc["completions"]) == 1
    assert doc["completions"][0]["assignmentId"] == aid


def test_complete_chore_with_multiple_assignments_creates_one_record_per_room(client, home_id, tmp_path):
    save_chores(home_id, make_chore_doc())
    aid1 = client.post(f"/api/homes/{home_id}/assignments", json={"choreId": "c1", "roomId": "r1"}).json()["id"]
    aid2 = client.post(f"/api/homes/{home_id}/assignments", json={"choreId": "c1", "roomId": "r2"}).json()["id"]
    resp = client.post(f"/api/homes/{home_id}/chores/c1/complete", json={"notes": "done"})
    assert resp.status_code == 200
    doc = client.get(f"/api/homes/{home_id}/chores").json()
    assert len(doc["completions"]) == 2
    assignment_ids = {r["assignmentId"] for r in doc["completions"]}
    assert assignment_ids == {aid1, aid2}
    assert all(r["notes"] == "done" for r in doc["completions"])
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd packages/backend && python -m pytest tests/test_chores.py -k "creates_one_completion_per_assignment or creates_one_record_per_room" -v`
Expected: both FAIL — the first because `assignmentId` comes back `None` instead of `aid`; the second because only 1 completion is created instead of 2.

- [ ] **Step 3: Implement the fix**

Replace `complete_chore` in `packages/backend/src/myhome/routes/chores.py` (lines 283-323) with:

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
    completed_at_str = completed_at.strftime("%Y-%m-%dT%H:%M:%SZ")

    # One completion record per assignment, tagged with that assignment's id,
    # so history resolves the real room(s) instead of always falling back to
    # whole-house. A chore with no assignments yet still gets exactly one
    # untagged record -- there's nothing to attach it to.
    chore_assignments = [a for a in doc.assignments if a.choreId == chore_id]
    target_assignment_ids: list[str | None] = [a.id for a in chore_assignments] if chore_assignments else [None]
    new_completions = [
        CompletionRecord(
            id=str(uuid.uuid4()),
            choreId=chore_id,
            assignmentId=aid,
            completedAt=completed_at_str,
            scheduledDue=chore.nextDueDate,
            notes=notes,
        )
        for aid in target_assignment_ids
    ]
    doc.completions.extend(new_completions)

    completions_for_chore = [c for c in doc.completions if c.choreId == chore_id]
    new_ids = {c.id for c in new_completions}
    other_completions = [c for c in completions_for_chore if c.id not in new_ids]
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

- [ ] **Step 4: Run the full chores test file to verify everything passes**

Run: `cd packages/backend && python -m pytest tests/test_chores.py -v`
Expected: PASS — all existing tests (including `test_complete_chore_records_history`, which uses a chore with zero assignments and still expects exactly one `assignmentId: None` record, and `test_multiple_completions_accumulate`, two separate zero-assignment calls) continue to pass unchanged, plus the two new tests from Step 1.

- [ ] **Step 5: Commit**

```bash
git add packages/backend/src/myhome/routes/chores.py packages/backend/tests/test_chores.py
git commit -m "fix(chores): record one completion per assignment on chore-level complete"
```

---

### Task 2: Frontend — fix "Monthly" mislabel for month-restricted day-of-month schedules

`scheduleLabel()` always renders `day_of_the_month` schedules as "Monthly on day {n}," ignoring `frequencyMetadata.months` — the restriction `ScheduleEditor.svelte` already lets users set (e.g. "day 20, August only"). This task makes the label reflect the restriction instead of claiming it's monthly.

**Files:**
- Modify: `packages/editor/src/lib/choreStore.svelte.ts:1-3,29-33` (imports + the `day_of_the_month` branch of `scheduleLabel`)
- Modify: `packages/editor/src/lib/locales/en.json:393`, `packages/editor/src/lib/locales/fr.json:393` (add one new key each)
- Test: `packages/editor/test/choreStore.test.ts`

**Interfaces:**
- Consumes: `toMonthNum(v: unknown): number | null` (existing, `packages/editor/src/lib/scheduleNames.ts:32-34`); `chore.frequencyMetadata.months: unknown[] | undefined` (already read/written by `ScheduleEditor.svelte`).
- Produces: no change to `scheduleLabel(chore: Chore): string`'s signature — same function, same callers (`ChoresPage.svelte`'s schedule column and sort, `ChoreEditModal.svelte` doesn't call it directly). No other task depends on this one.

- [ ] **Step 1: Write the failing tests**

Add these to the `describe("scheduleLabel", ...)` block in `packages/editor/test/choreStore.test.ts` (after the last existing test, before the closing `});` around line 267):

```ts
  it("shows month names instead of 'Monthly' when day_of_the_month is restricted to specific months", () => {
    const chore = makeChore({ frequencyType: "day_of_the_month", frequency: 20, frequencyMetadata: { months: [8] } });
    expect(scheduleLabel(chore)).toBe("On day 20 (Aug)");
  });

  it("joins multiple restricted months in calendar order regardless of input order", () => {
    const chore = makeChore({ frequencyType: "day_of_the_month", frequency: 15, frequencyMetadata: { months: [10, 1, 4, 7] } });
    expect(scheduleLabel(chore)).toBe("On day 15 (Jan, Apr, Jul, Oct)");
  });

  it("keeps the plain 'Monthly on day N' label when no months restriction is set", () => {
    const chore = makeChore({ frequencyType: "day_of_the_month", frequency: 20, frequencyMetadata: {} });
    expect(scheduleLabel(chore)).toBe("Monthly on day 20");
  });

  it("handles Donetick-shaped string month names in the restriction", () => {
    const chore = makeChore({ frequencyType: "day_of_the_month", frequency: 15, frequencyMetadata: { months: ["March", "June", "September", "December"] } });
    expect(scheduleLabel(chore)).toBe("On day 15 (Mar, Jun, Sep, Dec)");
  });
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd packages/editor && npx vitest run test/choreStore.test.ts -t "day_of_the_month is restricted|calendar order|no months restriction|Donetick-shaped string month"`
Expected: FAIL — all four currently return `"Monthly on day 20"` / `"Monthly on day 15"` regardless of `months`.

- [ ] **Step 3: Add the new i18n key**

In `packages/editor/src/lib/locales/en.json`, line 393, change:
```json
      "monthlyOnDay": "Monthly on day {n}",
```
to:
```json
      "monthlyOnDay": "Monthly on day {n}",
      "dayOfMonthRestricted": "On day {n} ({months})",
```

In `packages/editor/src/lib/locales/fr.json`, line 393, change:
```json
      "monthlyOnDay": "Mensuel le {n}",
```
to:
```json
      "monthlyOnDay": "Mensuel le {n}",
      "dayOfMonthRestricted": "Le {n} ({months})",
```

- [ ] **Step 4: Implement the fix in `scheduleLabel`**

In `packages/editor/src/lib/choreStore.svelte.ts`, change the import on line 1-3 from:
```ts
import { _ } from "svelte-i18n";
import { get } from "svelte/store";
import { toWeekdayNum } from "./scheduleNames";
```
to:
```ts
import { _, locale } from "svelte-i18n";
import { get } from "svelte/store";
import { toWeekdayNum, toMonthNum } from "./scheduleNames";
```

Then change line 33 from:
```ts
  if (ft === "day_of_the_month") return t("chores.schedule.monthlyOnDay", { values: { n } });
```
to:
```ts
  if (ft === "day_of_the_month") {
    const rawMonths = (meta as Record<string, unknown[]>)?.months ?? [];
    const months = rawMonths.map(toMonthNum).filter((m): m is number => m !== null);
    if (months.length > 0) {
      const loc = get(locale) ?? "en";
      const monthNames = months
        .slice()
        .sort((a, b) => a - b)
        .map((m) => new Intl.DateTimeFormat(loc, { month: "short" }).format(new Date(2000, m - 1, 1)));
      return t("chores.schedule.dayOfMonthRestricted", { values: { n, months: monthNames.join(", ") } });
    }
    return t("chores.schedule.monthlyOnDay", { values: { n } });
  }
```

- [ ] **Step 5: Run the full test file to verify everything passes**

Run: `cd packages/editor && npx vitest run test/choreStore.test.ts`
Expected: PASS — all existing `scheduleLabel` tests plus the four new ones.

- [ ] **Step 6: Commit**

```bash
git add packages/editor/src/lib/choreStore.svelte.ts packages/editor/src/lib/locales/en.json packages/editor/src/lib/locales/fr.json packages/editor/test/choreStore.test.ts
git commit -m "fix(chores): stop mislabeling month-restricted day-of-month schedules as Monthly"
```

---

### Task 3: Frontend — clickable/highlightable HorizontalBarChart segments and StatTile

Adds the click + highlight affordance to the two shared components the Chores KPI summary uses. Neither component wires this into Chores yet — that's Task 4. Both changes are purely additive (new optional props defaulting to inert), so every other consumer of these shared components (Works, Costs, Inventory, Consumables) is unaffected.

**Files:**
- Modify: `packages/editor/src/lib/components/HorizontalBarChart.svelte`
- Modify: `packages/editor/src/lib/components/ui/StatTile.svelte`
- Test: `packages/editor/test/HorizontalBarChart.test.ts`
- Test: `packages/editor/test/StatTile.test.ts`

**Interfaces:**
- Produces: `HorizontalBarChart` gains `activeId?: string | null` and `onsegmentclick?: (id: string) => void` props. `StatTile` gains `active?: boolean` and `onclick?: () => void` props. Task 4 wires both from `ChoresPage.svelte`.

- [ ] **Step 1: Write the failing tests**

Add to `packages/editor/test/HorizontalBarChart.test.ts` — first change the import on line 1 from:
```ts
import { describe, it, expect } from "vitest";
```
to:
```ts
import { describe, it, expect, vi } from "vitest";
```
Then add these tests inside the `describe("HorizontalBarChart", ...)` block, after the last existing test (before the closing `});`):

```ts
  it("calls onsegmentclick with the segment's id when clicked", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const onsegmentclick = vi.fn();
    const comp = mount(HorizontalBarChart, { target, props: { segments, onsegmentclick } });
    flushSync();
    (target.querySelectorAll(".stacked-segment")[1] as HTMLElement).click();
    expect(onsegmentclick).toHaveBeenCalledWith("low");
    unmount(comp);
    target.remove();
  });

  it("marks the segment matching activeId as active and dims the others", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(HorizontalBarChart, { target, props: { segments, activeId: "low" } });
    flushSync();
    const segs = Array.from(target.querySelectorAll(".stacked-segment"));
    expect(segs[0].classList.contains("dimmed")).toBe(true);
    expect(segs[1].classList.contains("active")).toBe(true);
    unmount(comp);
    target.remove();
  });

  it("dims no segments when activeId is null", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(HorizontalBarChart, { target, props: { segments, activeId: null } });
    flushSync();
    expect(target.querySelectorAll(".stacked-segment.dimmed")).toHaveLength(0);
    unmount(comp);
    target.remove();
  });
```

Add to `packages/editor/test/StatTile.test.ts` — first change the import on line 1 from:
```ts
import { describe, it, expect } from "vitest";
```
to:
```ts
import { describe, it, expect, vi } from "vitest";
```
Then add these tests inside the `describe("ui/StatTile", ...)` block, after the last existing test:

```ts
  it("calls onclick when clicked", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const onclick = vi.fn();
    const comp = mount(StatTile, { target, props: { value: 5, label: "Active", onclick } });
    flushSync();
    (target.querySelector(".ui-stat-tile") as HTMLElement).click();
    expect(onclick).toHaveBeenCalledOnce();
    unmount(comp);
    target.remove();
  });

  it("is not styled clickable when no onclick is passed", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(StatTile, { target, props: { value: 5, label: "Active" } });
    flushSync();
    expect(target.querySelector(".ui-stat-tile")!.classList.contains("clickable")).toBe(false);
    unmount(comp);
    target.remove();
  });

  it("applies the active class when active is true", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(StatTile, { target, props: { value: 5, label: "Active", active: true } });
    flushSync();
    expect(target.querySelector(".ui-stat-tile")!.classList.contains("active")).toBe(true);
    unmount(comp);
    target.remove();
  });
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd packages/editor && npx vitest run test/HorizontalBarChart.test.ts test/StatTile.test.ts`
Expected: FAIL — `onsegmentclick`/`activeId`/`onclick`/`active` don't exist yet, so clicks are no-ops and no `dimmed`/`active`/`clickable` classes appear.

- [ ] **Step 3: Implement `HorizontalBarChart.svelte`**

Replace the full contents of `packages/editor/src/lib/components/HorizontalBarChart.svelte` with:

```svelte
<script lang="ts">
  import type { DonutSegment } from "./DonutChart.svelte";
  import { textColorForFill } from "../colorContrast";

  interface Props {
    segments: DonutSegment[];
    activeId?: string | null;
    onsegmentclick?: (id: string) => void;
  }
  let { segments, activeId = null, onsegmentclick }: Props = $props();

  // A segment narrower than this can't plausibly hold its value text without
  // spilling into its neighbors, so the number is dropped (the legend below
  // always has the exact value regardless).
  const INSIDE_VALUE_MIN_PCT = 8;
</script>

<div class="stacked-bar-chart">
  <div class="stacked-bar">
    {#each segments as seg (seg.id)}
      <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
      <div
        class="stacked-segment"
        class:dimmed={activeId !== null && activeId !== seg.id}
        class:active={activeId === seg.id}
        style="width:{seg.pct}%; background:{seg.color}; color:{textColorForFill(seg.color)}; cursor:{onsegmentclick ? 'pointer' : 'default'}"
        title="{seg.label}: {seg.valueLabel} ({seg.pct.toFixed(0)}%)"
        onclick={() => onsegmentclick?.(seg.id)}
      >{seg.pct >= INSIDE_VALUE_MIN_PCT ? seg.valueLabel : ""}</div>
    {/each}
  </div>
  <div class="stacked-legend">
    {#each segments as seg (seg.id)}
      <div class="legend-item">
        <span class="legend-label">{seg.emoji} {seg.label}</span>
        <span class="legend-value">{seg.valueLabel}</span>
      </div>
    {/each}
  </div>
</div>

<style>
  .stacked-bar-chart { display: flex; flex-direction: column; gap: 10px; width: 100%; }
  .stacked-bar {
    display: flex;
    width: 100%;
    height: 36px;
    border-radius: var(--radius-sm);
    overflow: hidden;
    background: var(--surface-alt);
  }
  .stacked-segment {
    height: 100%;
    min-width: 3px;
    box-sizing: border-box;
    border-right: 2px solid var(--surface-alt);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 12px;
    font-weight: 600;
    overflow: hidden;
    white-space: nowrap;
    transition: width .2s, opacity .15s;
  }
  .stacked-segment:last-child { border-right: none; }
  .stacked-segment.dimmed { opacity: .35; }
  .stacked-segment.active { outline: 2px solid var(--text); outline-offset: -2px; }
  .stacked-legend { display: flex; flex-flow: row wrap; gap: 6px 16px; }
  .legend-item { display: flex; align-items: center; gap: 4px; font-size: 11px; white-space: nowrap; }
  .legend-label { color: var(--text); }
  .legend-value { color: var(--text-muted); font-weight: 600; }
</style>
```

- [ ] **Step 4: Implement `StatTile.svelte`**

Replace the full contents of `packages/editor/src/lib/components/ui/StatTile.svelte` with:

```svelte
<!-- packages/editor/src/lib/components/ui/StatTile.svelte -->
<script lang="ts">
  import type { Snippet } from "svelte";

  interface Props {
    value: string | number;
    label: string;
    variant?: "success" | "danger" | "warning";
    valueContent?: Snippet;
    active?: boolean;
    onclick?: () => void;
  }
  let { value, label, variant, valueContent, active = false, onclick }: Props = $props();
</script>

<!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
<div
  class="ui-card ui-stat-tile"
  class:clickable={!!onclick}
  class:active
  onclick={() => onclick?.()}
>
  <div class="ui-stat-label">{label}</div>
  <div
    class="ui-stat-value"
    class:success={variant === "success"}
    class:danger={variant === "danger"}
    class:warning={variant === "warning"}
  >
    {#if valueContent}{@render valueContent()}{:else}{value}{/if}
  </div>
</div>

<style>
  .ui-stat-tile {
    background: var(--surface);
    border-radius: var(--radius-lg);
    box-shadow: var(--shadow-sm);
    padding: var(--space-3);
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
  }
  .ui-stat-tile.clickable { cursor: pointer; }
  .ui-stat-tile.active { outline: 2px solid var(--accent); outline-offset: -2px; }
  .ui-stat-label {
    font-family: var(--font-sans);
    font-size: 11px; color: var(--text-faint);
    text-transform: uppercase; letter-spacing: 0.05em;
  }
  .ui-stat-value {
    font-family: var(--font-sans);
    font-size: 28px; font-weight: 700; color: var(--text); line-height: 1.2;
    margin-top: 4px;
  }
  .ui-stat-value.success { color: var(--success); }
  .ui-stat-value.danger { color: var(--danger); }
  .ui-stat-value.warning { color: var(--warning); }
</style>
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `cd packages/editor && npx vitest run test/HorizontalBarChart.test.ts test/StatTile.test.ts test/StatTileRow.test.ts`
Expected: PASS — including `StatTileRow.test.ts`, which mounts `StatTile` without the new props and must be unaffected.

- [ ] **Step 6: Commit**

```bash
git add packages/editor/src/lib/components/HorizontalBarChart.svelte packages/editor/src/lib/components/ui/StatTile.svelte packages/editor/test/HorizontalBarChart.test.ts packages/editor/test/StatTile.test.ts
git commit -m "feat(ui): add click-to-highlight support to HorizontalBarChart and StatTile"
```

---

### Task 4: Frontend — wire click-to-filter into ChoresPage

Wires Task 3's new props into the Chores summary section: clicking the "Overdue %"/"On track %" tiles or a bar-chart segment filters the list to that health bucket and highlights the selection; clicking the same one again clears it. "Active" always clears the filter (it has no matching bucket). Only reachable via the chart segment: "due-soon" (no tile represents it).

**Files:**
- Modify: `packages/editor/src/lib/components/ChoresPage.svelte`
- Test: `packages/editor/test/ChoresPage.test.ts`

**Interfaces:**
- Consumes: `HorizontalBarChart`'s `activeId`/`onsegmentclick` and `StatTile`'s `active`/`onclick` props (Task 3). `HealthBucket = "on-track" | "due-soon" | "overdue"` (existing type, `ChoresPage.svelte:64`); `healthBucket(pct: number): HealthBucket` (existing, `ChoresPage.svelte:72-76`).
- Produces: no new exports — this is a leaf wiring task.

- [ ] **Step 1: Write the failing tests**

Add this new `describe` block to `packages/editor/test/ChoresPage.test.ts`, after the `"ChoresPage — schedule health summary"` block (after line 122, before `describe("ChoresPage — schedule filter", ...)`):

```ts
describe("ChoresPage — health click-to-filter", () => {
  function makeThreeBucketStore() {
    const now = Date.now();
    const chore1 = makeChore({ id: "c1", name: "On track chore", periodDays: 10 });
    const chore2 = makeChore({ id: "c2", name: "Due soon chore", periodDays: 10 });
    const chore3 = makeChore({ id: "c3", name: "Overdue chore", periodDays: 10 });
    const store = makeStore([chore1, chore2, chore3]);
    store.assignments = [
      // All within the default "needs attention" 7-day cutoff, spanning the 3 health buckets.
      { id: "a1", choreId: "c1", roomId: null, nextDueDate: new Date(now + 6 * 86400000).toISOString() }, // pct 0.6 -> on-track
      { id: "a2", choreId: "c2", roomId: null, nextDueDate: new Date(now + 3 * 86400000).toISOString() }, // pct 0.3 -> due-soon
      { id: "a3", choreId: "c3", roomId: null, nextDueDate: new Date(now - 1 * 86400000).toISOString() }, // pct 0 -> overdue
    ] as typeof store.assignments;
    return store;
  }

  it("clicking the Overdue stat tile filters to overdue chores; clicking it again clears the filter", () => {
    const store = makeThreeBucketStore();
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(ChoresPage, { target, props: { store, floorStore: { floors: [] } } });
    flushSync();

    const overdueTile = Array.from(target.querySelectorAll(".ui-stat-tile")).find((el) => el.textContent?.includes("Overdue")) as HTMLElement;
    overdueTile.click();
    flushSync();
    expect(target.querySelectorAll(".name-cell")).toHaveLength(1);
    expect(target.querySelector(".name-cell")?.textContent).toContain("Overdue chore");
    expect(overdueTile.classList.contains("active")).toBe(true);

    overdueTile.click();
    flushSync();
    expect(overdueTile.classList.contains("active")).toBe(false);
    expect(target.querySelectorAll(".name-cell")).toHaveLength(3);

    unmount(comp);
  });

  it("clicking a bar chart segment filters to that bucket", () => {
    const store = makeThreeBucketStore();
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(ChoresPage, { target, props: { store, floorStore: { floors: [] } } });
    flushSync();

    const dueSoonSegment = Array.from(target.querySelectorAll(".stacked-segment")).find((el) => el.getAttribute("title")?.startsWith("Due soon")) as HTMLElement;
    dueSoonSegment.click();
    flushSync();
    expect(target.querySelectorAll(".name-cell")).toHaveLength(1);
    expect(target.querySelector(".name-cell")?.textContent).toContain("Due soon chore");

    unmount(comp);
  });

  it("clicking the Active tile clears any health filter", () => {
    const store = makeThreeBucketStore();
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(ChoresPage, { target, props: { store, floorStore: { floors: [] } } });
    flushSync();

    const overdueTile = Array.from(target.querySelectorAll(".ui-stat-tile")).find((el) => el.textContent?.includes("Overdue")) as HTMLElement;
    overdueTile.click();
    flushSync();
    expect(target.querySelectorAll(".name-cell")).toHaveLength(1);

    const activeTile = Array.from(target.querySelectorAll(".ui-stat-tile")).find((el) => el.textContent?.includes("Active")) as HTMLElement;
    activeTile.click();
    flushSync();
    expect(target.querySelectorAll(".name-cell")).toHaveLength(3);
    expect(activeTile.classList.contains("active")).toBe(true);

    unmount(comp);
  });
});
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd packages/editor && npx vitest run test/ChoresPage.test.ts -t "health click-to-filter"`
Expected: FAIL — clicking tiles/segments does nothing yet, so the list stays unfiltered (3 `.name-cell` rows) and no `active` class appears.

- [ ] **Step 3: Add `healthFilter` state and the filtering helper**

In `packages/editor/src/lib/components/ChoresPage.svelte`, change the filter-state block (lines 45-50) from:
```ts
  let searchQuery = $state("");
  let roomFilter = $state("");
  let scheduleFilter = $state("");
  let dueFilter = $state<"all" | "attention">("attention");
  let filterModalOpen = $state(false);
  const filtersActive = $derived(roomFilter !== "" || scheduleFilter !== "");
```
to:
```ts
  let searchQuery = $state("");
  let roomFilter = $state("");
  let scheduleFilter = $state("");
  let dueFilter = $state<"all" | "attention">("attention");
  let filterModalOpen = $state(false);
  let healthFilter = $state<HealthBucket | null>(null);
  const filtersActive = $derived(roomFilter !== "" || scheduleFilter !== "");
```

Then, immediately before the `filteredChores` derived (line 139), add:
```ts
  function choreHealthBuckets(chore: Chore): HealthBucket[] {
    return store.assignments
      .filter((a) => a.choreId === chore.id)
      .map((a) => healthBucket(store.getProgress(a, chore)));
  }

  function toggleHealthFilter(bucket: HealthBucket): void {
    healthFilter = healthFilter === bucket ? null : bucket;
  }

```

- [ ] **Step 4: Add the health-bucket check to `filteredChores`**

Change `filteredChores` (lines 139-148) from:
```ts
  const filteredChores = $derived(
    store.chores.filter((c) => {
      if (searchQuery && !c.name.toLowerCase().includes(searchQuery.toLowerCase())) return false;
      if (scheduleFilter && scheduleCategory(c) !== scheduleFilter) return false;
      const assignments = store.assignments.filter((a) => a.choreId === c.id);
      if (roomFilter && !assignments.some((a) => a.roomId === roomFilter)) return false;
      if (dueFilter === "attention" && !needsAttention(assignments)) return false;
      return true;
    }),
  );
```
to:
```ts
  const filteredChores = $derived(
    store.chores.filter((c) => {
      if (searchQuery && !c.name.toLowerCase().includes(searchQuery.toLowerCase())) return false;
      if (scheduleFilter && scheduleCategory(c) !== scheduleFilter) return false;
      const assignments = store.assignments.filter((a) => a.choreId === c.id);
      if (roomFilter && !assignments.some((a) => a.roomId === roomFilter)) return false;
      if (dueFilter === "attention" && !needsAttention(assignments)) return false;
      if (healthFilter && !choreHealthBuckets(c).includes(healthFilter)) return false;
      return true;
    }),
  );
```

- [ ] **Step 5: Wire the props in the template**

Change the chart/tiles block (lines 199-209) from:
```svelte
    <div class="chart-card-wrap">
      <Card style="flex:1; min-width:0;">
        <div class="chart-label">{$_('chores.page.scheduleHealth')}</div>
        <HorizontalBarChart segments={healthBreakdown} />
      </Card>
      <div class="stat-tiles">
        <StatTile label={$_('chores.page.active')} value={totalAssignments} />
        <StatTile label={$_('chores.page.overdue')} value={`${overduePct}%`} variant="danger" />
        <StatTile label={$_('chores.page.onTrack')} value={`${onTrackPct}%`} variant="success" />
      </div>
    </div>
```
to:
```svelte
    <div class="chart-card-wrap">
      <Card style="flex:1; min-width:0;">
        <div class="chart-label">{$_('chores.page.scheduleHealth')}</div>
        <HorizontalBarChart segments={healthBreakdown} activeId={healthFilter} onsegmentclick={(id) => toggleHealthFilter(id as HealthBucket)} />
      </Card>
      <div class="stat-tiles">
        <StatTile label={$_('chores.page.active')} value={totalAssignments} active={healthFilter === null} onclick={() => { healthFilter = null; }} />
        <StatTile label={$_('chores.page.overdue')} value={`${overduePct}%`} variant="danger" active={healthFilter === "overdue"} onclick={() => toggleHealthFilter("overdue")} />
        <StatTile label={$_('chores.page.onTrack')} value={`${onTrackPct}%`} variant="success" active={healthFilter === "on-track"} onclick={() => toggleHealthFilter("on-track")} />
      </div>
    </div>
```

- [ ] **Step 6: Run the full test file to verify everything passes**

Run: `cd packages/editor && npx vitest run test/ChoresPage.test.ts`
Expected: PASS — all existing describe blocks (external selection, schedule health summary, schedule filter, unassigned chores, mark-all-done backdating, responsive columns) plus the new health click-to-filter block.

- [ ] **Step 7: Commit**

```bash
git add packages/editor/src/lib/components/ChoresPage.svelte packages/editor/test/ChoresPage.test.ts
git commit -m "feat(chores): click a KPI tile or chart segment to filter the chore list"
```

---

### Task 5: Frontend — per-assignment label from the floor-plan pin popup

`Assignment.label` and its editing UI already exist (`ChoreEditModal.svelte`'s Assignments tab, `choreStore.svelte.ts`'s `updateAssignmentLabel`, and the History tab already shows it — all from PR #107, merged 2026-08-09). The one place it's still missing is `BadgePopup.svelte`, the popup that opens when clicking a chore's pin on the floor plan. This task adds a label field there, reusing the existing `updateAssignmentLabel` store method — no backend or API changes.

**Files:**
- Modify: `packages/editor/src/lib/components/BadgePopup.svelte`
- Modify: `packages/editor/src/App.svelte:1059-1068` (wire the new prop)
- Test: `packages/editor/test/BadgePopup.test.ts` (new file)

**Interfaces:**
- Consumes: `Assignment.label: string | null` (existing field, `choreStore.svelte.ts:90`); `choreStore.updateAssignmentLabel(id: string, label: string): Promise<void>` (existing, `choreStore.svelte.ts:270-280`).
- Produces: `BadgePopup` gains a required `onlabelchange: (label: string) => void` prop — its one caller (`App.svelte`) is updated in this same task, so nothing is left half-wired.

- [ ] **Step 1: Write the failing tests**

Create `packages/editor/test/BadgePopup.test.ts`:

```ts
import { describe, it, expect, vi } from "vitest";
import { mount, unmount, flushSync } from "svelte";
import BadgePopup from "../src/lib/components/BadgePopup.svelte";
import type { Chore, Assignment } from "../src/lib/choreStore.svelte";

function makeChore(overrides: Partial<Chore> = {}): Chore {
  return {
    id: "c1", donetickId: null, name: "🧹 Sweep", emoji: "🧹",
    periodDays: 7, frequencyType: "interval", frequency: 7, frequencyMetadata: {},
    scheduleFromDue: false, nextDueDate: "2027-01-01T00:00:00Z", description: "", attachments: [],
    ...overrides,
  };
}

function makeAssignment(overrides: Partial<Assignment> = {}): Assignment {
  return {
    id: "a1", choreId: "c1", roomId: "r1", position: { x: 1, y: 2 },
    nextDueDate: "2027-01-01T00:00:00Z", label: null,
    ...overrides,
  };
}

function target(): HTMLElement {
  const el = document.createElement("div");
  document.body.appendChild(el);
  return el;
}

function baseProps(overrides: Record<string, unknown> = {}) {
  return {
    chore: makeChore(),
    assignment: makeAssignment(),
    screenX: 10,
    screenY: 10,
    oncomplete: vi.fn(),
    oncompleteall: vi.fn(),
    onremove: vi.fn(),
    onclose: vi.fn(),
    onlabelchange: vi.fn(),
    ...overrides,
  };
}

describe("BadgePopup — label", () => {
  it("pre-fills the label input from the assignment's existing label", () => {
    const el = target();
    const comp = mount(BadgePopup, { target: el, props: baseProps({ assignment: makeAssignment({ label: "Side A" }) }) });
    flushSync();
    expect((el.querySelector(".popup-label-input") as HTMLInputElement).value).toBe("Side A");
    unmount(comp);
    el.remove();
  });

  it("shows an empty label input when the assignment has no label", () => {
    const el = target();
    const comp = mount(BadgePopup, { target: el, props: baseProps() });
    flushSync();
    expect((el.querySelector(".popup-label-input") as HTMLInputElement).value).toBe("");
    unmount(comp);
    el.remove();
  });

  it("calls onlabelchange with the trimmed value on blur when the label changed", () => {
    const el = target();
    const onlabelchange = vi.fn();
    const comp = mount(BadgePopup, { target: el, props: baseProps({ onlabelchange }) });
    flushSync();
    const input = el.querySelector(".popup-label-input") as HTMLInputElement;
    input.value = "  Window 1  ";
    input.dispatchEvent(new Event("blur"));
    expect(onlabelchange).toHaveBeenCalledWith("Window 1");
    unmount(comp);
    el.remove();
  });

  it("does not call onlabelchange when the value is unchanged on blur", () => {
    const el = target();
    const onlabelchange = vi.fn();
    const comp = mount(BadgePopup, {
      target: el,
      props: baseProps({ assignment: makeAssignment({ label: "Window 1" }), onlabelchange }),
    });
    flushSync();
    const input = el.querySelector(".popup-label-input") as HTMLInputElement;
    input.value = "Window 1";
    input.dispatchEvent(new Event("blur"));
    expect(onlabelchange).not.toHaveBeenCalled();
    unmount(comp);
    el.remove();
  });
});

describe("BadgePopup — existing behavior", () => {
  it("shows the chore name", () => {
    const el = target();
    const comp = mount(BadgePopup, { target: el, props: baseProps() });
    flushSync();
    expect(el.querySelector(".popup-name")?.textContent).toBe("🧹 Sweep");
    unmount(comp);
    el.remove();
  });

  it("calls oncompleteall when 'All done' is clicked", () => {
    const el = target();
    const oncompleteall = vi.fn();
    const comp = mount(BadgePopup, { target: el, props: baseProps({ oncompleteall }) });
    flushSync();
    (Array.from(el.querySelectorAll("button")).find((b) => b.textContent?.includes("All done")) as HTMLButtonElement).click();
    expect(oncompleteall).toHaveBeenCalledOnce();
    unmount(comp);
    el.remove();
  });
});
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd packages/editor && npx vitest run test/BadgePopup.test.ts`
Expected: FAIL on the label tests — `.popup-label-input` doesn't exist yet (the "existing behavior" tests pass already, since that part of the component is unchanged).

- [ ] **Step 3: Implement the label field in `BadgePopup.svelte`**

Replace the full contents of `packages/editor/src/lib/components/BadgePopup.svelte` with:

```svelte
<script lang="ts">
  import { _ } from "svelte-i18n";
  import type { Chore, Assignment } from "../choreStore.svelte";
  import { formatDate } from "../dateFormat";

  interface Props {
    chore: Chore;
    assignment: Assignment;
    screenX: number;
    screenY: number;
    oncomplete: () => void;
    oncompleteall: () => void;
    onremove: () => void;
    onclose: () => void;
    onlabelchange: (label: string) => void;
  }

  let { chore, assignment, screenX, screenY, oncomplete, oncompleteall, onremove, onclose, onlabelchange }: Props = $props();

  const overdue = $derived(new Date(assignment.nextDueDate).getTime() < Date.now());

  function handleLabelBlur(e: FocusEvent): void {
    const value = (e.target as HTMLInputElement).value.trim();
    if (value === (assignment.label ?? "")) return;
    onlabelchange(value);
  }
</script>

<!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
<div
  class="popup"
  style="left:{screenX + 26}px;top:{screenY - 20}px"
  onclick={(e) => e.stopPropagation()}
>
  <div class="popup-name">{chore.name}</div>
  <input
    class="popup-label-input"
    placeholder={$_('chores.editModal.labelPlaceholder')}
    value={assignment.label ?? ""}
    onblur={handleLabelBlur}
  />
  <div class="popup-due" class:overdue>
    {overdue ? $_('chores.badgePopup.overdueSince') : $_('chores.badgePopup.due')}: {formatDate(assignment.nextDueDate)}
  </div>
  <div class="popup-actions">
    <button onclick={oncompleteall}>✓ {$_('chores.badgePopup.allDone')}</button>
    <button onclick={oncomplete}>✓ {$_('chores.badgePopup.thisRoom')}</button>
    <button onclick={onremove}>✕ {$_('chores.badgePopup.remove')}</button>
    <button class="close-btn" onclick={onclose}>✕</button>
  </div>
</div>

<style>
  .popup {
    position: fixed;
    background: #2a2a3e;
    border: 1px solid #444;
    border-radius: 6px;
    padding: 8px 10px;
    min-width: 180px;
    z-index: 100;
    box-shadow: 0 4px 12px rgba(0,0,0,0.5);
    font-size: 12px;
    color: #ccc;
  }
  .popup-name {
    font-weight: 600;
    margin-bottom: 4px;
    color: #eee;
  }
  .popup-label-input {
    width: 100%;
    box-sizing: border-box;
    padding: 3px 6px;
    margin-bottom: 8px;
    border: 1px solid #444;
    border-radius: 3px;
    background: #1e1e2e;
    color: #ccc;
    font-size: 11px;
  }
  .popup-label-input:focus { outline: none; border-color: #6a6aaa; }
  .popup-due {
    color: #888;
    margin-bottom: 8px;
  }
  .popup-due.overdue {
    color: #f44336;
  }
  .popup-actions {
    display: flex;
    gap: 6px;
    flex-wrap: wrap;
  }
  .popup-actions button {
    padding: 3px 8px;
    border: none;
    border-radius: 3px;
    background: #3a3a5a;
    color: #ccc;
    cursor: pointer;
    font-size: 11px;
  }
  .popup-actions button:hover {
    background: #4a4a6a;
  }
  .close-btn {
    margin-left: auto;
  }
</style>
```

- [ ] **Step 4: Wire the new prop in `App.svelte`**

In `packages/editor/src/App.svelte`, change the `<BadgePopup>` usage (lines 1059-1068) from:
```svelte
                    <BadgePopup
                      {chore}
                      assignment={badge.assignment}
                      screenX={badge.screenX}
                      screenY={badge.screenY}
                      oncomplete={async () => { await choreStore.completeAssignment(badge.assignment.id); selectedBadge = null; }}
                      oncompleteall={async () => { await choreStore.completeChore(chore.id); selectedBadge = null; }}
                      onremove={async () => { await choreStore.deleteAssignment(badge.assignment.id); selectedBadge = null; }}
                      onclose={() => { selectedBadge = null; }}
                    />
```
to:
```svelte
                    <BadgePopup
                      {chore}
                      assignment={badge.assignment}
                      screenX={badge.screenX}
                      screenY={badge.screenY}
                      oncomplete={async () => { await choreStore.completeAssignment(badge.assignment.id); selectedBadge = null; }}
                      oncompleteall={async () => { await choreStore.completeChore(chore.id); selectedBadge = null; }}
                      onremove={async () => { await choreStore.deleteAssignment(badge.assignment.id); selectedBadge = null; }}
                      onlabelchange={(label) => choreStore.updateAssignmentLabel(badge.assignment.id, label)}
                      onclose={() => { selectedBadge = null; }}
                    />
```

- [ ] **Step 5: Run the tests to verify everything passes**

Run: `cd packages/editor && npx vitest run test/BadgePopup.test.ts`
Expected: PASS — all 6 tests.

Then run the full frontend suite to confirm nothing else broke (App.svelte has no existing tests referencing `BadgePopup`, so no other file needs updating):
Run: `cd packages/editor && npx vitest run`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add packages/editor/src/lib/components/BadgePopup.svelte packages/editor/src/App.svelte packages/editor/test/BadgePopup.test.ts
git commit -m "feat(chores): edit an assignment's label from the floor-plan pin popup"
```

---

## Self-Review Notes

- **Spec coverage:** All 4 design sections have a task — §1→Task 1, §2→Task 2, §3→Task 3+4, §4→Task 5.
- **Discovered during research (not in the original design doc):** most of §4's backend/data-model work (`Assignment.label`, `updateAssignmentLabel`, the Assignments tab, and History already showing the label) turned out to already exist on `main` (PR #107, merged 2026-08-09, one day before this plan was written). Task 5 is scoped down accordingly to just the one gap: `BadgePopup.svelte`.
- **Type consistency:** `HealthBucket` (Task 4) matches the existing type already declared in `ChoresPage.svelte:64`. `Assignment.label: string | null` (Task 5) matches the existing field in `choreStore.svelte.ts:90` and `models_chores.py:40`. `onsegmentclick`/`activeId` (Task 3) are consumed with matching names in Task 4 — no renaming drift.
