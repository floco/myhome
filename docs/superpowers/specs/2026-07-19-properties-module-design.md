# Properties Module — Design Spec

**Date:** 2026-07-19
**Status:** Approved

## Overview

Tracks individual property listings during a house search — land parcels,
existing houses, or new-builds still under construction. Replaces the
existing `#/properties` placeholder (reserved nav entry 🏘, module id already
present in `ALL_MODULE_IDS` and the Settings module-toggle list).

Each property is a single row: name, type, current pipeline status,
price/size details, free-text pros/cons, notes, and photo attachments. A
property can optionally link to a candidate area already entered in the
Locations module, but Properties works standalone too. Presented as a flat,
sortable/filterable table — one property per row — rather than a
side-by-side comparison matrix, since the natural workflow is managing a
growing list of individual listings over time (status changes, notes added
after visits) rather than scoring fixed criteria.

Out of scope: floor-plan pins (these are prospective properties, not the
user's own home — same reasoning as Locations), user-configurable
price/size units (app hardcodes € and m² elsewhere; Properties follows
suit), structured agent contact fields (single free-text field instead).

---

## 1. Data Model

### Property

```
id:            str
name:          str
emoji:         str = "🏠"
type:          Literal["land", "house", "new_build"]
status:        Literal["watching", "visited", "proposal_made", "purchased", "rejected"] = "watching"
locationId:    str | None = None      # optional FK into Locations module
address:       str = ""               # free-text specifics (street, etc.)
price:         float | None = None    # €
landSize:      float | None = None    # m²
builtSize:     float | None = None    # m²
bedrooms:      int | None = None
bathrooms:     int | None = None
listingUrl:    str | None = None
contact:       str = ""               # free-text agent/contact info
pros:          list[str] = []
cons:          list[str] = []
notes:         str = ""
attachments:   list[str] = []
```

### PropertiesDocument

```
version:    int = 1
properties: list[Property] = []
```

Stored in `properties.json` under the home's data directory. Lazily created
empty on first access, same as Works/Costs/Consumables — no default-seed
content (unlike Locations' 11 default criteria; there's nothing sensible to
pre-populate for listings).

`locationId` is not validated against the Locations document at write time
(consistent with how other soft cross-module references, e.g. Works'
`categoryId`, are handled) — the frontend resolves it for display and falls
back to "—" if the referenced location no longer exists.

---

## 2. Backend

Standalone module following the pattern of Works/Costs: new files only.

### New files

| File | Purpose |
|------|---------|
| `models_properties.py` | Pydantic models: `Property`, `PropertiesDocument`, `PropertyCreate`, `PropertyUpdate` |
| `persistence_properties.py` | Read/write `properties.json` |
| `routes/properties.py` | REST routes, including attachment upload/get/delete reusing the shared attachment helpers already used by `routes/costs.py` (`save_attachment`, `get_attachment_path`, `delete_attachment`, `delete_all_attachments`) |
| `mcp_tools_properties.py` | MCP tool exposure (`list_properties`, `create_property`, `update_property`, `delete_property`), mirroring `mcp_tools_works.py`'s `_*_impl` + `@mcp.tool()` wrapper pattern, role-gated the same way (`ro` for list, `normal` for mutations) |

`mcp_tools_properties` must also be added to the import list in `mcp_app.py`
(currently `mcp_tools_chores`, `..._consumables`, `..._costs`, `..._homes`,
`..._inventory`, `..._kb`, `..._locations`, `..._settings`, `..._works`) —
that import is what actually registers the tools against the shared `mcp`
singleton via the `@mcp.tool()` decorators' side effect; adding the file
alone does nothing.

### REST API

```
GET    /api/homes/{id}/properties
POST   /api/homes/{id}/properties                         → create property
PUT    /api/homes/{id}/properties/{pid}                   → update property
DELETE /api/homes/{id}/properties/{pid}                   → delete property + cascade-delete its attachments

POST   /api/homes/{id}/properties/{pid}/attachments        → upload attachment
GET    /api/homes/{id}/properties/{pid}/attachments/{filename}
DELETE /api/homes/{id}/properties/{pid}/attachments/{filename}
```

---

## 3. Frontend

### `propertiesStore.svelte.ts`

Fetch/cache `PropertiesDocument`, CRUD methods mirroring the REST routes,
plus `uploadAttachment`/`deleteAttachment`. Mirrors `worksStore.svelte.ts`.

### `PropertiesPage.svelte`

Replaces `PlaceholderPage` on route `#/properties`. Follows the
summary-stats + table layout used by `WorksPage.svelte`:

**Summary row (top, `Card`):** stat chips — count per status (Watching /
Visited / Proposal Made / Purchased / Rejected) plus total tracked.

**Table (below, `Card` + `SortableTable`):** toolbar with search (name/
address), status filter, type filter, "+ Add property" button. Columns:
emoji, name (+ address preview), type, location (resolved name via
`locationsStore`, "—" if unset/missing), price, size (`landSize`/
`builtSize` as applicable), status (color-coded chip, same convention as
Works' status chips). Row click opens `PropertyModal`.

### `PropertyModal.svelte`

Create/edit form, structurally mirroring `WorkModal.svelte`: name + emoji
picker, type select, status select, location dropdown (optional, sourced
from `locationsStore`, "— none —" option), address, price, land size, built
size, bedrooms, bathrooms, listing URL, contact (free text), two small
inline add/remove string-list editors for Pros and Cons, notes textarea,
`MediaGallery` for photo/PDF attachments (upload/view/delete), Save/Delete/
Cancel actions.

### `HomePropertiesWidget.svelte`

Added to `HomePage.svelte`'s side column alongside `HomeLocationsWidget`
and other `Home*Widget` components. Shown only when the `properties` module
is enabled and at least one property exists. Header "🏘 Properties" +
status count chips (Watching X · Visited X · Proposal X · ...) + up to 3
most-recently-added properties (name, price, status chip) — "recently
added" rather than "recently updated" since the truncate-and-reinsert
persistence pattern used here (same as Works/Locations) doesn't track a
modification timestamp; list order reflects insertion order. Click
navigates to `#/properties`. Mirrors `HomeLocationsWidget.svelte`.

### Routing

`NavMenu.svelte`: `properties` entry drops `placeholder: true`.
`App.svelte`: `{:else if currentRoute === "#/properties"}` renders
`<PropertiesPage store={propertiesStore} locationsStore={locationsStore} />`
instead of `PlaceholderPage`; `propertiesStore` initialized/reloaded
alongside the other per-home stores.

---

## 4. Testing

**Backend** (pytest, mirroring `test_works.py` / `test_works_persistence.py`
/ `test_mcp_tools_works.py`): CRUD for properties, attachment upload/get/
delete + cascade-delete on property delete, MCP tool coverage.

**Frontend** (vitest, mirroring `WorksPage.test.ts` / `worksStore.test.ts` /
`HomeWorksWidget.test.ts` where applicable): store CRUD + attachment
methods, table rendering/sort/filter (status + type + search), pros/cons
add/remove, location dropdown + resolution (including a deleted-location
edge case falling back to "—"), modal save/delete, widget rendering
(hidden when empty/disabled) and navigation.

**Manual verification** (webapp-testing skill, before calling the feature
done): add a project home, enable Properties, add listings of each type
(land / house / new-build), link one to an existing Location, move a
listing through several statuses, add pros/cons and a photo attachment,
confirm the table filters/sorts correctly and the home widget reflects
current data.
