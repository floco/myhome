# MCP Server — Design Spec

**Date:** 2026-07-04
**Status:** Approved

---

## Overview

Add a Model Context Protocol (MCP) server to MyHome so an LLM assistant (Claude Desktop, claude.ai, Claude Code, or Home Assistant's Assist via its MCP client integration) can query and act on the app's data — chores, inventory, consumables, costs, works, and knowledge base. The server is gated by an admin-only toggle in Settings and reuses the existing API token auth model (added in the auth/API-tokens spec) rather than inventing new authorization.

---

## Architecture

The MCP server runs **in-process** with the existing FastAPI backend — not a separate service or port. It uses the official `mcp` Python SDK's `FastMCP`, mounted as a sub-app at `/mcp` using the Streamable HTTP transport. This transport works for both remote Claude connectors and Home Assistant's MCP client integration.

Because `/mcp` is just another path in the same FastAPI app, it flows through the **existing global auth middleware** (`main.py`) unchanged — a request needs a valid session cookie or `Bearer <api-token>` or it is rejected before reaching MCP code. Tool handlers read `request.state.user` (already set by that middleware) to get the caller's `(user_id, role)` and apply the same `ROLE_ORDER` check (`ro < normal < admin`) used elsewhere — write tools require `normal`+, matching how the REST API gates POST/PUT/DELETE.

Tool implementations call the same persistence functions the REST routes already call (`load_chores`/`save_chores`, etc.) directly in-process, not via a self-HTTP round trip. This keeps MCP behavior identical to the REST API by construction — same code path, same data files.

### New Backend Files

| File | Purpose |
|---|---|
| `mcp_server.py` | Builds the `FastMCP` instance and registers all tools |
| `models_mcp.py` | `McpConfig` Pydantic model (`{enabled: bool}`) |
| `persistence_mcp.py` | Load/save `mcp_config.json` in `/data` |
| `routes/mcp_config.py` | `GET`/`PUT /api/mcp/config` (admin-only) |

### Existing Files Changed

- `main.py` — mount the MCP sub-app at `/mcp`; gate it with a check against `mcp_config.json`'s `enabled` flag (404 when disabled)
- `pyproject.toml` — add `mcp` dependency

### Frontend Changed

- `SettingsPage.svelte` — new "MCP Server" card (admin-only): toggle + connection URL + short instructions pointing at the existing API Tokens section

---

## Home Scoping

Every module tool takes an optional `home_id` parameter. Resolution:

1. If `home_id` is provided, validate it exists.
2. If omitted and the caller has exactly one home, auto-resolve to that home.
3. If omitted and there are multiple homes, return an error listing valid home IDs/names (call `list_homes` first).

This mirrors the REST API's `/api/homes/{home_id}/...` path structure with no new server-side "active home" concept (none exists today — `activeHomeId` is a frontend-only, in-memory value).

---

## Tool Surface

One tool per meaningful operation, grouped by module:

| Module | Tools |
|---|---|
| Homes | `list_homes`, `create_home`, `update_home`, `delete_home` |
| Settings | `get_settings` (read-only — categories/suppliers/units, so the caller can find valid `categoryId`/`supplierId` values) |
| Chores | `list_chores`, `create_chore`, `update_chore`, `delete_chore`, `complete_chore`, `undo_chore_completion` |
| Inventory | `list_inventory_items`, `create_inventory_item`, `update_inventory_item`, `delete_inventory_item` |
| Consumables | `list_consumables`, `create_consumable`, `update_consumable`, `delete_consumable`, `adjust_consumable_stock` |
| Costs | `list_cost_entries`, `create_cost_entry`, `update_cost_entry`, `delete_cost_entry` |
| Works | `list_works`, `create_work`, `update_work`, `delete_work` |
| KB | `list_kb_entries`, `create_kb_entry`, `update_kb_entry`, `delete_kb_entry` |

Tool input schemas mirror the corresponding `*Create`/`*Update` Pydantic models already used by the REST routes (e.g. `create_chore` takes the same fields as `ChoreCreate`).

`delete_home`'s tool description explicitly notes the cascade (deletes all data for that home), matching the warning already shown in the UI's delete-home confirmation dialog.

### Explicitly Out of Scope

- File/attachment upload endpoints (binary request bodies)
- Floor-plan pin/placement/position endpoints (all modules)
- Raw floor-plan house document (`GET`/`PUT .../house`)
- Backup/restore (binary, whole-system, destructive)
- Settings category/supplier/unit *mutation* (bulk-replace semantics; `get_settings` stays read-only)
- Chore room-assignment creation (`POST /assignments`) and per-assignment position/due-date update

---

## Auth & Permissions

- Read tools (`list_*`, `get_*`) work with any token role (`ro`+).
- Write tools (`create_*`, `update_*`, `delete_*`, `complete_*`, `undo_*`, `adjust_*`) require `normal`+; called with a `ro` token, they return an MCP tool error equivalent to the REST API's 403.
- No new token type or auto-provisioned token — the existing API Tokens section in Settings is the only way to mint credentials for MCP clients. The token-creation UI already anticipated this (its placeholder text says "e.g. Home Assistant MCP").

---

## Settings UI & Activation

New global config file `mcp_config.json` (alongside the existing `users.json`/`tokens.json` at the `DATA_DIR` root — global, not per-home, since this is an integration on/off switch, not home data): `{"enabled": bool}`.

New endpoints, admin-only (same pattern as user management):

| Method | Path | Description |
|---|---|---|
| GET | `/api/mcp/config` | Returns `{enabled}` |
| PUT | `/api/mcp/config` | Sets `{enabled}` |

**Settings page** gets a new "MCP Server" card, visible only to admins:

- Toggle: "Enable MCP Server" — flips the flag; when off, `/mcp` returns 404 for all requests.
- When on, shows the connection URL (derived from `window.location.origin` + `/mcp`) and a short note: "Create an API token above with the access level you want the assistant to have, then use it as the Bearer token when connecting."

---

## Testing

### Backend

- `test_mcp_config.py` — toggle persistence, admin-only gate (non-admin gets 403), `/mcp` returns 404 when disabled
- `test_mcp_tools.py` — each tool exercised against a real token fixture:
  - Happy path (list/create/update/delete/complete) per module
  - Write tool called with a `ro`-scoped token → permission error
  - Multi-home ambiguity error when `home_id` omitted and >1 home exists
  - Single-home auto-resolve when `home_id` omitted and exactly 1 home exists

### Frontend

- `SettingsPage.test.ts` additions: MCP card renders admin-only, shows connection URL when enabled, hides URL/instructions when disabled, non-admin doesn't see the card at all

### Manual Verification

Connect an actual MCP client (e.g., Claude Desktop config pointed at a local dev instance, or `mcp inspector`) and drive one read tool and one write tool end-to-end. Protocol-level behavior (tool schema negotiation, Streamable HTTP handshake) isn't exercised by the Python test suite and needs a real client round-trip before calling this done.

---

## Out of Scope (v1)

- Per-tool granular permission overrides beyond the token's role
- Auto-provisioned "MCP" token
- Settings category create/update/delete via MCP
- File/attachment tools
- Floor-plan/geometry tools
- stdio transport (Streamable HTTP only — this is a remote/network addon, not a local CLI tool)
