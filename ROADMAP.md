# Roadmap

This document tracks candidate next steps for MyHome. Ideas in **To Be Confirmed**
are exploratory — they need discussion and sign-off before any implementation
work starts (design spec + plan, per the usual workflow). The **Selected Idea**
section holds work that's already been decided on and is ready to move into
design.

---

## Selected Idea

_(none currently — see To Be Confirmed below)_

---

## Recently Completed

- **OIDC Integration** — external OIDC provider login (Keycloak, Authentik,
  Google Workspace, etc.) alongside local username/password, with role
  mapping and a Settings UI. Merged via PR #44 (2026-07-06), hardened
  against silent local-account takeover via PR #45 (2026-07-06). See
  [`docs/superpowers/specs/2026-07-06-oidc-integration-design.md`](docs/superpowers/specs/2026-07-06-oidc-integration-design.md).

- **Global search / command palette** — a single `Cmd+K`-style search across
  Knowledge Base, Inventory, Works, Costs, Chores, and Consumables,
  client-side over already-loaded module stores. Merged via PR #43
  (2026-07-05). See
  [`docs/superpowers/specs/2026-07-05-global-search-design.md`](docs/superpowers/specs/2026-07-05-global-search-design.md).

---

## To Be Confirmed

These are unvalidated ideas — pick, discuss, and refine scope before writing
a design spec for any of them.

1. **Notification center** — surface chores due soon, low consumable stock,
   and upcoming warranty/works expirations in one place, with optional
   push via Home Assistant's `notify` service.

2. **Automated scheduled backups** — build on the existing manual
   backup/restore (Settings) to add a scheduled job that produces backups
   on a cadence and prunes old ones, rather than requiring a manual click.

3. **Per-home granular permissions** — now that multi-home support exists,
   let a user's role be scoped per-home (e.g. Admin on their own home,
   RO on a shared/family home) instead of one global role.

4. **Home Assistant live sensor overlay on floor plan** — show live
   temperature/humidity/occupancy values as badges on rooms, extending the
   current static HA-area-label linkage into a live data overlay.

5. **Costs forecasting & budget dashboard** — project recurring bills
   (utilities, taxes) forward and compare actual vs. budget over time,
   building on the existing Costs module.

6. **Consumables shopping-list export / HA to-do sync** — turn "low stock"
   consumables into a shopping list that can be exported or pushed to a
   Home Assistant to-do list.

7. **Unified activity timeline / audit log** — a chronological feed of
   changes across modules (chore completions, works logged, costs added,
   inventory edits), plus a "who changed what" view once multi-user auth
   is in place.

8. **User-uploadable furniture templates** — let users add their own SVG
   icons/templates to the floor plan furniture library instead of being
   limited to the built-in 39 templates.

9. **PWA / offline support** — make the app installable to a phone home
   screen with an app icon and basic offline caching, useful now that API
   tokens exist for future mobile/automation use cases.
