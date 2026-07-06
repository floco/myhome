# Roadmap

This document tracks candidate next steps for MyHome. Ideas in **To Be Confirmed**
are exploratory — they need discussion and sign-off before any implementation
work starts (design spec + plan, per the usual workflow). The **Selected Idea**
section holds work that's already been decided on and is ready to move into
design.

---

## Selected Idea

### OIDC Integration

Extend authentication to support an external OIDC provider (e.g. Keycloak,
Authentik, Google Workspace) as an alternative to local username/password
login.

This builds directly on the `feat/auth-api-tokens` branch, merged to `main`
via PR #34 (2026-07-02). That spec
([`docs/superpowers/specs/2026-07-02-auth-api-tokens-design.md`](docs/superpowers/specs/2026-07-02-auth-api-tokens-design.md))
was explicitly written to be "OIDC-ready", with the intent that the JWT
validation layer could accept a second issuer without reworking the
protected-route layer.

Rough scope:
- Add an OIDC client (authorization code flow) alongside local login
- Map external claims to MyHome's existing role model (Admin / Normal / RO)
- Settings UI to configure issuer, client ID/secret, and enable/disable OIDC login
- Keep local username/password login available as a fallback (at least for the initial admin account)

**Next step:** write a design spec for OIDC following the same process as
prior features (in progress).

---

## To Be Confirmed

These are unvalidated ideas — pick, discuss, and refine scope before writing
a design spec for any of them.

1. **Global search / command palette** — a single `Cmd+K`-style search across
   Knowledge Base, Inventory, Works, Costs, and Chores, instead of searching
   each module separately.

2. **Notification center** — surface chores due soon, low consumable stock,
   and upcoming warranty/works expirations in one place, with optional
   push via Home Assistant's `notify` service.

3. **Automated scheduled backups** — build on the existing manual
   backup/restore (Settings) to add a scheduled job that produces backups
   on a cadence and prunes old ones, rather than requiring a manual click.

4. **Per-home granular permissions** — now that multi-home support exists,
   let a user's role be scoped per-home (e.g. Admin on their own home,
   RO on a shared/family home) instead of one global role.

5. **Home Assistant live sensor overlay on floor plan** — show live
   temperature/humidity/occupancy values as badges on rooms, extending the
   current static HA-area-label linkage into a live data overlay.

6. **Costs forecasting & budget dashboard** — project recurring bills
   (utilities, taxes) forward and compare actual vs. budget over time,
   building on the existing Costs module.

7. **Consumables shopping-list export / HA to-do sync** — turn "low stock"
   consumables into a shopping list that can be exported or pushed to a
   Home Assistant to-do list.

8. **Unified activity timeline / audit log** — a chronological feed of
   changes across modules (chore completions, works logged, costs added,
   inventory edits), plus a "who changed what" view once multi-user auth
   is in place.

9. **User-uploadable furniture templates** — let users add their own SVG
   icons/templates to the floor plan furniture library instead of being
   limited to the built-in 39 templates.

10. **PWA / offline support** — make the app installable to a phone home
    screen with an app icon and basic offline caching, useful now that API
    tokens exist for future mobile/automation use cases.
