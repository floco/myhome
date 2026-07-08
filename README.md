# My Home

A modular home management app for Home Assistant. Each aspect of your home — its layout, chores, inventory, supplies, costs, and renovation history — lives in its own module behind a unified sidebar.

## A note from the author

This app is **vibe coded**. I couldn't find anything out there that would properly manage a house — despite a house being, for most of us, the single most valuable asset we own — so I started building one myself. I code this in my spare time, and spare time is in short supply, so development happens in bursts and support is best-effort.

Take it or leave it. No guarantee, use at your own risk. I'm sharing it in case it's useful to someone else too.

## Modules

| Module | Description |
|--------|--------------|
| 🏡 **Home** | Dashboard with at-a-glance widgets for chores, costs, inventory, works, and consumables |
| 📐 **Floor Plan** | Draw rooms, walls, doors, and windows; place furniture from a built-in library; overlay chore/cost/inventory/works pins; label Home Assistant areas |
| ✅ **Chores** | Recurring chores with flexible schedules (daily/weekly/monthly/yearly, day-of-month, days-of-week), completion history with notes, and import from [Donetick](https://donetick.com) |
| 📦 **Inventory** | Catalog what you own — categories, floor plan pins, photos and documents attached to each item |
| 🛒 **Consumables** | Track stock levels for everyday supplies, with custom units and categories |
| 🔧 **Works** | Log renovations and repairs — costs, dates, photos and documents |
| 📖 **Knowledge Base** | Freeform notes with a markdown editor, for anything that doesn't fit elsewhere (manuals, warranties, contacts, procedures) |
| 💶 **Costs** | Track house expenses by category (property tax, fuel/mazout, electricity, water, ...), with suppliers and floor-plan pins |

Multiple homes are supported — switch between them from the top bar, each with its own floor plan, data, and enabled-modules configuration.

## Other features

- **Global search** — jump to anything across every module from one command palette (`Ctrl/Cmd+K`)
- **Media galleries** — attach photos and PDFs to inventory items, works, cost entries, chores, and KB pages, with a lightbox viewer
- **Notifications** — a notification center surfaces chores due soon, low-stock consumables, and expiring warranties, with an optional daily digest pushed to Home Assistant
- **Activity log** — an audit trail of who changed what, across every module
- **Backup & restore** — one-click manual backup/restore, plus scheduled automatic backups with retention
- **Users, roles & API tokens** — read-only/normal/admin roles, per-user accounts, and scoped API tokens for automation
- **Single Sign-On** — optional OIDC login (Keycloak, Authentik, Google Workspace, etc.) alongside local accounts
- **MCP server** — expose your home's data to AI assistants (Claude Desktop, Claude Code, claude.ai, Home Assistant's Assist) over the Model Context Protocol
- **Home Assistant integration** — runs as an ingress-enabled addon with a sidebar panel, and can label floor plan rooms with your existing HA areas
- **Light/dark theme**

All of the above is configurable from **Settings**, organized into General, Categories, Notifications, Security & Access, Integrations, Backup & Restore, and Activity Log.

## Installing as a Home Assistant Addon

### Step 1 — Add the repository

1. In Home Assistant, go to **Settings → Add-ons → Add-on Store**
2. Click the **⋮** menu (top right) and select **Repositories**
3. Add this URL and click **Add**:
   ```
   https://github.com/floco/myhome
   ```

### Step 2 — Install the addon

1. Refresh the Add-on Store page
2. Find **My Home** in the list and click it
3. Click **Install** and wait for the image to download

### Step 3 — Start the addon

1. Click **Start**
2. Enable **Show in sidebar** to pin it to your HA navigation
3. Open **My Home** from the sidebar

### Configuration

| Option | Default | Description |
|--------|---------|-------------|
| `log_level` | `info` | Log verbosity: `debug`, `info`, `warning`, `error`, `critical` |

Data is stored in `/data` inside the addon and persists across restarts and updates.

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

## Running locally (development)

Requirements: Node.js 22+, Python 3.12+

```bash
# Install dependencies
npm install
pip install -e packages/backend

# Start frontend dev server + backend
./dev.sh
```

Frontend at `http://localhost:5173`, API at `http://localhost:8000`.

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

## Architecture

```
packages/
  editor/    # Svelte 5 frontend (Vite)
  backend/   # FastAPI backend (Python)
  geometry/  # Shared geometry utilities
addon/
  config.yaml  # HA addon manifest
  run.sh       # Container entrypoint
Dockerfile     # Multi-stage build (frontend → backend)
```

## License

MIT — see [LICENSE](LICENSE).
