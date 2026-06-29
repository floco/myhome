# Release Versioning & Deployment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the existing per-arch build workflow with a split CI + release pipeline, update the addon image to a single multi-arch manifest, and add a docker-compose.yml for standalone deployment.

**Architecture:** Two GitHub Actions workflows — `ci.yml` (tests on every push/PR) and `release.yml` (tests + multi-arch Docker build on `v*` tags). The image switches from four per-arch images (`ghcr.io/floco/myhome/{arch}`) to one multi-arch manifest (`ghcr.io/floco/myhome`). `addon/config.yaml` is the single version source of truth.

**Tech Stack:** GitHub Actions, Docker buildx + QEMU, ghcr.io, docker-compose v2

---

## File Map

| Action | File | Responsibility |
|--------|------|---------------|
| Delete | `.github/workflows/build-addon.yml` | Old per-arch build (replaced by ci.yml + release.yml) |
| Create | `.github/workflows/ci.yml` | Run tests on push to main and PRs |
| Create | `.github/workflows/release.yml` | Validate version, build multi-arch image, push on v* tag |
| Create | `docker-compose.yml` | Standalone deployment outside Home Assistant |
| Modify | `addon/config.yaml` | Update description, image field, arch list |
| Modify | `README.md` | Add Deployment section, update Building section |

---

### Task 1: Create CI workflow

**Files:**
- Delete: `.github/workflows/build-addon.yml`
- Create: `.github/workflows/ci.yml`

- [ ] **Step 1: Remove the old build-addon workflow**

```bash
git rm .github/workflows/build-addon.yml
```

- [ ] **Step 2: Create `.github/workflows/ci.yml`**

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '22'
          cache: 'npm'

      - name: Install Node dependencies
        run: npm ci

      - name: Run frontend tests
        run: npm test -w @myhome/editor

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install backend dependencies
        run: pip install -e packages/backend

      - name: Run backend tests
        run: pytest packages/backend
```

- [ ] **Step 3: Validate YAML syntax locally**

```bash
python3 -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))" && echo "YAML valid"
```

Expected: `YAML valid`

- [ ] **Step 4: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: add CI workflow for tests on push and PR"
```

---

### Task 2: Create release workflow

**Files:**
- Create: `.github/workflows/release.yml`

- [ ] **Step 1: Test the version extraction script locally**

This is the exact script the workflow will run. Verify it extracts the right string before embedding it in the YAML.

```bash
CONFIG_VERSION=$(grep '^version:' addon/config.yaml | sed 's/version: *"\(.*\)"/\1/')
echo "Extracted: $CONFIG_VERSION"
```

Expected output: `Extracted: 0.2.0` (or whatever the current version is in addon/config.yaml)

- [ ] **Step 2: Test the tag comparison logic**

Simulate what the workflow does when tag `v0.3.0` is pushed and config says `0.3.0`:

```bash
CONFIG_VERSION=$(grep '^version:' addon/config.yaml | sed 's/version: *"\(.*\)"/\1/')
TAG_VERSION="v0.3.0"
TAG_VERSION="${TAG_VERSION#v}"
if [ "$CONFIG_VERSION" = "$TAG_VERSION" ]; then
  echo "MATCH: $CONFIG_VERSION"
else
  echo "MISMATCH: config=$CONFIG_VERSION tag=$TAG_VERSION"
fi
```

Expected: `MATCH: 0.2.0` (if config is 0.2.0 and you test with v0.2.0)

- [ ] **Step 3: Create `.github/workflows/release.yml`**

```yaml
name: Release

on:
  push:
    tags:
      - 'v*'

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '22'
          cache: 'npm'

      - name: Install Node dependencies
        run: npm ci

      - name: Run frontend tests
        run: npm test -w @myhome/editor

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install backend dependencies
        run: pip install -e packages/backend

      - name: Run backend tests
        run: pytest packages/backend

  release:
    needs: test
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write
    steps:
      - uses: actions/checkout@v4

      - name: Validate tag matches addon/config.yaml version
        run: |
          CONFIG_VERSION=$(grep '^version:' addon/config.yaml | sed 's/version: *"\(.*\)"/\1/')
          TAG_VERSION="${GITHUB_REF_NAME#v}"
          if [ "$CONFIG_VERSION" != "$TAG_VERSION" ]; then
            echo "ERROR: Tag $GITHUB_REF_NAME does not match addon/config.yaml version \"$CONFIG_VERSION\""
            exit 1
          fi
          echo "Version $CONFIG_VERSION validated."

      - name: Log in to GitHub Container Registry
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Set up QEMU
        uses: docker/setup-qemu-action@v3

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Extract version
        id: version
        run: echo "version=${GITHUB_REF_NAME#v}" >> "$GITHUB_OUTPUT"

      - name: Build and push multi-arch image
        uses: docker/build-push-action@v6
        with:
          context: .
          platforms: linux/amd64,linux/aarch64
          push: true
          tags: |
            ghcr.io/floco/myhome:${{ steps.version.outputs.version }}
            ghcr.io/floco/myhome:latest
          cache-from: type=gha
          cache-to: type=gha,mode=max
```

- [ ] **Step 4: Validate YAML syntax locally**

```bash
python3 -c "import yaml; yaml.safe_load(open('.github/workflows/release.yml'))" && echo "YAML valid"
```

Expected: `YAML valid`

- [ ] **Step 5: Commit**

```bash
git add .github/workflows/release.yml
git commit -m "ci: add release workflow — build and push multi-arch image on v* tag"
```

---

### Task 3: Create docker-compose.yml

**Files:**
- Create: `docker-compose.yml`

- [ ] **Step 1: Create `docker-compose.yml` at repo root**

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
      # Optional: uncomment for Home Assistant integration
      # SUPERVISOR_TOKEN: ${SUPERVISOR_TOKEN}
      # HA_URL: ${HA_URL:-http://homeassistant:8123}

volumes:
  myhome-data:
```

- [ ] **Step 2: Validate compose file syntax**

```bash
docker compose -f docker-compose.yml config --quiet && echo "Compose valid"
```

Expected: `Compose valid`

- [ ] **Step 3: Commit**

```bash
git add docker-compose.yml
git commit -m "feat: add docker-compose.yml for standalone deployment"
```

---

### Task 4: Update addon/config.yaml

**Files:**
- Modify: `addon/config.yaml`

Changes:
- `description`: update to reflect full app scope
- `image`: remove `{arch}` suffix (single multi-arch manifest)
- `arch`: drop armhf and armv7, keep amd64 and aarch64

- [ ] **Step 1: Edit `addon/config.yaml`**

Change these fields (leave all others unchanged):

```yaml
description: "Home management app — floor plans, chores, inventory, costs, works, knowledge base, and more."
image: "ghcr.io/floco/myhome"
arch:
  - amd64
  - aarch64
```

The full file after edits should be:

```yaml
name: "My Home"
version: "0.2.0"
slug: "myhome"
description: "Home management app — floor plans, chores, inventory, costs, works, knowledge base, and more."
url: "https://github.com/floco/myhome"
image: "ghcr.io/floco/myhome"
arch:
  - amd64
  - aarch64
startup: application
boot: auto
init: false
homeassistant_api: true
ingress: true
ingress_port: 8000
panel_icon: mdi:home-floor-plan
panel_title: My Home
map:
  - data:rw
options:
  log_level: info
schema:
  log_level: "list(debug|info|warning|error|critical)"
```

- [ ] **Step 2: Verify the version extraction script still works**

```bash
grep '^version:' addon/config.yaml | sed 's/version: *"\(.*\)"/\1/'
```

Expected: `0.2.0`

- [ ] **Step 3: Commit**

```bash
git add addon/config.yaml
git commit -m "chore: update addon config — multi-arch manifest, drop armhf/armv7, update description"
```

---

### Task 5: Update README.md

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Add a Deployment section after the existing "Installing as a Home Assistant Addon" section**

Insert this section between "Installing as a Home Assistant Addon" and "Running locally (development)":

```markdown
## Deploying with Docker Compose

The easiest way to run MyHome outside of Home Assistant.

**Prerequisites:** Docker and Docker Compose v2.

```bash
curl -O https://raw.githubusercontent.com/floco/myhome/main/docker-compose.yml
docker compose up -d
```

Open `http://localhost:8000` in your browser. Data persists in a Docker volume (`myhome-data`).

### Optional: Home Assistant integration

To connect to a Home Assistant instance on the same host, create a `.env` file next to `docker-compose.yml`:

```env
SUPERVISOR_TOKEN=your_token_here
HA_URL=http://homeassistant:8123
```

Then uncomment the corresponding lines in `docker-compose.yml` and restart: `docker compose up -d`.
```

- [ ] **Step 2: Update the "Building the Docker image" section**

Replace the existing section:

```markdown
## Building the Docker image

Pre-built multi-arch images (amd64 + aarch64) are available at `ghcr.io/floco/myhome`:

```bash
docker pull ghcr.io/floco/myhome:latest
```

To build locally:

```bash
docker build -t myhome .
docker run -p 8000:8000 -v myhome-data:/data myhome
```
```

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: add Docker Compose deployment instructions, update Docker section"
```
