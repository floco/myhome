# My Home

An interactive floor plan editor with chore tracking for Home Assistant.

## Features

- **Floor plan editor** — draw rooms, place furniture, label areas on an SVG canvas
- **Chore tracker** — track recurring chores with flexible schedules (daily, weekly, monthly, yearly, day-of-month, days-of-week), completion history, notes, and progress bars
- **Donetick import** — import chores from a Donetick JSON export
- **Home Assistant integration** — fetches your HA areas and overlays SVG badges on the floor plan

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

Data (floor plans, chores) is stored in `/data` inside the addon and persists across restarts and updates.

## Running locally (development)

Requirements: Node.js 22+, Python 3.12+

```bash
# Install dependencies
npm install
pip install -e packages/backend

# Start frontend dev server + backend
./dev.sh
```

The app is served at `http://localhost:5173` (frontend) and `http://localhost:8000` (API).

## Building the Docker image

```bash
docker build -t myhome .
docker run -p 8000:8000 myhome
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
