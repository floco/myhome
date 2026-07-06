# OIDC Integration — Design Spec

**Date:** 2026-07-06
**Status:** Approved

---

## Overview

Add support for logging into MyHome via an external OIDC provider (e.g. Keycloak,
Authentik, Google Workspace) as an alternative to local username/password login.
This builds on the auth system added in `feat/auth-api-tokens` (merged via PR #34,
2026-07-02): multi-user login, JWT session cookies, opaque API tokens, and an
Admin/Normal/RO role model.

That spec described itself as "OIDC-ready" via a pluggable multi-issuer JWT
validator. In practice `deps.py` only validates locally-signed JWTs against a
single secret today — this spec does not extend that validator to accept
IdP-issued tokens directly. Instead, OIDC is handled as a **federated login
that mints MyHome's own local session** (see Architecture). This keeps the
protected-route layer (`require_auth`, `deps.py`) completely unchanged.

Scope: a single configured OIDC provider (not multiple simultaneous
providers), authorization code flow with PKCE.

---

## Architecture

### Login flow

1. Login page shows a "Sign in with `<provider_name>`" button when OIDC is
   enabled (fetched from a public status endpoint). Clicking it navigates to
   `GET /api/auth/oidc/login`.
2. Backend generates `state`, a PKCE code verifier, and a `nonce`; stores them
   in a short-lived signed httpOnly cookie (`oidc_flow`, ~10 min expiry);
   redirects the browser to the IdP's authorization endpoint (discovered from
   the configured issuer URL via `/.well-known/openid-configuration`, cached
   after first fetch) with `code_challenge`, `state`, `nonce`, and
   `scope=openid profile email`.
3. User authenticates at the IdP. IdP redirects to
   `GET /api/auth/oidc/callback?code=...&state=...`.
4. Backend validates `state` against the `oidc_flow` cookie, exchanges `code`
   + verifier for tokens at the token endpoint, and validates the ID token's
   signature (via cached JWKS) and claims (`iss`, `aud`, `nonce`, `exp`).
5. Backend extracts `preferred_username` (fallback: local part of `email`)
   from the ID token/userinfo response. Looks up a local user by username,
   case-insensitive:
   - **Match found** → treat this login as that existing user (keeps their
     role, tokens, history).
   - **No match** → JIT-provision a new local user with `auth_provider:
     "oidc"`, `password_hash: null`, and the role from `OidcConfig.default_role`.
6. Backend mints MyHome's own access/refresh JWT cookies exactly as password
   login does (`_set_auth_cookies`), clears the `oidc_flow` cookie, and
   redirects to the app. **No change to `deps.py` or `require_auth`** — every
   authenticated request after login looks identical regardless of how the
   session started.

### Library

Use **Authlib** for discovery, PKCE, code exchange, and ID-token/JWKS
validation rather than hand-rolling that logic — it's security-sensitive code
better delegated to a vetted library, and complements the existing
`python-jose`/`passlib` dependencies used for local auth.

---

## Data Model

### `User` (modified, in `models_auth.py`)

```
password_hash: str | None   # was required; OIDC-only users have none until they set one
auth_provider: "local" | "oidc"   # new, informational
```

No other existing fields change. Existing local users get `auth_provider: "local"`
via a default on load (no migration script needed — Pydantic default handles it).

### `OidcConfig` (new)

```
enabled: bool
provider_name: str        # display label, e.g. "Keycloak"
issuer: str                # e.g. https://auth.example.com/realms/home
client_id: str
client_secret: str
default_role: "admin" | "normal" | "ro"
scopes: list[str]          # default ["openid", "profile", "email"]
```

Stored in `/data/oidc_config.json` as `{"version": 1, "config": {...}}`. Admin-only,
analogous to `users.json`/`tokens.json` persistence.

---

## API Endpoints

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/auth/oidc/status` | none | `{enabled, provider_name}` — used by the login page to conditionally render the SSO button before authentication |
| GET | `/api/auth/oidc/config` | admin | Full config; `client_secret` masked (`••••`) once set, same pattern as API tokens |
| PUT | `/api/auth/oidc/config` | admin | Create/update config. Validates the issuer's discovery document is reachable before persisting; 422 with the discovery error if not |
| GET | `/api/auth/oidc/login` | none | Redirects to the IdP's authorization endpoint |
| GET | `/api/auth/oidc/callback` | none | Handles the IdP redirect: token exchange, ID-token validation, user provisioning/linking, local session mint |

---

## Frontend Design

### Settings: "Single Sign-On" tab (new, admin-only)

Alongside the existing Users / API Tokens tabs:
- Enable toggle
- Provider display name (free text, e.g. "Keycloak")
- Issuer URL
- Client ID
- Client secret (write-only input; shows masked once saved, with a "Change" action to overwrite)
- Default role dropdown (Admin / Normal / RO)
- Read-only "Redirect URI" field showing `<app base url>/api/auth/oidc/callback`,
  for the admin to paste into their IdP's client registration
- Save validates discovery reachability inline; shows the error under the
  issuer field if unreachable

### Login Page

- On mount, fetches `/api/auth/oidc/status`.
- If `enabled`, renders a "Sign in with `<provider_name>`" button. Local
  username/password form remains visible at all times — OIDC never hides or
  replaces it, per the always-available fallback decision.
- Error banner (existing pattern) also triggers on `?error=oidc_failed` query
  param, shown after a redirect back from a failed OIDC attempt.

---

## Error Handling

- IdP returns an error param at the callback, or `state`/`nonce` validation
  fails, or the `oidc_flow` cookie is missing/expired → redirect to
  `/login?error=oidc_failed`; existing login error banner displays a generic
  "Sign-in failed, please try again" message.
- Login attempted with a username whose `password_hash` is `null` → 401
  "No local password set for this account" instead of a crash in
  `pwd_ctx.verify`. (Change-password on a `null` hash is handled as a "set"
  path, not an error — see Edge Cases.)
- OIDC config save with an unreachable/invalid issuer discovery document →
  422, surfaced inline in the Settings form.

## Edge Cases

- An OIDC-provisioned user can set a local password later via the existing
  "change password" endpoint: if `password_hash` is currently `null`, the
  `current_password` check is skipped and `new_password` is hashed and saved
  directly (treated as "set" rather than "change"). After that, both login
  methods work for that account.
- Deleting a user via the existing Users tab works identically regardless of
  `auth_provider`; cascades to that user's API tokens as today.
- If an admin renames their local username after OIDC was set up, the next
  OIDC login won't match and will JIT-provision a second account — accepted
  limitation (see Out of Scope: linking by stable subject ID).

---

## Testing

### Backend

- `test_auth_oidc.py`:
  - Config CRUD: admin-only access, secret masking on read, 422 on
    unreachable-issuer save
  - `/api/auth/oidc/status` returns `{enabled, provider_name}` with no auth
    and never leaks the secret
  - `/api/auth/oidc/login` builds a redirect with correct PKCE challenge and
    `state` params, and sets the `oidc_flow` cookie
  - `/api/auth/oidc/callback` happy path (mocked discovery/token
    endpoint/JWKS) creates a new user at `default_role`
  - Callback links to an existing local user by matching username
    (case-insensitive)
  - Callback rejects mismatched/expired `state` and missing `oidc_flow` cookie
  - Login against a user with `password_hash: null` returns 401 cleanly;
    change-password against `password_hash: null` sets it instead of requiring
    `current_password`

### Frontend

- `LoginPage.test.ts`: SSO button shown/hidden based on mocked `/oidc/status`;
  local form always present
- `SettingsPage.test.ts`: new SSO tab — form CRUD, secret masking, inline
  discovery-error display

---

## Out of Scope (v1)

- Multiple simultaneous OIDC providers
- Claim/group-based role mapping (fixed default role only)
- Linking by stable IdP subject ID (username match only)
- A separate "test connection" action distinct from save-time validation
- Auto-redirecting straight to the IdP when only OIDC is configured (local
  form always shown)
- Self-service linking UI (a user manually attaching their existing local
  account to an OIDC identity outside of the username-match path)
