# Floor plan mobile toolbar regrouping

## Problem

The floor plan editor's `.floating-toolbar` (`App.svelte:1271-1354`) already has a
mobile breakpoint (`@media (max-width: 480px)`, `App.svelte:1750-1776`) that
turns it into a fixed bottom bar with `overflow-x: auto`, but in edit mode it
holds ~18 controls (drag handle, floor switcher, layers dropdown, picker
toggle, furniture toggle, mode toggle, save, reset view, undo, redo, pan,
select, wall, divider, garden, door, window, delete) sized to content with no
real touch-target minimum. Users have to scroll horizontally and tap
uncomfortably small icons to switch tools.

## Scope

Mobile only (`max-width: 480px`), edit mode primarily — view mode's toolbar is
already short today (drag handle, floor/layers, mode toggle, pan, reset) and
needs no grouping. Desktop's current full inline floating toolbar is
unaffected; two render paths already exist via the media query, this just
changes what mobile renders.

## Design

### Grouping

Controls split into 3 categories, each behind an icon button that opens a
`Modal` listing that category's items. Tapping an item inside a modal performs
the action / selects the tool and immediately closes the modal (one tap to
open a group, zero extra taps to act within it).

- **View** (👁): Pan, Select, Reset view.
- **Draw** (📐): Wall, Divider, Garden, Door, Window.
- **Actions** (⚡): Undo, Redo, Delete.

Picker and Furniture stay as 2 standalone icon toggles (not worth a modal for
2 items). Floor switcher and Layers dropdown are already self-contained
popover components and stay standalone too, but their closed/collapsed
trigger becomes icon-only — no visible text label — matching the rest of the
row. Edit/View mode toggle and Save stay on the primary row: mode toggle is a
top-level state switch (hiding it would make the rest of the toolbar
confusing), and Save is frequent enough plus already carries status via
icon+color (saved/saving/error/dirty).

Primary row (mobile, edit mode):

```
[⠿] [🏢Floor] [🗂Layers] [📋Picker] [🪑Furniture] [✏️/✏️⃠ Mode] [💾Save] [👁View] [📐Draw] [⚡Actions]
```

Icons:
- Mode toggle: ✏️ for edit mode; view mode reuses the same ✏️ with a diagonal
  slash overlay (CSS line across the icon) rather than a different glyph, so
  it reads as "editing disabled," not a separate concept like "eye/preview."
- View category: 👁 (freed up from the mode toggle).
- Draw category: 📐 (unchanged from initial proposal).
- Actions category: ⚡ (replaces the earlier "⋯" proposal).

### Floating active-tool indicator

A small chip anchored bottom-right, floating just above the toolbar, shows
the icon of whichever tool is currently active in `toolStore.state.tool`
(Pan/Select/Wall/Divider/Garden/Door/Window), regardless of which category
owns it. Only rendered when `!viewMode` and a tool is active. Tapping it
reopens the owning category's modal (View modal for Pan/Select, Draw modal
for the 5 drawing tools), so switching tools is: tap chip → tap new tool →
done, without needing to locate the right category icon first.

### Implementation

- One shared modal driven by local state `openGroup: 'view' | 'draw' |
  'actions' | null` in `App.svelte`, alongside existing `pickerOpen` /
  `furnitureLibraryOpen` — no new store, this is local UI state like those.
  Reuse `Modal.svelte` directly with a small list of tool buttons passed in,
  rather than 3 separate modal components.
- Floating indicator is a small new component (or inline markup) reading
  `toolStore.state.tool`; `onclick` sets `openGroup` based on which category
  owns the active tool.
- Styling extends the existing `@media (max-width: 480px)` block in
  `App.svelte` — no new breakpoint, desktop untouched.
- i18n: new keys for category modal titles/tooltips in EN/FR message files,
  following the existing `app.floatingToolbar.*` / `floorPlan.tools.*` key
  patterns.

### Testing

Existing tests that click `ft-btn` tools directly (e.g. clicking "Wall")
under a mobile viewport will need updating to open the Draw modal first —
same pattern as the test-update note in the compact-module-toolbars design
(`2026-08-07-compact-module-toolbars-design.md`). Desktop-viewport tests are
unaffected since that render path doesn't change.

## Out of scope

- Any change to desktop (>480px) toolbar layout or behavior.
- Changing which tools exist or their underlying `toolStore` behavior.
- View-mode toolbar grouping (already short enough, no change needed).
- A "contextual floating delete button" near a selected element — Delete
  stays inside the Actions modal, consistent with Undo/Redo.
