# Locations Module — UI Redesign Design Spec

**Date:** 2026-07-18
**Status:** Approved

## Overview

Follow-up to the Locations module (`docs/superpowers/specs/2026-07-18-locations-module-design.md`, merged PR #70). The initial matrix UI packed add/edit forms directly into the table (a full-width add-location column with an emoji picker + text input + button, and a full-width add-criterion row), which eats too much screen space and leaves all structural controls (reorder/edit/delete) visible at all times. This spec covers four changes:

1. **View/Edit mode toggle** — a clean read-only-structure "View" mode for the everyday action (rating cells), and an "Edit" mode that reveals add/reorder/rename/delete controls.
2. **Modal-based add/edit** for both locations and criteria, replacing the inline table forms with a compact "+" trigger + modal.
3. **Country flags** in the emoji picker, opt-in via a new prop so every other module using the shared picker is unaffected.
4. **Star rating** (★☆) replacing the 1–5 number buttons, both in the rating popup and in the matrix cell display.

No backend or data-model changes — `score` stays `int 1-5 | null`, `weight` stays `"low"|"medium"|"high"`, `emoji` stays a plain string (a flag is just another emoji string, already valid). This is a frontend-only change.

---

## 1. View/Edit mode

`LocationsMatrix.svelte` gains a `mode: "view" | "edit"` local state, defaulting to `"view"`, toggled by a small segmented control ("👁 View" / "✏️ Edit") rendered above the table.

- **View mode:** location column headers show only emoji + name; criterion cells show only name + weight tag + description. No reorder arrows, no ✏️ edit icon, no 🗑 delete icon, no "+" add triggers anywhere. Clicking a rating cell still opens the rating popup — rating is the point of View mode.
- **Edit mode:** every row/column shows its existing reorder (◀▶ for locations, ▲▼ for criteria), ✏️ edit, and 🗑 delete controls (delete keeps its existing inline confirm-click step). Two "+" triggers appear: one after the last location column, one next to the "Criteria" corner label.
- Rating cells behave identically in both modes (click → popup) — mode only gates structural controls.

## 2. Modal-based add/edit

Replaces the inline add-location column (emoji picker + text input + button occupying a full table column) and the inline add-criterion row (occupying a full table row), plus the inline in-place edit forms for both, with two small modals:

### `LocationModal.svelte`
Props: `location: Location | null` (`null` = create), `onsave: (data: { name: string; emoji: string }) => void`, `onclose: () => void`. Fields: flag/emoji picker (`EmojiPicker` with `flags` enabled) + name `Input`. Save disabled until name is non-empty. Follows the existing small-modal pattern in this codebase (`Modal` + `Input` + `Button`).

### `LocationCriterionModal.svelte`
Props: `criterion: LocationCriterion | null`, `onsave: (data: { name: string; description: string; weight: Weight }) => void`, `onclose: () => void`. Fields: name `Input`, description textarea, weight select (Low/Medium/High). Same create/edit reuse pattern.

In `LocationsMatrix.svelte`: `showLocationModal: Location | "new" | null` and `showCriterionModal: LocationCriterion | "new" | null` replace all the old per-field inline-edit `$state` variables. The ✏️ edit icon on an existing row/column opens the matching modal pre-filled; the "+" trigger opens it in create mode. `onsave` calls `store.createLocation`/`updateLocation` or `store.createCriterion`/`updateCriterion` as appropriate, then closes the modal.

## 3. Country flags in the emoji picker

`EmojiPicker.svelte` gets a new optional prop `flags?: boolean = false`. When `false` (the default, and therefore every existing call site — Chores, Inventory, Consumables, Works, Costs, KB), behavior is byte-for-byte unchanged: no tabs, just the existing Objects grid.

When `flags` is `true` (only `LocationModal` passes this), the panel shows a two-tab header ("Objects" / "Flags") above the grid, defaulting to "Objects" each time it opens. The Flags tab shows a small text filter input (filters the country list by name, case-insensitive substring) above the same scrollable grid layout already used for Objects, populated from a new data file:

### `countryFlags.ts`
```ts
export interface CountryFlag { code: string; name: string; flag: string; }
export function flagEmoji(code: string): string { /* regional-indicator pair from ISO alpha-2 */ }
export const COUNTRY_FLAGS: CountryFlag[]; // ~195 UN member states, sorted by name
```
`flag` is computed from `code` via Unicode regional indicator symbols (`🇫 + 🇷` → 🇫🇷), not hand-typed, so the list only needs `{code, name}` pairs plus the one conversion function — no risk of a mistyped flag glyph.

The existing "Custom…" free-text entry at the bottom of the panel is shared across both tabs unchanged (still useful for a non-country pin emoji even when `flags` is on).

## 4. Star rating

New shared `StarRating.svelte`:
```
Props: score: number | null; size?: "sm" | "md" = "md"; interactive?: boolean = false; onselect?: (score: number) => void;
```
Renders 5 star glyphs (★ filled up to `score`, ☆ empty beyond it), gold fill (`#f5b301`) / `var(--text-faint)` empty, sized by `size`. When `interactive`, stars are clickable buttons that call `onselect(v)` for the clicked value — the component is intentionally dumb about "toggle to clear" semantics; that logic (click the already-selected star to clear it) stays in the caller, exactly as `LocationRatingPopup`'s existing `selectScore` already does it today for the button version.

- **`LocationRatingPopup.svelte`:** the row of five number buttons is replaced by `<StarRating score={score} interactive size="md" onselect={selectScore} />`. Everything else (note textarea, Save/Clear/Close, Escape-to-close) is unchanged.
- **`LocationsMatrix.svelte`:** a rated cell's `<span class="score-badge">{rating.score}</span>` is replaced by `<StarRating score={rating.score} size="sm" />`. Unrated cells keep showing "—" (StarRating is only rendered when `rating?.score != null`, same branching as today — this avoids an all-empty 5-star row reading as "rated zero"). The best-cell green outline highlight is unchanged, now wrapping stars instead of a colored circle.

---

## Testing

- **`StarRating.test.ts`** (new): renders the correct filled/empty star count for a given score; `interactive` clicks call `onselect` with the clicked value; non-interactive renders no click handlers.
- **`countryFlags.test.ts`** (new): `flagEmoji()` produces the correct pair for known codes (e.g. `"FR"` → 🇫🇷); the list has no duplicate codes and every entry has a non-empty name.
- **`EmojiPicker.test.ts`**: add cases for the new `flags` prop — tabs only render when `flags` is true; switching to the Flags tab renders flag buttons and the filter narrows them; selecting a flag calls `onchange` with the flag string; existing no-flags behavior stays covered (regression).
- **`LocationModal.test.ts`** / **`LocationCriterionModal.test.ts`** (new): create mode calls the right store method with entered values; edit mode pre-fills from the passed entity and calls update; Save disabled until required fields are filled.
- **`LocationsMatrix.test.ts`**: rewritten add-location/add-criterion tests now open the modal via the "+" trigger instead of filling an inline form; new tests for View mode (structural controls hidden, rating still clickable) and Edit mode (controls visible); best-cell highlight test updated to look for star markup instead of `.score-badge`.
- **`LocationRatingPopup.test.ts`**: score-selection tests updated to click star elements instead of number buttons; same assertions on `onsave`.
- **`LocationsPage.test.ts`**, **`HomeLocationsWidget.test.ts`**: unaffected, no changes expected.

## Out of scope

- No changes to the backend, REST API, or MCP tools.
- No changes to the ranking chart (`LocationRankingChart.svelte`) — it displays a weighted average, not discrete stars, so it's unaffected.
- No hover-preview animation on stars beyond a simple filled/empty state (can be a later polish pass).
