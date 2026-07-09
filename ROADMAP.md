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

- **Unified activity timeline / audit log** — an admin-only Activity Log
  section in Settings showing "who did what" across Chores, Works, Costs,
  Inventory, Consumables, and Knowledge Base (create/update/delete, plus
  chore completion), with module/user/date filters and 90-day retention.
  See [`docs/superpowers/specs/2026-07-08-activity-log-design.md`](docs/superpowers/specs/2026-07-08-activity-log-design.md)
  and [`docs/superpowers/plans/2026-07-08-activity-log.md`](docs/superpowers/plans/2026-07-08-activity-log.md).

- **Automated scheduled backups** — daily/weekly/monthly scheduled backups
  with configurable retention (keep last N), a "Run backup now" manual
  trigger, and a browsable list in Settings with per-entry download/delete.
  Built on a second independent background scheduler loop alongside the
  notification digest. See
  [`docs/superpowers/specs/2026-07-07-scheduled-backups-design.md`](docs/superpowers/specs/2026-07-07-scheduled-backups-design.md)
  and [`docs/superpowers/plans/2026-07-07-scheduled-backups.md`](docs/superpowers/plans/2026-07-07-scheduled-backups.md).

- **Notification center** — surfaces chores due soon, low-stock consumables,
  and expiring inventory warranties in one place via a topbar bell/dropdown,
  with an optional daily digest pushed via Home Assistant's `notify`
  service (the first background scheduler in this codebase). See
  [`docs/superpowers/specs/2026-07-06-notification-center-design.md`](docs/superpowers/specs/2026-07-06-notification-center-design.md)
  and [`docs/superpowers/plans/2026-07-06-notification-center.md`](docs/superpowers/plans/2026-07-06-notification-center.md).

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

1. **Per-home granular permissions** — now that multi-home support exists,
   let a user's role be scoped per-home (e.g. Admin on their own home,
   RO on a shared/family home) instead of one global role.

2. **Home Assistant live sensor overlay on floor plan** — show live
   temperature/humidity/occupancy values as badges on rooms, extending the
   current static HA-area-label linkage into a live data overlay.

3. **Costs forecasting & budget dashboard** — project recurring bills
   (utilities, taxes) forward and compare actual vs. budget over time,
   building on the existing Costs module.

4. **Consumables shopping-list export / HA to-do sync** — turn "low stock"
   consumables into a shopping list that can be exported or pushed to a
   Home Assistant to-do list.

5. **User-uploadable furniture templates** — let users add their own SVG
   icons/templates to the floor plan furniture library instead of being
   limited to the built-in 39 templates.

6. **PWA / offline support** — make the app installable to a phone home
   screen with an app icon and basic offline caching, useful now that API
   tokens exist for future mobile/automation use cases.

7. **Insurance/asset-value report** — a one-click exportable PDF/CSV "home
   insurance inventory" built from data Inventory and Costs already track
   (purchase price, date, photos per item).

8. **Energy/utility usage tracking** — a module for meter readings/usage
   trends over time, complementing Costs (which tracks bills) with actual
   consumption data, to help catch anomalies like a leak or failing HVAC
   before the bill shows it.

9. **In-app AI chat** — surface the existing MCP server's 32 tools directly
   in the app via a chat panel ("when does my furnace warranty expire?",
   "log that I fixed the garbage disposal"), instead of only through
   external MCP clients.

10. **Document auto-extraction** — when a receipt or manual is uploaded to
    Inventory or Knowledge Base, use the same LLM/MCP plumbing to auto-fill
    warranty expiry, model number, and purchase price instead of manual
    entry.

11. **Scoped, time-boxed share links** — a read-only link to a single Work
    item or KB manual for a contractor/guest, without issuing a full
    account. Distinct from per-home permissions (idea 1): this is
    per-item, not per-home.

12. **ICS calendar export** — a subscribable feed of chore due-dates and
    scheduled works, for household members who'd rather check their
    phone's calendar than open the app.

13. **Outbound HA automation triggers** — the current Home Assistant
    integration is inbound-only (area labels, notify service); firing HA
    automations/webhooks *from* MyHome events (chore completed, consumable
    low) would close the loop.

14. **Mobile quick-capture flow** — point the phone camera at a receipt to
    auto-file it as a Costs entry or Inventory attachment. Pairs with the
    PWA idea (6) rather than replacing it.
