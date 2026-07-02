# Auth & API Tokens — Design Spec

**Date:** 2026-07-02  
**Status:** Approved

---

## Overview

Add authentication and user management to MyHome. The app currently has no auth — all API endpoints are publicly accessible. This spec covers:

1. Multi-user login with username + password
2. Three roles: Admin, Normal, RO (read-only)
3. JWT-based browser sessions (httpOnly cookies)
4. Opaque API tokens for automation, MCP server, and future mobile use
5. User management UI (admin only)
6. API token management UI in Settings (all users)

The design is OIDC-ready: the JWT validation middleware is structured to accept tokens from multiple issuers so a future Keycloak or other OIDC provider can be added without changing the protected route layer.

---

## Architecture

### Token Strategy (Option C)

- **Browser sessions** — short-lived JWT stored in an `httpOnly` cookie (`access_token`, 1h). Refresh via a long-lived `httpOnly` refresh token cookie (7d). The frontend never reads the JWT directly; it calls `/api/auth/me` on load to get user info.
- **API tokens** — opaque random strings (32 bytes, hex-encoded). Only the `sha256` hash is stored server-side. The full token is shown once on creation. Used as `Authorization: Bearer <token>` on all API calls from scripts, MCP, and future mobile.

### Backend New Files

| File | Purpose |
|---|---|
| `models_auth.py` | `User`, `ApiToken` Pydantic models |
| `persistence_auth.py` | Load/save `users.json` and `tokens.json` in `/data` |
| `routes/auth.py` | Auth endpoints (login, refresh, logout, user CRUD, token CRUD) |
| `deps.py` | `require_auth(min_role)` FastAPI dependency — validates JWT cookie or Bearer opaque token |

### Existing Files Changed

- `main.py` — include `auth.router`; apply `require_auth` globally via middleware or dependency on all `/api/*` routes except `/api/auth/login` and `/api/auth/refresh`
- `pyproject.toml` — add `python-jose[cryptography]`, `passlib[bcrypt]`

### Frontend New Files

| File | Purpose |
|---|---|
| `authStore.svelte.ts` | Current user state (`{id, username, role}`), loaded via `/api/auth/me` on app start |
| `LoginPage.svelte` | Full-page login form, shown when unauthenticated |

### Existing Files Changed

- `App.svelte` — import `authStore`; show `LoginPage` if not authenticated; add user menu to topbar
- `SettingsPage.svelte` — add "API Tokens" tab (all users) and "Users" tab (admin only)

---

## Data Models

### User

```
id: str          # nanoid
username: str    # unique, case-insensitive
password_hash: str  # bcrypt
role: "admin" | "normal" | "ro"
created_at: str  # ISO-8601
```

Stored in `/data/users.json` as `{"version": 1, "users": [...]}`.

### ApiToken

```
id: str          # nanoid
name: str        # human label, e.g. "Home Assistant MCP"
token_hash: str  # sha256 hex of the raw token
role: "admin" | "normal" | "ro"  # scope, capped at owner's role
owner_id: str    # user who created it
created_at: str  # ISO-8601
last_used_at: str | null
```

Stored in `/data/tokens.json` as `{"version": 1, "tokens": [...]}`.

---

## API Endpoints

### Auth

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/api/auth/login` | none | Username + password → sets `access_token` + `refresh_token` httpOnly cookies |
| POST | `/api/auth/refresh` | refresh cookie | Issues new `access_token` cookie |
| POST | `/api/auth/logout` | any | Clears both cookies |
| GET | `/api/auth/me` | required | Returns `{id, username, role}` — 401 if not authenticated |
| PUT | `/api/auth/me/password` | required | Change own password `{current_password, new_password}` |

### User Management (admin only)

| Method | Path | Description |
|---|---|---|
| GET | `/api/auth/users` | List all users (no password hashes) |
| POST | `/api/auth/users` | Create user `{username, password, role}` |
| PUT | `/api/auth/users/{id}` | Update role or password |
| DELETE | `/api/auth/users/{id}` | Delete user (cannot delete self) — cascades to delete all that user's API tokens |

### API Token Management (own tokens)

| Method | Path | Description |
|---|---|---|
| GET | `/api/auth/tokens` | List caller's tokens (no raw token, only metadata) |
| POST | `/api/auth/tokens` | Create token `{name, role}` → returns full token once |
| DELETE | `/api/auth/tokens/{id}` | Revoke token |

---

## Permission Model

The `require_auth(min_role)` dependency enforces a role hierarchy: `ro < normal < admin`.

| Endpoint class | Admin | Normal | RO |
|---|---|---|---|
| All GET data endpoints | ✓ | ✓ | ✓ |
| All PUT/POST/DELETE data endpoints | ✓ | ✓ | ✗ |
| User management endpoints | ✓ | ✗ | ✗ |
| Own token management | ✓ | ✓ | ✓ |
| Token scope ceiling | admin | normal | ro |

Token scope is validated on creation: `role` must be ≤ the creating user's role. If an admin creates a token with `role: "ro"`, that token can only access read endpoints even though the owner is an admin.

### OIDC Readiness

`deps.py` extracts the JWT validator into a pluggable interface. The initial implementation validates tokens signed with the local secret. A future OIDC provider is added by registering a second validator that fetches the provider's JWKS and accepts tokens from that issuer. Protected routes don't change — only the validator list grows.

---

## First-Boot Behaviour

If `/data/users.json` does not exist on startup, the server:
1. Generates a random 16-character password
2. Creates an `admin` user with username `admin`
3. Prints the credentials to stdout: `[myhome] First boot — admin password: <password>`

This avoids needing environment variables for initial setup while keeping the password auditable in container logs.

---

## Frontend Design

### Login Page

Full-page centered card (dark-themed, consistent with existing design tokens):

- App logo (🏠) + "MyHome" title
- Username field
- Password field  
- "Sign in" button
- Error banner shown after a failed attempt (not pre-emptively)
- Footer: "Contact your admin to create an account" (no self-registration)
- No "forgot password" flow in v1 — admin resets passwords via user management

On successful login the frontend calls `/api/auth/me`, stores `{id, username, role}` in `authStore`, and navigates to the original destination (or home).

### Topbar User Menu

Small avatar/initials chip in the top-right of the nav bar:
- Shows current username + role badge
- "Change password" action → modal with current password + new password fields
- "Sign out" action → calls `/api/auth/logout`, clears store, redirects to login

### Settings: API Tokens Tab

Visible to all roles.

- Table: **Name** | **Scope** | **Created** | **Last used** | **Revoke**
- "New token" button → modal:
  - Token name field (required)
  - Scope dropdown (options capped to the user's own role)
  - On submit: shows the full token in a copy-able text box with a warning: "This token will not be shown again. Copy it now."
- Revoke: confirm dialog → DELETE, row removed from table

### Settings: Users Tab

Visible to admin only.

- Table: **Username** | **Role** | **Created** | **Actions**
- "New user" button → modal: username + password + role dropdown
- Per row: "Edit role" (dropdown, cannot demote self) | "Reset password" (modal, new password only) | "Delete" (cannot delete self)

---

## Testing

### Backend

- `test_auth.py` — login happy path, wrong password → 401, token refresh, logout, `/me` before/after login
- `test_auth_users.py` — admin CRUD on users, non-admin blocked, self-delete blocked
- `test_auth_tokens.py` — create token, list, revoke, scope ceiling enforced, bearer auth on data endpoint
- `test_auth_roles.py` — RO token blocked on write endpoints, normal token blocked on user management
- Existing route tests updated: add auth fixtures (admin JWT cookie) to all existing test helpers

### Frontend

- `authStore.test.ts` — initial state, login sets user, logout clears user
- `LoginPage.test.ts` — renders form, shows error on failure, redirects on success
- `SettingsPage.test.ts` — tokens tab renders list, create modal, revoke; users tab admin-only gate

---

## Out of Scope (v1)

- Self-service account registration
- Forgot password / email reset flow
- OIDC / SSO (infrastructure is ready, not wired)
- Per-module granular permissions (e.g., RO on costs but normal on chores)
- Audit log of user actions
- Session listing / remote logout of other sessions
