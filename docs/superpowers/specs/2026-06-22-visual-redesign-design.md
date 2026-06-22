# Visual Redesign — Design System (Spec 6) — Design Document

**Status:** Approved for planning
**Date:** 2026-06-22

## Overview

App-wide visual redesign inspired by [TREK](https://github.com/mauriceboe/TREK)'s look: light theme by default (with a working dark mode), rounded cards with soft shadows, near-monochrome primary accent (black in light mode / near-white in dark mode), bold pill-shaped buttons, and color reserved for data/status rather than chrome.

myhome currently has no design-system tooling: colors are hardcoded hex strings scattered across ~35 Svelte components, with ad hoc spacing and border-radius values (2px–10px) and no theme switching. This spec introduces a centralized token system and a small shared UI component library, then migrates every surface in the app to use them.

This is a styling-only change. No data models, API contracts, or application behavior change. Floor-plan editing logic, chore/inventory/costs/works business logic, and all existing routes are untouched.

---

## Design Tokens

New file `packages/editor/src/lib/theme.css`, defining CSS custom properties on `:root` (light, default) and `[data-theme="dark"]` (dark overrides).

### Light theme

| Token | Value | Use |
|---|---|---|
| `--bg` | `#f5f5f7` | App background |
| `--surface` | `#ffffff` | Cards, panels, modals |
| `--surface-alt` | `#fafafa` | Secondary surfaces, hover states |
| `--surface-hover` | `#f0f0f2` | Row/item hover |
| `--border` | `#e5e5e7` | Card/input borders |
| `--text` | `#1a1a1e` | Primary text |
| `--text-muted` | `#767680` | Secondary text |
| `--text-faint` | `#9a9aa2` | Captions, placeholders |
| `--accent` | `#111111` | Primary buttons, active nav, focus rings |
| `--accent-contrast` | `#ffffff` | Text/icons on `--accent` |

### Dark theme

| Token | Value |
|---|---|
| `--bg` | `#15151a` |
| `--surface` | `#1e1e24` |
| `--surface-alt` | `#242430` |
| `--surface-hover` | `#2a2a33` |
| `--border` | `#2c2c35` |
| `--text` | `#e8e8ea` |
| `--text-muted` | `#9a9aa5` |
| `--text-faint` | `#6b6b75` |
| `--accent` | `#f0f0f0` |
| `--accent-contrast` | `#111111` |

### Shared (both themes; tuned per-theme only where contrast requires it)

| Token | Light | Dark |
|---|---|---|
| `--success` | `#2a8f5c` | `#4ade80` |
| `--danger` | `#e0444d` | `#f87171` |
| `--warning` | `#d99a1b` | `#fbbf24` |

### Scales (theme-independent)

- Radius: `--radius-sm: 6px`, `--radius-md: 10px`, `--radius-lg: 16px`, `--radius-pill: 999px`
- Shadow: `--shadow-sm: 0 1px 3px rgba(0,0,0,.06)`, `--shadow-md: 0 4px 16px rgba(0,0,0,.08)`, `--shadow-lg: 0 8px 32px rgba(0,0,0,.16)` (dark theme shadows use a higher alpha, `.4`/`.5`, to stay visible against dark surfaces)
- Spacing: `--space-1: 4px` through `--space-6: 32px` (4/8/12/16/24/32)
- Font: `--font-sans: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif` (no web font load)

### Canvas tokens (separate from UI chrome — see Canvas Theming below)

`--canvas-bg`, `--canvas-grid`, `--canvas-wall`, `--canvas-wall-selected`, `--canvas-room-fill`, defined per theme, tuned independently from `--bg`/`--surface` since drawing contrast needs differ from UI contrast.

---

## Theme Toggle & Persistence

- New `packages/editor/src/lib/theme.ts`: reads `localStorage["myhome-theme"]` on load (`"light"` | `"dark"`), defaults to `"light"` if unset, sets `data-theme` attribute on `<html>`. Exposes `toggleTheme()` which flips the value and persists it.
- Toggle button (sun/moon icon) added to the topbar in `App.svelte`, next to the existing floor switcher.
- No backend/server-side persistence — this is a per-browser UI preference, consistent with how the rest of the app has no per-user accounts.

---

## Shared Component Library

New directory `packages/editor/src/lib/components/ui/`:

| Component | Purpose |
|---|---|
| `Button.svelte` | Variants: `primary` (filled `--accent`), `secondary` (bordered), `ghost` (text-only). Pill radius (`--radius-pill`), padding `8px 18px`. |
| `Card.svelte` | `--surface` background, `--radius-lg`, `--shadow-sm`, padding `--space-4`. |
| `Panel.svelte` | Like `Card` but with a `density` prop (`"normal"` \| `"compact"`) controlling padding/font-size — used by editor side panels (see Density Rule). |
| `Input.svelte` | Text/number input, `--surface-alt` background, `--border`, `--radius-md`, focus ring `--accent`. |
| `Modal.svelte` | Wraps the existing modal shell pattern (backdrop + centered panel): `--surface`, `--radius-lg`, `--shadow-lg`. Replaces the bespoke shell currently duplicated in `InventoryModal`, `CostsEntryModal`, `CostsCategoryModal`, `WorkModal`, `NewChoreModal`. |
| `Badge.svelte` | Status pill: `--radius-pill`, small padding, semantic background tint (success/danger/warning) + matching text color. |
| `StatTile.svelte` | Big bold number (`24px`/`700`) + small uppercase label, `Card`-based — used for dashboard-style metric tiles (e.g. item counts, low-stock counts). |

Existing components migrate to compose these instead of their current one-off markup and inline hex colors.

---

## Density Rule

- **Full treatment** (generous padding, `--space-4`/`--space-6`, `Card`/`Modal` defaults): topbar, nav, all modals, all standalone pages (Inventory, Chores, Costs, Works, Settings, Consumables).
- **Compact treatment** (`Panel` with `density="compact"`: `--space-2`/`--space-3` padding, 11–12px type): the floor-plan editor's own panels — `ItemPickerPanel`, `RoomPanel`, `Toolbar`. These keep tighter spacing so the canvas doesn't shrink, but pull colors/borders/radius from the same tokens as everything else, so they read as the same system at a different zoom level rather than a different system.

---

## Canvas Theming

Per the chosen direction, the floor-plan canvas follows the active theme rather than staying fixed:

- Light theme: pale canvas background, dark wall/room outlines — a "blueprint on paper" look.
- Dark theme: current dark canvas styling, retained roughly as-is.
- Affected components: `Canvas.svelte`, `Grid.svelte`, `WallShape.svelte`, `DividerShape.svelte`, `RoomShape.svelte`, `OpeningShape.svelte`, `SelectionHandles.svelte`, `DrawPreview.svelte`. Each switches its hardcoded colors to the new `--canvas-*` tokens.
- Contrast for selection handles, drag previews, and badge/pin overlays needs visual re-verification in both themes during implementation, since these currently assume a single dark background.

---

## Rollout Phases

Implemented as separate plans under this spec, in order:

**Phase 1 — Foundation**
New: `theme.css`, `theme.ts`, `components/ui/*` (all 7 components).
Modified: `App.svelte` (topbar layout + theme toggle button, imports `theme.css`), `NavMenu.svelte` (tokens + pill active state).
This phase is the proving ground — global chrome only.

**Phase 2 — Floor-plan editor panels + canvas**
Modified: `ItemPickerPanel.svelte`, `RoomPanel.svelte`, `Toolbar.svelte`, `FloorSwitcher.svelte`, `LayersDropdown.svelte` (compact `Panel` treatment); `Canvas.svelte`, `Grid.svelte`, `WallShape.svelte`, `DividerShape.svelte`, `RoomShape.svelte`, `OpeningShape.svelte`, `SelectionHandles.svelte`, `DrawPreview.svelte` (canvas tokens, both themes).

**Phase 3 — Modals**
Modified: `InventoryModal.svelte`, `CostsEntryModal.svelte`, `CostsCategoryModal.svelte`, `WorkModal.svelte`, `NewChoreModal.svelte`, `DatePicker.svelte` — migrated onto the shared `Modal`/`Input`/`Button` components.

**Phase 4 — Pages**
Modified: `InventoryPage.svelte`, `ChoresPage.svelte`, `ChoreListPage.svelte`, `CostsPage.svelte`, `WorksPage.svelte`, `SettingsPage.svelte`, `ConsumablesPage.svelte` — migrated onto `Card`/`StatTile`/`Button`/tokens; existing tables/charts keep their current data logic, only visual styling changes.

**Phase 5 — Canvas overlays & popups**
Modified: `ChoreOverlay.svelte`, `InventoryOverlay.svelte`, `CostsOverlay.svelte`, `WorksOverlay.svelte`, `BadgePopup.svelte`, `InventoryPinPopup.svelte`, `CostsPinPopup.svelte`, `WorksPinPopup.svelte` — token colors, `Badge` for status chips.

---

## Testing

No visual regression tooling exists in this repo today, so verification per phase is manual: open the app in both light and dark mode and check the surfaces touched by that phase. Existing backend and frontend unit/component tests must keep passing unmodified, since no data models, stores, or API contracts change — this is a pure styling/markup migration.

---

## What is NOT in scope

- Any change to data models, API routes, or business logic
- Server-side or per-account theme persistence (theme is a per-browser `localStorage` preference)
- Loading a custom web font (system font stack only)
- New features beyond what already exists (this is a re-skin, not a re-scope)
- Floor-plan editing behavior changes
- Automated visual regression testing infrastructure
