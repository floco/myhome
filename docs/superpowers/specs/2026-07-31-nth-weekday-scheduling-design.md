# Chore scheduling: Nth-weekday-of-month/quarter recurrence

## Overview

Donetick supports a "Nth weekday of period" recurrence pattern (e.g. "2nd Tuesday of every month", "last Friday of every quarter"), implemented internally as a variant of its `days_of_the_week` frequency type discriminated by a `weekPattern` + `occurrences` metadata pair. myhome's scheduler and Donetick import currently don't model this at all — such a chore imports as `frequencyType: "days_of_the_week"` and gets scheduled as plain "every week on this day," which is wrong.

This spec closely follows the pattern established by `docs/superpowers/specs/2026-07-31-chore-scheduling-design.md` (rich recurrence types, reusing the existing engine, no new DB columns) and by the just-fixed month-name-string bug (`to_month_num`/`to_weekday_num` normalization) — this is the next gap in that same "Donetick parity" effort, found while checking whether the import fully reflects Donetick's newer scheduling features.

**Trigger:** while fixing an unrelated bug (imported `day_of_the_month` chores ignoring their month restriction, because Donetick sends month names as strings like `"March"` and myhome's scheduler compared them against ints), a review of Donetick's own scheduler source (`internal/chore/scheduler.go`) turned up this second, larger gap: Donetick's `week_of_month` / `week_of_quarter` patterns aren't modeled at all.

**Out of scope:** time-of-day (unchanged elsewhere in this app); Donetick's legacy `weekNumbers` metadata field (superseded by `occurrences` upstream per their own migration history — only `occurrences` needs support); multi-day combinations in myhome's own manual UI (the picker is single-weekday; multi-day only arises from Donetick imports, and the backend already handles that generally).

## Data model

No new columns. Reuses `Chore.frequencyType` / `frequency` / `frequencyMetadata`, matching the existing reuse-first pattern.

- `frequencyType` stays `"days_of_the_week"` — this is what Donetick itself uses for both plain weekly-on-days and Nth-weekday patterns; there is no new top-level type.
- New `frequencyMetadata` keys, stored **exactly** as Donetick's own JSON shape (no import-time translation, mirroring how `days`/`months` are already stored verbatim and normalized only at read-time):
  - `weekPattern`: absent or `"every_week"` (today's plain-weekly behavior, completely unchanged) | `"week_of_month"` | `"week_of_quarter"`
  - `occurrences`: `number[]`, where `1`–`4` mean the 1st–4th occurrence of the weekday in the period and `-1` means "last" (mirrors Donetick's own `Occurrences []*int` encoding, where `-1` = last)
- `days` (existing key) is reused for the weekday(s), already normalized via the existing `to_weekday_num` (handles both ints and Donetick's capitalized day-name strings).
- `frequency` is unused for this type (set to `1`), consistent with other categorical types (`daily`, `yearly`, `adaptive`).

## Backend changes

### `chore_scheduling.py`

New helpers (ported from Donetick's own algorithm, verified against `internal/chore/scheduler.go`):

```python
def nth_weekday_occurrence(date: datetime, period_start: datetime) -> int:
    """1-based count of how many times `date`'s weekday has occurred from
    `period_start` (inclusive) through `date` (inclusive)."""

def is_last_weekday_in_month(date: datetime) -> bool:
    """True if `date + 7 days` falls in the next calendar month."""

def is_last_weekday_in_quarter(date: datetime) -> bool:
    """True if `date + 7 days` falls in the next calendar quarter."""

def quarter_start(date: datetime) -> datetime:
    """First day of the quarter (Jan/Apr/Jul/Oct 1) containing `date`."""
```

`next_due_from_schedule`'s existing `days_of_the_week` branch gets a new conditional path, checked first:

```python
if ft == "days_of_the_week":
    week_pattern = meta.get("weekPattern")
    if week_pattern in ("week_of_month", "week_of_quarter"):
        days = {to_weekday_num(d) - 1 for d in (meta.get("days") or [])}  # 0=Mon..6=Sun
        occurrences = {int(o) for o in (meta.get("occurrences") or [])}
        wants_last = -1 in occurrences
        is_monthly = week_pattern == "week_of_month"
        candidate = from_dt + timedelta(days=1)
        for _ in range(730):  # Donetick's own 2-year safety cap
            if candidate.weekday() in days:
                period_start = candidate.replace(day=1) if is_monthly else quarter_start(candidate)
                occurrence = nth_weekday_occurrence(candidate, period_start)
                is_last = is_last_weekday_in_month(candidate) if is_monthly else is_last_weekday_in_quarter(candidate)
                if occurrence in occurrences or (wants_last and is_last):
                    return candidate
            candidate += timedelta(days=1)
        return candidate  # unreachable in practice; mirrors Donetick's own fallback shape
    # ...existing plain-weekly logic, unchanged...
```

(`days` values compared 0-based Mon=0..Sun=6 to match Python's `datetime.weekday()`; `to_weekday_num` already returns 1-based Mon=1..Sun=7, so subtract 1 — same conversion the existing plain-weekly branch already does.)

### `routes/chores.py`

- `_period_days`: add a case for `"days_of_the_week"` so the progress-bar estimate is reasonable for all its sub-patterns instead of falling through to the generic `30.0` default: `7.0` for plain weekly (no `weekPattern`, or `"every_week"`), `30.0` for `week_of_month`, `91.0` for `week_of_quarter`. (Purely an estimate used for the progress bar — not schedule-affecting — but touched by this same code path, so worth correcting while here.)
- Import logic itself needs no changes — `frequencyMetadata=rc.get("frequencyMetadata") or {}` already copies `weekPattern`/`occurrences` verbatim, same as `days`/`months`.

## Frontend changes

### `ScheduleEditor.svelte`

- New `Category` value `"nth_weekday"`, added to the picker's `<select>` between "Monthly on a specific day" and "Yearly".
- `categoryFor(ft, meta)` — signature grows a second parameter so it can distinguish this from plain `days_of_the_week` by checking `meta?.weekPattern`.
- Sub-controls when this category is selected:
  - Period toggle (Month / Quarter radio or two-button toggle, styled like the existing controls) → sets `weekPattern` to `"week_of_month"` / `"week_of_quarter"`.
  - Weekday `<select>` (single-select, matching the approved mockup) → `days: [selectedDay]`.
  - Occurrence checkboxes: 1st / 2nd / 3rd / 4th / Last → `occurrences` (`-1` for Last).
- Validation: at least one occurrence must be selected.
- Restoring an existing chore (including Donetick-imported ones with multiple days/occurrences) shows the first day in the weekday select and all matching occurrence checkboxes checked; saving after any interaction will collapse it to myhome's single-day shape — same acceptable "editing normalizes to the simpler shape" behavior the app already has elsewhere (e.g. `day_of_the_month`'s months restriction).

### `choreStore.svelte.ts` (`scheduleLabel`)

- New branch: when `frequencyType === "days_of_the_week"` and `weekPattern` is set, render e.g. "2nd Tuesday of the month" / "Last Friday of the quarter" (using the first day/occurrence pair if there are several — a compact label can't enumerate an open-ended imported set).
- New i18n keys (EN + FR) for the ordinal words (1st–4th, Last) and the "{occurrence} {weekday} of the month/quarter" template.

### `ChoresPage.svelte`

- `scheduleCategory()`: new `"nth_weekday"` bucket, checked before the existing `days_of_the_week`/`weekly` case.
- Schedule filter `<select>`: new `<option value="nth_weekday">` alongside daily/weekly/monthly/yearly/adaptive.

### `scheduleParser.ts`

New EN/FR patterns, checked before the existing plain-weekly-on-days pattern (since "every 2nd Tuesday" would otherwise partially match the plain weekday pattern):

- EN: `"every 2nd Tuesday of the month"`, `"the last Friday of every month"`, `"every 3rd Monday of the quarter"`
- FR: `"le 2e mardi du mois"`, `"le dernier vendredi de chaque mois"`, `"le 3e lundi du trimestre"`

Ordinal-word → occurrence-number mapping (`1st`/`1er` → `1`, `2nd`/`2e` → `2`, `3rd`/`3e` → `3`, `4th`/`4e` → `4`, `last`/`dernier`/`dernière` → `-1`); `"month"`/`"mois"` → `week_of_month`, `"quarter"`/`"trimestre"` → `week_of_quarter`. Falls through to existing patterns when nothing matches, same as today — no change to the no-match `null` contract.

## Testing plan

- **Backend** (`pytest packages/backend`):
  - `chore_scheduling`: `nth_weekday_occurrence` and the last-occurrence boundary checks for both month and quarter (including a December→January and Q4→Q1 year-boundary case); `next_due_from_schedule` cases mirroring Donetick's own semantics ("2nd Tuesday of the month", "last Friday of the quarter").
  - `routes/chores.py`: a Donetick-import-shaped test — string weekday name (`"Tuesday"`) + `weekPattern`/`occurrences` copied straight through, verifying the computed due date lands on the correct Nth occurrence (this is the direct regression test for the gap that motivated this spec); `_period_days` estimates for all three `days_of_the_week` sub-cases.
- **Frontend** (`vitest`, editor package):
  - `ScheduleEditor.test.ts`: selecting the new category, period toggle, weekday select, occurrence checkboxes, validation (no occurrence selected), and restoring an existing (including Donetick-string-shaped) chore.
  - `scheduleParser.test.ts`: table-driven EN + FR phrases for both month and quarter variants, plus the "last" variant.
  - `choreStore.test.ts`: new `scheduleLabel` branch.
- **Manual browser check** (per project convention — no Svelte component-render test infra beyond the `mount()`-based pattern already in use): create one "2nd Tuesday of the month" chore and one "last Friday of the quarter" chore, confirm the label, filter dropdown, and computed next-due date all look right; edit an imported-shaped chore and confirm the picker restores correctly.
