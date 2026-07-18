# Locations Module — Design Spec

**Date:** 2026-07-18
**Status:** Approved

## Overview

A comparison tool for evaluating candidate locations (countries, cities, regions) against a set of criteria — used when scouting a new house or planning a relocation/retirement move. Replaces the existing `#/locations` placeholder (see `docs/superpowers/specs/2026-07-02-multi-home-design.md`), which already reserves the module id, nav entry (🌍), and "Coming soon" screen for Project homes.

One comparison lives per Project home — as many candidate locations as the user wants (3+), compared against a customizable, weighted list of criteria. Each location × criterion cell holds a 1–5 score plus a free-text note. The page visually surfaces both the best location per individual criterion and the best location overall (weighted).

Out of scope: floor-plan pins (these are prospective places, not the user's own home), multiple named comparisons per home, map/geocoding integration.

---

## 1. Data Model

### LocationCriterion

```
id:           str
name:         str
description:  str = ""
weight:       Literal["low", "medium", "high"] = "medium"   # multiplier 1 / 2 / 3
order:        int
```

### Location

```
id:     str
name:   str
emoji:  str = "📍"
order:  int
```

### Rating

Sparse — an entry exists only once a cell has been scored or noted.

```
locationId:   str
criterionId:  str
score:        int | null   # 1-5
note:         str = ""
```

### LocationsDocument

```
version:    int = 1
criteria:   list[LocationCriterion]
locations:  list[Location]
ratings:    list[Rating]
```

Stored in `locations.json` under the home's data directory.

### Default criteria seed

When a new home with `type: "project"` is created, `locations.json` is initialized with these 11 default criteria (weight `"medium"`, no locations yet), fully editable/removable/reorderable, and the user can add their own:

| Name | Description |
|---|---|
| Geography & Climate | Geographic location, climate patterns, seasonal temperatures. |
| Cost of Living | Cost of land, construction, everyday goods and services relative to your budget. |
| Healthcare | Quality and accessibility of the healthcare system, especially for retirement. |
| Taxation | Tax rules and residency implications for foreign residents. |
| Language & Culture | Local language and your comfort with it; familiarity and appeal of the local culture. |
| Social Network & Community | Presence of an existing community/family nearby and opportunities for social integration. |
| Safety | Personal and property safety in the area. |
| Access to Services | Proximity to essential services: hospitals, shops, etc. |
| Mobility & Transport | Airports, roads, and public transport connections. |
| Real Estate Regulations | Building and zoning regulations that would apply. |
| Quality of Life | Overall subjective quality of life in the area. |

Existing homes (any other `type`) never get a `locations.json`; the module is hidden unless enabled via `enabledModules` (existing multi-home mechanism).

---

## 2. Backend

Standalone module following the pattern of Consumables/Works/Costs: new files only.

### New files

| File | Purpose |
|------|---------|
| `models_locations.py` | Pydantic models: `LocationCriterion`, `Location`, `Rating`, `LocationsDocument`, plus Create/Update variants |
| `persistence_locations.py` | Read/write `locations.json`; seeds default criteria on project-home creation |
| `routes/locations.py` | REST routes |
| `mcp_tools_locations.py` | MCP tool exposure, for parity with every other content module |

### REST API

```
GET    /api/homes/{id}/locations

POST   /api/homes/{id}/locations/criteria                → create criterion (appended, weight defaults "medium")
PUT    /api/homes/{id}/locations/criteria/{cid}           → update name/description/weight
DELETE /api/homes/{id}/locations/criteria/{cid}           → delete criterion + cascade-delete its ratings
PUT    /api/homes/{id}/locations/criteria/reorder          → body: ordered list of criterion ids

POST   /api/homes/{id}/locations/locations                 → create location
PUT    /api/homes/{id}/locations/locations/{lid}           → update name/emoji
DELETE /api/homes/{id}/locations/locations/{lid}           → delete location + cascade-delete its ratings
PUT    /api/homes/{id}/locations/locations/reorder          → body: ordered list of location ids

PUT    /api/homes/{id}/locations/ratings/{lid}/{cid}        → upsert {score, note}
DELETE /api/homes/{id}/locations/ratings/{lid}/{cid}        → clear cell back to unscored (removes the Rating entry)
```

Scoring/ranking math is computed client-side from raw ratings — the backend just stores the sparse rating list.

---

## 3. Frontend

### `LocationsPage.svelte`

Replaces `PlaceholderPage` on route `#/locations`. Two stacked sections, following the existing "summary chart + detail card" layout used on Costs/Chores/Inventory/Consumables:

**Ranking chart (top):** horizontal bar per location showing its weighted overall score — `Σ(score × weight) / Σ(weight)` over that location's *rated* criteria only (unrated criteria neither help nor hurt it). Bars sorted descending; the top location (ties included) gets a crown/badge. A location with zero rated criteria displays "—" and sorts last.

**Comparison matrix (below):** rows = criteria (ordered list, each row tagged with its Low/Med/High weight), columns = locations. Each cell renders a color-coded score badge (red → green across 1–5) plus a truncated note preview. Clicking a cell opens a floating popover (same interaction pattern as `ConsumablePinPopup`) with a 1–5 score picker and a note textarea, Save/Clear actions. The best score(s) in each row get a highlight ring — ties highlight every matching cell; a row with no ratings at all gets no highlight.

**Managing criteria:** "+ Add criterion" affordance in the matrix; each row has inline edit (name/description/weight) and delete, plus up/down reorder buttons (no drag-and-drop — kept simple).

**Managing locations:** "+ Add location" affordance in the matrix header; each column has inline edit (name/emoji) and delete, plus left/right reorder buttons.

### `HomeLocationsWidget.svelte`

Added to `HomePage.svelte`'s side column alongside the other `Home*Widget` components — shows the current top-ranked location and a mini version of the ranking bar chart, links to `#/locations`.

### Routing

`NavMenu.svelte`: `locations` entry drops `placeholder: true`.
`App.svelte`: `{:else if currentRoute === "#/locations"}` renders `LocationsPage` instead of `PlaceholderPage`.

### Store

`locationsStore.svelte.ts` — fetch/cache `LocationsDocument`, CRUD methods mirroring the REST routes, plus derived helpers for per-location weighted score and per-criterion best-score lookup (used by both the chart and the matrix highlight logic).

---

## 4. Testing

**Backend** (pytest, mirroring `test_consumables.py` / `test_consumables_persistence.py` / `test_mcp_tools_consumables.py`): CRUD for criteria/locations/ratings, cascade deletes, default-seed-on-project-home-creation, reorder endpoints, MCP tool coverage.

**Frontend** (vitest, mirroring `ConsumablesPage.test.ts` / `consumableStore.test.ts` / `HomeConsumablesWidget.test.ts`): store CRUD + derived score/highlight logic (including tie handling and all-blank-row handling), matrix rendering, cell popover open/save/clear, criteria/location add/edit/delete/reorder, widget rendering and navigation.

**Manual verification** (webapp-testing skill, before calling the feature done): create a Project home, add 3+ locations, edit/add criteria with different weights, rate several cells, confirm the ranking chart and best-per-row highlights update correctly, confirm ties render sanely.
