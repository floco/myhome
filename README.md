# My Home

A modular home management app for Home Assistant. Each aspect of your home — its layout, chores, inventory, supplies, and renovation history — lives in its own module behind a unified sidebar.

## Modules

| Module | Status | Description |
|--------|--------|-------------|
| 🏠 **Floor Plan** | Live | Draw rooms, place doors/windows, overlay chore badges, label HA areas |
| ✅ **Chores** | Live | Track recurring chores with flexible schedules, completion history, and notes |
| 📦 **Inventory** | Planned | Catalog items stored in your home — furniture, appliances, tools, valuables |
| 🛒 **Consumables** | Planned | Monitor stock levels for everyday supplies and household essentials |
| 🔧 **Works** | Planned | Log renovations and repairs — contractors, costs, warranties, photos |
| 💶 **Finance** | Planned | Track house costs — property taxes, fuel/mazout orders, electricity bills, and other expenses |

## Chores

Chores supports flexible recurrence (daily, weekly, monthly, yearly, day-of-month, days-of-week), completion history with notes, and two scheduling modes — advance from the planned date or from the actual completion date. Chores can be imported from [Donetick](https://donetick.com).

From the **Chores** module, use the ⚙ button (left of `+`) to open chore settings for creating, editing, deleting, and importing chores.

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
