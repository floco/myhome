# Global Search — Design Spec

**Date:** 2026-07-05
**Status:** Approved

---

## Overview

Add a global search / command palette that lets users find items across all
data modules (Knowledge Base, Inventory, Works, Costs, Chores, Consumables)
from anywhere in the app, without navigating to each module and searching
separately.

Search is scoped to the currently selected home. Selecting a result navigates
to that module and opens the item's existing detail/edit view.

---

## Approach

Every module store (`kbStore`, `inventoryStore`, `worksStore`, `costsStore`,
`choreStore`, `consumableStore`) is already eagerly loaded in full for the
current home when the app starts (`App.svelte` calls `.reload()` on all of
them up front). Search is implemented **entirely client-side**, filtering
these already-in-memory stores — no new backend endpoint.

This was chosen over a backend search endpoint because:
- It matches the existing architecture (all module data for the current home
  is already resident in the browser).
- It avoids a network round-trip per keystroke.
- It's consistent with the existing KB MCP tool, which already documents
  that there's deliberately no server-side search ("fetch the list and
  filter/search over titles and content yourself").

This won't scale to modules with thousands of items, which isn't this app's
usage profile (single-home personal data).

---

## Components & Data Flow

### `searchIndex.ts` (new, `packages/editor/src/lib/`)

A pure function:

```ts
buildSearchIndex(stores: {
  kbStore, inventoryStore, worksStore, costsStore, choreStore, consumableStore, settingsStore
}): SearchResult[]
```

Maps each module's already-loaded items into a common shape:

```ts
interface SearchResult {
  module: "chores" | "inventory" | "consumables" | "works" | "costs" | "kb";
  id: string;
  icon: string;       // item emoji, or a module default icon
  title: string;
  subtitle: string;
  searchText: string; // lowercased concatenation of all matched fields, for filtering
  titleMatch: boolean; // true if the query matched title/name (vs. body text) — used for ranking
}
```

This is called reactively (`$derived`) from within `CommandPalette.svelte`, so
the index always reflects current store state. No caching layer, no
invalidation logic — it's cheap to recompute given the small per-home data
sizes.

### `CommandPalette.svelte` (new)

A modal overlay: text input, results list grouped by module, keyboard
navigation, substring highlighting in matched results, empty state. This is
the single implementation of the search UI — both entry points below open
the same component instance/overlay.

### Entry points

1. **`Ctrl/Cmd+K`** global shortcut, listened for in `App.svelte`. Toggles
   the palette: opens it if closed; if already open, refocuses the input
   rather than closing.
2. **Topbar search affordance** — a search icon/box in the topbar that opens
   the identical overlay on click. This is a launcher, not a second live-filter
   implementation.

### Result selection wiring

Extends the `selectedItemId` / `onclearselection` prop pattern that
`InventoryPage.svelte` already implements. Today, `ChoresPage`,
`ConsumablesPage`, `WorksPage`, `KBPage`, and `CostsPage` manage their
detail-modal state (e.g. `CostsPage`'s local `modalEntry`) purely internally.
Each of these five pages gets the same external prop pair added:

```ts
selectedItemId?: string | null;
onclearselection?: () => void;
```

On mount / whenever `selectedItemId` changes, the page opens its existing
detail/edit modal for that id (for `CostsPage`, this means setting
`modalEntry` to the matching entry). The page calls `onclearselection` when
that modal is closed, mirroring `InventoryPage`'s existing behavior exactly.

Selecting a search result:
1. Closes the palette.
2. Sets `window.location.hash` to the target module's route (e.g. `#/works`).
3. Sets that module's `selectedItemId` state in `App.svelte`.
4. The page (already re-rendered for the new route) opens the matching
   item's modal via the mechanism above.

---

## Search Behavior

**Fields matched per module** (case-insensitive substring match):

| Module | Matched against | Subtitle shown |
|---|---|---|
| Knowledge Base | title, content | "Knowledge Base" |
| Inventory | name, brand, model, serialNumber, notes | category |
| Works | title, description, notes | status + date |
| Costs | notes, resolved category name, resolved supplier name | category + amount |
| Chores | name, description | next due date |
| Consumables | name, description | quantity / unit |

Category and supplier names for Costs are resolved via `settingsStore`
(costs entries store `categoryId`/`supplierId`, not names).

**Ranking:** results where the query matches the title/name are ranked above
results that only match body text (notes/description/content). Within each
rank, original store order is preserved (no secondary sort).

**Result cap:** 20 results total, grouped by module in a fixed order:
Chores, Inventory, Consumables, Works, Costs, Knowledge Base.

**Minimum query length:** 2 characters. Below that, the palette shows its
empty/prompt state rather than an unfiltered list.

---

## Edge Cases & Accessibility

- **Home switch while palette is open:** the index is `$derived` off the
  current stores, which already reset on home switch — results update
  automatically, no special handling needed.
- **Keyboard navigation:** ↑/↓ moves the highlighted result, `Enter` selects
  it, `Esc` closes the palette. Focus stays trapped inside the palette while
  open, consistent with other modals in the app.
- **No results:** a simple "No results for '…'" empty state. There's no
  error state to handle since this never touches the network.

---

## Testing

- Unit tests for `buildSearchIndex`: correct fields matched per module,
  title-match-before-body-match ranking, 20-result cap, fixed module
  ordering, Costs category/supplier name resolution.
- Component tests for `CommandPalette.svelte`: keyboard navigation, open/close
  via `Ctrl/Cmd+K` and via the topbar entry point, selecting a result emits
  the correct module + id.
- Per-page tests confirming the new `selectedItemId` prop opens the correct
  existing detail modal, for each of the five newly-extended pages
  (`ChoresPage`, `ConsumablesPage`, `WorksPage`, `KBPage`, `CostsPage`).

---

## Dependencies / Coordination

The `feat/ui-refactor-topbar-toolbar-badges` branch (in progress, not yet
merged) also touches the topbar markup. The topbar search affordance in this
spec should be added after that branch merges, or rebased carefully if built
in parallel, to avoid a layout conflict in `App.svelte`'s `<header
class="topbar">` block.

---

## Non-Goals

- Fuzzy matching (typo tolerance) — plain substring match only, for now.
- Cross-home search — explicitly scoped to the current home only.
- Server-side search endpoint — see Approach above.
- Floor plan / furniture object search — furniture objects have no name/data
  linkage today, so they're not part of this search's scope.
