# Nth-Weekday-of-Month/Quarter Chore Scheduling Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Support Donetick's "Nth weekday of month/quarter" recurrence (e.g. "2nd Tuesday of every month", "last Friday of every quarter") in myhome's scheduler, Donetick import, and manual `ScheduleEditor` UI — today it isn't modeled at all and imports/behaves as plain "every week on this day."

**Architecture:** Reuses the existing `frequencyType: "days_of_the_week"` (no new top-level type), discriminated by two new `frequencyMetadata` keys copied verbatim from Donetick's own JSON shape: `weekPattern` (`"week_of_month"` | `"week_of_quarter"`) and `occurrences` (`number[]`, `-1` = "last"). `next_due_from_schedule`'s existing `days_of_the_week` branch gains a new conditional path for this; the plain-weekly path is untouched. `ScheduleEditor.svelte` gets a new "Nth weekday" category; `scheduleParser.ts` gets matching EN/FR quick-add phrases.

**Tech Stack:** FastAPI + Pydantic (backend), Svelte 5 runes + svelte-i18n + Vitest (frontend), pytest (backend tests).

## Global Constraints

- Full design at `docs/superpowers/specs/2026-07-31-nth-weekday-scheduling-design.md` — read it if anything below is ambiguous.
- No new DB columns — everything reuses `Chore.frequencyType` / `frequency` / `frequencyMetadata`.
- `days`/`months`/`weekPattern`/`occurrences` are stored **exactly** as Donetick's own JSON shape (no import-time translation) — normalization to numbers happens only at read-time (`to_weekday_num`/`to_month_num` on the backend, `toWeekdayNum`/`toMonthNum` on the frontend), matching the pattern already established for the `day_of_the_month` months-restriction fix.
- The manual `ScheduleEditor` picker is single-weekday only (per the approved design); the backend scheduler must still handle multi-day Donetick imports generally (it iterates a `set` of allowed weekdays, so this falls out naturally — no special-casing needed).
- Labels use existing `chores.schedule.dayAbbrev.*` abbreviations (e.g. "Tue"), not full weekday names — this matches the existing `weeklyOn` label convention and avoids adding a parallel full-name i18n key set.
- Add every new i18n key to **both** `en.json` and `fr.json` in the same task that introduces it.
- Run `cd /projects/myhome && pytest packages/backend` and `cd /projects/myhome/packages/editor && npx vitest run` before any commit that touches backend/frontend code respectively, to confirm nothing else broke.

---

### Task 1: Backend — Nth-weekday-occurrence math helpers

**Files:**
- Modify: `packages/backend/src/myhome/chore_scheduling.py`
- Test: `packages/backend/tests/test_chore_scheduling.py`

**Interfaces:**
- Produces: `nth_weekday_occurrence(date: datetime, period_start: datetime) -> int`, `is_last_weekday_in_month(date: datetime) -> bool`, `quarter_start(date: datetime) -> datetime`, `is_last_weekday_in_quarter(date: datetime) -> bool` — all used by Task 2.

- [ ] **Step 1: Write the failing tests**

Append to `packages/backend/tests/test_chore_scheduling.py`:

```python
def test_nth_weekday_occurrence_counts_within_month():
    from myhome.chore_scheduling import nth_weekday_occurrence
    period_start = datetime(2026, 7, 1)
    date = datetime(2026, 7, 14)  # 2nd Tuesday of July 2026
    assert nth_weekday_occurrence(date, period_start) == 2


def test_nth_weekday_occurrence_first_of_period_is_occurrence_one():
    from myhome.chore_scheduling import nth_weekday_occurrence
    period_start = datetime(2026, 7, 1)  # a Wednesday
    assert nth_weekday_occurrence(period_start, period_start) == 1


def test_is_last_weekday_in_month_true_at_month_boundary():
    from myhome.chore_scheduling import is_last_weekday_in_month
    assert is_last_weekday_in_month(datetime(2026, 12, 29)) is True  # +7d crosses into January


def test_is_last_weekday_in_month_false_mid_month():
    from myhome.chore_scheduling import is_last_weekday_in_month
    assert is_last_weekday_in_month(datetime(2026, 12, 22)) is False  # +7d stays in December


def test_quarter_start_for_each_quarter():
    from myhome.chore_scheduling import quarter_start
    assert quarter_start(datetime(2026, 2, 15)) == datetime(2026, 1, 1)
    assert quarter_start(datetime(2026, 5, 1)) == datetime(2026, 4, 1)
    assert quarter_start(datetime(2026, 8, 31)) == datetime(2026, 7, 1)
    assert quarter_start(datetime(2026, 12, 25)) == datetime(2026, 10, 1)


def test_is_last_weekday_in_quarter_true_at_year_boundary():
    from myhome.chore_scheduling import is_last_weekday_in_quarter
    assert is_last_weekday_in_quarter(datetime(2026, 12, 25)) is True  # +7d crosses into Q1 2027


def test_is_last_weekday_in_quarter_false_mid_quarter():
    from myhome.chore_scheduling import is_last_weekday_in_quarter
    assert is_last_weekday_in_quarter(datetime(2026, 8, 7)) is False  # +7d stays in Q3
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /projects/myhome && pytest packages/backend/tests/test_chore_scheduling.py -v -k "occurrence or last_weekday or quarter_start"`
Expected: FAIL with `ImportError`/`AttributeError` — none of these functions exist yet.

- [ ] **Step 3: Implement**

In `packages/backend/src/myhome/chore_scheduling.py`, add these four functions right after `to_month_num` and before `adaptive_period_days`:

```python
def nth_weekday_occurrence(date: datetime, period_start: datetime) -> int:
    """1-based count of how many times `date`'s weekday has occurred from
    `period_start` (inclusive) through `date` (inclusive)."""
    count = 0
    d = period_start
    while d <= date:
        if d.weekday() == date.weekday():
            count += 1
        d += timedelta(days=1)
    return count


def is_last_weekday_in_month(date: datetime) -> bool:
    """True if `date + 7 days` falls in the next calendar month."""
    return (date + timedelta(days=7)).month != date.month


def quarter_start(date: datetime) -> datetime:
    """First day of the quarter (Jan/Apr/Jul/Oct 1) containing `date`."""
    q_month = ((date.month - 1) // 3) * 3 + 1
    return date.replace(month=q_month, day=1)


def is_last_weekday_in_quarter(date: datetime) -> bool:
    """True if `date + 7 days` falls in the next calendar quarter."""
    return quarter_start(date + timedelta(days=7)) != quarter_start(date)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /projects/myhome && pytest packages/backend/tests/test_chore_scheduling.py -v -k "occurrence or last_weekday or quarter_start"`
Expected: all 7 new tests PASS.

- [ ] **Step 5: Commit**

```bash
cd /projects/myhome
git add packages/backend/src/myhome/chore_scheduling.py packages/backend/tests/test_chore_scheduling.py
git commit -m "feat(chores): add Nth-weekday-of-period scheduling math helpers"
```

---

### Task 2: Backend — wire `next_due_from_schedule` for week_of_month/week_of_quarter

**Files:**
- Modify: `packages/backend/src/myhome/chore_scheduling.py`
- Test: `packages/backend/tests/test_chore_scheduling.py`

**Interfaces:**
- Consumes: `nth_weekday_occurrence`, `is_last_weekday_in_month`, `quarter_start`, `is_last_weekday_in_quarter` from Task 1; `to_weekday_num` (existing).

- [ ] **Step 1: Write the failing tests**

Append to `packages/backend/tests/test_chore_scheduling.py`:

```python
def test_days_of_the_week_nth_occurrence_of_month():
    chore = _chore(
        frequencyType="days_of_the_week", frequency=1,
        frequencyMetadata={"days": [2], "weekPattern": "week_of_month", "occurrences": [2]},  # Tuesday, 2nd occurrence
    )
    from_dt = datetime(2026, 7, 1, tzinfo=timezone.utc)
    result = next_due_from_schedule(chore, from_dt)
    assert result == datetime(2026, 7, 14, tzinfo=timezone.utc)


def test_days_of_the_week_last_occurrence_of_quarter():
    chore = _chore(
        frequencyType="days_of_the_week", frequency=1,
        frequencyMetadata={"days": [5], "weekPattern": "week_of_quarter", "occurrences": [-1]},  # Friday, last occurrence
    )
    from_dt = datetime(2026, 7, 1, tzinfo=timezone.utc)
    result = next_due_from_schedule(chore, from_dt)
    assert result == datetime(2026, 9, 25, tzinfo=timezone.utc)  # last Friday of Q3 2026


def test_days_of_the_week_plain_weekly_unaffected_by_new_branch():
    """Regression guard: a plain days_of_the_week chore (no weekPattern) must
    keep using the existing fast-path logic, not the new occurrence search."""
    chore = _chore(frequencyType="days_of_the_week", frequency=1, frequencyMetadata={"days": [3]})  # Wednesday
    from_dt = datetime(2026, 7, 4, tzinfo=timezone.utc)  # a Saturday
    result = next_due_from_schedule(chore, from_dt)
    assert result == datetime(2026, 7, 8, tzinfo=timezone.utc)  # next Wednesday


def test_days_of_the_week_nth_occurrence_with_donetick_day_name_string():
    """Donetick stores `days` as full English day-name strings (e.g. "Tuesday"),
    not ints, for this pattern just like plain days_of_the_week."""
    chore = _chore(
        frequencyType="days_of_the_week", frequency=1,
        frequencyMetadata={"days": ["Tuesday"], "weekPattern": "week_of_month", "occurrences": [2]},
    )
    from_dt = datetime(2026, 7, 1, tzinfo=timezone.utc)
    result = next_due_from_schedule(chore, from_dt)
    assert result == datetime(2026, 7, 14, tzinfo=timezone.utc)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /projects/myhome && pytest packages/backend/tests/test_chore_scheduling.py -v -k nth_occurrence_of_month or last_occurrence_of_quarter or donetick_day_name`
Expected: the three new week_of_month/week_of_quarter tests FAIL (wrong dates — currently computed via the plain-weekly fast path since there's no `weekPattern` branch yet); `test_days_of_the_week_plain_weekly_unaffected_by_new_branch` PASSES already (it exercises existing behavior, included here as a pre-change baseline).

- [ ] **Step 3: Implement**

In `packages/backend/src/myhome/chore_scheduling.py`, replace the `days_of_the_week` branch of `next_due_from_schedule`:

```python
    if ft == "days_of_the_week":
        week_pattern = meta.get("weekPattern")
        if week_pattern in ("week_of_month", "week_of_quarter"):
            allowed_weekdays = {(to_weekday_num(d) - 1) % 7 for d in (meta.get("days") or [])}
            occurrences = {int(o) for o in (meta.get("occurrences") or [])}
            wants_last = -1 in occurrences
            is_monthly = week_pattern == "week_of_month"
            candidate = from_dt + timedelta(days=1)
            for _ in range(730):  # Donetick's own 2-year safety cap
                if candidate.weekday() in allowed_weekdays:
                    period_start = candidate.replace(day=1) if is_monthly else quarter_start(candidate)
                    occurrence = nth_weekday_occurrence(candidate, period_start)
                    is_last = is_last_weekday_in_month(candidate) if is_monthly else is_last_weekday_in_quarter(candidate)
                    if occurrence in occurrences or (wants_last and is_last):
                        return candidate
                candidate += timedelta(days=1)
            return candidate
        days = sorted((to_weekday_num(d) - 1) % 7 for d in (meta.get("days") or []))
        if not days:
            return from_dt + timedelta(weeks=1)
        wd = from_dt.weekday()
        for d in days:
            if d > wd:
                return from_dt + timedelta(days=d - wd)
        return from_dt + timedelta(days=7 - wd + days[0])
```

(This is the existing branch with a new `if week_pattern in (...)` block inserted before the pre-existing plain-weekly logic, which is otherwise unchanged.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /projects/myhome && pytest packages/backend/tests/test_chore_scheduling.py -v`
Expected: all tests in the file PASS (including every pre-existing test — the plain-weekly path must be untouched).

- [ ] **Step 5: Commit**

```bash
cd /projects/myhome
git add packages/backend/src/myhome/chore_scheduling.py packages/backend/tests/test_chore_scheduling.py
git commit -m "feat(chores): schedule week_of_month/week_of_quarter recurrence"
```

---

### Task 3: Backend — `_period_days` estimate + Donetick-import-shaped integration test

**Files:**
- Modify: `packages/backend/src/myhome/routes/chores.py`
- Test: `packages/backend/tests/test_chores.py`

**Interfaces:**
- Consumes: the `days_of_the_week` scheduling behavior from Task 2 (via the `/complete` route, exercised end-to-end).

- [ ] **Step 1: Write the failing test**

Append to `packages/backend/tests/test_chores.py`, right after `test_day_of_month_respects_allowed_months_as_donetick_month_names` (added by the earlier month-name-string fix):

```python
def test_days_of_the_week_nth_occurrence_with_donetick_shaped_import(client, home_id, tmp_path):
    """A chore shaped exactly like Donetick's own week_of_month JSON (string
    day name, weekPattern, occurrences) must schedule to the correct Nth
    occurrence end-to-end through the /complete route -- this is the direct
    regression test for the gap that motivated this feature (Donetick's
    Nth-weekday pattern wasn't modeled at all before this)."""
    doc = ChoreDocument(
        chores=[
            Chore(
                id="c1", name="Board meeting prep", emoji="📋", periodDays=30,
                frequencyType="days_of_the_week", frequency=1,
                frequencyMetadata={"days": ["Tuesday"], "weekPattern": "week_of_month", "occurrences": [2]},
                scheduleFromDue=True,
                nextDueDate="2026-07-01T00:00:00Z",
            )
        ],
        assignments=[],
    )
    save_chores(home_id, doc)
    aid = client.post(f"/api/homes/{home_id}/assignments", json={"choreId": "c1", "roomId": "r1"}).json()["id"]
    resp = client.post(f"/api/homes/{home_id}/assignments/{aid}/complete")
    assert resp.status_code == 200
    next_due = resp.json()["nextDueDate"]
    from datetime import datetime, timezone
    dt = datetime.fromisoformat(next_due.replace("Z", "+00:00"))
    assert (dt.year, dt.month, dt.day) == (2026, 7, 14), f"expected 2nd Tuesday of July 2026, got {dt}"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /projects/myhome && pytest packages/backend/tests/test_chores.py -v -k donetick_shaped_import`
Expected: this specific test already PASSES (Task 2 already wired the scheduler) — this step confirms that, since the test's purpose is regression coverage for the end-to-end route, not new logic. Proceed to Step 3 regardless, since `_period_days` still needs its own fix.

- [ ] **Step 3: Implement**

In `packages/backend/src/myhome/routes/chores.py`, find the `_period_days` function and change the `day_of_the_month` branch's trailing section:

```python
    elif freq_type == "day_of_the_month":
        return 30.0
    return 30.0
```

Replace with:

```python
    elif freq_type == "day_of_the_month":
        return 30.0
    elif freq_type == "days_of_the_week":
        week_pattern = meta.get("weekPattern")
        if week_pattern == "week_of_month":
            return 30.0
        if week_pattern == "week_of_quarter":
            return 91.0
        return 7.0
    return 30.0
```

- [ ] **Step 4: Add a test for the `_period_days` estimate**

Append to `packages/backend/tests/test_chores.py`:

```python
def test_import_period_days_estimate_for_days_of_the_week_variants(client, home_id, monkeypatch):
    """_period_days must distinguish plain weekly-on-days (~7d) from the two
    Nth-weekday patterns (~30d/91d) instead of falling through to the generic
    30.0 default for all of them."""
    donetick_response = {
        "res": [
            {"id": 1, "name": "Plain weekly", "frequencyType": "days_of_the_week", "frequency": 1,
             "frequencyMetadata": {"days": ["Monday"]}, "nextDueDate": "2027-01-01T00:00:00Z"},
            {"id": 2, "name": "Nth of month", "frequencyType": "days_of_the_week", "frequency": 1,
             "frequencyMetadata": {"days": ["Tuesday"], "weekPattern": "week_of_month", "occurrences": [2]},
             "nextDueDate": "2027-01-01T00:00:00Z"},
            {"id": 3, "name": "Nth of quarter", "frequencyType": "days_of_the_week", "frequency": 1,
             "frequencyMetadata": {"days": ["Friday"], "weekPattern": "week_of_quarter", "occurrences": [-1]},
             "nextDueDate": "2027-01-01T00:00:00Z"},
        ]
    }
    import respx
    import httpx
    _mock_public_dns(monkeypatch)
    with respx.mock:
        respx.get("https://donetick.example.com/api/v1/chores/").mock(
            return_value=httpx.Response(200, json=donetick_response)
        )
        for chore_id in (1, 2, 3):
            respx.get(f"https://donetick.example.com/api/v1/chores/{chore_id}/history").mock(
                return_value=httpx.Response(200, json={"res": []})
            )
        resp = client.post(
            f"/api/homes/{home_id}/chores/import",
            json={"token": "test-token", "url": "https://donetick.example.com"},
        )
    assert resp.status_code == 200
    chores = client.get(f"/api/homes/{home_id}/chores").json()["chores"]
    by_id = {c["donetickId"]: c for c in chores}
    assert by_id[1]["periodDays"] == 7.0
    assert by_id[2]["periodDays"] == 30.0
    assert by_id[3]["periodDays"] == 91.0
```

(This matches the exact endpoint path and request/mock shape already used by `test_import_from_donetick` earlier in this same file.)

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd /projects/myhome && pytest packages/backend/tests/test_chores.py -v -k "days_of_the_week or donetick_shaped"`
Expected: all PASS.

- [ ] **Step 6: Run the full backend suite**

Run: `cd /projects/myhome && pytest packages/backend -q`
Expected: all tests PASS, no regressions.

- [ ] **Step 7: Commit**

```bash
cd /projects/myhome
git add packages/backend/src/myhome/routes/chores.py packages/backend/tests/test_chores.py
git commit -m "feat(chores): correct periodDays estimate for days_of_the_week sub-patterns"
```

---

### Task 4: Frontend — shared weekday/month name normalizer + fix existing label bug

**Files:**
- Create: `packages/editor/src/lib/scheduleNames.ts`
- Modify: `packages/editor/src/lib/components/ScheduleEditor.svelte`
- Modify: `packages/editor/src/lib/choreStore.svelte.ts`
- Test: `packages/editor/test/scheduleNames.test.ts` (new), `packages/editor/test/choreStore.test.ts`

**Interfaces:**
- Produces: `toWeekdayNum(v: unknown): number | null`, `toMonthNum(v: unknown): number | null` — used by Task 6 (ScheduleEditor) and Task 7 (choreStore label).

**Context:** `ScheduleEditor.svelte` already has local `WEEKDAY_NUMS`/`MONTH_NUMS`/`toNum` (added by the earlier month-name-string bug fix). This task extracts them into a shared module so Task 7's `scheduleLabel` fix can reuse the same conversion — and, while here, fixes a twin of that same bug already latent in `scheduleLabel`: its `days_of_the_week` branch does `dayKeys[(d - 1) % 7]` assuming `d` is always an int, but Donetick sends day names as strings (e.g. `"Monday"`) for plain weekly imports too, not just the new Nth-weekday pattern — `("Monday" - 1)` is `NaN` in JS, so an imported plain-weekly chore's label silently breaks today.

- [ ] **Step 1: Write the failing test for the shared module**

Create `packages/editor/test/scheduleNames.test.ts`:

```ts
import { describe, it, expect } from "vitest";
import { toWeekdayNum, toMonthNum } from "../src/lib/scheduleNames";

describe("toWeekdayNum", () => {
  it("passes through an int unchanged", () => {
    expect(toWeekdayNum(3)).toBe(3);
  });
  it("converts a full Donetick day name, case-insensitively", () => {
    expect(toWeekdayNum("Tuesday")).toBe(2);
    expect(toWeekdayNum("SUNDAY")).toBe(7);
  });
  it("converts an abbreviated day name", () => {
    expect(toWeekdayNum("mon")).toBe(1);
  });
  it("returns null for unrecognized input", () => {
    expect(toWeekdayNum("not-a-day")).toBeNull();
  });
});

describe("toMonthNum", () => {
  it("passes through an int unchanged", () => {
    expect(toMonthNum(9)).toBe(9);
  });
  it("converts a full Donetick month name, case-insensitively", () => {
    expect(toMonthNum("March")).toBe(3);
    expect(toMonthNum("DECEMBER")).toBe(12);
  });
  it("returns null for unrecognized input", () => {
    expect(toMonthNum("not-a-month")).toBeNull();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /projects/myhome/packages/editor && npx vitest run test/scheduleNames.test.ts`
Expected: FAIL — module doesn't exist yet.

- [ ] **Step 3: Create the shared module**

Create `packages/editor/src/lib/scheduleNames.ts`:

```ts
// Donetick stores weekdays/months as full English name strings (e.g.
// "Monday", "March"), compared case-insensitively -- never ints. These
// converters normalize either shape to the 1-based int myhome's own UI and
// scheduler use (Mon=1..Sun=7, Jan=1..Dec=12).

const WEEKDAY_NUMS: Record<string, number> = {
  monday: 1, tuesday: 2, wednesday: 3, thursday: 4, friday: 5, saturday: 6, sunday: 7,
  mon: 1, tue: 2, wed: 3, thu: 4, fri: 5, sat: 6, sun: 7,
};

const MONTH_NUMS: Record<string, number> = {
  january: 1, february: 2, march: 3, april: 4, may: 5, june: 6,
  july: 7, august: 8, september: 9, october: 10, november: 11, december: 12,
  jan: 1, feb: 2, mar: 3, apr: 4, jun: 6, jul: 7, aug: 8, sep: 9, sept: 9, oct: 10, nov: 11, dec: 12,
};

function toNum(v: unknown, names: Record<string, number>): number | null {
  if (typeof v === "number") return v;
  if (typeof v === "string") {
    const named = names[v.toLowerCase().trim()];
    if (named !== undefined) return named;
    const parsed = Number(v);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
}

export function toWeekdayNum(v: unknown): number | null {
  return toNum(v, WEEKDAY_NUMS);
}

export function toMonthNum(v: unknown): number | null {
  return toNum(v, MONTH_NUMS);
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /projects/myhome/packages/editor && npx vitest run test/scheduleNames.test.ts`
Expected: all 8 tests PASS.

- [ ] **Step 5: Refactor `ScheduleEditor.svelte` to use the shared module**

In `packages/editor/src/lib/components/ScheduleEditor.svelte`, replace:

```ts
  // Donetick stores `days`/`months` as full English name strings (e.g. "Monday",
  // "March"), compared case-insensitively -- never ints -- so a chore imported
  // from Donetick needs the same name-to-number conversion the backend scheduler
  // already applies, or its selected days/months would show as unchecked here.
  const WEEKDAY_NUMS: Record<string, number> = {
    monday: 1, tuesday: 2, wednesday: 3, thursday: 4, friday: 5, saturday: 6, sunday: 7,
    mon: 1, tue: 2, wed: 3, thu: 4, fri: 5, sat: 6, sun: 7,
  };
  const MONTH_NUMS: Record<string, number> = {
    january: 1, february: 2, march: 3, april: 4, may: 5, june: 6,
    july: 7, august: 8, september: 9, october: 10, november: 11, december: 12,
    jan: 1, feb: 2, mar: 3, apr: 4, jun: 6, jul: 7, aug: 8, sep: 9, sept: 9, oct: 10, nov: 11, dec: 12,
  };
  function toNum(v: unknown, names: Record<string, number>): number | null {
    if (typeof v === "number") return v;
    if (typeof v === "string") {
      const named = names[v.toLowerCase().trim()];
      if (named !== undefined) return named;
      const parsed = Number(v);
      return Number.isFinite(parsed) ? parsed : null;
    }
    return null;
  }

  const initialDays = ((frequencyMetadata?.days as unknown[] | undefined) ?? [])
    .map((d) => toNum(d, WEEKDAY_NUMS))
    .filter((n): n is number => n !== null);
  const initialMonths = ((frequencyMetadata?.months as unknown[] | undefined) ?? [])
    .map((m) => toNum(m, MONTH_NUMS))
    .filter((n): n is number => n !== null);
```

with:

```ts
  const initialDays = ((frequencyMetadata?.days as unknown[] | undefined) ?? [])
    .map(toWeekdayNum)
    .filter((n): n is number => n !== null);
  const initialMonths = ((frequencyMetadata?.months as unknown[] | undefined) ?? [])
    .map(toMonthNum)
    .filter((n): n is number => n !== null);
```

And add the import at the top of the `<script>` block:

```ts
  import { toWeekdayNum, toMonthNum } from "../scheduleNames";
```

(right after the existing `import { _, locale } from "svelte-i18n";` line)

- [ ] **Step 6: Run `ScheduleEditor.test.ts` to confirm the refactor didn't break anything**

Run: `cd /projects/myhome/packages/editor && npx vitest run test/ScheduleEditor.test.ts`
Expected: all 9 existing tests still PASS (pure refactor, no behavior change).

- [ ] **Step 7: Write the failing test for the `scheduleLabel` plain-weekly string-day bug**

Append to the `describe("scheduleLabel", ...)` block in `packages/editor/test/choreStore.test.ts`:

```ts
  it("renders a plain days_of_the_week label from Donetick-shaped string day names", () => {
    // Donetick stores `days` as full English day-name strings (e.g. "Monday"),
    // not ints -- (`"Monday" - 1`) is NaN in JS, so this silently broke before
    // the shared toWeekdayNum normalizer was wired in here.
    const chore = makeChore({ frequencyType: "days_of_the_week", frequency: 1, frequencyMetadata: { days: ["Monday", "Wednesday"] } });
    expect(scheduleLabel(chore)).toBe("Weekly on Mon, Wed");
  });
```

- [ ] **Step 8: Run test to verify it fails**

Run: `cd /projects/myhome/packages/editor && npx vitest run test/choreStore.test.ts`
Expected: the new test FAILS (renders something like `"Weekly on undefined, undefined"` or similar).

- [ ] **Step 9: Implement the fix in `choreStore.svelte.ts`**

In `packages/editor/src/lib/choreStore.svelte.ts`, add the import at the top:

```ts
import { toWeekdayNum } from "./scheduleNames";
```

Then replace:

```ts
  if (ft === "days_of_the_week") {
    const dayKeys = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"];
    const days = ((meta as Record<string, number[]>)?.days ?? []).map((d) => t(`chores.schedule.dayAbbrev.${dayKeys[(d - 1) % 7]}`));
    return days.length ? t("chores.schedule.weeklyOn", { values: { days: days.join(", ") } }) : t("chores.schedule.weekly");
  }
```

with:

```ts
  if (ft === "days_of_the_week") {
    const dayKeys = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"];
    const dayNums = ((meta as Record<string, unknown[]>)?.days ?? []).map(toWeekdayNum).filter((d): d is number => d !== null);
    const days = dayNums.map((d) => t(`chores.schedule.dayAbbrev.${dayKeys[(d - 1) % 7]}`));
    return days.length ? t("chores.schedule.weeklyOn", { values: { days: days.join(", ") } }) : t("chores.schedule.weekly");
  }
```

(Task 7 will extend this same branch further for the Nth-weekday case — this step only fixes the pre-existing plain-weekly bug.)

- [ ] **Step 10: Run tests to verify they pass**

Run: `cd /projects/myhome/packages/editor && npx vitest run test/choreStore.test.ts`
Expected: all tests PASS, including the new one.

- [ ] **Step 11: Commit**

```bash
cd /projects/myhome
git add packages/editor/src/lib/scheduleNames.ts packages/editor/test/scheduleNames.test.ts \
        packages/editor/src/lib/components/ScheduleEditor.svelte \
        packages/editor/src/lib/choreStore.svelte.ts packages/editor/test/choreStore.test.ts
git commit -m "refactor(chores): extract shared weekday/month name normalizer, fix scheduleLabel string-day bug"
```

---

### Task 5: Frontend — i18n keys (English + French)

**Files:**
- Modify: `packages/editor/src/lib/locales/en.json`
- Modify: `packages/editor/src/lib/locales/fr.json`

**Interfaces:**
- Produces: `chores.schedule.occurrence1st/2nd/3rd/4th/Last`, `chores.schedule.nthWeekdayOfMonth/nthWeekdayOfQuarter`, `chores.schedule.nthWeekday`, `chores.scheduleEditor.categoryNthWeekday/period/periodMonth/periodQuarter/weekday/occurrence/selectAtLeastOneOccurrence` — used by Tasks 6, 7, 8.

- [ ] **Step 1: Edit `en.json`**

Find (inside `chores.schedule`, at the end):
```json
      "adaptive": "Adaptive",
      "adaptiveDays": "Adaptive (~{n} days)"
    },
```
Replace with:
```json
      "adaptive": "Adaptive",
      "adaptiveDays": "Adaptive (~{n} days)",
      "occurrence1st": "1st",
      "occurrence2nd": "2nd",
      "occurrence3rd": "3rd",
      "occurrence4th": "4th",
      "occurrenceLast": "Last",
      "nthWeekdayOfMonth": "{occurrence} {weekday} of the month",
      "nthWeekdayOfQuarter": "{occurrence} {weekday} of the quarter",
      "nthWeekday": "Nth weekday"
    },
```

Find (inside `chores.scheduleEditor`, at the end):
```json
      "periodDaysHint": "Adjusts automatically after each completion",
      "selectAtLeastOneDay": "Select at least one day"
    },
```
Replace with:
```json
      "periodDaysHint": "Adjusts automatically after each completion",
      "selectAtLeastOneDay": "Select at least one day",
      "categoryNthWeekday": "Nth weekday of month/quarter",
      "period": "Period",
      "periodMonth": "Month",
      "periodQuarter": "Quarter",
      "weekday": "Weekday",
      "occurrence": "Occurrence",
      "selectAtLeastOneOccurrence": "Select at least one occurrence"
    },
```

- [ ] **Step 2: Edit `fr.json`**

Find (inside `chores.schedule`, at the end):
```json
      "adaptive": "Adaptatif",
      "adaptiveDays": "Adaptatif (~{n} jours)"
    },
```
Replace with:
```json
      "adaptive": "Adaptatif",
      "adaptiveDays": "Adaptatif (~{n} jours)",
      "occurrence1st": "1er",
      "occurrence2nd": "2e",
      "occurrence3rd": "3e",
      "occurrence4th": "4e",
      "occurrenceLast": "Dernier",
      "nthWeekdayOfMonth": "{occurrence} {weekday} du mois",
      "nthWeekdayOfQuarter": "{occurrence} {weekday} du trimestre",
      "nthWeekday": "N-ième jour"
    },
```

Find (inside `chores.scheduleEditor`, at the end):
```json
      "periodDaysHint": "S'ajuste automatiquement après chaque réalisation",
      "selectAtLeastOneDay": "Sélectionnez au moins un jour"
    },
```
Replace with:
```json
      "periodDaysHint": "S'ajuste automatiquement après chaque réalisation",
      "selectAtLeastOneDay": "Sélectionnez au moins un jour",
      "categoryNthWeekday": "Nième jour de la semaine (mois/trimestre)",
      "period": "Période",
      "periodMonth": "Mois",
      "periodQuarter": "Trimestre",
      "weekday": "Jour de la semaine",
      "occurrence": "Occurrence",
      "selectAtLeastOneOccurrence": "Sélectionnez au moins une occurrence"
    },
```

- [ ] **Step 3: Verify both files are valid JSON**

Run: `cd /projects/myhome/packages/editor && node -e "JSON.parse(require('fs').readFileSync('src/lib/locales/en.json'))" && node -e "JSON.parse(require('fs').readFileSync('src/lib/locales/fr.json'))" && echo OK`
Expected: prints `OK`.

Run: `cd /projects/myhome/packages/editor && npx vitest run`
Expected: all existing tests still PASS (a JSON syntax error here would fail every test — `test/setup.ts` loads both locale files at startup).

- [ ] **Step 4: Commit**

```bash
cd /projects/myhome
git add packages/editor/src/lib/locales/en.json packages/editor/src/lib/locales/fr.json
git commit -m "feat(chores): add i18n keys for Nth-weekday-of-period scheduling"
```

---

### Task 6: Frontend — `ScheduleEditor.svelte` new "Nth weekday" category

**Files:**
- Modify: `packages/editor/src/lib/components/ScheduleEditor.svelte`
- Test: `packages/editor/test/ScheduleEditor.test.ts`

**Interfaces:**
- Consumes: `chores.scheduleEditor.categoryNthWeekday/period/periodMonth/periodQuarter/weekday/occurrence/selectAtLeastOneOccurrence`, `chores.schedule.occurrence1st/2nd/3rd/4th/Last` (Task 5); `initialDays` (already computed in this file, reused for restoring the weekday select).

- [ ] **Step 1: Write the failing tests**

Append to `packages/editor/test/ScheduleEditor.test.ts`:

```ts
  it("switching to Nth-weekday defaults to week_of_month, Monday, and is invalid until an occurrence is picked", () => {
    const { target, comp } = mountWrapper();
    const select = target.querySelector("#se-category") as HTMLSelectElement;
    select.value = "nth_weekday";
    select.dispatchEvent(new Event("change", { bubbles: true }));
    flushSync();
    const state = readState(target);
    expect(state.frequencyType).toBe("days_of_the_week");
    expect(state.frequencyMetadata).toEqual({ days: [1], weekPattern: "week_of_month", occurrences: [] });
    expect(state.valid).toBe(false);
    unmount(comp);
  });

  it("picking an occurrence and switching to Quarter for Nth-weekday sets the right metadata", () => {
    const { target, comp } = mountWrapper();
    const select = target.querySelector("#se-category") as HTMLSelectElement;
    select.value = "nth_weekday";
    select.dispatchEvent(new Event("change", { bubbles: true }));
    flushSync();

    const quarterBtn = Array.from(target.querySelectorAll(".period-toggle .day-toggle")).find((b) => b.textContent === "Quarter") as HTMLButtonElement;
    quarterBtn.click();
    flushSync();

    const weekdaySelect = target.querySelector("#se-nth-weekday") as HTMLSelectElement;
    weekdaySelect.value = "5"; // Friday
    weekdaySelect.dispatchEvent(new Event("change", { bubbles: true }));
    flushSync();

    const lastBtn = Array.from(target.querySelectorAll(".occurrence-toggles .day-toggle")).find((b) => b.textContent === "Last") as HTMLButtonElement;
    lastBtn.click();
    flushSync();

    const state = readState(target);
    expect(state.frequencyType).toBe("days_of_the_week");
    expect(state.frequencyMetadata).toEqual({ days: [5], weekPattern: "week_of_quarter", occurrences: [-1] });
    expect(state.periodDays).toBe(91);
    expect(state.valid).toBe(true);
    unmount(comp);
  });

  it("restores an existing Donetick-imported Nth-weekday chore (string day name) on mount", () => {
    const { target, comp } = mountWrapper({
      initialFrequencyType: "days_of_the_week", initialFrequency: 1,
      initialFrequencyMetadata: { days: ["Tuesday"], weekPattern: "week_of_month", occurrences: [2] },
    });
    const state = readState(target);
    expect(state.frequencyType).toBe("days_of_the_week");
    const weekdaySelect = target.querySelector("#se-nth-weekday") as HTMLSelectElement;
    expect(weekdaySelect.value).toBe("2");
    const active = Array.from(target.querySelectorAll(".occurrence-toggles .day-toggle.active")).map((b) => b.textContent);
    expect(active).toEqual(["2nd"]);
    unmount(comp);
  });
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /projects/myhome/packages/editor && npx vitest run test/ScheduleEditor.test.ts`
Expected: the three new tests FAIL — `"nth_weekday"` isn't a valid `cat` value yet and none of the new controls (`#se-nth-weekday`, `.period-toggle`, `.occurrence-toggles`) exist.

- [ ] **Step 3: Implement**

In `packages/editor/src/lib/components/ScheduleEditor.svelte`:

3a. Update the `Category` type:

```ts
  type Category = "interval" | "daily" | "days_of_the_week" | "day_of_the_month" | "nth_weekday" | "yearly" | "adaptive";
```

3b. Update `categoryFor` to also check `frequencyMetadata.weekPattern` (so a plain `days_of_the_week` chore and an Nth-weekday one are told apart), and change its call site to pass `frequencyMetadata`:

```ts
  function categoryFor(ft: string, meta: Record<string, unknown>): Category {
    if (ft === "days_of_the_week" && (meta?.weekPattern === "week_of_month" || meta?.weekPattern === "week_of_quarter")) return "nth_weekday";
    if (ft === "days_of_the_week") return "days_of_the_week";
    if (ft === "day_of_the_month") return "day_of_the_month";
    if (ft === "yearly") return "yearly";
    if (ft === "adaptive") return "adaptive";
    if (ft === "daily") return "daily";
    return "interval";
  }
```

Find:
```ts
  let cat = $state<Category>(categoryFor(frequencyType));
```
Replace with:
```ts
  let cat = $state<Category>(categoryFor(frequencyType, frequencyMetadata));
```

3c. Add new state, right after the existing `adaptivePeriod` line:

```ts
  let nthPeriod = $state<"week_of_month" | "week_of_quarter">(
    (frequencyMetadata?.weekPattern as "week_of_month" | "week_of_quarter" | undefined) ?? "week_of_month"
  );
  let nthWeekday = $state<number>(initialDays[0] ?? 1);
  let nthOccurrences = $state<number[]>(
    cat === "nth_weekday" ? ((frequencyMetadata?.occurrences as number[] | undefined) ?? []) : []
  );
```

3d. Add a `toggleOccurrence` function, right after `toggleMonth`:

```ts
  function toggleOccurrence(o: number): void {
    nthOccurrences = nthOccurrences.includes(o) ? nthOccurrences.filter((x) => x !== o) : [...nthOccurrences, o].sort((a, b) => a - b);
  }
```

3e. Add a new branch to the `$effect` block, right after the `day_of_the_month` branch and before the `yearly` branch:

```ts
    } else if (cat === "nth_weekday") {
      frequencyType = "days_of_the_week";
      frequency = 1;
      frequencyMetadata = { days: [nthWeekday], weekPattern: nthPeriod, occurrences: nthOccurrences };
      periodDays = nthPeriod === "week_of_month" ? 30 : 91;
      valid = nthOccurrences.length > 0;
    } else if (cat === "yearly") {
```

3f. Add the new dropdown option, right after the "Monthly on a specific day" option:

```svelte
      <option value="day_of_the_month">{$_('chores.scheduleEditor.categoryMonthly')}</option>
      <option value="nth_weekday">{$_('chores.scheduleEditor.categoryNthWeekday')}</option>
      <option value="yearly">{$_('chores.scheduleEditor.categoryYearly')}</option>
```

3g. Add the new UI section, right after the `day_of_the_month` `{:else if}` block's closing `{/if}` and before `{:else if cat === "adaptive"}`:

```svelte
  {:else if cat === "nth_weekday"}
    <div class="field period-toggle">
      <button type="button" class="day-toggle" class:active={nthPeriod === "week_of_month"} onclick={() => (nthPeriod = "week_of_month")}>{$_('chores.scheduleEditor.periodMonth')}</button>
      <button type="button" class="day-toggle" class:active={nthPeriod === "week_of_quarter"} onclick={() => (nthPeriod = "week_of_quarter")}>{$_('chores.scheduleEditor.periodQuarter')}</button>
    </div>
    <div class="field">
      <label for="se-nth-weekday">{$_('chores.scheduleEditor.weekday')}</label>
      <select id="se-nth-weekday" class="native-input" bind:value={nthWeekday}>
        {#each DAY_KEYS as key, i (key)}
          <option value={i + 1}>{$_(`chores.schedule.dayAbbrev.${key}`)}</option>
        {/each}
      </select>
    </div>
    <div class="field">
      <span class="field-label">{$_('chores.scheduleEditor.occurrence')}</span>
      <div class="day-toggles occurrence-toggles">
        {#each [1, 2, 3, 4, -1] as o (o)}
          <button
            type="button"
            class="day-toggle"
            class:active={nthOccurrences.includes(o)}
            onclick={() => toggleOccurrence(o)}
          >{o === -1 ? $_('chores.schedule.occurrenceLast') : $_(`chores.schedule.occurrence${["1st", "2nd", "3rd", "4th"][o - 1]}`)}</button>
        {/each}
      </div>
      {#if nthOccurrences.length === 0}<div class="hint-error">{$_('chores.scheduleEditor.selectAtLeastOneOccurrence')}</div>{/if}
    </div>
```

3h. Add one small style rule (the existing `.field label` selector doesn't match a bare `<span>`):

```css
  .field-label { font-size: 11px; color: var(--text-muted); }
  .period-toggle { flex-direction: row; gap: 8px; }
```

(add these two lines right after the existing `.field label { ... }` rule)

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /projects/myhome/packages/editor && npx vitest run test/ScheduleEditor.test.ts`
Expected: all 12 tests PASS.

- [ ] **Step 5: Typecheck**

Run: `cd /projects/myhome/packages/editor && npx svelte-check --tsconfig ./tsconfig.json 2>&1 | tail -20`
Expected: no new type errors introduced by this change.

- [ ] **Step 6: Commit**

```bash
cd /projects/myhome
git add packages/editor/src/lib/components/ScheduleEditor.svelte packages/editor/test/ScheduleEditor.test.ts
git commit -m "feat(chores): add Nth-weekday-of-period category to ScheduleEditor"
```

---

### Task 7: Frontend — `scheduleLabel` renders Nth-weekday schedules

**Files:**
- Modify: `packages/editor/src/lib/choreStore.svelte.ts`
- Test: `packages/editor/test/choreStore.test.ts`

**Interfaces:**
- Consumes: `chores.schedule.occurrence1st/2nd/3rd/4th/Last`, `chores.schedule.nthWeekdayOfMonth/nthWeekdayOfQuarter` (Task 5); `toWeekdayNum` (Task 4, already imported into this file).

- [ ] **Step 1: Write the failing tests**

Append to the `describe("scheduleLabel", ...)` block in `packages/editor/test/choreStore.test.ts`:

```ts
  it("renders a 2nd-Tuesday-of-the-month schedule", () => {
    const chore = makeChore({ frequencyType: "days_of_the_week", frequency: 1, frequencyMetadata: { days: [2], weekPattern: "week_of_month", occurrences: [2] } });
    expect(scheduleLabel(chore)).toBe("2nd Tue of the month");
  });

  it("renders a last-Friday-of-the-quarter schedule", () => {
    const chore = makeChore({ frequencyType: "days_of_the_week", frequency: 1, frequencyMetadata: { days: [5], weekPattern: "week_of_quarter", occurrences: [-1] } });
    expect(scheduleLabel(chore)).toBe("Last Fri of the quarter");
  });

  it("renders a Donetick-imported Nth-weekday schedule with a string day name", () => {
    const chore = makeChore({ frequencyType: "days_of_the_week", frequency: 1, frequencyMetadata: { days: ["Tuesday"], weekPattern: "week_of_month", occurrences: [2] } });
    expect(scheduleLabel(chore)).toBe("2nd Tue of the month");
  });
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /projects/myhome/packages/editor && npx vitest run test/choreStore.test.ts`
Expected: the three new tests FAIL (currently renders as if plain weekly-on-Tuesday/Friday, ignoring `weekPattern`/`occurrences`).

- [ ] **Step 3: Implement**

In `packages/editor/src/lib/choreStore.svelte.ts`, replace the `days_of_the_week` branch (as left by Task 4) with:

```ts
  if (ft === "days_of_the_week") {
    const dayKeys = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"];
    const weekPattern = (meta as Record<string, string>)?.weekPattern;
    const dayNums = ((meta as Record<string, unknown[]>)?.days ?? []).map(toWeekdayNum).filter((d): d is number => d !== null);
    if (weekPattern === "week_of_month" || weekPattern === "week_of_quarter") {
      const occurrences = (meta as Record<string, number[]>)?.occurrences ?? [];
      const occurrenceKey = occurrences.includes(-1) ? "occurrenceLast"
        : occurrences.includes(1) ? "occurrence1st"
        : occurrences.includes(2) ? "occurrence2nd"
        : occurrences.includes(3) ? "occurrence3rd"
        : "occurrence4th";
      const weekdayKey = dayKeys[(((dayNums[0] ?? 1) - 1) % 7 + 7) % 7];
      const template = weekPattern === "week_of_month" ? "chores.schedule.nthWeekdayOfMonth" : "chores.schedule.nthWeekdayOfQuarter";
      return t(template, { values: { occurrence: t(`chores.schedule.${occurrenceKey}`), weekday: t(`chores.schedule.dayAbbrev.${weekdayKey}`) } });
    }
    const days = dayNums.map((d) => t(`chores.schedule.dayAbbrev.${dayKeys[(d - 1) % 7]}`));
    return days.length ? t("chores.schedule.weeklyOn", { values: { days: days.join(", ") } }) : t("chores.schedule.weekly");
  }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /projects/myhome/packages/editor && npx vitest run test/choreStore.test.ts`
Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
cd /projects/myhome
git add packages/editor/src/lib/choreStore.svelte.ts packages/editor/test/choreStore.test.ts
git commit -m "feat(chores): render Nth-weekday-of-period schedules in scheduleLabel"
```

---

### Task 8: Frontend — `ChoresPage.svelte` schedule filter recognizes Nth-weekday

**Files:**
- Modify: `packages/editor/src/lib/components/ChoresPage.svelte`

**Interfaces:**
- Consumes: `chores.schedule.nthWeekday` (Task 5).

- [ ] **Step 1: Implement**

Find the `scheduleCategory` function:

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

Replace with:

```ts
  function scheduleCategory(chore: Chore): string {
    const { frequencyType: ft, frequency: n, frequencyMetadata: meta } = chore;
    const unit = (meta as Record<string, string>)?.unit ?? "days";
    const weekPattern = (meta as Record<string, string>)?.weekPattern;
    if (ft === "daily") return "daily";
    if (ft === "adaptive") return "adaptive";
    if (ft === "days_of_the_week" && (weekPattern === "week_of_month" || weekPattern === "week_of_quarter")) return "nth_weekday";
    if (ft === "days_of_the_week" || ft === "weekly") return "weekly";
    if (ft === "day_of_the_month" || ft === "monthly") return "monthly";
    if (ft === "yearly") return "yearly";
    if (ft === "interval") {
```

Find the schedule filter `<select>`:

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

Replace with:

```svelte
      <select class="native-input" bind:value={scheduleFilter}>
        <option value="">{$_('chores.page.allSchedules')}</option>
        <option value="daily">{$_('chores.schedule.daily')}</option>
        <option value="weekly">{$_('chores.schedule.weekly')}</option>
        <option value="monthly">{$_('chores.schedule.monthly')}</option>
        <option value="nth_weekday">{$_('chores.schedule.nthWeekday')}</option>
        <option value="yearly">{$_('chores.schedule.yearly')}</option>
        <option value="adaptive">{$_('chores.schedule.adaptive')}</option>
      </select>
```

- [ ] **Step 2: Typecheck**

Run: `cd /projects/myhome/packages/editor && npx svelte-check --tsconfig ./tsconfig.json 2>&1 | tail -20`
Expected: no new errors (this file has no dedicated component-render test, per the established project convention — verified instead by Task 10's manual browser check).

- [ ] **Step 3: Commit**

```bash
cd /projects/myhome
git add packages/editor/src/lib/components/ChoresPage.svelte
git commit -m "feat(chores): recognize Nth-weekday-of-period chores in the schedule filter"
```

---

### Task 9: Frontend — natural-language quick-add for Nth-weekday phrases

**Files:**
- Modify: `packages/editor/src/lib/scheduleParser.ts`
- Test: `packages/editor/test/scheduleParser.test.ts`

**Interfaces:**
- Produces: extends `parseScheduleText` (existing signature/contract unchanged) to also recognize Nth-weekday-of-period phrases.

- [ ] **Step 1: Write the failing tests**

Append to `packages/editor/test/scheduleParser.test.ts`, inside the existing `describe("parseScheduleText (English)", ...)` block:

```ts
  it("parses an Nth weekday of the month", () => {
    const result = parseScheduleText("Water the lawn every 2nd Tuesday of the month", "en");
    expect(result).toEqual({
      name: "Water the lawn",
      schedule: { frequencyType: "days_of_the_week", frequency: 1, frequencyMetadata: { days: [2], weekPattern: "week_of_month", occurrences: [2] } },
    });
  });

  it("parses the last weekday of every month", () => {
    const result = parseScheduleText("Pay rent the last Friday of every month", "en");
    expect(result).toEqual({
      name: "Pay rent",
      schedule: { frequencyType: "days_of_the_week", frequency: 1, frequencyMetadata: { days: [5], weekPattern: "week_of_month", occurrences: [-1] } },
    });
  });

  it("parses an Nth weekday of the quarter", () => {
    const result = parseScheduleText("Rotate emergency supplies every 3rd Monday of the quarter", "en");
    expect(result).toEqual({
      name: "Rotate emergency supplies",
      schedule: { frequencyType: "days_of_the_week", frequency: 1, frequencyMetadata: { days: [1], weekPattern: "week_of_quarter", occurrences: [3] } },
    });
  });
```

Append to the existing `describe("parseScheduleText (French)", ...)` block:

```ts
  it("parses an Nth weekday of the month", () => {
    const result = parseScheduleText("Nettoyer le garage le 2e mardi du mois", "fr");
    expect(result).toEqual({
      name: "Nettoyer le garage",
      schedule: { frequencyType: "days_of_the_week", frequency: 1, frequencyMetadata: { days: [2], weekPattern: "week_of_month", occurrences: [2] } },
    });
  });

  it("parses the last weekday of every month", () => {
    const result = parseScheduleText("Payer le loyer le dernier vendredi de chaque mois", "fr");
    expect(result).toEqual({
      name: "Payer le loyer",
      schedule: { frequencyType: "days_of_the_week", frequency: 1, frequencyMetadata: { days: [5], weekPattern: "week_of_month", occurrences: [-1] } },
    });
  });

  it("parses an Nth weekday of the quarter", () => {
    const result = parseScheduleText("Vérifier l'extincteur le 3e lundi du trimestre", "fr");
    expect(result).toEqual({
      name: "Vérifier l'extincteur",
      schedule: { frequencyType: "days_of_the_week", frequency: 1, frequencyMetadata: { days: [1], weekPattern: "week_of_quarter", occurrences: [3] } },
    });
  });
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /projects/myhome/packages/editor && npx vitest run test/scheduleParser.test.ts`
Expected: the six new tests FAIL — no Nth-weekday pattern exists yet, so these currently fall through to the plain weekly-on-day pattern or return a different shape.

- [ ] **Step 3: Implement**

In `packages/editor/src/lib/scheduleParser.ts`, add a new constant right after `WEEKDAY_NUM`:

```ts
const ORDINAL_NUM: Record<string, number> = {
  "1st": 1, first: 1, "1er": 1, premier: 1, première: 1, premiere: 1,
  "2nd": 2, second: 2, seconde: 2, "2e": 2, deuxième: 2, deuxieme: 2,
  "3rd": 3, third: 3, "3e": 3, troisième: 3, troisieme: 3,
  "4th": 4, fourth: 4, "4e": 4, quatrième: 4, quatrieme: 4,
  last: -1, dernier: -1, dernière: -1, derniere: -1,
};
```

Then, inside `parseScheduleText`, insert this new check right after the existing `weekdayMatch` block (i.e. after its closing `}` and before the `domRe`/`domMatch` block), reusing the already-computed `dayNames` variable from that same block:

```ts
  const ordinalWords = Object.keys(ORDINAL_NUM).join("|");
  const periodWords = loc === "fr" ? "mois|trimestre" : "month|quarter";
  const nthWeekdayRe = loc === "fr"
    ? new RegExp(`\\ble\\s+(${ordinalWords})\\s+(${dayNames})\\s+(?:du|de\\s+chaque)\\s+(${periodWords})\\b`, "i")
    : new RegExp(`\\b(?:every|the)\\s+(${ordinalWords})\\s+(${dayNames})\\s+of\\s+(?:the|every)\\s+(${periodWords})\\b`, "i");
  const nthWeekdayMatch = trimmed.match(nthWeekdayRe);
  if (nthWeekdayMatch) {
    const occurrence = ORDINAL_NUM[nthWeekdayMatch[1].toLowerCase()];
    const day = normalizeDayToken(nthWeekdayMatch[2]);
    const periodWord = nthWeekdayMatch[3].toLowerCase();
    const weekPattern = periodWord === "month" || periodWord === "mois" ? "week_of_month" : "week_of_quarter";
    if (occurrence !== undefined && day !== null) {
      return {
        name: stripMatch(trimmed, nthWeekdayMatch),
        schedule: { frequencyType: "days_of_the_week", frequency: 1, frequencyMetadata: { days: [day], weekPattern, occurrences: [occurrence] } },
      };
    }
  }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /projects/myhome/packages/editor && npx vitest run test/scheduleParser.test.ts`
Expected: all tests PASS (existing + 6 new).

- [ ] **Step 5: Run the full frontend suite**

Run: `cd /projects/myhome/packages/editor && npx vitest run`
Expected: all tests PASS, no regressions from the `dayNames` reuse or the new regex ordering.

- [ ] **Step 6: Commit**

```bash
cd /projects/myhome
git add packages/editor/src/lib/scheduleParser.ts packages/editor/test/scheduleParser.test.ts
git commit -m "feat(chores): parse EN/FR Nth-weekday-of-period quick-add phrases"
```

---

### Task 10: Full-suite verification + manual browser check

**Files:** none (verification only)

- [ ] **Step 1: Run the full backend suite**

Run: `cd /projects/myhome && pytest packages/backend -q`
Expected: all tests PASS.

- [ ] **Step 2: Run the full frontend suite**

Run: `cd /projects/myhome/packages/editor && npx vitest run`
Expected: all tests PASS.

- [ ] **Step 3: Manual browser check**

Use the `run` skill (or start the dev server manually per this project's existing convention) and, in the running app:
1. Create a chore with category "Nth weekday of month/quarter" → Month → Tuesday → 2nd. Confirm the chore list shows "2nd Tue of the month" and the computed next-due date is a Tuesday.
2. Edit that same chore, confirm the picker restores Month/Tuesday/2nd correctly (not reset to defaults).
3. Create a second chore → Quarter → Friday → Last. Confirm the label reads "Last Fri of the quarter" and the due date is a Friday.
4. Use the quick-add box with "Change the air filter every 2nd Tuesday of the month" (English) and confirm it pre-fills the picker correctly; repeat with a French phrase after switching the app language to French.
5. Filter the chore list by the new "Nth weekday" schedule filter option and confirm both created chores show up.

- [ ] **Step 4: Report results**

If all manual checks pass, proceed to finishing the branch (see below). If anything looks wrong, treat it as a new bug — return to Phase 1 of systematic-debugging rather than patching blindly.

---

### Task 11: Finish the branch and open a PR

**Files:** none (branch/PR workflow only)

- [ ] **Step 1: Confirm full test suites are green**

Run: `cd /projects/myhome && pytest packages/backend -q && cd packages/editor && npx vitest run`
Expected: all PASS (repeat of Task 10 Steps 1-2, as a final gate right before opening the PR).

- [ ] **Step 2: Push the branch and open a PR**

```bash
cd /projects/myhome
git push -u origin HEAD
gh pr create --title "Fix Donetick month-restriction scheduling bug; add Nth-weekday-of-month/quarter recurrence" --body "$(cat <<'EOF'
## Summary
- Fixes an existing bug: Donetick stores day_of_the_month month restrictions (and days_of_the_week days) as full English name strings, not ints, so an imported chore restricted to specific months silently ignored that restriction and scheduled ~1 year out. Added `to_month_num`/shared frontend normalizers to fix both the backend scheduling computation and the edit-modal display.
- Adds a new recurrence type: "Nth weekday of month/quarter" (e.g. "2nd Tuesday of every month", "last Friday of every quarter"), matching a Donetick pattern that wasn't modeled at all before — found while auditing the import for full scheduling-feature parity. Reuses the existing `days_of_the_week` frequencyType with new `weekPattern`/`occurrences` metadata (no new DB columns), available via the manual ScheduleEditor picker, Donetick import, and the EN/FR quick-add box.

## Test plan
- [x] `pytest packages/backend` — full suite green
- [x] `npx vitest run` (editor package) — full suite green
- [x] Manual browser check: create/edit an Nth-weekday chore in both Month and Quarter modes, confirm label/filter/next-due date; quick-add in both languages

🤖 Generated with [Claude Code](https://claude.com/claude-code)

https://claude.ai/code/session_0159oDBXbbksGqrX5XxA2yPx
EOF
)"
```

- [ ] **Step 3: Report the PR URL back to the user**
