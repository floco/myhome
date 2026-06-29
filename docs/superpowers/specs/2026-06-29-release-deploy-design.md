# Release Versioning & Deployment Design

**Date:** 2026-06-29
**Status:** Approved

## Overview

Add a proper release workflow to MyHome: git-tag-triggered CI/CD that builds and pushes multi-arch Docker images to ghcr.io, plus a `docker-compose.yml` for standalone deployment outside of Home Assistant.

## Versioning

`addon/config.yaml` is the single source of truth for the app version. No other version fields (`pyproject.toml`, `package.json`) need to be kept in sync — they remain as internal identifiers only.

### Release process

1. Update `version` in `addon/config.yaml` (e.g. `0.2.0` → `0.3.0`)
2. Also update `description` in `addon/config.yaml` to reflect current app scope (see below)
3. Commit: `git commit -m "chore: release v0.3.0"`
4. Tag and push: `git tag v0.3.0 && git push origin main --tags`
5. GitHub Actions release workflow runs automatically

The release workflow validates that the tag (e.g. `v0.3.0`) matches the `version` field in `addon/config.yaml` exactly. If they diverge, the workflow fails before touching the registry.

### addon/config.yaml description update

Current description is stale ("Interactive floor plan editor with chore tracking"). Update to:
> "Home management app — floor plans, chores, inventory, costs, works, knowledge base, and more."

## GitHub Actions Workflows

Two files in `.github/workflows/`:

### `ci.yml`

Triggers on push to `main` and on all pull requests.

Steps:
- Run frontend tests: `npm test -w @myhome/editor`
- Run backend tests: `pytest packages/backend`

No Docker build — keeps CI fast.

### `release.yml`

Triggers on `v*` tag push. Runs the full test suite as a gate before publishing (re-runs tests inline rather than depending on a prior `workflow_run`, which avoids timing/branch ambiguity).

Steps:
1. Run frontend tests (gate)
2. Run backend tests (gate)
3. Validate tag matches `addon/config.yaml` version (script: extract version, compare to `GITHUB_REF_NAME` stripped of `v` prefix)
4. Log in to ghcr.io using `GITHUB_TOKEN`
5. Set up QEMU + Docker buildx for multi-arch
6. Build and push image:
   - Frontend build stage pinned to `--platform=linux/amd64` (rolldown requirement)
   - Final image produced for `linux/amd64` and `linux/aarch64`
   - Tags: `ghcr.io/floco/myhome:<version>` and `ghcr.io/floco/myhome:latest`

### Registry & image name

Image: `ghcr.io/floco/myhome`

The `{arch}` suffix in the current `addon/config.yaml` `image` field is an older HA pattern. With Docker buildx multi-arch manifests, a single image name serves all architectures. Update `addon/config.yaml` `image` field to `ghcr.io/floco/myhome` (no arch suffix).

### Architectures

- `linux/amd64`
- `linux/aarch64`

armhf and armv7 are dropped — modern HA hardware (Pi 4+, NAS, x86 servers) is covered by these two.

## Docker Compose

A `docker-compose.yml` at the repo root for standalone deployment (no Home Assistant required).

```yaml
services:
  myhome:
    image: ghcr.io/floco/myhome:latest
    ports:
      - "8000:8000"
    volumes:
      - myhome-data:/data
    environment:
      LOG_LEVEL: info
      # Optional: uncomment for HA integration
      # SUPERVISOR_TOKEN: ${SUPERVISOR_TOKEN}
      # HA_URL: ${HA_URL:-http://homeassistant:8123}

volumes:
  myhome-data:
```

For standalone use: `docker compose up -d` — no env vars needed.

For HA integration on the same host: set `SUPERVISOR_TOKEN` and `HA_URL` in a `.env` file alongside the compose file.

## README Updates

Add a **Deployment** section to `README.md` with two sub-sections:

1. **Docker Compose (standalone)** — one-liner `docker compose up -d`, link to compose file
2. **Home Assistant Addon** — keep existing instructions, update to reflect the removed arch suffix

Update the existing "Building the Docker image" section to note that pre-built images are available from ghcr.io.

## Files Changed

| File | Change |
|------|--------|
| `.github/workflows/ci.yml` | New — runs tests on push/PR |
| `.github/workflows/release.yml` | New — builds and pushes image on v* tag |
| `docker-compose.yml` | New — standalone deployment |
| `addon/config.yaml` | Update `description`, update `image` field (remove `{arch}`), keep `arch` list as `[amd64, aarch64]` |
| `README.md` | Add Deployment section, update Building section |
