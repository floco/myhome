# Move Donetick import to Settings → Integrations

## Problem

The "Import from Donetick" button/token-input currently lives inline in the
Chores page toolbar (`ChoresPage.svelte`). It's an admin/integration concern,
not a Chores-workflow concern, and it clutters the toolbar alongside
search/filter controls. Settings already has an Integrations panel
(`SettingsIntegrations.svelte`) with one admin-only card (MCP Server) — this
is the natural home for it.

## Decisions (confirmed with user)

- Fully remove the import UI from the Chores page; no shortcut/link left
  behind.
- Token is entered fresh each import, same as today — nothing new persisted.
- New Donetick card is admin-only, matching the existing MCP Server card's
  gating (`authStore.user?.role === "admin"`).
- Backend is unchanged: same `POST /api/homes/{home_id}/chores/import`
  endpoint and `choreStore.importFromDonetick` store method.

## Changes

**`packages/editor/src/lib/components/ChoresPage.svelte`**
Remove: the import toolbar block (button, token input, status message),
backing state (`showImportInput`, `importToken`, `importStatus`,
`importCount`), `handleImport()`, and the `.msg-error`/`.msg-success` styles
(unused elsewhere in the file after removal).

**`packages/editor/src/lib/components/settings/SettingsIntegrations.svelte`**
Add a new `Card` for "Donetick" below the MCP Server card, gated by the same
admin check. Contains: short description, password-type API token input,
Import button (disabled while loading, label toggles to "Importing…"),
inline status message (`"{n} imported"` on success, `"Failed"` on error).
New required prop: `importFromDonetick: (token: string) => Promise<number>`.

**`packages/editor/src/lib/components/SettingsPage.svelte`**
Accept new prop `importFromDonetick: (token: string) => Promise<number>` and
forward it to `<SettingsIntegrations>`.

**`packages/editor/src/App.svelte`**
Pass `importFromDonetick={choreStore.importFromDonetick}` into
`<SettingsPage>` (narrow function prop, not the whole store).

## Testing

- `test/SettingsIntegrations.test.ts`: extend with cases for the Donetick
  card — shows for admin, hidden for non-admin, successful import shows
  "N imported", failed import shows "Failed". Mock `importFromDonetick` prop.
- `test/ChoresPage.test.ts`: no existing cases reference Donetick/import;
  confirm suite still passes after removal (toolbar layout assertions, if
  any, shouldn't reference the removed controls).

## Out of scope

- Persisting/saving the token.
- Any backend endpoint or model changes.
- Changing MCP card behavior.
