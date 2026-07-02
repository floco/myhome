# Multi-Home Support

**Date:** 2026-07-02
**Status:** Approved

## Overview

Allow users to create and manage multiple homes within the app, switching between them from the side nav. Each home is fully isolated: its own data, module configuration, and settings. Two home types determine default enabled modules: **Existing home** (fully operational property) and **Project home** (location scouting, land search, or construction in progress).

---

## 1. Data Model & Backend

### Homes registry

`/data/homes.json` — the authoritative list of all homes.

```json
{
  "version": 1,
  "homes": [
    {
      "id": "home-abc123",
      "name": "Rue des Lilas",
      "type": "existing",
      "enabledModules": ["home", "plan", "chores", "inventory", "consumables", "works", "kb", "costs"],
      "createdAt": "2026-07-02T12:00:00Z"
    }
  ]
}
```

### Per-home data directory

Each home stores its data in `/data/homes/{home-id}/`:
- `house.json`, `chores.json`, `costs.json`, `inventory.json`, `works.json`, `kb.json`, `consumables.json`, `settings.json`
- Attachment subdirectories: `chores-attachments/`, `costs-attachments/`, `inventory-attachments/`, `works-attachments/`, `kb-attachments/`

### API routes

New homes management endpoints:
- `GET /api/homes` — list all homes
- `POST /api/homes` — create a home (body: `{name, type}`)
- `PATCH /api/homes/{id}` — update name, type, or enabledModules
- `DELETE /api/homes/{id}` — delete a home and all its data

All existing module endpoints get a home ID prefix:
- `GET /api/homes/{id}/house` (was `/api/house`)
- `GET /api/homes/{id}/chores` (was `/api/chores`)
- `GET /api/homes/{id}/costs` (was `/api/costs`)
- … same pattern for inventory, works, kb, consumables, settings, svg, ha

### Persistence layer

All persistence functions gain a `home_id: str` parameter and resolve paths to `/data/homes/{home_id}/`. A new `persistence_homes.py` handles the registry CRUD.

### Migration

On first startup, if `/data/homes.json` is absent but flat legacy files exist (e.g. `/data/house.json`), the backend auto-migrates:
1. Creates a default home entry (`id: "default"`, `type: "existing"`, all modules enabled).
2. Moves all existing flat files into `/data/homes/default/`.
3. Writes `/data/homes.json`.

---

## 2. Home Types & Modules

### Module IDs

`home`, `plan`, `chores`, `inventory`, `consumables`, `works`, `kb`, `costs`, `locations`, `properties`, `budget`, `visits`, `contacts`, `checklist`

### Default enabled modules by type

| Module | Existing home | Project home |
|---|---|---|
| Home (dashboard) | ✅ | ✅ |
| Floor Plan | ✅ | ✅ |
| Works | ✅ | ✅ |
| Knowledge Base | ✅ | ✅ |
| Chores | ✅ | — |
| Inventory | ✅ | — |
| Consumables | ✅ | — |
| Costs | ✅ | — |
| Locations 🌍 | — | — |
| Properties 🏘 | — | — |
| Budget 💰 | — | — |
| Visits 📅 | — | — |
| Contacts 👤 | — | — |
| Checklist ✅ | — | — |

Project placeholder modules are off by default for both types. The user enables them individually in Settings.

### Placeholder modules (Phase 1 scope)

The six project modules are wired into the nav and Settings toggle list but show a "Coming soon" screen when navigated to. They have no backend routes or data storage in this phase. This scaffolding allows future independent implementation without touching the multi-home layer.

| Module | Icon | Purpose |
|---|---|---|
| Locations | 🌍 | Compare countries, cities, neighborhoods with notes and ratings |
| Properties | 🏘 | Track candidate plots/homes with specs, price, pros/cons |
| Budget | 💰 | Purchase + build cost scenarios, financing options |
| Visits | 📅 | Log property/site viewings with date, notes, photos, rating |
| Contacts | 👤 | Agents, notaries, architects, contractors |
| Checklist | ✅ | Due diligence items, permits, legal steps to verify |

---

## 3. Frontend

### Home switcher (side nav — top slot)

A compact component sits above the module list:
- **Collapsed:** home type icon (🏠 existing / 🏗 project) + home name, truncated
- **Expanded (click):** inline dropdown listing all homes; "+ New home" at the bottom
- Selecting a home switches context; "+ New home" opens the creation modal

### Zero-homes state

If the homes list is empty on app load (fresh install with no legacy data), the app shows a full-screen "Create your first home" prompt instead of the normal layout — same form as the creation modal but without the cancel option. The user must create at least one home before accessing any module. The "Delete this home" action in Settings is disabled (greyed out) when only one home exists, preventing the zero-homes state at runtime.

### New home creation modal

Fields: home name (text input), home type (radio: "Existing home" / "Project home" with a short description of each). On confirm: backend creates the home, frontend switches to it immediately.

### Home switching

A top-level `homesStore` holds the homes list and `activeHomeId`. On switch:
1. `activeHomeId` updates.
2. All module stores detect the change and reload from the new home's API endpoints.
3. The current route is preserved where the module exists in the new home; otherwise redirects to `#/`.

### Module visibility

`NavMenu` renders only modules present in `enabledModules` of the active home:
- **Enabled, implemented:** normal nav entry
- **Enabled, placeholder:** dimmed entry labelled "Soon"
- **Disabled:** not rendered

Settings is always accessible regardless of `enabledModules`.

### API calls

All store fetch/save calls include `activeHomeId` in the URL path (e.g. `/api/homes/${activeHomeId}/chores`). Stores import `activeHomeId` from `homesStore`.

---

## 4. Settings

### New: Home section (top of Settings page)

- Home name — editable inline
- Home type — badge (Existing / Project), editable via dropdown
- "Delete this home" — danger action; disabled if only one home exists; requires confirmation dialog ("Delete [name]? This permanently removes all data for this home.")

### New: Modules section (below Home section)

Toggle list grouped in two categories:

**Core modules:** Home, Floor Plan, Chores, Inventory, Consumables, Works, Knowledge Base, Costs

**Project modules (placeholder):** Locations, Properties, Budget, Visits, Contacts, Checklist

Toggling a module off when it has existing data shows a warning: "This hides [Module] but does not delete your data." Toggle state is saved immediately via `PATCH /api/homes/{id}`.

### Existing sections

Cost categories, inventory categories, work categories, suppliers, consumable units, API tokens — all remain **per-home** (each home has its own `settings.json`). No changes to their structure.

---

## 5. Out of Scope

- Sharing data between homes
- Per-user access control (multi-user is a separate concern)
- Implementation of placeholder module data/backend (future specs per module)
- Export/import of individual homes
