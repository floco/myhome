# HA Ingress Trust — Design Spec

**Date:** 2026-07-21
**Status:** Approved

---

## Overview

When myhome is installed as a Home Assistant add-on with `ingress: true`
(`addon/config.yaml:14`), users currently still hit MyHome's own login page
(local password or OIDC) the first time they open it, even though they've
already authenticated to Home Assistant itself. This spec adds a third,
automatic login path — **HA ingress trust** — that silently establishes a
MyHome session for a user who reaches the app via Home Assistant's Supervisor
ingress proxy, using the HA-asserted identity Supervisor forwards.

This builds on the auth system from `feat/auth-api-tokens` (JWT session
cookies, roles) and the OIDC integration
(`docs/superpowers/specs/2026-07-06-oidc-integration-design.md`, which
introduced the `auth_provider`-per-user pattern this spec extends).

Scope: identity + session issuance for add-on/ingress deployments only. Local
password login and OIDC continue to work unchanged, in every deployment mode,
as the always-available fallback.

---

## Background: what HA ingress actually provides

Confirmed against HA's Supervisor source and developer docs (no existing
handling of this in the repo — verified via full-repo grep, zero hits):

- Supervisor's ingress proxy validates the browser's HA session **before**
  ever forwarding to the add-on; an unauthenticated request never reaches
  MyHome this way.
- It then forwards three headers: `X-Remote-User-Id`, `X-Remote-User-Name`,
  `X-Remote-User-Display-Name`. It does **not** forward admin/role status —
  HA's own docs and source confirm there's no `is_admin` header, and there is
  no reliable, documented API an add-on can call to look this up from a
  Supervisor-token-authenticated context. Treated as infeasible for this spec
  (see Out of Scope).
- HA's own guidance for trusting these headers: only do so if connections are
  also restricted to Supervisor's fixed internal proxy address,
  `172.30.32.2`. Since Supervisor connects to the add-on directly (single
  hop), `request.client.host` reflects this reliably without needing
  `--proxy-headers`/`X-Forwarded-For` trust.
- `addon/config.yaml` declares no `ports:` mapping, so under a normal add-on
  install this is the *only* network path in — but the same image can also
  run standalone via `docker run -p 8000:8000` (documented in `README.md`),
  which has no ingress and no `SUPERVISOR_TOKEN`. The trust conditions below
  must never fire in that mode.

---

## Architecture

### Trust boundary (activation gate)

A request's HA-asserted identity is only trusted when **all** hold:

1. `SUPERVISOR_TOKEN` env var is set (we're running as an HA add-on, not
   standalone Docker).
2. `request.client.host == "172.30.32.2"` (HA's documented, fixed Supervisor
   ingress proxy address).
3. `X-Remote-User-Id`, `X-Remote-User-Name`, and `X-Remote-User-Display-Name`
   are all present on the request.

If any condition fails, behavior is completely unchanged from today: no
cookie/token → 401 → SPA shows `LoginPage` (local password or OIDC). This is
also what satisfies "if no HA user is logged in, nothing is accessible" —
outside of genuine Supervisor-proxied traffic, these headers are never
trusted, so there's no way to reach an authenticated state without going
through a real login.

No separate on/off config toggle is added — the three structural conditions
above are the only gate, and they structurally can't be satisfied outside a
genuine add-on-behind-ingress deployment.

### Session issuance

`auth_middleware` (`main.py:99-124`) already runs on every `/api/*` and
`/mcp*` request and can inspect the response. It gets one more fallback
step, inserted where `user is None` is currently handled unconditionally as
a 401 (`main.py:112-114`):

```
user = await get_user_from_request(request)
if user is None:
    ingress_user = await resolve_ha_ingress_user(request)   # NEW
    if ingress_user is not None:
        user_id, role = ingress_user
        _set_auth_cookies(response_to_be_built, user_id, role)  # see note
        user = (user_id, role)
if user is None:
    return JSONResponse({"detail": "Authentication required"}, status_code=401)
```

(Exact mechanics: since `@app.middleware("http")` doesn't hand you a
`Response` to attach cookies to before calling `call_next`, the
implementation calls `call_next(request)` first to get the real response,
then sets the two cookies on *that* response object before returning it —
`Response.set_cookie` works identically post-hoc. `request.state.user` is
set before `call_next` either way, exactly as today.)

`resolve_ha_ingress_user(request)`:
1. Checks the three trust conditions above; returns `None` immediately if any
   fail (fast path — the vast majority of requests in any deployment).
2. Looks up an existing `User` by `ha_user_id == X-Remote-User-Id`.
3. If found, returns `(user.id, user.role)`.
4. If not found, provisions a new user (see Data Model + Bootstrap below) and
   returns its `(id, role)`.

Every request after the first just rides the normal `myhome_access` cookie —
no repeated header-trust logic, and logout/refresh/role-checks are completely
unchanged. The frontend needs zero special handling: its existing boot-time
`GET /api/auth/me` (`authStore.svelte.ts`) simply succeeds on the first
ingress request instead of 401'ing into `LoginPage`.

---

## Data Model

### `User` (modified, in `models_auth.py`)

```python
auth_provider: str = "local"  # "local" | "oidc" | "ha_ingress"   # extended
ha_user_id: str | None = None  # HA's X-Remote-User-Id, set only for auth_provider="ha_ingress"
```

Mirrors the existing `oidc_sub` pattern exactly. Matching is **only** ever by
`ha_user_id` — never by username collision against an existing account, and
never auto-linked into a `local`- or `oidc`-provider account. This directly
reuses the account-takeover-hardening lesson from the OIDC linking work
(PR #45): identity matching must anchor on a stable, unforgeable ID, not a
mutable display name.

New columns require a real migration (unlike a brand-new table, SQLite
`create_all()` is a no-op against an existing `users` table — see
`migrations.py`'s own docstring). Add to `schema.py`:

```python
Column("ha_user_id", String),
```

and a new entry in `migrations.py`:

```python
CURRENT_VERSION = 3

def _add_ha_user_id_column(conn: Connection) -> None:
    conn.execute(text("ALTER TABLE users ADD COLUMN ha_user_id VARCHAR"))

MIGRATIONS: list[tuple[int, Callable[[Connection], None]]] = [
    (2, _drop_kb_folders_table),
    (3, _add_ha_user_id_column),
]
```

`load_users()`/`save_users()` in `persistence_auth.py` get the new column
threaded through identically to `oidc_sub`.

---

## Provisioning & Bootstrap

### New `ha_ingress` user, common case

`username` derived from `X-Remote-User-Name`, de-duplicated with a numeric
suffix (`-2`, `-3`, ...) if it collides with an existing username (from any
provider). `password_hash: None` — this account can only ever authenticate
via ingress trust, exactly like an OIDC-only account can only authenticate
via OIDC today. Display name from `X-Remote-User-Display-Name`. Default
`role: "normal"` — see next section for the one exception.

### First-ever ingress login auto-promotes to admin

`_first_boot()` (`main.py:47-88`) already creates a placeholder local
`admin` user + one-time password file
(`persistence_auth.initial_admin_password_file()`) on every fresh install,
regardless of deployment mode. Its password file's existence is already a
reliable "nobody has ever logged in yet" signal — it's deleted by
`clear_initial_admin_password()` the moment any login succeeds
(`routes/auth.py:119`).

`resolve_ha_ingress_user` reuses that exact signal: when it's about to
provision a **brand-new** `ha_ingress` user, it first checks whether
`initial_admin_password_file()` still exists.

- **If it exists** (nobody has claimed the placeholder admin yet): the new
  `ha_ingress` user is created with `role: "admin"` instead of `"normal"`,
  in the same transaction the placeholder local `admin` user record and its
  password file are deleted — fully superseded, nothing left dangling. This
  is the expected common case: the first person to open the add-on's
  ingress panel just installed it, and becomes admin with zero manual steps
  and no password ever surfaced to a human.
- **If it doesn't exist** (someone already logged in locally with the
  bootstrap password before ever using ingress — unusual, but possible): the
  signal correctly doesn't fire. That local admin account stays untouched,
  and this and every subsequent new `ha_ingress` account gets `role:
  "normal"` as the standard case.

A theoretical race exists if two people hit ingress at the exact same
instant on first install and both observe the password file as
"unclaimed" — both would be promoted. Accepted as a low-risk edge case for
a home/self-hosted deployment; guarded at the DB layer with a single
transaction around the check-file / create-user / delete-placeholder
sequence (SQLite's default transaction isolation makes this correct: the
whole sequence runs inside one `engine.begin()` block, so a second
concurrent request either sees the file already gone or blocks until the
first transaction commits).

### Standalone Docker (no `SUPERVISOR_TOKEN`)

Completely unchanged. The trust boundary in the Architecture section can
never be satisfied without `SUPERVISOR_TOKEN`, so `_first_boot()`'s existing
behavior — write `/data/.initial-admin-password`, never print it to stdout —
stays exactly as-is. This remains the only way to log in for that deployment
mode.

### Add-on context: no more log printing needed

Because the common case is now fully automatic, the log-printing idea
explored earlier in brainstorming is dropped entirely — nothing needs to
change about `_first_boot()`'s existing behavior. The placeholder admin +
password file still get created up front (needed as the "unclaimed" signal),
but they're deleted as part of the first ingress login before anyone would
need to read them. They remain on disk (never logged) as a break-glass path
only for the unusual case ingress is never used.

---

## Error Handling

- Trust conditions fail (wrong source IP, missing headers, or no
  `SUPERVISOR_TOKEN`) → falls straight through to the existing 401 → login
  page path. No new error surface.
- Migration `_add_ha_user_id_column` runs unconditionally for any DB created
  before version 3; idempotent per the existing `schema_version` bookkeeping
  (only runs once, regardless of deployment mode).
- Username collision on provisioning → numeric-suffix disambiguation (no
  user-visible error).

## Edge Cases

- A user renames themselves in HA (`X-Remote-User-Name` changes) after their
  `ha_ingress` account already exists: matching is by `ha_user_id`, so the
  same MyHome account is reused; consider whether to refresh the stored
  display name on each ingress login (recommended: yes, cheap, keeps it
  accurate) — implementation detail, not a design fork.
- Admin later wants to demote/remove an auto-promoted `ha_ingress` admin:
  works identically to any other user via the existing Users settings panel
  — no special-casing needed since `auth_provider` is informational there
  already (per the OIDC spec's Edge Cases).
- Someone maps a host port directly on an add-on deployment (advanced,
  non-standard override of the add-on's own network config): `SUPERVISOR_TOKEN`
  is still set in that container, but the peer-IP check
  (`172.30.32.2`) still requires traffic to have actually come from
  Supervisor's internal proxy — direct LAN access wouldn't match that source
  IP, so ingress trust still doesn't fire for it. Local/OIDC login remains
  available.

---

## Testing

### Backend

- `test_ha_ingress.py` (new):
  - All three trust conditions must hold — test each one failing
    independently falls through to 401 (missing `SUPERVISOR_TOKEN`, wrong
    source IP, missing/partial headers).
  - First-ever ingress login: placeholder admin password file present →
    new user gets `role="admin"`, placeholder local admin deleted, password
    file removed.
  - Second ingress login (different `X-Remote-User-Id`, password file
    already gone): new user gets `role="normal"`.
  - Repeat login with same `X-Remote-User-Id`: resolves to the same existing
    user, no duplicate created.
  - Username collision: second HA user with the same `X-Remote-User-Name`
    as an existing account gets a disambiguated username.
  - Matching never links to an existing `local`/`oidc`-provider account even
    when username matches.
  - Migration test: a DB seeded at schema version 2 gets `ha_user_id` added
    on `run_migrations()`, existing data intact.

### Manual verification (required before merge — not achievable via unit tests)

Everything above tests MyHome's own logic against synthetic headers. It does
**not** prove HA's Supervisor actually sends these headers/IP the way the
docs describe, since that behavior lives entirely outside this repo. Per
`docs/superpowers/specs/2026-07-15-ha-addon-packaging` lessons (real
reverse-proxy repro caught a bug docs-only testing missed), this needs a
real HA instance + Supervisor + the packaged add-on, verifying:

1. Opening the add-on via the HA sidebar as an admin user logs straight into
   MyHome as an auto-provisioned admin, no login page shown.
2. Opening the same add-on as a second, non-admin HA user creates a second
   MyHome account at `role="normal"`.
3. Hitting the container directly (bypassing Supervisor, e.g. from another
   container on the same docker network) does **not** get ingress-trusted —
   falls through to the login page.

---

## Out of Scope (v1)

- Deriving HA admin/role status automatically (no reliable API for this from
  a Supervisor-token context — confirmed via HA docs; every new `ha_ingress`
  account after the first defaults to `normal`, promoted manually via the
  existing Users settings panel).
- An explicit add-on config toggle to disable ingress trust — the structural
  trust conditions are considered sufficient gating for v1.
- Syncing role changes made in HA back into MyHome on an ongoing basis (role
  is only ever set at account-creation time, per above).
- Multi-instance/clustered add-on deployments (single-container assumption,
  consistent with the rest of the codebase).
