# KB & Chores UI Fixes — Design

Date: 2026-08-12

## Summary

Four small, independent UI fixes reported by the user:

1. KB tree expand/collapse disclosure icon doesn't clearly convey its toggle state.
2. KB save status ("Enregistrement…"/"Enregistré") is text; should be an icon.
3. KB pages can only be edited via double-click; needs a discoverable edit icon too.
4. Chores' "Room" concept should be relabeled "Zone" (e.g. garden isn't a room).

None of these change data models, APIs, or the MCP surface. All are display-layer only.

## 1. KB tree disclosure icon

**File:** `packages/editor/src/lib/components/ui/KBTree.svelte` (lines 174–179, `.disclosure` style ~258–264)

Currently renders two different unicode characters depending on state (`▶` closed / `▼` open), with only an `aria-label` (no visible tooltip) indicating what it does.

**Change:** use a single chevron glyph (`▸`) and rotate it 90° via CSS `transform` when open, instead of swapping characters. Add a `transition: transform 0.15s ease` for a visible animated toggle. Add a `title` attribute (visible hover tooltip) alongside the existing `aria-label`, both sourced from the existing `kb.tree.expand`/`kb.tree.collapse` i18n keys — no new i18n keys needed.

## 2. KB save status → icon

**File:** `packages/editor/src/lib/components/KBPage.svelte` (lines 562–568, `.save-status`)

Currently a `<span>` showing translated text for `saving`/`pending`, `saved`, and `error` states (state machine at line 36, unchanged).

**Change:** replace the text content with a small icon per state:
- `saving`/`pending`: a spinner glyph with a CSS rotation animation
- `saved`: a checkmark, using the existing 2s auto-revert-to-idle timeout (unchanged)
- `error`: a warning glyph (existing `save-status-error` class stays)

The existing i18n strings (`kb.page.saving`/`saved`/`saveFailed`) move to a `title`/`aria-label` on the span so the meaning is still available on hover and to screen readers — this is a visual swap, not a removal of the text.

## 3. KB edit icon

**File:** `packages/editor/src/lib/components/KBPage.svelte` (header-actions, near line 569)

Currently the only way into edit mode is double-clicking the page body (`MarkdownEditor` with `editTrigger="dblclick"`). No icon/button exists for it.

**Change:** add a pencil-icon button in `header-actions`, shown only when `!editing`, that sets `editing = true` — the same effect the double-click handler already produces (`KBPage.svelte` uses `bind:editing` with `MarkdownEditor`, so this is a one-line assignment, no new state machine). Double-click keeps working unchanged. New i18n key: `kb.page.edit` = "Edit" / "Modifier" (en/fr), used as the button's `title`/`aria-label`.

## 4. Chores "Room" → "Zone" (display text only)

Scope, confirmed with user:
- **Everywhere in the UI**, including the floor plan editor, not just Chores — Costs and Inventory too.
- **Display text only.** No renaming of `roomId`, the `Room` type in the geometry package, DB columns, or MCP tool parameter names. This is a copy change, not a data-model change — avoids migration risk and keeps the MCP API surface stable.
- i18n **key names** stay the same (e.g. `chores.page.allRooms` keeps its key, only its string value changes) — key names aren't user-facing and renaming them adds churn/risk for no visible benefit.

**Files:** `packages/editor/src/lib/locales/en.json` and `fr.json` — value-only edits to:

| Key | Current (en) | New (en) | Current (fr) | New (fr) |
|---|---|---|---|---|
| `floorPlan.roomPanel.title` | Room | Zone | Pièce | Zone |
| `floorPlan.openingPanel.noArea` | Assign this room to an HA Area first | Assign this zone to an HA Area first | Associez d'abord cette pièce à une zone HA | Associez d'abord cette zone à une HA Area |
| `chores.badgePopup.thisRoom` | This room | This zone | Cette pièce | Cette zone |
| `chores.list.roomInFloor` | Room ({floor}) | Zone ({floor}) | Pièce ({floor}) | Zone ({floor}) |
| `chores.list.unknownRoom` | Unknown room | Unknown zone | Pièce inconnue | Zone inconnue |
| `chores.list.emptyState` | …assign them to rooms. | …assign them to zones. | …les assigner à des pièces. | …les assigner à des zones. |
| `chores.editModal.selectRoom` | Select a room… | Select a zone… | Choisir une pièce… | Choisir une zone… |
| `chores.page.allRooms` | All rooms | All zones | Toutes les pièces | Toutes les zones |
| `chores.page.notAssigned` | Not assigned to any room | Not assigned to any zone | Non assignée à une pièce | Non assignée à une zone |
| `chores.page.rooms` | Rooms | Zones | Pièces | Zones |
| `chores.page.roomCount` | {n} rooms | {n} zones | {n} pièces | {n} zones |
| `costs.page.room` | Room | Zone | Pièce | Zone |
| `costs.entryModal.noRoom` | No room | No zone | Aucune pièce | Aucune zone |

`InventoryPage.svelte` reuses `chores.page.allRooms` and `costs.page.room` for its own room filter/column — covered automatically, no separate inventory keys exist.

**Naming collision fix (French only):** `floorPlan.roomPanel.haArea` is currently `"Zone HA"` (for the Home Assistant Area field), which sits inside the same panel whose title is becoming "Zone". To avoid a "Zone" panel containing a "Zone HA" field, reword `fr.json`'s `floorPlan.roomPanel.haArea` from `"Zone HA"` to `"HA Area"` (matching the English wording directly, per user's choice), and correspondingly update `floorPlan.openingPanel.noArea`'s reference to "zone HA" the same way (see table above) — these are pre-existing strings that only need to change because of the new collision, not because they mention "room".

**Out of scope (explicitly excluded):**
- Room *type*/descriptive labels ("Bedroom", "Bathroom", "Living Room", "Garden" furniture-library categories) — these name a kind of space, not the umbrella "Room" concept, and stay as-is.
- `properties.modal.bedrooms`/`bathrooms`, `build.*` bathroom/flooring task text — unrelated room-count/construction terms.
- CSS class names (`room-panel`, `room`, `room-label`) — internal, not user-facing.

## Testing impact

- Component/unit tests asserting on the old English strings ("All rooms", "Rooms", "Select a room…", etc.) need their expected-text updated to match the new copy — a grep across `packages/editor/src/**/*.test.ts` for these literals during implementation.
- New test coverage: KB edit-icon button (click sets `editing = true`, hidden while already editing), KB disclosure chevron rotation/tooltip, KB save-status icon per state.
