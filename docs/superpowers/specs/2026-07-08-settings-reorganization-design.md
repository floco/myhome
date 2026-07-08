# Settings Page Reorganization

## Problem

`SettingsPage.svelte` has grown to 1840 lines and 14 stacked sections rendered
on one long scrolling page: Home, Modules, Cost categories, Inventory
categories, Work categories, Suppliers, Consumables, Notifications, API
Tokens, Users, MCP Server, Single Sign-On, Backup & Restore (+ Scheduled
Backups), Activity Log. This is hard to navigate and hard to maintain.

## Goal

Reorganize Settings into a small number of named groups navigable via a
vertical sidebar, without changing the behavior of any individual section.

## Navigation

- A vertical sidebar (`SettingsNav.svelte`) lists the visible groups as
  icon+label buttons. Clicking a group shows only that group's panel.
- Active group is local Svelte `$state` in `SettingsPage.svelte`, default
  `"general"`. This is client-side only — no route/URL changes. Reloading
  Settings or navigating away and back resets to General.
- Groups are filtered per the current user's role before being handed to the
  nav: a group is included only if it has at least one visible section for
  that role.
- Responsive behavior is CSS-only (no JS breakpoint/resize listeners):
  - Above the breakpoint: `.page` is a flex row — nav column on the left,
    content on the right.
  - Below the breakpoint: nav renders as a `<select>` dropdown at the top of
    a single-column layout, driving the same `activeGroup` state. Both
    markup variants exist in `SettingsNav.svelte`; CSS media queries decide
    which is visible.

## Groups and content mapping

1. **General** — Home metadata (name, type, delete home), Modules (core /
   project module toggles)
2. **Categories** — Cost categories, Inventory categories, Work categories,
   Suppliers, Consumables (units + categories), each as its own tab within
   this group
3. **Notifications** — Notification center settings
4. **Security & Access** — API Tokens (all roles), Users (admin only), Single
   Sign-On (admin only). Visible to all roles because API Tokens is
   non-admin-visible; admin-only rows within it hide individually as they do
   today.
5. **Integrations** — MCP Server (admin only). Entire group hidden for
   non-admin users.
6. **Backup & Restore** — Backup & Restore actions, Scheduled Backups
   (config + history table)
7. **Activity Log** — Activity log viewer (admin only). Entire group hidden
   for non-admin users.

## Categories group internals

`SettingsCategories.svelte` holds its own `activeTab` state
(`"cost" | "inventory" | "work" | "suppliers" | "consumables"`) and renders
the existing `Tabs.svelte` component with those 5 entries. Only the selected
subsection's card is shown at a time — a behavior change from today (all 5
shown stacked) to one-at-a-time, matching the sub-tab pattern already used
elsewhere in the app.

## Component split

`SettingsPage.svelte` becomes a thin shell: renders `SettingsNav.svelte`,
tracks `activeGroup`, and renders the matching panel component below. All
props (`store`, `authStore`) pass through unchanged.

New files under `packages/editor/src/lib/components/settings/`:

- `SettingsGeneral.svelte`
- `SettingsCategories.svelte`
- `SettingsNotifications.svelte`
- `SettingsSecurity.svelte`
- `SettingsIntegrations.svelte`
- `SettingsBackup.svelte`
- `SettingsActivityLog.svelte`

Each panel component owns the `$state`, fetch calls, and markup that
currently live inline in `SettingsPage.svelte` for its section(s). This is a
pure decomposition: no logic changes, no API changes, no persisted-state
changes (aside from `activeGroup`/`activeTab` being new ephemeral UI state).

`SettingsNav.svelte` is new, under
`packages/editor/src/lib/components/settings/`.

## Testing

`SettingsPage.test.ts` is split to mirror the component split:

- A slim `SettingsPage.test.ts` covering: nav renders the correct groups for
  a given role, clicking a group switches the visible panel, the mobile
  dropdown variant is present in the markup.
- One test file per panel component (e.g. `SettingsCategories.test.ts`,
  `SettingsSecurity.test.ts`, ...) carrying over the existing assertions for
  that section's behavior, relocated rather than rewritten.

## Out of scope

- No changes to any section's underlying behavior, API calls, or data model.
- No URL/routing changes.
- No new settings or removed settings.
