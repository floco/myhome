# Module Data Reset — Design

**Date:** 2026-07-30
**Status:** Approved, ready for planning

## Problem

There's no way to wipe just one module's data for a home. If chores get messy (e.g. after fiddling with Donetick or importing wrong data), the only escape hatch is deleting the whole home. Users need a per-module "reset" that clears that module's records while leaving everything else — other modules, categories/config, the home itself — untouched. Motivating case: reset Chores, then re-run the Donetick import for a clean pull.

## Scope

**In scope (11 modules):** Chores, Inventory, Consumables, Works, KB, Costs, Locations, Properties, Build, Contacts, Insurance.

**Out of scope:** Home and Plan. Both are structural — Home is the container itself, Plan is the floor plan/rooms that other modules' data points into (chore assignment positions, inventory pins, consumable placements). Resetting either is a different, riskier operation than this feature covers.

**Config/records split:** Reset always keeps shared configuration and deletes only the module's data records. Per-module breakdown:

| Module | Deleted | Kept |
|---|---|---|
| Chores | chores, assignments, completions, attachments | — |
| Inventory | items, attachments | — |
| Consumables | consumables, stock transactions | — |
| Works | work entries, attachments | — |
| KB | all pages + trash, attachments | — |
| Costs | cost entries, attachments | cost categories, suppliers |
| Locations | locations, ratings | evaluation criteria (acts as config) |
| Properties | property entries, attachments | — |
| Build | build project, phases, tasks, dependencies, attachments | — |
| Contacts | contacts | contact types |
| Insurance | policies, attachments | insurance categories |

**Accepted limitation:** some modules loosely reference rows in other modules (e.g. a Build task's `contractor_id` points at a Contact). Reset does not cascade-clean those cross-module references — a reference left dangling after a reset behaves the same way the UI already tolerates a deleted category (falls back / shows blank). Not addressed by this feature.

## Backend

**Endpoint:** `POST /api/homes/{home_id}/modules/{module_id}/reset`

- Admin-gated via `require_auth("admin")`, matching Delete Home and the Donetick import endpoint.
- `module_id` is validated against the 11-entry allowlist above. Anything else (including `home`/`plan`) returns 400.
- Dispatches to a per-module `reset(home_id)` function:
  - **Chores, Inventory, Works, Costs, Properties, Insurance:** `save_X(home_id, XDocument())` (empty document) to clear the SQLite rows, plus `shutil.rmtree()` of the module's `<module>-attachments/` directory under the home dir if it exists.
  - **Consumables, Contacts:** `save_X(home_id, XDocument())` only — no attachments directory exists for these modules.
  - **Build:** reuse the existing `delete_build_project(home_id)` in `persistence_build.py` unchanged — it already clears the project/phases/tasks/dependencies and removes `build-attachments/`.
  - **KB:** file-based, not a SQL document — `rmtree` the home's `kb/` and `kb-attachments/` directories directly.
  - **Locations:** bespoke — delete only the `locations` and `location_ratings` rows for the home; `location_criteria` is left alone. Cannot reuse `save_locations` with an empty document since that also clears criteria.
- On success, calls `log_activity(home_id, user_id, module_id, "reset", ...)`. Extends `ACTION_VERBS` in `persistence_activity.py` with a `"reset"` entry, and special-cases `describe()` for that action to render module-level text (e.g. "reset chore data") rather than the normal "verb noun 'label'" shape, since there's no single entity label for a module-wide wipe.
- Returns `204 No Content` on success.

## Frontend

- `SettingsGeneral.svelte`: each of the 11 resettable module rows (in the existing module-activation list) gets a small "Reset" button, styled like the existing ghost-variant `Edit`/`Change` buttons in the same card. Shown regardless of whether the module is currently enabled/disabled, since data can exist while a module is hidden.
- Clicking it opens a `Modal` (same pattern as the existing Delete-Home confirmation): names the module, states what will be deleted and what's kept, Cancel/Reset buttons.
- On confirm, calls a new `resetModuleData(homeId, moduleId)` function in `homesStore.svelte.ts` (`POST` to the new endpoint, mirroring `deleteHome`'s fetch shape). On success: close the modal, show a brief inline success message in the card.
- No proactive refresh of other modules' in-memory stores — each module page already reloads its data from the API on mount/navigation, so the reset is reflected next time the user visits that module.
- New i18n keys (English + French) under the existing `settings.general.*` namespace: button label, per-module modal title/body text, success message.

## Testing

- Backend: one test per module's `reset()` persistence function (data cleared, config preserved, attachments directory removed where applicable), plus route-level tests for the endpoint (403 for non-admin, 400 for invalid `module_id`, 400/404 for `home`/`plan`, 204 + activity log entry on success, and a check that other modules' data for the same home is untouched).
- Frontend: `SettingsGeneral` component tests for the reset button/modal appearing per module, confirm-triggers-API-call, and the success message rendering.

## Non-goals

- No bulk "reset multiple modules at once."
- No cross-module reference cleanup (see Accepted limitation above).
- No undo — this is a destructive, admin-gated action with an explicit confirm modal, same trust model as Delete Home.
