# About Screen — Design Spec

Date: 2026-07-26

## Problem

There's no way to see which version of My Home is running, no visibility into
basic deployment/runtime info for troubleshooting, and no way to tell whether
a newer version is available. This surfaced directly from a support case: a
user updated the Home Assistant add-on and the UI kept showing stale content
(old costs icon, old settings layout, missing Insurance module) even though
Supervisor reported the new version installed. A reinstall fixed it for them,
but the app has no way to help a user notice or diagnose that kind of
staleness on their own.

## Goals

- Show the running app version and basic system/runtime info in Settings, for
  all logged-in users (not admin-gated — nothing here is sensitive).
- Tell the user whether a newer version is available, checked against the
  project's published git tags on GitHub.
- Reduce the odds of the update-staleness symptom recurring by adding proper
  cache headers to the served frontend assets.

## Non-goals

- No auto-update mechanism — this is informational only.
- No historical changelog rendering.
- No telemetry / phone-home beyond the on-demand GitHub tags check.

## Architecture

One new backend endpoint, `GET /api/system/info`, returns both static system
info and the update-check result in a single response. One new frontend
Settings tab, `SettingsAbout.svelte`, fetches it on mount. No new persistence,
no schema changes.

## Backend

### Version baking

`addon/config.yaml`'s `version:` field is already the single source of truth
(the release workflow validates the git tag against it). The Dockerfile gains
a step, in the backend build stage, that extracts that value into
`/app/VERSION` at image build time:

```dockerfile
COPY addon/config.yaml /tmp/addon-config.yaml
RUN grep '^version:' /tmp/addon-config.yaml | sed 's/version: *"\(.*\)"/\1/' > /app/VERSION \
    && rm /tmp/addon-config.yaml
```

The backend reads this file at startup (mirroring the existing `STATIC_DIR`
env-var-with-default pattern), falling back to `"unknown"` if the file is
missing (e.g. running outside the built image, such as under pytest).

### `GET /api/system/info`

Requires an authenticated user (no admin gate — same visibility as most other
Settings tabs). Returns:

```json
{
  "version": "0.8.0",
  "deployment_mode": "home_assistant",
  "python_version": "3.12.3",
  "db_schema_version": 6,
  "arch": "x86_64",
  "uptime_seconds": 12345,
  "home_count": 3,
  "database_size_bytes": 2093312,
  "update_check": {
    "status": "up_to_date",
    "latest_version": "0.8.0",
    "checked_at": "2026-07-26T18:00:00Z"
  }
}
```

Field sources:
- `version` — `/app/VERSION` (see above).
- `deployment_mode` — `"home_assistant"` if `SUPERVISOR_TOKEN` is set in the
  environment, else `"standalone"` (same detection already used in
  `routes/ha.py`).
- `python_version` — `platform.python_version()`.
- `arch` — `platform.machine()`.
- `db_schema_version` — `migrations.CURRENT_VERSION`.
- `home_count` — `len(load_homes().homes)`.
- `database_size_bytes` — `os.path.getsize()` on `DATA_DIR/myhome.db`
  (0 if the file doesn't exist yet).
- `uptime_seconds` — wall-clock delta from a start timestamp recorded once at
  process startup (module-level, set in `main.py`'s lifespan or at import
  time) to "now".
- `update_check` — see below.

### Update check

A new `system.py` module (or function within the new `routes/system.py`)
calls the public GitHub API: `GET https://api.github.com/repos/floco/myhome/tags`
with a `User-Agent` header (required by GitHub) and a 5s timeout, using the
existing `httpx` dependency. It filters tag names matching `^v\d+\.\d+\.\d+$`,
picks the maximum by tuple-of-ints comparison, and strips the `v` prefix to
get `latest_version`.

Result is cached in a module-level variable for one hour (`checked_at` +
`status` + `latest_version`), so concurrent or repeated page loads across
users don't each trigger a GitHub call. On failure (network error, non-200,
timeout):
- If a previous successful check exists in the cache, keep serving that
  stale-but-known result rather than flipping to `"unknown"`.
- If there has never been a successful check, return
  `{"status": "unknown", "latest_version": null, "checked_at": null}`.

`status` is computed by comparing `latest_version` to the running `version`
as parsed `(major, minor, patch)` tuples: `"update_available"` if the latest
tag is strictly greater, else `"up_to_date"`.

### Cache-control headers

Currently `app.mount("/", StaticFiles(directory=str(_static_dir), html=True))`
serves the built frontend with only `Last-Modified`/`ETag`, no explicit
`Cache-Control`. Replace `StaticFiles` with a small subclass (e.g.
`_CachingStaticFiles`) that overrides `file_response` to inspect the resolved
file's basename after calling `super().file_response(...)`:
- `index.html` → `Cache-Control: no-cache` (always revalidate; the file is
  tiny, so this costs nothing, and it's the file responsible for the
  reported staleness symptom).
- everything else (Vite's content-hashed JS/CSS/asset files under
  `/assets/`) → `Cache-Control: public, max-age=31536000, immutable`.

## Frontend

New `packages/editor/src/lib/components/settings/SettingsAbout.svelte`:
- Fetches `/api/system/info` on mount via the existing `apiUrl()` helper.
- Shows the version prominently at the top.
- Shows an update-status line based on `update_check.status`:
  - `up_to_date` → "You're up to date" (checkmark styling).
  - `update_available` → "Update available: v{latest_version}" with a link
    to `https://github.com/floco/myhome/tags`.
  - `unknown` → "Unable to check for updates" (neutral styling, no error
    treatment).
- Shows the rest of the fields as a label/value list: deployment mode,
  Python version, architecture, DB schema version, number of homes,
  database size (formatted as MB), uptime (formatted human-readably, e.g.
  "3d 4h").

`SettingsPage.svelte`'s `ALL_GROUPS` gains a new entry:
`{ id: "about", icon: "ℹ️" }` (no `adminOnly`), rendered last in the nav
list, wired to `<SettingsAbout />` with no required props beyond what it
fetches itself.

New i18n keys added to both `en` and `fr` locale files following the existing
`settings.nav.*` / `settings.<tab>.*` pattern.

## Error handling

- GitHub API failures never surface as a page-level error — `update_check`
  degrades to a cached or `"unknown"` result, and the frontend renders that
  as a neutral message.
- `/app/VERSION` missing (e.g. local dev, tests) → `"unknown"`, not a crash.
- `DATA_DIR/myhome.db` missing (fresh install, no home created yet) →
  `database_size_bytes: 0`, not a 404/500.

## Testing

- Backend: unit tests for `/api/system/info` covering
  `update_available` / `up_to_date` / `unknown` (mocking the GitHub call),
  `deployment_mode` detection via env var presence/absence, and a check that
  static-file responses carry the expected `Cache-Control` header
  (`no-cache` for `index.html`, `immutable` long-cache for other assets).
- Frontend: component test for `SettingsAbout.svelte` rendering each of the
  three update-status states, plus a `SettingsPage` test confirming the new
  tab appears and is not admin-gated.
