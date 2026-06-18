# Chore Tracker (Spec 2) — Design Document

## Overview

Add a chore/maintenance tracker to the existing myhome HA add-on. Chores are visualised as circular progress-ring badges overlaid on the floor plan. Each badge shows how much time remains before the chore is due: green → orange → red → empty-red (overdue). Chores can be assigned to specific rooms (badge appears on the map) or to the whole house (shown in a side panel list). One-time import from Donetick; full CRUD lives inside the add-on thereafter.

---

## Data Model

Single new file: **`/data/chores.json`**

```json
{
  "version": 1,
  "chores": [
    {
      "id": "uuid",
      "donetickId": 17,
      "name": "🪟 Nettoyer fenetres Veranda",
      "emoji": "🪟",
      "periodDays": 730,
      "nextDueDate": "2027-05-01T21:59:00Z",
      "description": ""
    }
  ],
  "assignments": [
    {
      "id": "uuid",
      "choreId": "chore-uuid",
      "roomId": "room-uuid",
      "position": { "x": 340, "y": 210 }
    }
  ]
}
```

**Chore** — the definition of a recurring task:

| Field | Type | Notes |
|-------|------|-------|
| `id` | UUID string | Generated locally |
| `donetickId` | int \| null | Donetick chore ID; null for manually-created |
| `name` | string | Full name including emoji prefix |
| `emoji` | string | Extracted emoji, used inside the badge ring |
| `periodDays` | number | Recurrence period in days (see conversion below) |
| `nextDueDate` | ISO 8601 string | Next time this chore is due |
| `description` | string | Free-text, optional |

**Assignment** — a placement of one chore onto one room or the whole house:

| Field | Type | Notes |
|-------|------|-------|
| `id` | UUID string | |
| `choreId` | UUID string | References `chore.id` |
| `roomId` | string \| null | Room ID from house document; `null` = whole house |
| `position` | `{x,y}` \| null | World coordinates on the floor plan; `null` when `roomId` is null |

One chore can have multiple assignments (different rooms). A chore with `roomId: null` is a house-level chore and has no map position.

### Donetick → periodDays conversion

```
frequencyType="interval"  → frequency * unit_to_days[unit]
frequencyType="yearly"    → frequency * 365
frequencyType="weekly"    → frequency * 7
frequencyType="day_of_the_month" → frequency   (treat frequency as days)

unit_to_days = { days: 1, weeks: 7, months: 30, years: 365 }
```

---

## Backend

All new routes added to the existing FastAPI app in `packages/backend/src/myhome/`. A new `routes/chores.py` module, registered in `main.py` alongside existing routers.

Persistence: `packages/backend/src/myhome/persistence.py` gains a `load_chores()` / `save_chores()` pair mirroring the existing `load_house()` / `save_house()` (atomic write via `.tmp` + `os.replace`).

### Routes

| Method | Path | Body | Response | Notes |
|--------|------|------|----------|-------|
| GET | `/api/chores` | — | `ChoreDocument` | Full `{version, chores, assignments}` |
| POST | `/api/chores` | `ChoreCreate` | `Chore` (201) | Create chore definition |
| PUT | `/api/chores/{id}` | `ChoreUpdate` | 204 | Update name/emoji/period/nextDueDate/description |
| DELETE | `/api/chores/{id}` | — | 204 | Delete chore + all its assignments |
| POST | `/api/chores/{id}/complete` | — | `Chore` (200) | Advance `nextDueDate` by `periodDays` from today |
| POST | `/api/chores/import` | `{token: str}` | `{imported: int}` (200) | One-time Donetick import |
| POST | `/api/assignments` | `AssignmentCreate` | `Assignment` (201) | Create assignment |
| PUT | `/api/assignments/{id}` | `AssignmentUpdate` | 204 | Update position only |
| DELETE | `/api/assignments/{id}` | — | 204 | Remove assignment |

### Pydantic models (new file `models_chores.py`)

```python
class Position(BaseModel):
    x: float
    y: float

class Chore(BaseModel):
    id: str
    donetickId: int | None = None
    name: str
    emoji: str
    periodDays: float
    nextDueDate: str        # ISO 8601
    description: str = ""

class Assignment(BaseModel):
    id: str
    choreId: str
    roomId: str | None = None
    position: Position | None = None

class ChoreDocument(BaseModel):
    version: int = 1
    chores: list[Chore] = []
    assignments: list[Assignment] = []

class ChoreCreate(BaseModel):
    name: str
    emoji: str
    periodDays: float
    nextDueDate: str
    description: str = ""
    donetickId: int | None = None

class ChoreUpdate(BaseModel):
    name: str | None = None
    emoji: str | None = None
    periodDays: float | None = None
    nextDueDate: str | None = None
    description: str | None = None

class AssignmentCreate(BaseModel):
    choreId: str
    roomId: str | None = None
    position: Position | None = None

class AssignmentUpdate(BaseModel):
    position: Position | None = None
```

### `/api/chores/import` behaviour

- Calls Donetick `GET /api/v1/chores/` with `secretkey: {token}` header via `httpx`
- For each chore in the response: converts `frequency`+`frequencyType`+`frequencyMetadata.unit` → `periodDays`, extracts leading emoji from `name`, generates a local UUID
- Skips chores whose `donetickId` already exists in the local store (idempotent re-import)
- Returns `{ "imported": N }` where N is the number of new chores added
- Does **not** create assignments — room assignment is done manually in the UI

---

## Frontend

### Chore mode toggle

A **"Chores"** button in the topbar (right of "Reset View"). Clicking it sets a `choreMode: boolean` state.

**Badges are always rendered** on the floor plan regardless of mode — the map always shows chore status at a glance.

In chore mode additionally:
- The drawing toolbar is hidden
- Badges become interactive (hover highlight, click, drag)
- The ChorePanel slide-over appears on the right

### ChorePanel (right slide-over, `~340px` wide)

Rendered inside `App.svelte` when `choreMode` is true. Three sections:

**1. Import** (shown only if `chores.length === 0`):
- "Import from Donetick" button
- On click: shows an inline token input (`<input type="password">`) + "Import" button
- Calls `POST /api/chores/import`, shows count of imported chores on success, hides the section

**2. House-level chores** (assignments where `roomId === null`):
- Collapsible section header "🏠 Whole house"
- Each row: progress ring mini-badge (20px) + chore name + "Mark done ✓" button
- "Mark done" calls `POST /api/chores/{id}/complete`, refreshes the store

**3. All chores list**:
- Each row shows:
  - 28px progress ring badge (ring + emoji)
  - Chore name
  - Days remaining label (e.g. "−3d" if overdue, "+42d" if not)
  - "Assign to room →" button — enters assignment mode for this chore
  - "🏠" button — creates house-level assignment immediately
  - ✏️ (opens inline edit form) / 🗑️ (confirm-delete)
- "＋ New chore" button at bottom — opens inline creation form (name, emoji, period in days, next due date)

### Assignment mode

When the user clicks "Assign to room →" for a chore:
- `assigningChoreId` is set in state
- Cursor on the canvas changes to crosshair
- Clicking on a room polygon calls `POST /api/assignments` with `choreId`, `roomId`, and `position` defaulting to the room's centroid
- Pressing Escape cancels assignment mode

### Badge overlay

A new Svelte component `ChoreOverlay.svelte`, rendered as an `<svg>` absolutely positioned over the canvas (same dimensions). Always visible. In chore mode pointer-events are enabled (click, drag); outside chore mode pointer-events are `none` so the drawing tools remain usable.

For each assignment where `roomId !== null`:
- Transform world `position` → screen coords via existing viewport transform
- Render a badge at that screen position:

```svg
<!-- Background track -->
<circle cx={sx} cy={sy} r={R} fill="none" stroke="#2a2a2a" stroke-width="5"/>
<!-- Progress arc -->
<circle cx={sx} cy={sy} r={R} fill="none" stroke={color} stroke-width="5"
  stroke-dasharray="{pct * C} {C}" stroke-linecap="round"
  transform="rotate(-90 {sx} {sy})"/>
<!-- Emoji -->
<text x={sx} y={sy+5} text-anchor="middle" font-size="13">{emoji}</text>
```

Where `R = 18`, `C = 2π × R ≈ 113.1`, `pct = clamp((nextDueDate - now) / (periodDays * 86400000), 0, 1)`.

Color logic:
- `pct > 0.5` → `#4caf50` (green)
- `0.25 < pct ≤ 0.5` → `#ff9800` (orange)
- `pct ≤ 0.25` → `#f44336` (red)

Multiple badges for the same room are rendered at their individual stored positions (each is independently draggable).

### Badge interaction

**Click** (no drag): shows a small popup `BadgePopup.svelte` anchored to the badge:
- Chore name
- Next due date (formatted)
- "✓ Mark done" → `POST /api/chores/{id}/complete`, refreshes
- "✏️ Edit" → opens chore edit form in ChorePanel
- "✕ Remove from room" → `DELETE /api/assignments/{id}`

**Drag**: on `pointerdown` on a badge, capture pointer and track movement. On `pointerup`, call `PUT /api/assignments/{id}` with new world position. No room-boundary constraint on drop (keep it simple; the user can reposition freely).

### Frontend data store

New `choreStore.svelte.ts`:
- `$state` holding `ChoreDocument` (`{ chores, assignments }`)
- `init()` auto-called: `GET /api/chores`
- `save()` not needed — each mutation calls its own endpoint and refreshes via `init()`
- Helper: `getProgress(chore): number` → pct [0,1]
- Helper: `getColor(pct): string` → hex color
- Helper: `assignmentsForRoom(roomId): Assignment[]`

---

## Testing

**Backend** (`packages/backend/tests/`):
- `test_chores.py`: CRUD routes, import endpoint (mock httpx), complete endpoint (date arithmetic), delete cascades assignments
- `test_chore_persistence.py`: atomic write, load returns empty document when file missing

**Frontend** (`packages/editor/test/`):
- `choreStore.test.ts`: init fetches, complete advances date, helpers (getProgress, getColor)
- `ChoreOverlay.test.ts`: renders correct number of badges, applies correct color class

---

## What is NOT in scope

- Syncing "mark done" back to Donetick
- Push notifications / HA automations based on overdue chores
- Multi-user / circle support (single user only)
- Recurring import / auto-sync with Donetick
- Room-boundary drag constraint for badges
