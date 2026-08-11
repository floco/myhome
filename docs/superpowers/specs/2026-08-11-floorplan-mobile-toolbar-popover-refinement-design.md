# Floor plan mobile toolbar: bigger icons + anchored popovers

## Problem

The mobile toolbar shipped in v0.21.0 (see
`2026-08-11-floorplan-mobile-toolbar-design.md`) already avoids horizontal
scrolling by grouping tools into View/Draw/Actions, but the icons themselves
are still small (`.ft-btn` mobile CSS sets `font-size: 10px`, inherited by
the emoji glyph) and every button still shows a tiny label underneath,
eating vertical space that could go to a bigger icon. The View/Draw/Actions
groups also open as full-screen `Modal` overlays, which feels heavier than
necessary for picking one of 3-5 tools.

## Scope

Mobile only (`max-width: 480px`), floor plan editor toolbar
(`packages/editor/src/App.svelte`) and its two satellite dropdown
components (`FloorSwitcher.svelte`, `LayersDropdown.svelte`). Desktop is
unaffected — this only touches the mobile media query and the mobile-only
rendering path already established.

## Design

### Primary row: bigger, uniform, label-free

- Every primary-row button (Floor switcher, Layers, Picker, Furniture,
  Edit/mode toggle, Save, View, Draw, Actions) drops its `.ft-label` text on
  mobile and becomes a fixed-aspect-ratio square icon button:
  `flex: 1 1 0; max-width: 44px; aspect-ratio: 1/1;` with a larger icon
  font-size (~22px, up from 10px).
- Using `flex: 1 1 0` on all buttons means they evenly shrink to fill
  whatever width is actually available, capped at 44px — this is a
  structural guarantee against overflow (no manual pixel-fitting per
  device), so the mobile `overflow-x: auto` fallback on `.floating-toolbar`
  is removed since it's no longer needed.
- FloorSwitcher's compact trigger currently shows an icon *and* a chevron
  (▾); the chevron is hidden on mobile so the button is icon-only like
  every other one, making it genuinely the same size as its neighbors.

### View/Draw/Actions: anchored popover instead of full-screen modal

- New shared component `packages/editor/src/lib/components/ui/Popover.svelte`:
  props `open`, `anchorEl: HTMLElement | null`, `onclose`, `children`
  (Snippet) — no title/header (unlike `Modal.svelte`), since this is a
  lightweight anchored panel, not a modal.
- Positioning mirrors the existing copy-pasted pattern in
  `EmojiPicker.svelte`/`LayersDropdown.svelte`/`FloorSwitcher.svelte`
  (portal to `document.body`, `position: fixed`, viewport-clamped via
  `getBoundingClientRect()` + `Math.max/min`), but opens *above* the anchor
  instead of below, since the floor-plan toolbar sits at the very bottom of
  the screen and there's no room underneath — same reasoning already used
  for the floating tool-indicator's placement. Closes on click-outside or
  Escape, same as the existing popovers.
- This is extracted into one shared component instead of copy-pasted a
  fourth time, since this change adds 3 new instances of the same pattern
  at once. The 3 pre-existing copies (EmojiPicker, LayersDropdown,
  FloorSwitcher) are left as-is — retrofitting them is out of scope.
- All three groups — View (Pan, Select, Reset), Draw (Wall, Divider,
  Garden, Door, Window), Actions (Undo, Redo, Delete) — render inside a
  `Popover` as a vertical list of rows (icon left, label text right,
  ~44px-tall touch target each), replacing today's full-screen `Modal` +
  icon grid for all three groups. Tapping a row performs the action and
  closes the popover immediately, same behavior as the current modals.
- The floating active-tool indicator chip is unchanged.

### Testing

- `App.test.ts`'s exact-title-list assertion needs updating again since
  button `title`s stay the same but the queried structure around them
  changes (buttons no longer contain a `.ft-label` span on mobile — desktop
  keeps its label, this only affects the mobile media query which jsdom
  doesn't evaluate, so the underlying DOM structure change is what tests
  must track, not a visual/CSS distinction).
- Existing tests that open a group and click a tool inside `.ui-modal` need
  updating to instead query inside the new `Popover`'s container (a new
  class, e.g. `.ui-popover`) rather than `.ui-modal`.
- New tests: `FloorSwitcher` chevron hidden state is CSS-only (not testable
  in jsdom, same limitation as the existing icon-only mobile assertion) —
  covered by the existing markup-presence tests plus manual browser
  verification.

## Out of scope

- Any change to desktop (`>480px`) toolbar layout or behavior.
- Retrofitting `EmojiPicker`/`LayersDropdown`/`FloorSwitcher`'s existing
  popovers to use the new shared `Popover.svelte`.
- Changing which tools exist in each group, or their guard conditions
  (`!viewMode`, `!choreLayerActive && !allFloorsMode`) — unchanged from the
  v0.21.0 design.
