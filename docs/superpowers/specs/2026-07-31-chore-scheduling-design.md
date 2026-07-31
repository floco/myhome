# Chore scheduling: rich recurrence, natural-language quick-add, adaptive scheduling

## Overview

Today, manually creating a chore only supports one recurrence shape: "repeat every N days/weeks/months/years" (`frequencyType: "interval"`). The backend scheduling engine (`chore_scheduling.py`) already implements richer types — `weekly`, `monthly`/`month`, `yearly`/`year`, `day_of_the_month`, `days_of_the_week` — but they are reachable only as Donetick-import artifacts; the manual create/edit UI never exposes them, and `ChoreEditModal` can't even display or change a chore's `frequencyType` once set.

This spec adds, on top of that existing engine, three things modeled on Donetick's scheduling UX:

1. A shared recurrence-type picker (`ScheduleEditor.svelte`) used by both create and edit, covering Daily / Every N units / Weekly on day(s) / Monthly on day N (optionally restricted to specific months) / Yearly / Adaptive.
2. A natural-language quick-add box (English + French) that parses a sentence like "Change water filter every 6 months" into a name + structured schedule, pre-filling the same picker for review.
3. A new `"adaptive"` recurrence type that learns a chore's cadence from its completion history (average of the last 5 gaps between completions) instead of a fixed period.

**Out of scope:** time-of-day (all due dates remain date-only, matching the rest of the app); any change to `scheduleFromDue` (due-date vs. completion-date anchoring is already fully implemented and is preserved as-is, orthogonal to which recurrence type is picked).

**Two small pre-existing gaps get fixed incidentally**, since this work touches the same code:
- `next_due_from_schedule` doesn't explicitly handle `"daily"` — it silently falls through to a `periodDays`-based fallback. This gets an explicit `+1 day` branch.
- `_period_days` (routes/chores.py) only recognizes the literal `"yearly"`, not the `"year"` alias that `next_due_from_schedule` already accepts. This gets the same alias handling.

## Data model

No breaking/new columns. Everything reuses the existing `Chore.frequencyType` / `frequency` / `frequencyMetadata` fields (`frequency_metadata` is already a free-form JSON-in-`Text` column).

- New `frequencyType` value: `"adaptive"`. Uses `frequencyMetadata: {}` (no new metadata keys) — `periodDays` itself doubles as both the seed value (set by the client at creation, same way `interval` already computes and sends its own `periodDays`) and the fallback used whenever there isn't yet enough completion history to compute a real average. This avoids introducing a redundant field that would just duplicate `periodDays`.
- No other model changes. The `yearly` and `daily` types already exist in the type system; they simply weren't reachable from manual creation and (for `daily`) weren't fully implemented in the scheduler.

## Backend changes

### `chore_scheduling.py`

- `next_due_from_schedule(chore, from_dt, completions: list[CompletionRecord] | None = None)` — new optional third parameter, purely additive (existing call sites without history keep working; only the new `adaptive` branch consumes it).
  - Add explicit `if ft == "daily": return from_dt + timedelta(days=1)`.
  - Add `if ft == "adaptive": return from_dt + timedelta(days=adaptive_period_days(chore, completions or []))`.
- New **exported** helper `adaptive_period_days(chore, completions_for_chore) -> float` (used both here and by the completion routes below, so the two stay consistent by construction):
  1. Filter/sort this chore's completions by `completedAt`.
  2. Compute gaps in days between consecutive completions.
  3. Average the last 5 gaps (fewer if that's all there is).
  4. If there are 0 or 1 completions (no gap available), return `chore.periodDays` unchanged (the seed value set at creation, or whatever it was last computed to be).

### `routes/chores.py`

- `_period_days(chore)` (import-time only — Donetick never emits an "adaptive" type, so no case needed there): fix the `"yearly"` branch to also match `"year"`, matching the alias `next_due_from_schedule` already accepts.
- **`periodDays` staleness fix for adaptive chores**: `periodDays` is a stored column, only refreshed at specific write points (create/import) — `GET /chores` returns it as-is, it's never recomputed on read. For `interval`/`weekly`/etc. this is fine since their period never changes after creation, but `adaptive`'s whole point is that the period *does* change as history accrues. So `complete_chore` and `complete_assignment`, right after appending the new `CompletionRecord` to `doc.completions`, must also do: if `chore.frequencyType == "adaptive"`, recompute `chore.periodDays = adaptive_period_days(chore, [c for c in doc.completions if c.choreId == chore.id])` and persist it alongside the new `nextDueDate`. This keeps the progress bar and the "Adaptive (~N days)" label (which just reads `chore.periodDays` — see below) always in sync with the same next-due computation, with no separate frontend recomputation needed.
- At creation time, an adaptive chore has no history yet, so the client sends its chosen starting `periodDays` directly in the `POST /chores` body — same pattern `interval` already uses (client computes `periodDays` from its own inputs and sends it along); no backend change needed for `create_chore` itself.

### `mcp_tools_chores.py`

- `_complete_chore_impl` gets the same `periodDays` refresh-on-completion treatment as `complete_chore`.

## Frontend changes

### `scheduleLabel` (`choreStore.svelte.ts`)

- No signature change needed. New `"adaptive"` branch reads the chore's own (backend-kept-fresh, per above) `periodDays` directly: renders "Adaptive (~{periodDays} days)". A chore with zero completions yet shows its seed value this way too, since that's what `periodDays` holds until the first gap can be computed — no separate "learning" wording needed, the number itself is honest either way.
- Existing branches unchanged.

### `ScheduleEditor.svelte` (new, `packages/editor/src/lib/components/`)

Shared component bound via `frequencyType` / `frequency` / `frequencyMetadata` props (two-way bound, mirrors `DatePicker`/`EmojiPicker` usage elsewhere).

- Top-level `<select>` for recurrence category, then a category-specific sub-row:

| Category | `frequencyType` | Sub-controls |
|---|---|---|
| Every N days/weeks/months/years | `interval` | number input + unit select (today's existing UI, moved as-is) |
| Daily | `daily` | none |
| Weekly on day(s) | `days_of_the_week` | weekday multi-select checkboxes, reusing `chores.schedule.dayAbbrev.*` i18n keys |
| Monthly on day N | `day_of_the_month` | day-of-month number (1–31) + optional "restrict to specific months" multi-select (off by default = all months) |
| Yearly | `yearly` | none (advances by exactly 1 year from the anchor due date) |
| Adaptive | `adaptive` | editable "Period (days)" number input bound to `periodDays` — the same value the backend auto-recomputes after each completion; editing it manually re-seeds the average (e.g. to correct drift or start a new cadence) |

- Validation: disable the parent modal's Save when `days_of_the_week` has zero days selected, or `day_of_the_month` day is outside 1–31.
- `ChoresPage.svelte`'s existing `scheduleCategory()` filter-bucketing function gets two small fixes while touching this area: an explicit `if (ft === "daily") return "daily"` branch (today a literal `daily` chore — reachable via Donetick import already — falls through to an unfiltered `"other"` bucket that no dropdown option matches) and a new `if (ft === "adaptive") return "adaptive"` branch plus a matching `<option value="adaptive">` in the schedule filter dropdown.

### `NewChoreModal.svelte`

- Replace the inline `freq-row` block with `<ScheduleEditor>`.
- Add the natural-language quick-add text input above the name field (see below).

### `ChoreEditModal.svelte`

- Replace the plain `periodDays` number input in the Info tab with `<ScheduleEditor>`, seeded from the chore's current `frequencyType`/`frequency`/`frequencyMetadata` (today this tab ignores schedule shape entirely and only edits `periodDays`).

### `scheduleParser.ts` (new, `packages/editor/src/lib/`)

```
parseScheduleText(text: string, locale: "en" | "fr"):
  { name: string; schedule: Partial<Pick<Chore, "frequencyType"|"frequency"|"frequencyMetadata">> } | null
```

- Rule-based (regex/keyword matching), no external NLP library or LLM call.
- Returns `null` only when no recurrence-like phrase is found at all; in that case the quick-add box still fills `name` with the raw text, no schedule guess.
- Patterns (mirrored EN/FR):
  - Interval: "every 6 months" / "tous les 6 mois", "every 3 days" / "tous les 3 jours" → `interval`
  - Daily: "every day" / "tous les jours", "daily" / "quotidien" → `daily`
  - Weekly on day(s): "every Monday and Tuesday" / "tous les lundis et mardis", "every Monday" / "chaque lundi" → `days_of_the_week`
  - Monthly on day N: "on the 15th of every month" / "le 15 de chaque mois" → `day_of_the_month`
  - Yearly: "every year" / "chaque année", "annually" / "annuellement" → `yearly`
  - Bare "every N" with unrecognized unit → `interval` in days
- Name extraction: strip the matched recurrence clause from the sentence; trim remaining connector words; what's left becomes the chore name.
- UI: single text input + "Parse" action in `NewChoreModal`, filling `name` and driving the bound `ScheduleEditor` props — always reviewable/adjustable before saving, never silently auto-created.

## Testing plan

- **Backend** (`pytest packages/backend`):
  - `chore_scheduling`: `daily` explicit branch; `adaptive_period_days` with 0, 1, and 5+ completions; `next_due_from_schedule`'s `adaptive` branch; `_period_days` `"year"` alias fix.
  - `routes/chores.py`: `complete_chore`/`complete_assignment` persist a refreshed `periodDays` for adaptive chores after completion, and leave it untouched for other types.
- **Frontend** (`vitest`, editor package):
  - `scheduleLabel`: new `adaptive` branch, reading `chore.periodDays` directly.
  - `ScheduleEditor.svelte`: one test per recurrence category (renders correct sub-controls, updates bound props, validation disables save appropriately).
  - `scheduleParser.ts`: table-driven EN + FR input strings → expected `{name, schedule}`, plus the no-match fallback case.
- **Manual browser check** (per project convention for UI changes): create one chore per new recurrence category, plus one quick-add phrase in each language, and confirm the resulting schedule label and next-due date look right.
