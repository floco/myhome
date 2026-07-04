# UI Refactor: Topbar, Floating Toolbar, Badge Scaling, Map Height

**Date:** 2026-07-04  
**Status:** Approved

## Overview

Five targeted UI improvements to clean up the topbar, move floor-plan controls into a floating panel, scale badges proportionally to the map, and give the home dashboard map widget more vertical space.

---

## 1. Topbar Reorganization

### Current layout (left → right)
`[☰] [My Home] [🌙] · [floor plan: FloorSwitcher | spacer | toolbar | sep | LayersDropdown | 📋 | 💾 | ↺ | sep] · [AB]`

The topbar is context-sensitive: floor-plan controls appear/disappear based on route.

### New layout (left → right)
`[☰] [My Home]  →  [⌂ Home name ▼] [🌙] [│] [AB]`

- Identical on every route — no conditional blocks
- `[⌂ Home name ▼]` = HomesSwitcher (topbar variant, compact, always inline)
- `[🌙]` = theme toggle (moved from near-left to near-right)
- All floor-plan-specific controls are removed from the topbar entirely

### HomesSwitcher changes
- Add `topbar: boolean = false` prop to `HomesSwitcher.svelte`
- When `topbar=true`: no `expanded`/`onexpand` dependency; always shows `⌂ Name ▼`; no border-bottom or sidebar padding; dropdown opens below-right
- When `topbar=false` (default): existing sidebar behaviour unchanged
- Remove `<HomesSwitcher>` from `NavMenu.svelte`; remove the `onexpand` prop from `NavMenu`
- In `App.svelte`: remove the `onexpand` callback passed to `NavMenu`; add `<HomesSwitcher topbar={true} />` to the topbar right-side group

---

## 2. Floating Vertical Toolbar (Floor Plan Only)

### Position & style
- `position: absolute; right: 12px; top: 50%; transform: translateY(-50%)`
- Width: `~40px`; padding: `4px`; gap: `2px`; `flex-direction: column`
- Background: `var(--surface)`; border: `1px solid var(--border)`; border-radius: `var(--radius-lg)`; box-shadow: `0 2px 12px rgba(0,0,0,0.2)`
- Only rendered when `isFloorPlan && !allFloorsMode`

### Panel contents (top → bottom)
```
FloorSwitcher     ← compact trigger (icon + floor name + chevron), popover opens leftward
─── sep ───
LayersDropdown    ← opens leftward
📋 picker toggle
💾 save
↺ reset view
─── sep ───
↩ undo
↪ redo
─── sep ───
🖱 select         ← this group hidden when choreLayerActive
🧱 wall
╌ divider
🚪 door
🪟 window
─── sep ───
🗑 delete
```

### Picker panel interaction
The item picker panel (`.right-panels`) is `position: absolute; right: 0`. When the picker is open, the floating toolbar shifts left to avoid overlap:
- Add a CSS class `picker-open` to the floating toolbar wrapper when `pickerOpen === true`
- `.floating-toolbar.picker-open { right: calc(220px + 16px); }` — `ItemPickerPanel` has a fixed width of `220px`

### FloorSwitcher in the panel
The existing `FloorSwitcher` component is used as-is. Its dropdown opens leftward (add `align: 'left'` prop or CSS override) so it doesn't go off-screen.

### Removed from topbar
- `{#if isFloorPlan}` block in topbar (FloorSwitcher, spacer, inline toolbar buttons, LayersDropdown, picker, save, reset) — fully deleted
- `.spacer`, `.topbar-sep`, `.toolbar` CSS classes in App.svelte can be removed once unused

---

## 3. Badge Scaling with Viewport Zoom

### Problem
All five overlay components (ChoreOverlay, InventoryOverlay, CostsOverlay, WorksOverlay, ConsumableOverlay) use hardcoded pixel sizes for badge geometry. At the home dashboard zoom level (~20 px/unit) these badges appear as large as they do at full-floor-plan zoom (~80–100 px/unit), making them oversized relative to the small map widget.

### Fix
Derive a `badgeScale` factor from `viewport.zoom` and apply it as an SVG `scale()` transform on each badge group:

```
badgeScale = clamp(viewport.zoom / 80, 0.35, 1.2)
```

Apply in SVG:
```svelte
<g transform="translate({sp.x},{sp.y}) scale({badgeScale})">
  <!-- all existing badge child elements unchanged -->
</g>
```

All child geometry (circles, text, rects, dasharray values) remains at its current literal values — the scale transform handles everything uniformly.

### Scale behaviour
| Context | Typical zoom | badgeScale | Effect |
|---|---|---|---|
| Home dashboard widget | ~20 | 0.35 (clamped min) | Badges ~35% original size |
| Full floor plan (fit) | ~80 | 1.0 | Badges identical to today |
| Zoomed in (full plan) | ~160 | 1.2 (clamped max) | Badges slightly enlarged |

### Files changed
- `ChoreOverlay.svelte` — derive `badgeScale`, wrap `<g transform>` per badge
- `InventoryOverlay.svelte` — same
- `CostsOverlay.svelte` — same
- `WorksOverlay.svelte` — same
- `ConsumableOverlay.svelte` — same

---

## 4. Home Dashboard Map Height

`HomeMapWidget.svelte` `.map-area { height: 220px }` → `height: 360px`.

The home page already scrolls vertically (`overflow-y: auto`) so no layout breakage. The larger map gives more room for floor plan detail and badge readability.

---

## Implementation Notes

- No new stores or data model changes
- No backend changes
- `HomesSwitcher` topbar variant is a pure CSS/prop change — sidebar behaviour unchanged
- Badge scaling requires no prop changes on callers — `viewport` is already passed to all overlays
- The `FloorSwitcher` dropdown direction (leftward) may need a small CSS tweak if it currently opens rightward
- All removed topbar CSS classes (`.spacer`, `.topbar-sep`, `.toolbar`) should be cleaned up once the `isFloorPlan` block is gone

## Files Touched

- `packages/editor/src/App.svelte` — topbar restructure, floating toolbar addition
- `packages/editor/src/lib/components/NavMenu.svelte` — remove HomesSwitcher, remove onexpand prop
- `packages/editor/src/lib/components/HomesSwitcher.svelte` — add topbar variant
- `packages/editor/src/lib/components/HomeMapWidget.svelte` — map height 220→360
- `packages/editor/src/lib/components/ChoreOverlay.svelte` — badge scale
- `packages/editor/src/lib/components/InventoryOverlay.svelte` — badge scale
- `packages/editor/src/lib/components/CostsOverlay.svelte` — badge scale
- `packages/editor/src/lib/components/WorksOverlay.svelte` — badge scale
- `packages/editor/src/lib/components/ConsumableOverlay.svelte` — badge scale
