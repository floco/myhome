# Demo Home Seed Data Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a third `"demo"` home type that, on creation, seeds a realistic floor plan and ≥30 records in every content module (Chores, Inventory, Costs, Works, Knowledge Base, Consumables).

**Architecture:** A new `demo_geometry.py` procedurally builds a small grid-based floor plan (walls/doors/rooms). A new `demo_content.py` holds curated static data (chore names, inventory items, work titles, KB titles, consumables, demo-specific settings categories/suppliers). A new `demo_data.py` orchestrates: builds each module's document from the content + geometry using a per-call `random.Random` instance (fresh entropy in production, seeded in tests), and writes them via each module's existing `save_*` persistence function. `persistence_homes.create_home()` calls this orchestrator when `type == "demo"`, with cleanup on failure. Frontend gets a third radio option in `NewHomeModal` and a distinguishing icon in `HomesSwitcher`.

**Tech Stack:** Python 3.12 / FastAPI / Pydantic v2 (backend), Svelte 5 + TypeScript (frontend), pytest (backend tests), vitest + raw Svelte `mount`/`unmount` (frontend tests). No new dependencies.

Spec: `docs/superpowers/specs/2026-07-11-demo-home-seed-data-design.md`

---

## Task 1: `Home.type` gains `"demo"`

**Files:**
- Modify: `packages/backend/src/myhome/models_homes.py`
- Test: `packages/backend/tests/test_homes.py`

- [ ] **Step 1: Write the failing test**

Append to `packages/backend/tests/test_homes.py`:

```python
def test_create_home_demo_enables_all_modules(client):
    resp = client.post("/api/homes", json={"name": "Demo House", "type": "demo"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["type"] == "demo"
    from myhome.models_homes import ALL_MODULE_IDS
    assert set(data["enabledModules"]) == set(ALL_MODULE_IDS)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/backend && uv run pytest tests/test_homes.py::test_create_home_demo_enables_all_modules -v`
Expected: FAIL — 422 (Pydantic rejects `type: "demo"` since the `Literal` doesn't include it yet).

- [ ] **Step 3: Implement**

In `packages/backend/src/myhome/models_homes.py`, replace lines 12-40:

```python
DEFAULT_EXISTING_MODULES: list[str] = [
    "home", "plan", "chores", "inventory", "consumables", "works", "kb", "costs",
]

DEFAULT_PROJECT_MODULES: list[str] = ["home", "plan", "works", "kb"]

DEFAULT_DEMO_MODULES: list[str] = list(ALL_MODULE_IDS)


class Home(BaseModel):
    id: str
    name: str
    type: Literal["existing", "project", "demo"]
    enabledModules: list[str]
    createdAt: str


class HomeCreate(BaseModel):
    name: str
    type: Literal["existing", "project", "demo"]


class HomePatch(BaseModel):
    name: str | None = None
    type: Literal["existing", "project", "demo"] | None = None
    enabledModules: list[str] | None = None


class HomesDocument(BaseModel):
    version: int = 1
    homes: list[Home] = []
```

In `packages/backend/src/myhome/persistence_homes.py`, update the import (line 12-17) and `create_home` (line 67-72):

```python
from .models_homes import (
    Home,
    HomesDocument,
    DEFAULT_EXISTING_MODULES,
    DEFAULT_PROJECT_MODULES,
    DEFAULT_DEMO_MODULES,
)
```

```python
def create_home(name: str, home_type: str) -> Home:
    if home_type == "existing":
        modules = DEFAULT_EXISTING_MODULES[:]
    elif home_type == "demo":
        modules = DEFAULT_DEMO_MODULES[:]
    else:
        modules = DEFAULT_PROJECT_MODULES[:]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd packages/backend && uv run pytest tests/test_homes.py -v`
Expected: PASS (all tests in the file, including the new one and the pre-existing `test_create_home_existing`/`test_create_home_project`).

- [ ] **Step 5: Commit**

```bash
git add packages/backend/src/myhome/models_homes.py packages/backend/src/myhome/persistence_homes.py packages/backend/tests/test_homes.py
git commit -m "feat: add demo home type with all modules enabled"
```

---

## Task 2: Static placeholder attachment assets

**Files:**
- Create: `packages/backend/src/myhome/demo_assets/placeholder-photo-1.png`
- Create: `packages/backend/src/myhome/demo_assets/placeholder-photo-2.png`
- Create: `packages/backend/src/myhome/demo_assets/placeholder-manual.pdf`
- Create: `packages/backend/src/myhome/demo_assets/placeholder-receipt.pdf`
- Create: `packages/backend/src/myhome/demo_assets/placeholder-warranty.pdf`
- Test: `packages/backend/tests/test_demo_assets.py`

- [ ] **Step 1: Write the failing test**

Create `packages/backend/tests/test_demo_assets.py`:

```python
from pathlib import Path

ASSETS_DIR = Path(__file__).parent.parent / "src" / "myhome" / "demo_assets"

EXPECTED_FILES = [
    "placeholder-photo-1.png",
    "placeholder-photo-2.png",
    "placeholder-manual.pdf",
    "placeholder-receipt.pdf",
    "placeholder-warranty.pdf",
]


def test_all_expected_assets_exist_and_are_nonempty():
    for name in EXPECTED_FILES:
        path = ASSETS_DIR / name
        assert path.exists(), f"missing {name}"
        assert path.stat().st_size > 0


def test_png_assets_have_valid_signature():
    for name in ["placeholder-photo-1.png", "placeholder-photo-2.png"]:
        data = (ASSETS_DIR / name).read_bytes()
        assert data[:8] == b"\x89PNG\r\n\x1a\n"


def test_pdf_assets_have_valid_signature():
    for name in ["placeholder-manual.pdf", "placeholder-receipt.pdf", "placeholder-warranty.pdf"]:
        data = (ASSETS_DIR / name).read_bytes()
        assert data[:5] == b"%PDF-"
        assert data.rstrip().endswith(b"%%EOF")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/backend && uv run pytest tests/test_demo_assets.py -v`
Expected: FAIL — `assert path.exists()` fails, files don't exist yet.

- [ ] **Step 3: Generate the asset files**

Run this one-off script to generate the files (the script itself is not committed — only its output):

```bash
cd /projects/myhome/packages/backend
python3 - <<'EOF'
import pathlib
import struct
import zlib

ASSETS = pathlib.Path("src/myhome/demo_assets")
ASSETS.mkdir(parents=True, exist_ok=True)


def solid_png(width: int, height: int, rgb: tuple[int, int, int]) -> bytes:
    def chunk(tag: bytes, data: bytes) -> bytes:
        return (struct.pack(">I", len(data)) + tag + data +
                struct.pack(">I", zlib.crc32(tag + data) & 0xffffffff))

    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
    raw = b"".join(b"\x00" + bytes(rgb) * width for _ in range(height))
    idat = chunk(b"IDAT", zlib.compress(raw))
    iend = chunk(b"IEND", b"")
    return sig + ihdr + idat + iend


def build_pdf(text: str) -> bytes:
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 200 200] "
        b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    stream = f"BT /F1 14 Tf 20 100 Td ({text}) Tj ET".encode()
    objects.append(b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream")

    out = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for i, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n".encode() + body + b"\nendobj\n"
    xref_offset = len(out)
    out += f"xref\n0 {len(objects) + 1}\n".encode()
    out += b"0000000000 65535 f \n"
    for off in offsets[1:]:
        out += f"{off:010d} 00000 n \n".encode()
    out += (f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF").encode()
    return bytes(out)


(ASSETS / "placeholder-photo-1.png").write_bytes(solid_png(64, 64, (91, 141, 239)))
(ASSETS / "placeholder-photo-2.png").write_bytes(solid_png(64, 64, (240, 176, 90)))
(ASSETS / "placeholder-manual.pdf").write_bytes(build_pdf("Appliance Manual"))
(ASSETS / "placeholder-receipt.pdf").write_bytes(build_pdf("Receipt"))
(ASSETS / "placeholder-warranty.pdf").write_bytes(build_pdf("Warranty Card"))
print("done")
EOF
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd packages/backend && uv run pytest tests/test_demo_assets.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add packages/backend/src/myhome/demo_assets/ packages/backend/tests/test_demo_assets.py
git commit -m "feat: add static placeholder attachment assets for demo homes"
```

---

## Task 3: Floor plan geometry generator

**Files:**
- Create: `packages/backend/src/myhome/demo_geometry.py`
- Test: `packages/backend/tests/test_demo_geometry.py`

- [ ] **Step 1: Write the failing test**

Create `packages/backend/tests/test_demo_geometry.py`:

```python
from myhome.demo_geometry import generate_demo_house, room_centroid


def test_house_has_two_floors_with_expected_room_counts():
    doc = generate_demo_house()
    assert len(doc.floors) == 2
    ground = next(f for f in doc.floors if f.order == 0)
    upper = next(f for f in doc.floors if f.order == 1)
    assert ground.name == "Ground Floor"
    assert len(ground.rooms) == 6
    assert upper.name == "First Floor"
    assert len(upper.rooms) == 4


def test_rooms_have_valid_polygons_and_positive_area():
    doc = generate_demo_house()
    for floor in doc.floors:
        for room in floor.rooms:
            assert room.polygon is not None
            assert len(room.polygon) == 4
            assert room.areaM2 > 0


def test_room_and_wall_ids_are_unique_across_house():
    doc = generate_demo_house()
    room_ids = [r.id for f in doc.floors for r in f.rooms]
    wall_ids = [w.id for f in doc.floors for w in f.walls]
    assert len(room_ids) == len(set(room_ids))
    assert len(wall_ids) == len(set(wall_ids))


def test_every_floor_has_exactly_one_door_per_room_including_exterior():
    # The generator builds a spanning tree over the occupied cells (rooms - 1
    # interior doors) plus exactly one exterior door, so total doors == room count.
    doc = generate_demo_house()
    for floor in doc.floors:
        doors = [o for o in floor.openings if o.type == "door"]
        assert len(doors) == len(floor.rooms)
        wall_ids = {w.id for w in floor.walls}
        for door in doors:
            assert door.wallId in wall_ids
            assert door.width > 0


def test_room_centroid_is_center_of_polygon():
    doc = generate_demo_house()
    room = doc.floors[0].rooms[0]
    cx, cy = room_centroid(room)
    xs = [p.x for p in room.polygon]
    ys = [p.y for p in room.polygon]
    assert cx == sum(xs) / len(xs)
    assert cy == sum(ys) / len(ys)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/backend && uv run pytest tests/test_demo_geometry.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'myhome.demo_geometry'`

- [ ] **Step 3: Implement**

Create `packages/backend/src/myhome/demo_geometry.py`:

```python
from __future__ import annotations

import uuid

from .models import Floor, House, HouseDocument, Opening, Point, Room, Wall

CELL_SIZE = 3.5
DOOR_WIDTH = 0.9
WALL_THICKNESS = 0.15

# (row, col) grid cells occupied by each floor, in the order room names are
# assigned. Ground floor omits three corners to produce an L/cross-shaped
# footprint instead of a plain rectangle; cells stay edge-connected through
# the (1, 1) hub so the spanning-tree door algorithm below reaches every room.
_GROUND_FLOOR_CELLS: list[tuple[int, int]] = [(0, 1), (1, 0), (1, 1), (1, 2), (2, 1), (2, 2)]
_GROUND_FLOOR_ROOMS = ["Kitchen", "Living Room", "Dining Room", "Garage", "Bathroom", "Laundry Room"]

_UPPER_FLOOR_CELLS: list[tuple[int, int]] = [(0, 0), (0, 1), (1, 0), (1, 1)]
_UPPER_FLOOR_ROOMS = ["Primary Bedroom", "Bedroom 2", "Home Office", "Bathroom 2"]

# direction name -> (row delta, col delta) -> function building the two
# endpoints of that cell edge from its bounding box
_EDGES = [
    ("top", (-1, 0), lambda x0, y0, x1, y1: (Point(x=x0, y=y0), Point(x=x1, y=y0))),
    ("bottom", (1, 0), lambda x0, y0, x1, y1: (Point(x=x0, y=y1), Point(x=x1, y=y1))),
    ("left", (0, -1), lambda x0, y0, x1, y1: (Point(x=x0, y=y0), Point(x=x0, y=y1))),
    ("right", (0, 1), lambda x0, y0, x1, y1: (Point(x=x1, y=y0), Point(x=x1, y=y1))),
]


def _cell_rect(row: int, col: int) -> tuple[float, float, float, float]:
    x0, y0 = col * CELL_SIZE, row * CELL_SIZE
    return x0, y0, x0 + CELL_SIZE, y0 + CELL_SIZE


def _wall_length(wall: Wall) -> float:
    return ((wall.end.x - wall.start.x) ** 2 + (wall.end.y - wall.start.y) ** 2) ** 0.5


def _build_floor(name: str, order: int, cells: list[tuple[int, int]], room_names: list[str]) -> Floor:
    occupied = set(cells)
    rooms: list[Room] = []
    walls: list[Wall] = []
    wall_by_pair: dict[frozenset, Wall] = {}
    exterior_walls_by_cell: dict[tuple[int, int], list[Wall]] = {}

    for cell, label in zip(cells, room_names):
        x0, y0, x1, y1 = _cell_rect(*cell)
        rooms.append(Room(
            id=str(uuid.uuid4()),
            label=label,
            polygon=[Point(x=x0, y=y0), Point(x=x1, y=y0), Point(x=x1, y=y1), Point(x=x0, y=y1)],
            areaM2=CELL_SIZE * CELL_SIZE,
        ))

    for cell in cells:
        x0, y0, x1, y1 = _cell_rect(*cell)
        for _dir_name, (dr, dc), points_fn in _EDGES:
            neighbor = (cell[0] + dr, cell[1] + dc)
            start, end = points_fn(x0, y0, x1, y1)
            if neighbor in occupied:
                pair = frozenset({cell, neighbor})
                if pair in wall_by_pair:
                    continue  # already emitted from the neighbor's side
                wall = Wall(id=str(uuid.uuid4()), start=start, end=end, thickness=WALL_THICKNESS, type="wall")
                wall_by_pair[pair] = wall
                walls.append(wall)
            else:
                wall = Wall(id=str(uuid.uuid4()), start=start, end=end, thickness=WALL_THICKNESS, type="wall")
                walls.append(wall)
                exterior_walls_by_cell.setdefault(cell, []).append(wall)

    # Spanning tree (depth-first) over the occupied cells: exactly
    # len(cells) - 1 interior doors, guaranteeing every room is reachable.
    openings: list[Opening] = []
    visited = {cells[0]}
    stack = [cells[0]]
    while stack:
        current = stack.pop()
        for _dir_name, (dr, dc), _points_fn in _EDGES:
            neighbor = (current[0] + dr, current[1] + dc)
            if neighbor in occupied and neighbor not in visited:
                wall = wall_by_pair[frozenset({current, neighbor})]
                length = _wall_length(wall)
                openings.append(Opening(
                    id=str(uuid.uuid4()), wallId=wall.id, type="door",
                    offset=(length - DOOR_WIDTH) / 2, width=DOOR_WIDTH,
                ))
                visited.add(neighbor)
                stack.append(neighbor)

    # One exterior door, on the first occupied cell that has an exterior wall.
    for cell in cells:
        ext_walls = exterior_walls_by_cell.get(cell)
        if ext_walls:
            wall = ext_walls[0]
            length = _wall_length(wall)
            openings.append(Opening(
                id=str(uuid.uuid4()), wallId=wall.id, type="door",
                offset=(length - DOOR_WIDTH) / 2, width=DOOR_WIDTH,
            ))
            break

    return Floor(id=str(uuid.uuid4()), name=name, order=order, walls=walls, openings=openings, rooms=rooms, furnitureObjects=[])


def room_centroid(room: Room) -> tuple[float, float]:
    xs = [p.x for p in room.polygon]
    ys = [p.y for p in room.polygon]
    return sum(xs) / len(xs), sum(ys) / len(ys)


def generate_demo_house() -> HouseDocument:
    ground = _build_floor("Ground Floor", 0, _GROUND_FLOOR_CELLS, _GROUND_FLOOR_ROOMS)
    upper = _build_floor("First Floor", 1, _UPPER_FLOOR_CELLS, _UPPER_FLOOR_ROOMS)
    return HouseDocument(house=House(name="Demo Home"), floors=[ground, upper])
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd packages/backend && uv run pytest tests/test_demo_geometry.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add packages/backend/src/myhome/demo_geometry.py packages/backend/tests/test_demo_geometry.py
git commit -m "feat: add grid-based floor plan generator for demo homes"
```

---

## Task 4: Demo settings content (categories, suppliers)

**Files:**
- Create: `packages/backend/src/myhome/demo_content.py`
- Test: `packages/backend/tests/test_demo_content.py`

- [ ] **Step 1: Write the failing test**

Create `packages/backend/tests/test_demo_content.py`:

```python
from myhome.demo_content import (
    CHORES,
    CONSUMABLES,
    INVENTORY_ITEMS,
    KB_TITLES,
    WORKS,
    generate_demo_settings,
)


def test_generate_demo_settings_has_expected_category_counts():
    settings = generate_demo_settings()
    assert len(settings.costCategories) == 9
    assert len(settings.workCategories) == 7
    assert len(settings.inventoryCategories) == 8
    assert len(settings.consumableCategories) == 6
    assert len(settings.suppliers) == 9
    assert len(settings.consumableUnits) > 0


def test_generate_demo_settings_ids_are_unique():
    settings = generate_demo_settings()
    assert len({c.id for c in settings.costCategories}) == 9
    assert len({c.id for c in settings.workCategories}) == 7
    assert len({c.id for c in settings.inventoryCategories}) == 8
    assert len({c.id for c in settings.consumableCategories}) == 6
    assert len({s.id for s in settings.suppliers}) == 9


def test_curated_content_lists_have_at_least_32_entries():
    assert len(CHORES) >= 32
    assert len(INVENTORY_ITEMS) >= 32
    assert len(WORKS) >= 32
    assert len(KB_TITLES) >= 32
    assert len(CONSUMABLES) >= 32


def test_curated_entries_reference_valid_category_ids():
    settings = generate_demo_settings()
    inventory_cat_ids = {c.id for c in settings.inventoryCategories}
    work_cat_ids = {c.id for c in settings.workCategories}
    consumable_cat_ids = {c.id for c in settings.consumableCategories}
    for _name, _emoji, category_id, _price_range in INVENTORY_ITEMS:
        assert category_id in inventory_cat_ids
    for _title, category_id, _cost_range in WORKS:
        assert category_id in work_cat_ids
    for _name, _emoji, category_id, _unit in CONSUMABLES:
        assert category_id in consumable_cat_ids
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/backend && uv run pytest tests/test_demo_content.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'myhome.demo_content'`

- [ ] **Step 3: Implement**

Create `packages/backend/src/myhome/demo_content.py`:

```python
from __future__ import annotations

from .models_settings import (
    ConsumableCategory,
    CostCategory,
    InventoryCategory,
    Supplier,
    SettingsDocument,
    WorkCategory,
    _default_consumable_units,
)

# ── Settings: demo-specific category/supplier sets ──────────────────────────
# These are independent of the app's built-in _default_*() lists (used for
# regular homes) so the demo home has enough category variety to spread 30+
# records across meaningfully.

_COST_CATEGORIES = [
    CostCategory(id="cat-fuel", name="Fuel / Heating", emoji="🛢", unit="L", color="#4466cc"),
    CostCategory(id="cat-electricity", name="Electricity", emoji="💡", unit="kWh", color="#44aacc"),
    CostCategory(id="cat-water", name="Water", emoji="💧", unit="m³", color="#44ccaa"),
    CostCategory(id="cat-mortgage", name="Mortgage / Rent", emoji="🏦", unit=None, color="#9966cc"),
    CostCategory(id="cat-insurance", name="Insurance", emoji="🛡", unit=None, color="#cc6699"),
    CostCategory(id="cat-groceries", name="Groceries", emoji="🛒", unit=None, color="#66cc88"),
    CostCategory(id="cat-maintenance", name="Maintenance", emoji="🔧", unit=None, color="#cc8844"),
    CostCategory(id="cat-internet", name="Internet & Phone", emoji="📶", unit=None, color="#4488cc"),
    CostCategory(id="cat-entertainment", name="Entertainment", emoji="🎬", unit=None, color="#aa66cc"),
]

_WORK_CATEGORIES = [
    WorkCategory(id="wcat-plumbing", name="Plumbing", emoji="🔧"),
    WorkCategory(id="wcat-electrical", name="Electrical", emoji="⚡"),
    WorkCategory(id="wcat-roofing", name="Roofing", emoji="🏠"),
    WorkCategory(id="wcat-painting", name="Painting", emoji="🎨"),
    WorkCategory(id="wcat-flooring", name="Flooring", emoji="🪵"),
    WorkCategory(id="wcat-hvac", name="HVAC", emoji="❄️"),
    WorkCategory(id="wcat-landscaping", name="Landscaping", emoji="🌳"),
]

_INVENTORY_CATEGORIES = [
    InventoryCategory(id="inv-electronics", name="Electronics"),
    InventoryCategory(id="inv-appliances", name="Appliances"),
    InventoryCategory(id="inv-furniture", name="Furniture"),
    InventoryCategory(id="inv-tools", name="Tools"),
    InventoryCategory(id="inv-outdoor", name="Outdoor"),
    InventoryCategory(id="inv-bedroom", name="Bedroom"),
    InventoryCategory(id="inv-office", name="Office"),
    InventoryCategory(id="inv-decor", name="Décor"),
]

_CONSUMABLE_CATEGORIES = [
    ConsumableCategory(id="ccat-cleaning", name="Cleaning Supplies", emoji="🧽"),
    ConsumableCategory(id="ccat-kitchen", name="Kitchen Consumables", emoji="🍽️"),
    ConsumableCategory(id="ccat-bathroom", name="Bathroom Supplies", emoji="🧴"),
    ConsumableCategory(id="ccat-filters", name="Filters & Batteries", emoji="🔋"),
    ConsumableCategory(id="ccat-pet", name="Pet Supplies", emoji="🐾"),
    ConsumableCategory(id="ccat-office", name="Office Supplies", emoji="📎"),
]

_SUPPLIERS = [
    Supplier(id="sup-metro-plumbing", name="Metro Plumbing Co."),
    Supplier(id="sup-brightspark-electric", name="BrightSpark Electric"),
    Supplier(id="sup-greenscape-landscaping", name="GreenScape Landscaping"),
    Supplier(id="sup-ace-hardware", name="Ace Hardware"),
    Supplier(id="sup-cleanpro-services", name="CleanPro Services"),
    Supplier(id="sup-valleyview-appliance-repair", name="ValleyView Appliance Repair"),
    Supplier(id="sup-suntrust-roofing", name="SunTrust Roofing"),
    Supplier(id="sup-clearview-window-gutter", name="ClearView Window & Gutter"),
    Supplier(id="sup-home-comfort-hvac", name="Home Comfort HVAC"),
]


def generate_demo_settings() -> SettingsDocument:
    return SettingsDocument(
        costCategories=list(_COST_CATEGORIES),
        workCategories=list(_WORK_CATEGORIES),
        inventoryCategories=list(_INVENTORY_CATEGORIES),
        consumableCategories=list(_CONSUMABLE_CATEGORIES),
        suppliers=list(_SUPPLIERS),
        consumableUnits=_default_consumable_units(),
    )


# ── Chores: (name, emoji, periodDays, room label hint) ──────────────────────
CHORES: list[tuple[str, str, float, str]] = [
    ("Vacuum living room", "🧹", 7, "Living Room"),
    ("Mop kitchen floor", "🧽", 7, "Kitchen"),
    ("Take out trash", "🗑️", 3, "Kitchen"),
    ("Take out recycling", "♻️", 14, "Kitchen"),
    ("Wash bed sheets", "🛏️", 14, "Primary Bedroom"),
    ("Clean bathroom", "🚿", 7, "Bathroom"),
    ("Clean toilets", "🚽", 7, "Bathroom 2"),
    ("Dust furniture", "🪶", 14, "Living Room"),
    ("Wipe kitchen counters", "🧴", 3, "Kitchen"),
    ("Clean refrigerator", "🧊", 30, "Kitchen"),
    ("Clean oven", "🔥", 60, "Kitchen"),
    ("Descale coffee maker", "☕", 30, "Kitchen"),
    ("Clean windows", "🪟", 60, "Living Room"),
    ("Mow lawn", "🌱", 14, "Garage"),
    ("Water houseplants", "🪴", 7, "Living Room"),
    ("Water garden plants", "🌻", 3, "Garage"),
    ("Rake leaves", "🍂", 30, "Garage"),
    ("Trim hedges", "✂️", 45, "Garage"),
    ("Clean gutters", "🍁", 180, "Garage"),
    ("Change HVAC filter", "🌬️", 90, "Laundry Room"),
    ("Test smoke detectors", "🔥", 180, "Living Room"),
    ("Test carbon monoxide detectors", "⚠️", 180, "Living Room"),
    ("Check fire extinguisher", "🧯", 180, "Kitchen"),
    ("Clean dryer lint trap", "🌀", 30, "Laundry Room"),
    ("Deep clean washing machine", "🫧", 60, "Laundry Room"),
    ("Sanitize dishwasher", "🍽️", 60, "Kitchen"),
    ("Organize pantry", "🥫", 60, "Kitchen"),
    ("Organize garage", "🧰", 90, "Garage"),
    ("Wash car", "🚗", 21, "Garage"),
    ("Change car oil", "🛢️", 120, "Garage"),
    ("Sweep porch / entryway", "🧹", 7, "Living Room"),
    ("Clean light fixtures", "💡", 60, "Living Room"),
    ("Wipe down light switches & doorknobs", "🧼", 14, "Living Room"),
    ("Rotate mattress", "🛌", 180, "Primary Bedroom"),
    ("Service HVAC system", "❄️", 180, "Laundry Room"),
]

# ── Inventory: (name, emoji, category id, (min price, max price)) ──────────
INVENTORY_ITEMS: list[tuple[str, str, str, tuple[float, float]]] = [
    ("Samsung 55\" QLED TV", "📺", "inv-electronics", (600, 1200)),
    ("Sony Soundbar", "🔊", "inv-electronics", (150, 400)),
    ("Apple MacBook Pro", "💻", "inv-electronics", (1200, 2500)),
    ("Dell Home Office Monitor", "🖥️", "inv-office", (150, 350)),
    ("HP LaserJet Printer", "🖨️", "inv-office", (100, 250)),
    ("KitchenAid Stand Mixer", "🍰", "inv-appliances", (250, 450)),
    ("Ninja Blender", "🥤", "inv-appliances", (60, 150)),
    ("Breville Espresso Machine", "☕", "inv-appliances", (300, 700)),
    ("Instant Pot", "🍲", "inv-appliances", (70, 150)),
    ("Whirlpool Refrigerator", "🧊", "inv-appliances", (900, 1800)),
    ("Bosch Dishwasher", "🍽️", "inv-appliances", (500, 900)),
    ("LG Washing Machine", "🌀", "inv-appliances", (500, 900)),
    ("Samsung Dryer", "🔥", "inv-appliances", (500, 900)),
    ("IKEA MALM Bed Frame", "🛏️", "inv-bedroom", (150, 350)),
    ("Tempur-Pedic Mattress", "🛌", "inv-bedroom", (800, 2000)),
    ("IKEA PAX Wardrobe", "🚪", "inv-bedroom", (300, 600)),
    ("Nightstand Set", "🕯️", "inv-bedroom", (80, 200)),
    ("Sectional Sofa", "🛋️", "inv-furniture", (800, 2000)),
    ("Dining Table Set", "🍴", "inv-furniture", (400, 1000)),
    ("Bookshelf", "📚", "inv-furniture", (100, 300)),
    ("Coffee Table", "☕", "inv-furniture", (100, 300)),
    ("Office Desk", "🗄️", "inv-office", (150, 400)),
    ("Ergonomic Office Chair", "🪑", "inv-office", (150, 500)),
    ("Dyson V11 Vacuum", "🧹", "inv-tools", (400, 700)),
    ("Cordless Drill Set", "🔩", "inv-tools", (80, 200)),
    ("Ladder", "🪜", "inv-tools", (60, 150)),
    ("Pressure Washer", "💦", "inv-tools", (150, 350)),
    ("Lawn Mower", "🌱", "inv-outdoor", (250, 600)),
    ("Leaf Blower", "🍃", "inv-outdoor", (80, 200)),
    ("Weber Genesis Grill", "🔥", "inv-outdoor", (400, 900)),
    ("Patio Furniture Set", "🪑", "inv-outdoor", (300, 800)),
    ("Garden Shed", "🏚️", "inv-outdoor", (500, 1500)),
    ("Area Rug", "🧵", "inv-decor", (80, 250)),
    ("Wall Art Print Set", "🖼️", "inv-decor", (50, 150)),
    ("Table Lamp Set", "💡", "inv-decor", (40, 120)),
]

# Category id -> preferred room labels (searched on the generated house).
INVENTORY_CATEGORY_ROOM_HINTS: dict[str, list[str]] = {
    "inv-electronics": ["Living Room"],
    "inv-appliances": ["Kitchen"],
    "inv-bedroom": ["Primary Bedroom", "Bedroom 2"],
    "inv-furniture": ["Living Room", "Dining Room"],
    "inv-office": ["Home Office"],
    "inv-tools": ["Garage"],
    "inv-outdoor": ["Garage"],
    "inv-decor": ["Living Room"],
}

CONSUMABLE_CATEGORY_ROOM_HINTS: dict[str, list[str]] = {
    "ccat-cleaning": ["Laundry Room"],
    "ccat-kitchen": ["Kitchen"],
    "ccat-bathroom": ["Bathroom"],
    "ccat-filters": ["Laundry Room"],
    "ccat-pet": ["Kitchen"],
    "ccat-office": ["Home Office"],
}

# ── Works: (title, category id, (min cost, max cost)) ───────────────────────
WORKS: list[tuple[str, str, tuple[float, float]]] = [
    ("Replace water heater", "wcat-plumbing", (800, 1600)),
    ("Fix leaking kitchen faucet", "wcat-plumbing", (100, 300)),
    ("Unclog main sewer line", "wcat-plumbing", (200, 600)),
    ("Repipe upstairs bathroom", "wcat-plumbing", (1500, 3500)),
    ("Install new toilet", "wcat-plumbing", (250, 500)),
    ("Repair garbage disposal", "wcat-plumbing", (100, 250)),
    ("Upgrade electrical panel", "wcat-electrical", (1200, 2500)),
    ("Install ceiling fan", "wcat-electrical", (150, 350)),
    ("Rewire living room outlets", "wcat-electrical", (300, 700)),
    ("Install outdoor security lighting", "wcat-electrical", (200, 500)),
    ("Replace smoke detector wiring", "wcat-electrical", (150, 400)),
    ("Install EV charger", "wcat-electrical", (800, 1800)),
    ("Replace roof shingles (section)", "wcat-roofing", (1500, 4000)),
    ("Repair roof flashing", "wcat-roofing", (300, 800)),
    ("Clean and inspect chimney", "wcat-roofing", (150, 350)),
    ("Install gutter guards", "wcat-roofing", (400, 900)),
    ("Repaint living room", "wcat-painting", (300, 800)),
    ("Repaint exterior siding", "wcat-painting", (2000, 5000)),
    ("Paint kitchen cabinets", "wcat-painting", (500, 1200)),
    ("Touch up trim and baseboards", "wcat-painting", (100, 300)),
    ("Refinish hardwood floors", "wcat-flooring", (1500, 3500)),
    ("Install new carpet in bedroom", "wcat-flooring", (600, 1400)),
    ("Repair damaged tile in bathroom", "wcat-flooring", (200, 500)),
    ("Install laminate flooring in office", "wcat-flooring", (800, 1800)),
    ("Service HVAC system", "wcat-hvac", (150, 350)),
    ("Replace furnace", "wcat-hvac", (2500, 5500)),
    ("Install smart thermostat", "wcat-hvac", (150, 350)),
    ("Duct cleaning", "wcat-hvac", (300, 600)),
    ("Repair air conditioning unit", "wcat-hvac", (200, 600)),
    ("Landscape front yard", "wcat-landscaping", (800, 2500)),
    ("Install sprinkler system", "wcat-landscaping", (1500, 3500)),
    ("Trim large trees", "wcat-landscaping", (300, 800)),
    ("Build backyard deck", "wcat-landscaping", (3000, 8000)),
    ("Repair fence panel", "wcat-landscaping", (150, 400)),
    ("Install garden retaining wall", "wcat-landscaping", (800, 2000)),
]

# ── Knowledge Base: titles ───────────────────────────────────────────────────
KB_TITLES: list[str] = [
    "Furnace Filter Replacement Guide",
    "Wi-Fi Router Reset Instructions",
    "Water Shutoff Valve Location",
    "Main Electrical Panel Location & Breaker Map",
    "Trash & Recycling Pickup Schedule",
    "Home Alarm System Codes (keep private)",
    "Emergency Contact List",
    "Warranty Contacts & Reference Numbers",
    "Appliance Manuals — Where to Find Them",
    "HVAC System Maintenance Schedule",
    "Smoke & CO Detector Battery Replacement Log",
    "Garage Door Opener Remote Programming",
    "Septic Tank Service History",
    "Well Water Testing Schedule",
    "Gas Shutoff Valve Location",
    "Circuit Breaker Labeling Reference",
    "Paint Colors Reference (by room)",
    "Flooring Materials Reference",
    "Home Insurance Policy Summary",
    "Property Tax Payment Schedule",
    "Home Security Camera Access Instructions",
    "Guest Wi-Fi Password Instructions",
    "Sprinkler System Zone Map",
    "Pool / Spa Maintenance Checklist",
    "Snow Removal Contractor Info",
    "Lawn Care Schedule",
    "Pest Control Service History",
    "Chimney Sweep Service History",
    "Roof Inspection Notes",
    "Window & Door Weatherproofing Notes",
    "Moving-In Checklist",
    "Utility Provider Contacts",
    "HOA Rules & Contact Info",
    "Recommended Local Contractors",
    "Home Inventory for Insurance Claims",
]

KB_OPENERS: list[str] = [
    "Keep this reference up to date so anyone in the household can find it quickly.",
    "Written down here so it doesn't get lost in a drawer somewhere.",
    "Update this whenever something changes so it stays accurate.",
    "A quick reference for future-you, or whoever's dealing with this next.",
]

KB_CLOSERS: list[str] = [
    "Double-check details in person before relying on this for anything urgent.",
    "If anything here goes out of date, update it the same day you notice.",
    "Ask a neighbor or the previous owner if any of this seems unclear.",
    "Cross-reference with the relevant manual or provider website if unsure.",
]

# ── Consumables: (name, emoji, category id, unit) ────────────────────────────
CONSUMABLES: list[tuple[str, str, str, str]] = [
    ("Paper Towels", "🧻", "ccat-cleaning", "rolls"),
    ("Dish Soap", "🧴", "ccat-kitchen", "L"),
    ("Laundry Detergent", "🧺", "ccat-cleaning", "L"),
    ("Fabric Softener", "🌸", "ccat-cleaning", "L"),
    ("All-Purpose Cleaner", "🧽", "ccat-cleaning", "L"),
    ("Glass Cleaner", "🪟", "ccat-cleaning", "L"),
    ("Toilet Bowl Cleaner", "🚽", "ccat-bathroom", "count"),
    ("Bathroom Bleach", "🧴", "ccat-bathroom", "L"),
    ("Sponges", "🧽", "ccat-kitchen", "count"),
    ("Trash Bags", "🗑️", "ccat-cleaning", "rolls"),
    ("Recycling Bags", "♻️", "ccat-cleaning", "rolls"),
    ("Toilet Paper", "🧻", "ccat-bathroom", "rolls"),
    ("Facial Tissues", "🤧", "ccat-bathroom", "count"),
    ("Hand Soap", "🧼", "ccat-bathroom", "count"),
    ("Shampoo", "🧴", "ccat-bathroom", "count"),
    ("Conditioner", "🧴", "ccat-bathroom", "count"),
    ("Toothpaste", "🪥", "ccat-bathroom", "count"),
    ("HVAC Filter 16x20", "🌬️", "ccat-filters", "count"),
    ("Water Filter Cartridge", "💧", "ccat-filters", "count"),
    ("Vacuum Bags", "🧹", "ccat-cleaning", "count"),
    ("AA Batteries", "🔋", "ccat-filters", "count"),
    ("AAA Batteries", "🔋", "ccat-filters", "count"),
    ("9V Batteries", "🔋", "ccat-filters", "count"),
    ("Light Bulbs (LED)", "💡", "ccat-filters", "count"),
    ("Coffee Pods", "☕", "ccat-kitchen", "count"),
    ("Ground Coffee", "☕", "ccat-kitchen", "kg"),
    ("Dishwasher Pods", "🍽️", "ccat-kitchen", "count"),
    ("Aluminum Foil", "🧴", "ccat-kitchen", "count"),
    ("Plastic Wrap", "🧴", "ccat-kitchen", "count"),
    ("Ziplock Bags", "🧴", "ccat-kitchen", "count"),
    ("Dog Food", "🐕", "ccat-pet", "kg"),
    ("Cat Litter", "🐈", "ccat-pet", "kg"),
    ("Printer Paper", "📄", "ccat-office", "packs"),
    ("Printer Ink Cartridges", "🖨️", "ccat-office", "count"),
    ("Sticky Notes", "📝", "ccat-office", "packs"),
]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd packages/backend && uv run pytest tests/test_demo_content.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add packages/backend/src/myhome/demo_content.py packages/backend/tests/test_demo_content.py
git commit -m "feat: add curated demo content and settings generator"
```

---

## Task 5: Chores generator

**Files:**
- Create: `packages/backend/src/myhome/demo_data.py`
- Test: `packages/backend/tests/test_demo_data.py`

- [ ] **Step 1: Write the failing test**

Create `packages/backend/tests/test_demo_data.py`:

```python
import random

from myhome.demo_geometry import generate_demo_house
from myhome.demo_data import generate_demo_chores


def test_generate_demo_chores_has_at_least_32_chores():
    house = generate_demo_house()
    doc = generate_demo_chores(house, random.Random(42))
    assert len(doc.chores) >= 32


def test_generate_demo_chores_assignments_reference_valid_rooms():
    house = generate_demo_house()
    doc = generate_demo_chores(house, random.Random(42))
    room_ids = {r.id for f in house.floors for r in f.rooms}
    chore_ids = {c.id for c in doc.chores}
    assert len(doc.assignments) > 0
    for a in doc.assignments:
        assert a.choreId in chore_ids
        assert a.roomId in room_ids


def test_generate_demo_chores_has_some_overdue_and_some_upcoming():
    from datetime import datetime, timezone
    house = generate_demo_house()
    doc = generate_demo_chores(house, random.Random(42))
    now = datetime.now(timezone.utc)
    due_dates = [datetime.fromisoformat(c.nextDueDate) for c in doc.chores]
    assert any(d < now for d in due_dates)
    assert any(d >= now for d in due_dates)


def test_generate_demo_chores_completions_reference_valid_chores():
    chore_ids_seen = set()
    house = generate_demo_house()
    doc = generate_demo_chores(house, random.Random(42))
    chore_ids = {c.id for c in doc.chores}
    assert len(doc.completions) > 0
    for comp in doc.completions:
        assert comp.choreId in chore_ids
        chore_ids_seen.add(comp.choreId)


def test_generate_demo_chores_is_deterministic_for_a_given_seed():
    house = generate_demo_house()
    doc1 = generate_demo_chores(house, random.Random(7))
    doc2 = generate_demo_chores(house, random.Random(7))
    assert [c.name for c in doc1.chores] == [c.name for c in doc2.chores]
    assert [c.nextDueDate for c in doc1.chores] == [c.nextDueDate for c in doc2.chores]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/backend && uv run pytest tests/test_demo_data.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'myhome.demo_data'`

- [ ] **Step 3: Implement**

Create `packages/backend/src/myhome/demo_data.py`:

```python
from __future__ import annotations

import random
import uuid
from datetime import datetime, timedelta, timezone

from .demo_content import CHORES
from .demo_geometry import room_centroid
from .models import HouseDocument, Room
from .models_chores import Assignment, ChoreDocument, Chore, CompletionRecord, Position


def _find_room(house: HouseDocument, label: str) -> Room:
    for floor in house.floors:
        for room in floor.rooms:
            if room.label == label:
                return room
    # Fall back to any room so a typo'd hint never crashes generation.
    return house.floors[0].rooms[0]


def _floor_id_for_room(house: HouseDocument, room_id: str) -> str:
    for floor in house.floors:
        if any(r.id == room_id for r in floor.rooms):
            return floor.id
    return house.floors[0].id


def _jittered_position(room: Room, rng: random.Random) -> Position:
    cx, cy = room_centroid(room)
    return Position(x=cx + rng.uniform(-0.8, 0.8), y=cy + rng.uniform(-0.8, 0.8))


def generate_demo_chores(house: HouseDocument, rng: random.Random) -> ChoreDocument:
    now = datetime.now(timezone.utc)
    chores: list[Chore] = []
    assignments: list[Assignment] = []
    completions: list[CompletionRecord] = []

    shuffled = CHORES[:]
    rng.shuffle(shuffled)
    overdue_count = round(len(shuffled) * 0.2)
    due_soon_count = round(len(shuffled) * 0.3)

    for i, (name, emoji, period_days, room_hint) in enumerate(shuffled):
        jitter = rng.uniform(0.8, 1.2)
        period = round(period_days * jitter, 1)

        if i < overdue_count:
            due = now - timedelta(days=rng.randint(1, 30))
        elif i < overdue_count + due_soon_count:
            due = now + timedelta(days=rng.randint(0, 7))
        else:
            due = now + timedelta(days=rng.randint(8, max(9, int(period))))

        chore = Chore(
            id=str(uuid.uuid4()),
            name=name,
            emoji=emoji,
            periodDays=period,
            frequency=max(1, round(period)),
            frequencyMetadata={"unit": "days"},
            nextDueDate=due.isoformat(),
        )
        chores.append(chore)

        for _ in range(rng.randint(0, 4)):
            completed_at = now - timedelta(days=rng.randint(1, 90))
            scheduled_due = completed_at - timedelta(days=rng.randint(0, 5))
            completions.append(CompletionRecord(
                id=str(uuid.uuid4()), choreId=chore.id,
                completedAt=completed_at.isoformat(),
                scheduledDue=scheduled_due.isoformat(),
            ))

        if i < 20:
            room = _find_room(house, room_hint)
            assignments.append(Assignment(
                id=str(uuid.uuid4()), choreId=chore.id, roomId=room.id,
                position=_jittered_position(room, rng), nextDueDate=due.isoformat(),
            ))

    return ChoreDocument(chores=chores, assignments=assignments, completions=completions)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd packages/backend && uv run pytest tests/test_demo_data.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add packages/backend/src/myhome/demo_data.py packages/backend/tests/test_demo_data.py
git commit -m "feat: add demo chores generator"
```

---

## Task 6: Inventory generator

**Files:**
- Modify: `packages/backend/src/myhome/demo_data.py`
- Test: `packages/backend/tests/test_demo_data.py`

- [ ] **Step 1: Write the failing test**

Append to `packages/backend/tests/test_demo_data.py`:

```python
from datetime import date

from myhome.demo_content import generate_demo_settings
from myhome.demo_data import generate_demo_inventory


def test_generate_demo_inventory_has_at_least_32_items():
    house = generate_demo_house()
    settings = generate_demo_settings()
    doc = generate_demo_inventory(house, settings, random.Random(42))
    assert len(doc.items) >= 32


def test_generate_demo_inventory_items_have_valid_category_and_placement():
    house = generate_demo_house()
    settings = generate_demo_settings()
    doc = generate_demo_inventory(house, settings, random.Random(42))
    category_ids = {c.id for c in settings.inventoryCategories}
    floor_ids = {f.id for f in house.floors}
    room_ids = {r.id for f in house.floors for r in f.rooms}
    for item in doc.items:
        assert item.category in category_ids
        assert item.placement is not None
        assert item.placement.floorId in floor_ids
        assert item.placement.roomId in room_ids
        assert item.purchasePrice > 0


def test_generate_demo_inventory_some_warranties_already_expired():
    house = generate_demo_house()
    settings = generate_demo_settings()
    doc = generate_demo_inventory(house, settings, random.Random(42))
    today = date.today().isoformat()
    expired = [i for i in doc.items if i.warrantyExpiryDate and i.warrantyExpiryDate < today]
    assert len(expired) > 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/backend && uv run pytest tests/test_demo_data.py -v -k inventory`
Expected: FAIL — `ImportError: cannot import name 'generate_demo_inventory'`

- [ ] **Step 3: Implement**

Append to `packages/backend/src/myhome/demo_data.py` (add imports at top and the function at the end):

```python
from datetime import date

from .demo_content import INVENTORY_CATEGORY_ROOM_HINTS, INVENTORY_ITEMS
from .models_inventory import InventoryDocument, InventoryItem, InventoryPlacement, InventoryPosition
from .models_settings import SettingsDocument
```

```python
def generate_demo_inventory(house: HouseDocument, settings: SettingsDocument, rng: random.Random) -> InventoryDocument:
    today = date.today()
    items: list[InventoryItem] = []

    for name, emoji, category_id, (price_min, price_max) in INVENTORY_ITEMS:
        hints = INVENTORY_CATEGORY_ROOM_HINTS.get(category_id, [])
        room_label = rng.choice(hints) if hints else house.floors[0].rooms[0].label
        room = _find_room(house, room_label)
        floor_id = _floor_id_for_room(house, room.id)

        purchase_days_ago = rng.randint(30, 5 * 365)
        purchase_date = today - timedelta(days=purchase_days_ago)
        warranty_days = rng.randint(365, 3 * 365)
        warranty_expiry = purchase_date + timedelta(days=warranty_days)
        cx, cy = room_centroid(room)

        items.append(InventoryItem(
            id=str(uuid.uuid4()),
            name=name,
            emoji=emoji,
            category=category_id,
            purchaseDate=purchase_date.isoformat(),
            purchasePrice=round(rng.uniform(price_min, price_max), 2),
            warrantyExpiryDate=warranty_expiry.isoformat(),
            placement=InventoryPlacement(
                floorId=floor_id, roomId=room.id,
                position=InventoryPosition(x=cx + rng.uniform(-0.8, 0.8), y=cy + rng.uniform(-0.8, 0.8)),
            ),
        ))

    return InventoryDocument(items=items)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd packages/backend && uv run pytest tests/test_demo_data.py -v`
Expected: PASS (all tests so far)

- [ ] **Step 5: Commit**

```bash
git add packages/backend/src/myhome/demo_data.py packages/backend/tests/test_demo_data.py
git commit -m "feat: add demo inventory generator"
```

---

## Task 7: Costs generator

**Files:**
- Modify: `packages/backend/src/myhome/demo_data.py`
- Test: `packages/backend/tests/test_demo_data.py`

- [ ] **Step 1: Write the failing test**

Append to `packages/backend/tests/test_demo_data.py`:

```python
from myhome.demo_data import generate_demo_costs


def test_generate_demo_costs_has_at_least_32_entries():
    settings = generate_demo_settings()
    doc = generate_demo_costs(settings, random.Random(42))
    assert len(doc.entries) >= 32


def test_generate_demo_costs_entries_reference_valid_categories_and_suppliers():
    settings = generate_demo_settings()
    doc = generate_demo_costs(settings, random.Random(42))
    category_ids = {c.id for c in settings.costCategories}
    supplier_ids = {s.id for s in settings.suppliers}
    for entry in doc.entries:
        assert entry.categoryId in category_ids
        assert entry.totalAmount > 0
        if entry.supplierId is not None:
            assert entry.supplierId in supplier_ids


def test_generate_demo_costs_spread_across_last_12_months():
    from datetime import date, timedelta
    settings = generate_demo_settings()
    doc = generate_demo_costs(settings, random.Random(42))
    cutoff = (date.today() - timedelta(days=370)).isoformat()
    assert all(e.date >= cutoff for e in doc.entries)
    assert len({e.date[:7] for e in doc.entries}) >= 6  # spans several distinct months
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/backend && uv run pytest tests/test_demo_data.py -v -k costs`
Expected: FAIL — `ImportError: cannot import name 'generate_demo_costs'`

- [ ] **Step 3: Implement**

Append to `packages/backend/src/myhome/demo_data.py` (add imports and function):

```python
from .models_costs import CostEntry, CostsDocument
```

```python
def _months_ago(base: date, n: int) -> date:
    month_index = base.month - 1 - n
    year = base.year + month_index // 12
    month = month_index % 12 + 1
    day = min(base.day, 28)
    return date(year, month, day)


def generate_demo_costs(settings: SettingsDocument, rng: random.Random) -> CostsDocument:
    today = date.today()
    entries: list[CostEntry] = []
    supplier_ids = [s.id for s in settings.suppliers]

    for i in range(12):
        entries.append(CostEntry(
            id=str(uuid.uuid4()), categoryId="cat-mortgage",
            date=_months_ago(today, i).isoformat(),
            totalAmount=round(rng.uniform(1200, 1800), 2), notes="Monthly mortgage payment",
        ))
    for i in range(12):
        entries.append(CostEntry(
            id=str(uuid.uuid4()), categoryId="cat-electricity",
            date=_months_ago(today, i).isoformat(),
            totalAmount=round(rng.uniform(60, 180), 2), notes="Electricity bill",
        ))
    for i in range(4):
        entries.append(CostEntry(
            id=str(uuid.uuid4()), categoryId="cat-water",
            date=_months_ago(today, i * 3).isoformat(),
            totalAmount=round(rng.uniform(80, 150), 2), notes="Quarterly water bill",
        ))
    entries.append(CostEntry(
        id=str(uuid.uuid4()), categoryId="cat-insurance",
        date=(today - timedelta(days=rng.randint(30, 300))).isoformat(),
        totalAmount=round(rng.uniform(800, 1500), 2), notes="Annual home insurance premium",
    ))
    for note in ["Furnace repair", "Gutter cleaning", "Pest control treatment"]:
        entries.append(CostEntry(
            id=str(uuid.uuid4()), categoryId="cat-maintenance",
            date=(today - timedelta(days=rng.randint(1, 365))).isoformat(),
            totalAmount=round(rng.uniform(100, 600), 2), notes=note,
            supplierId=rng.choice(supplier_ids),
        ))
    for note in ["Streaming subscription bundle", "Home theater setup"]:
        entries.append(CostEntry(
            id=str(uuid.uuid4()), categoryId="cat-entertainment",
            date=(today - timedelta(days=rng.randint(1, 365))).isoformat(),
            totalAmount=round(rng.uniform(20, 150), 2), notes=note,
        ))
    entries.append(CostEntry(
        id=str(uuid.uuid4()), categoryId="cat-groceries",
        date=(today - timedelta(days=rng.randint(1, 365))).isoformat(),
        totalAmount=round(rng.uniform(300, 600), 2), notes="Monthly grocery restock",
    ))

    return CostsDocument(entries=entries)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd packages/backend && uv run pytest tests/test_demo_data.py -v`
Expected: PASS (all tests so far — 35 entries: 12+12+4+1+3+2+1)

- [ ] **Step 5: Commit**

```bash
git add packages/backend/src/myhome/demo_data.py packages/backend/tests/test_demo_data.py
git commit -m "feat: add demo costs generator"
```

---

## Task 8: Works generator

**Files:**
- Modify: `packages/backend/src/myhome/demo_data.py`
- Test: `packages/backend/tests/test_demo_data.py`

- [ ] **Step 1: Write the failing test**

Append to `packages/backend/tests/test_demo_data.py`:

```python
from myhome.demo_data import generate_demo_works


def test_generate_demo_works_has_at_least_32_entries():
    house = generate_demo_house()
    settings = generate_demo_settings()
    doc = generate_demo_works(house, settings, random.Random(42))
    assert len(doc.works) >= 32


def test_generate_demo_works_has_a_mix_of_statuses():
    house = generate_demo_house()
    settings = generate_demo_settings()
    doc = generate_demo_works(house, settings, random.Random(42))
    statuses = {w.status for w in doc.works}
    assert statuses == {"planned", "in_progress", "done"}
    done = [w for w in doc.works if w.status == "done"]
    assert all(w.totalCost is not None for w in done)
    planned = [w for w in doc.works if w.status == "planned"]
    assert all(w.totalCost is None for w in planned)


def test_generate_demo_works_reference_valid_categories_and_floors():
    house = generate_demo_house()
    settings = generate_demo_settings()
    doc = generate_demo_works(house, settings, random.Random(42))
    category_ids = {c.id for c in settings.workCategories}
    floor_ids = {f.id for f in house.floors}
    for w in doc.works:
        assert w.categoryId in category_ids
        assert w.placement is not None
        assert w.placement.floorId in floor_ids
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/backend && uv run pytest tests/test_demo_data.py -v -k works`
Expected: FAIL — `ImportError: cannot import name 'generate_demo_works'`

- [ ] **Step 3: Implement**

Append to `packages/backend/src/myhome/demo_data.py` (add imports and function):

```python
from .demo_content import WORKS
from .models_works import Work, WorksDocument, WorkPlacement, WorkPosition
```

```python
def generate_demo_works(house: HouseDocument, settings: SettingsDocument, rng: random.Random) -> WorksDocument:
    today = date.today()
    supplier_ids = [s.id for s in settings.suppliers]
    all_rooms = [(f.id, r) for f in house.floors for r in f.rooms]

    shuffled = WORKS[:]
    rng.shuffle(shuffled)
    done_count = round(len(shuffled) * 0.5)
    in_progress_count = round(len(shuffled) * 0.15)

    works: list[Work] = []
    for i, (title, category_id, (cost_min, cost_max)) in enumerate(shuffled):
        floor_id, room = rng.choice(all_rooms)
        cx, cy = room_centroid(room)
        placement = WorkPlacement(
            floorId=floor_id,
            position=WorkPosition(x=cx + rng.uniform(-0.8, 0.8), y=cy + rng.uniform(-0.8, 0.8)),
        )

        if i < done_count:
            status = "done"
            work_date = today - timedelta(days=rng.randint(10, 700))
            total_cost = round(rng.uniform(cost_min, cost_max), 2)
            supplier_id = rng.choice(supplier_ids)
        elif i < done_count + in_progress_count:
            status = "in_progress"
            work_date = today - timedelta(days=rng.randint(0, 30))
            total_cost = round(rng.uniform(cost_min, cost_max) * 0.5, 2)
            supplier_id = rng.choice(supplier_ids)
        else:
            status = "planned"
            work_date = today + timedelta(days=rng.randint(5, 180))
            total_cost = None
            supplier_id = None

        works.append(Work(
            id=str(uuid.uuid4()), title=title, status=status, categoryId=category_id,
            date=work_date.isoformat(), totalCost=total_cost, supplierId=supplier_id,
            placement=placement,
        ))

    return WorksDocument(works=works)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd packages/backend && uv run pytest tests/test_demo_data.py -v`
Expected: PASS (all tests so far)

- [ ] **Step 5: Commit**

```bash
git add packages/backend/src/myhome/demo_data.py packages/backend/tests/test_demo_data.py
git commit -m "feat: add demo works generator"
```

---

## Task 9: Knowledge Base generator

**Files:**
- Modify: `packages/backend/src/myhome/demo_data.py`
- Test: `packages/backend/tests/test_demo_data.py`

- [ ] **Step 1: Write the failing test**

Append to `packages/backend/tests/test_demo_data.py`:

```python
from myhome.demo_data import generate_demo_kb


def test_generate_demo_kb_has_at_least_32_entries():
    doc = generate_demo_kb(random.Random(42))
    assert len(doc.entries) >= 32


def test_generate_demo_kb_entries_have_content_and_valid_dates():
    doc = generate_demo_kb(random.Random(42))
    for entry in doc.entries:
        assert entry.title
        assert entry.content
        assert entry.updatedAt >= entry.createdAt
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/backend && uv run pytest tests/test_demo_data.py -v -k kb`
Expected: FAIL — `ImportError: cannot import name 'generate_demo_kb'`

- [ ] **Step 3: Implement**

Append to `packages/backend/src/myhome/demo_data.py` (add imports and function):

```python
from .demo_content import KB_CLOSERS, KB_OPENERS, KB_TITLES
from .models_kb import KBDocument, KBEntry
```

```python
def generate_demo_kb(rng: random.Random) -> KBDocument:
    now = datetime.now(timezone.utc)
    entries: list[KBEntry] = []

    for title in KB_TITLES:
        created = now - timedelta(days=rng.randint(10, 400))
        updated = created + timedelta(days=rng.randint(0, max(1, (now - created).days)))
        content = f"## {title}\n\n{rng.choice(KB_OPENERS)}\n\n{rng.choice(KB_CLOSERS)}"
        entries.append(KBEntry(
            id=str(uuid.uuid4()), title=title, content=content,
            createdAt=created.isoformat(), updatedAt=updated.isoformat(),
        ))

    return KBDocument(entries=entries)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd packages/backend && uv run pytest tests/test_demo_data.py -v`
Expected: PASS (all tests so far)

- [ ] **Step 5: Commit**

```bash
git add packages/backend/src/myhome/demo_data.py packages/backend/tests/test_demo_data.py
git commit -m "feat: add demo knowledge base generator"
```

---

## Task 10: Consumables generator

**Files:**
- Modify: `packages/backend/src/myhome/demo_data.py`
- Test: `packages/backend/tests/test_demo_data.py`

- [ ] **Step 1: Write the failing test**

Append to `packages/backend/tests/test_demo_data.py`:

```python
from myhome.demo_data import generate_demo_consumables


def test_generate_demo_consumables_has_at_least_32_items():
    house = generate_demo_house()
    settings = generate_demo_settings()
    doc = generate_demo_consumables(house, settings, random.Random(42))
    assert len(doc.consumables) >= 32


def test_generate_demo_consumables_some_are_below_min_quantity():
    house = generate_demo_house()
    settings = generate_demo_settings()
    doc = generate_demo_consumables(house, settings, random.Random(42))
    below = [c for c in doc.consumables if c.quantity < c.minQuantity]
    assert len(below) > 0
    assert len(below) < len(doc.consumables)


def test_generate_demo_consumables_transactions_end_at_final_quantity():
    house = generate_demo_house()
    settings = generate_demo_settings()
    doc = generate_demo_consumables(house, settings, random.Random(42))
    assert len(doc.transactions) == 2 * len(doc.consumables)
    for consumable in doc.consumables:
        txns = sorted(
            (t for t in doc.transactions if t.consumableId == consumable.id),
            key=lambda t: t.timestamp,
        )
        assert txns[-1].quantityAfter == consumable.quantity


def test_generate_demo_consumables_reference_valid_categories():
    house = generate_demo_house()
    settings = generate_demo_settings()
    doc = generate_demo_consumables(house, settings, random.Random(42))
    category_ids = {c.id for c in settings.consumableCategories}
    for c in doc.consumables:
        assert c.categoryId in category_ids
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/backend && uv run pytest tests/test_demo_data.py -v -k consumables`
Expected: FAIL — `ImportError: cannot import name 'generate_demo_consumables'`

- [ ] **Step 3: Implement**

Append to `packages/backend/src/myhome/demo_data.py` (add imports and function):

```python
from .demo_content import CONSUMABLE_CATEGORY_ROOM_HINTS, CONSUMABLES
from .models_consumables import (
    Consumable,
    ConsumableDocument,
    ConsumablePlacement,
    ConsumablePosition,
    ConsumableTransaction,
)

_CONSUMABLE_UNIT_BASELINE = {"L": 2.0, "kg": 2.0, "count": 8.0, "rolls": 6.0, "packs": 5.0}


def _consumable_quantities(unit: str, rng: random.Random) -> tuple[float, float]:
    baseline = _CONSUMABLE_UNIT_BASELINE.get(unit, 8.0)
    min_quantity = round(baseline * rng.uniform(0.2, 0.4), 1)
    quantity = round(min_quantity * rng.uniform(0.3, 3.0), 1)
    return quantity, min_quantity


def _build_consumable_transactions(consumable_id: str, final_quantity: float, rng: random.Random, now: datetime) -> list[ConsumableTransaction]:
    extra = round(rng.uniform(2, 8), 1)
    restocked_qty = round(final_quantity + extra, 1)
    restock_ts = now - timedelta(days=rng.randint(20, 60))
    use_ts = now - timedelta(days=rng.randint(1, 19))
    return [
        ConsumableTransaction(
            id=str(uuid.uuid4()), consumableId=consumable_id,
            delta=restocked_qty, quantityAfter=restocked_qty,
            note="Restocked", timestamp=restock_ts.isoformat(),
        ),
        ConsumableTransaction(
            id=str(uuid.uuid4()), consumableId=consumable_id,
            delta=round(final_quantity - restocked_qty, 1), quantityAfter=final_quantity,
            note="Used", timestamp=use_ts.isoformat(),
        ),
    ]


def generate_demo_consumables(house: HouseDocument, settings: SettingsDocument, rng: random.Random) -> ConsumableDocument:
    now = datetime.now(timezone.utc)
    consumables: list[Consumable] = []
    transactions: list[ConsumableTransaction] = []

    for name, emoji, category_id, unit in CONSUMABLES:
        hints = CONSUMABLE_CATEGORY_ROOM_HINTS.get(category_id, [])
        room_label = rng.choice(hints) if hints else house.floors[0].rooms[0].label
        room = _find_room(house, room_label)
        floor_id = _floor_id_for_room(house, room.id)
        quantity, min_quantity = _consumable_quantities(unit, rng)
        cx, cy = room_centroid(room)

        consumable = Consumable(
            id=str(uuid.uuid4()), name=name, emoji=emoji, unit=unit,
            quantity=quantity, minQuantity=min_quantity, categoryId=category_id,
            placement=ConsumablePlacement(
                floorId=floor_id, roomId=room.id,
                position=ConsumablePosition(x=cx + rng.uniform(-0.8, 0.8), y=cy + rng.uniform(-0.8, 0.8)),
            ),
        )
        consumables.append(consumable)
        transactions.extend(_build_consumable_transactions(consumable.id, quantity, rng, now))

    return ConsumableDocument(consumables=consumables, transactions=transactions)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd packages/backend && uv run pytest tests/test_demo_data.py -v`
Expected: PASS (all tests so far)

- [ ] **Step 5: Commit**

```bash
git add packages/backend/src/myhome/demo_data.py packages/backend/tests/test_demo_data.py
git commit -m "feat: add demo consumables generator"
```

---

## Task 11: Attachment wiring

**Files:**
- Modify: `packages/backend/src/myhome/demo_data.py`
- Test: `packages/backend/tests/test_demo_data.py`

- [ ] **Step 1: Write the failing test**

Append to `packages/backend/tests/test_demo_data.py`:

```python
import os

from myhome.demo_data import attach_demo_files


def test_attach_demo_files_gives_a_subset_of_records_attachments(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    home_id = "test-home"
    (tmp_path / "homes" / home_id).mkdir(parents=True)

    house = generate_demo_house()
    settings = generate_demo_settings()
    rng = random.Random(42)
    chores_doc = generate_demo_chores(house, rng)
    inventory_doc = generate_demo_inventory(house, settings, rng)
    costs_doc = generate_demo_costs(settings, rng)
    works_doc = generate_demo_works(house, settings, rng)

    attach_demo_files(home_id, chores_doc, inventory_doc, costs_doc, works_doc, random.Random(1))

    chores_with_attachments = [c for c in chores_doc.chores if c.attachments]
    inventory_with_attachments = [i for i in inventory_doc.items if i.attachments]
    costs_with_attachments = [c for c in costs_doc.entries if c.attachments]
    done_works = [w for w in works_doc.works if w.status == "done"]
    works_with_attachments = [w for w in done_works if w.attachments]

    assert 0 < len(chores_with_attachments) < len(chores_doc.chores)
    assert 0 < len(inventory_with_attachments) < len(inventory_doc.items)
    assert 0 < len(costs_with_attachments) < len(costs_doc.entries)
    assert 0 < len(works_with_attachments) <= len(done_works)

    for chore in chores_with_attachments:
        path = tmp_path / "homes" / home_id / "chores-attachments" / chore.id / chore.attachments[0]
        assert path.exists()
    for item in inventory_with_attachments:
        path = tmp_path / "homes" / home_id / "inventory-attachments" / item.id / item.attachments[0]
        assert path.exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/backend && uv run pytest tests/test_demo_data.py -v -k attach`
Expected: FAIL — `ImportError: cannot import name 'attach_demo_files'`

- [ ] **Step 3: Implement**

Append to `packages/backend/src/myhome/demo_data.py` (add imports and function):

```python
from pathlib import Path

from . import persistence_chores, persistence_costs, persistence_inventory, persistence_works

# ChoreDocument, InventoryDocument, CostsDocument, WorksDocument are already
# imported (unaliased) by the generator functions added in earlier tasks.

_ASSETS_DIR = Path(__file__).parent / "demo_assets"


def _attach_placeholder(*, save_attachment, get_attachment_path, generate_pdf_thumbnail, home_id: str, record_id: str, src: Path, dest_name: str) -> None:
    data = src.read_bytes()
    save_attachment(home_id, record_id, dest_name, data)
    if dest_name.endswith(".pdf"):
        pdf_path = get_attachment_path(home_id, record_id, dest_name)
        thumb_path = pdf_path.with_name(pdf_path.name + ".thumb.jpg")
        generate_pdf_thumbnail(pdf_path, thumb_path)


def attach_demo_files(
    home_id: str,
    chores_doc: ChoreDocument,
    inventory_doc: InventoryDocument,
    costs_doc: CostsDocument,
    works_doc: WorksDocument,
    rng: random.Random,
) -> None:
    photo_files = [_ASSETS_DIR / "placeholder-photo-1.png", _ASSETS_DIR / "placeholder-photo-2.png"]

    chore_subset = rng.sample(chores_doc.chores, k=max(1, round(len(chores_doc.chores) * 0.3)))
    for chore in chore_subset:
        photo = rng.choice(photo_files)
        _attach_placeholder(
            save_attachment=persistence_chores.save_attachment,
            get_attachment_path=persistence_chores.get_attachment_path,
            generate_pdf_thumbnail=persistence_chores.generate_pdf_thumbnail,
            home_id=home_id, record_id=chore.id, src=photo, dest_name=photo.name,
        )
        chore.attachments.append(photo.name)

    inventory_subset = rng.sample(inventory_doc.items, k=max(1, round(len(inventory_doc.items) * 0.3)))
    manual = _ASSETS_DIR / "placeholder-manual.pdf"
    for item in inventory_subset:
        _attach_placeholder(
            save_attachment=persistence_inventory.save_attachment,
            get_attachment_path=persistence_inventory.get_attachment_path,
            generate_pdf_thumbnail=persistence_inventory.generate_pdf_thumbnail,
            home_id=home_id, record_id=item.id, src=manual, dest_name=manual.name,
        )
        item.attachments.append(manual.name)

    costs_subset = rng.sample(costs_doc.entries, k=max(1, round(len(costs_doc.entries) * 0.3)))
    receipt = _ASSETS_DIR / "placeholder-receipt.pdf"
    for entry in costs_subset:
        _attach_placeholder(
            save_attachment=persistence_costs.save_attachment,
            get_attachment_path=persistence_costs.get_attachment_path,
            generate_pdf_thumbnail=persistence_costs.generate_pdf_thumbnail,
            home_id=home_id, record_id=entry.id, src=receipt, dest_name=receipt.name,
        )
        entry.attachments.append(receipt.name)

    done_works = [w for w in works_doc.works if w.status == "done"]
    works_subset = rng.sample(done_works, k=max(1, round(len(done_works) * 0.3))) if done_works else []
    warranty = _ASSETS_DIR / "placeholder-warranty.pdf"
    for work in works_subset:
        _attach_placeholder(
            save_attachment=persistence_works.save_attachment,
            get_attachment_path=persistence_works.get_attachment_path,
            generate_pdf_thumbnail=persistence_works.generate_pdf_thumbnail,
            home_id=home_id, record_id=work.id, src=warranty, dest_name=warranty.name,
        )
        work.attachments.append(warranty.name)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd packages/backend && uv run pytest tests/test_demo_data.py -v`
Expected: PASS (all tests so far)

- [ ] **Step 5: Commit**

```bash
git add packages/backend/src/myhome/demo_data.py packages/backend/tests/test_demo_data.py
git commit -m "feat: attach placeholder files to a subset of demo records"
```

---

## Task 12: Orchestrator `seed_demo_home`

**Files:**
- Modify: `packages/backend/src/myhome/demo_data.py`
- Test: `packages/backend/tests/test_demo_data.py`

- [ ] **Step 1: Write the failing test**

Append to `packages/backend/tests/test_demo_data.py`:

```python
from myhome.demo_data import seed_demo_home
from myhome import persistence, persistence_consumables, persistence_kb, persistence_settings


def test_seed_demo_home_writes_every_module(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    home_id = "seed-test-home"
    (tmp_path / "homes" / home_id).mkdir(parents=True)

    seed_demo_home(home_id)

    house = persistence.load_house(home_id)
    assert house is not None
    assert len(house.floors) == 2

    settings = persistence_settings.load_settings(home_id)
    assert len(settings.costCategories) == 9

    chores = persistence_chores.load_chores(home_id)
    assert len(chores.chores) >= 32

    inventory = persistence_inventory.load_inventory(home_id)
    assert len(inventory.items) >= 32

    costs = persistence_costs.load_costs(home_id)
    assert len(costs.entries) >= 32

    works = persistence_works.load_works(home_id)
    assert len(works.works) >= 32

    kb_entries = persistence_kb.load_all(home_id)
    assert len(kb_entries) >= 32

    consumables = persistence_consumables.load_consumables(home_id)
    assert len(consumables.consumables) >= 32
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/backend && uv run pytest tests/test_demo_data.py -v -k seed_demo_home`
Expected: FAIL — `ImportError: cannot import name 'seed_demo_home'`

- [ ] **Step 3: Implement**

Append to `packages/backend/src/myhome/demo_data.py` (add imports and function):

```python
from . import persistence, persistence_consumables, persistence_kb, persistence_settings
from .demo_content import generate_demo_settings
from .demo_geometry import generate_demo_house


def seed_demo_home(home_id: str) -> None:
    rng = random.Random()

    house = generate_demo_house()
    settings = generate_demo_settings()
    chores_doc = generate_demo_chores(house, rng)
    inventory_doc = generate_demo_inventory(house, settings, rng)
    costs_doc = generate_demo_costs(settings, rng)
    works_doc = generate_demo_works(house, settings, rng)
    kb_doc = generate_demo_kb(rng)
    consumables_doc = generate_demo_consumables(house, settings, rng)

    persistence_settings.save_settings(home_id, settings)
    persistence.save_house(home_id, house)
    persistence_chores.save_chores(home_id, chores_doc)
    persistence_inventory.save_inventory(home_id, inventory_doc)
    persistence_costs.save_costs(home_id, costs_doc)
    persistence_works.save_works(home_id, works_doc)
    for entry in kb_doc.entries:
        persistence_kb.save_entry(home_id, entry)
    persistence_consumables.save_consumables(home_id, consumables_doc)

    attach_demo_files(home_id, chores_doc, inventory_doc, costs_doc, works_doc, rng)
    persistence_chores.save_chores(home_id, chores_doc)
    persistence_inventory.save_inventory(home_id, inventory_doc)
    persistence_costs.save_costs(home_id, costs_doc)
    persistence_works.save_works(home_id, works_doc)
```

Note: attachments must be saved *after* the initial document writes (so `save_attachment` can write into `{module}-attachments/{record_id}/`), and the documents re-saved afterward so the `attachments: [...]` list mutations made in `attach_demo_files` persist to `{module}.json`.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd packages/backend && uv run pytest tests/test_demo_data.py -v`
Expected: PASS (all tests in the file)

- [ ] **Step 5: Commit**

```bash
git add packages/backend/src/myhome/demo_data.py packages/backend/tests/test_demo_data.py
git commit -m "feat: add seed_demo_home orchestrator"
```

---

## Task 13: Wire seeding into home creation, with cleanup on failure

**Files:**
- Modify: `packages/backend/src/myhome/persistence_homes.py`
- Test: `packages/backend/tests/test_homes.py`

- [ ] **Step 1: Write the failing test**

Append to `packages/backend/tests/test_homes.py`:

```python
def test_create_home_demo_seeds_every_module(client):
    resp = client.post("/api/homes", json={"name": "Demo House", "type": "demo"})
    assert resp.status_code == 201
    home_id = resp.json()["id"]

    for path, key in [
        ("/chores", "chores"), ("/inventory", "items"), ("/costs", "entries"),
        ("/works", "works"), ("/kb", None), ("/consumables", "consumables"),
    ]:
        r = client.get(f"/api/homes/{home_id}{path}")
        assert r.status_code == 200
        body = r.json()
        items = body if key is None else body[key]
        assert len(items) >= 32, f"{path} returned only {len(items)} records"

    house_resp = client.get(f"/api/homes/{home_id}/house")
    assert house_resp.status_code == 200
    assert len(house_resp.json()["floors"]) == 2


def test_create_home_demo_cleans_up_on_seeding_failure(client, monkeypatch):
    import myhome.persistence_homes as ph

    def boom(home_id: str) -> None:
        raise RuntimeError("seeding exploded")

    monkeypatch.setattr(ph, "seed_demo_home", boom)

    before = client.get("/api/homes").json()
    with pytest.raises(RuntimeError):
        client.post("/api/homes", json={"name": "Broken Demo", "type": "demo"})
    after = client.get("/api/homes").json()
    assert len(after) == len(before)
```

Add `import pytest` at the top of `packages/backend/tests/test_homes.py` if not already present.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/backend && uv run pytest tests/test_homes.py -v -k demo`
Expected: FAIL — `test_create_home_demo_seeds_every_module` fails with 404s (routes exist but nothing was seeded yet, since `create_home` doesn't call `seed_demo_home`); `test_create_home_demo_cleans_up_on_seeding_failure` fails with `AttributeError` (no `seed_demo_home` name in `persistence_homes` to monkeypatch).

- [ ] **Step 3: Implement**

In `packages/backend/src/myhome/persistence_homes.py`, add the import and update `create_home` (replace the function body from Task 1):

```python
from .demo_data import seed_demo_home
```

```python
def create_home(name: str, home_type: str) -> Home:
    if home_type == "existing":
        modules = DEFAULT_EXISTING_MODULES[:]
    elif home_type == "demo":
        modules = DEFAULT_DEMO_MODULES[:]
    else:
        modules = DEFAULT_PROJECT_MODULES[:]
    home = Home(
        id=secrets.token_hex(8),
        name=name,
        type=home_type,
        enabledModules=modules,
        createdAt=datetime.now(timezone.utc).isoformat(),
    )
    _home_dir(home.id).mkdir(parents=True, exist_ok=True)
    doc = load_homes()
    doc.homes.append(home)
    save_homes(doc)

    if home_type == "demo":
        try:
            seed_demo_home(home.id)
        except Exception:
            doc.homes = [h for h in doc.homes if h.id != home.id]
            save_homes(doc)
            home_dir = _home_dir(home.id)
            if home_dir.exists():
                shutil.rmtree(home_dir)
            raise

    return home
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd packages/backend && uv run pytest tests/test_homes.py -v`
Expected: PASS (all tests in the file)

- [ ] **Step 5: Run the full backend test suite**

Run: `cd packages/backend && uv run pytest -v`
Expected: PASS — no regressions in any other module (this confirms `demo_data` imports don't create a circular-import problem; `persistence_homes` now imports `demo_data`, which imports `persistence_chores`/`persistence_inventory`/etc. — none of those import `persistence_homes`, so there's no cycle).

- [ ] **Step 6: Commit**

```bash
git add packages/backend/src/myhome/persistence_homes.py packages/backend/tests/test_homes.py
git commit -m "feat: seed demo home data on creation, with rollback on failure"
```

---

## Task 14: MCP tool parity

**Files:**
- Modify: `packages/backend/src/myhome/mcp_tools_homes.py`
- Test: `packages/backend/tests/test_mcp_tools_homes.py`

- [ ] **Step 1: Write the failing test**

Append to `packages/backend/tests/test_mcp_tools_homes.py`:

```python
def test_create_demo_home():
    from myhome.mcp_tools_homes import _create_demo_home_impl, _list_homes_impl
    home = _create_demo_home_impl("My Demo")
    assert home["name"] == "My Demo"
    assert home["type"] == "demo"
    assert _list_homes_impl()[0]["id"] == home["id"]


def test_create_demo_home_defaults_name():
    from myhome.mcp_tools_homes import _create_demo_home_impl
    home = _create_demo_home_impl()
    assert home["name"] == "Demo Home"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/backend && uv run pytest tests/test_mcp_tools_homes.py -v -k demo`
Expected: FAIL — `ImportError: cannot import name '_create_demo_home_impl'`

- [ ] **Step 3: Implement**

In `packages/backend/src/myhome/mcp_tools_homes.py`, add after `_create_home_impl` (after line 21):

```python
def _create_demo_home_impl(name: str = "Demo Home") -> dict:
    return ph_create_home(name, "demo").model_dump()
```

Add the tool after the existing `create_home` tool (after line 55):

```python
@mcp.tool()
async def create_demo_home(ctx: Context, name: str = "Demo Home") -> dict:
    """Create a new home pre-filled with realistic sample data (30+ records)
    across every module: chores, inventory, costs, works, KB, consumables,
    plus a generated floor plan. Useful for exploring the app."""
    await _require_role(ctx.request_context.request, "normal")
    return _create_demo_home_impl(name)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd packages/backend && uv run pytest tests/test_mcp_tools_homes.py -v`
Expected: PASS (all tests in the file)

- [ ] **Step 5: Commit**

```bash
git add packages/backend/src/myhome/mcp_tools_homes.py packages/backend/tests/test_mcp_tools_homes.py
git commit -m "feat: add create_demo_home MCP tool"
```

---

## Task 15: Frontend — `homesStore` type union

**Files:**
- Modify: `packages/editor/src/lib/homesStore.svelte.ts`
- Test: `packages/editor/test/homesStore.test.ts`

- [ ] **Step 1: Write the failing test**

Append to `packages/editor/test/homesStore.test.ts`:

```typescript
describe("homesStore — createHome demo type", () => {
  it("accepts type 'demo' and switches to the new home", async () => {
    const newHome = { id: "h-demo", name: "Demo House", type: "demo", enabledModules: ["home", "plan", "chores"], createdAt: "" };
    vi.stubGlobal("fetch", makeFetch(201, newHome));
    await homesStore.createHome("Demo House", "demo");
    expect(homesStore.homes[0].type).toBe("demo");
    expect(homesStore.activeHomeId).toBe("h-demo");
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/editor && npx vitest run test/homesStore.test.ts`
Expected: FAIL — TypeScript error, `"demo"` is not assignable to `"existing" | "project"`.

- [ ] **Step 3: Implement**

In `packages/editor/src/lib/homesStore.svelte.ts`, replace line 3 and the `createHome`/`patchHome` signatures:

```typescript
export interface Home {
  id: string;
  name: string;
  type: "existing" | "project" | "demo";
  enabledModules: string[];
  createdAt: string;
}
```

```typescript
async function createHome(name: string, type: "existing" | "project" | "demo"): Promise<Home> {
```

```typescript
async function patchHome(
  id: string,
  patch: { name?: string; type?: "existing" | "project" | "demo"; enabledModules?: string[] },
): Promise<void> {
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd packages/editor && npx vitest run test/homesStore.test.ts`
Expected: PASS (all tests in the file)

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/lib/homesStore.svelte.ts packages/editor/test/homesStore.test.ts
git commit -m "feat: extend homesStore Home type with demo"
```

---

## Task 16: Frontend — third radio option in `NewHomeModal`

**Files:**
- Modify: `packages/editor/src/lib/components/NewHomeModal.svelte`
- Test: `packages/editor/test/NewHomeModal.test.ts`

- [ ] **Step 1: Write the failing test**

Create `packages/editor/test/NewHomeModal.test.ts`:

```typescript
import { describe, it, expect, vi, afterEach } from "vitest";
import { mount, unmount, flushSync, tick } from "svelte";
import NewHomeModal from "../src/lib/components/NewHomeModal.svelte";
import { homesStore } from "../src/lib/homesStore.svelte";

afterEach(() => {
  vi.restoreAllMocks();
  homesStore._reset();
});

function mountModal() {
  const target = document.createElement("div");
  document.body.appendChild(target);
  const comp = mount(NewHomeModal, {
    target,
    props: { open: true, onclose: vi.fn() },
  });
  return { target, comp };
}

describe("NewHomeModal — demo option", () => {
  it("renders a demo radio option", async () => {
    const { target, comp } = mountModal();
    await tick();
    flushSync();
    const radios = target.querySelectorAll('input[type="radio"]');
    const values = Array.from(radios).map((r) => (r as HTMLInputElement).value);
    expect(values).toContain("demo");
    unmount(comp);
    target.remove();
  });

  it("submits with type 'demo' when the demo option is selected", async () => {
    const createHomeSpy = vi.spyOn(homesStore, "createHome").mockResolvedValue({
      id: "h1", name: "Demo House", type: "demo", enabledModules: [], createdAt: "",
    });
    const { target, comp } = mountModal();
    await tick();
    flushSync();

    const nameInput = target.querySelector('input[type="text"]') as HTMLInputElement;
    nameInput.value = "Demo House";
    nameInput.dispatchEvent(new Event("input", { bubbles: true }));

    const demoRadio = target.querySelector('input[type="radio"][value="demo"]') as HTMLInputElement;
    demoRadio.click();
    await tick();
    flushSync();

    const submitBtn = Array.from(target.querySelectorAll("button")).find((b) => b.textContent?.includes("Create home"))!;
    submitBtn.click();
    await tick();
    flushSync();

    expect(createHomeSpy).toHaveBeenCalledWith("Demo House", "demo");
    unmount(comp);
    target.remove();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/editor && npx vitest run test/NewHomeModal.test.ts`
Expected: FAIL — `values` doesn't contain `"demo"` (radio doesn't exist yet).

- [ ] **Step 3: Implement**

In `packages/editor/src/lib/components/NewHomeModal.svelte`, change line 16:

```typescript
let type = $state<"existing" | "project" | "demo">("existing");
```

And in `submit()`, line 26-27 (reset after success):

```typescript
      name = "";
      type = "existing";
```

(unchanged — resetting to `"existing"` after any successful create, including a demo one, is correct so the form defaults back to the common case).

Add a third `<label class="type-option">` inside the `<fieldset class="type-group">`, after the `project` option (after line 58, before the closing `</fieldset>`):

```svelte
      <label class="type-option" class:selected={type === "demo"}>
        <input type="radio" bind:group={type} value="demo" />
        <span class="type-icon">🧪</span>
        <span class="type-body">
          <strong>Demo home</strong>
          <small>Pre-filled with sample data across every module — great for exploring the app.</small>
        </span>
      </label>
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd packages/editor && npx vitest run test/NewHomeModal.test.ts`
Expected: PASS (both tests)

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/lib/components/NewHomeModal.svelte packages/editor/test/NewHomeModal.test.ts
git commit -m "feat: add demo home option to NewHomeModal"
```

---

## Task 17: Frontend — demo icon in `HomesSwitcher`

**Files:**
- Modify: `packages/editor/src/lib/components/HomesSwitcher.svelte`
- Test: `packages/editor/test/HomesSwitcher.test.ts`

- [ ] **Step 1: Write the failing test**

Create `packages/editor/test/HomesSwitcher.test.ts`:

```typescript
import { describe, it, expect, afterEach, vi } from "vitest";
import { mount, unmount, flushSync, tick } from "svelte";
import HomesSwitcher from "../src/lib/components/HomesSwitcher.svelte";
import { homesStore } from "../src/lib/homesStore.svelte";

afterEach(() => {
  vi.restoreAllMocks();
  homesStore._reset();
});

describe("HomesSwitcher — demo home icon", () => {
  it("shows a distinct icon for demo-type homes in the dropdown", async () => {
    homesStore.homes.push(
      { id: "h1", name: "Real House", type: "existing", enabledModules: [], createdAt: "" },
      { id: "h2", name: "Demo House", type: "demo", enabledModules: [], createdAt: "" },
    );
    homesStore.setActiveHomeId("h1");

    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(HomesSwitcher, { target, props: { expanded: true } });
    await tick();
    flushSync();

    const current = target.querySelector(".current") as HTMLButtonElement;
    current.click();
    await tick();
    flushSync();

    const items = Array.from(target.querySelectorAll(".home-item"));
    const demoItem = items.find((el) => el.textContent?.includes("Demo House"));
    const existingItem = items.find((el) => el.textContent?.includes("Real House"));
    expect(demoItem?.querySelector(".icon")?.textContent).toBe("🧪");
    expect(existingItem?.querySelector(".icon")?.textContent).toBe("🏠");

    unmount(comp);
    target.remove();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/editor && npx vitest run test/HomesSwitcher.test.ts`
Expected: FAIL — demo item's icon is `"🏠"` (the `typeIcon()` fallback), not `"🧪"`.

- [ ] **Step 3: Implement**

In `packages/editor/src/lib/components/HomesSwitcher.svelte`, replace `typeIcon()` (lines 34-36):

```typescript
  function typeIcon(type: string): string {
    if (type === "project") return "🏗";
    if (type === "demo") return "🧪";
    return "🏠";
  }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd packages/editor && npx vitest run test/HomesSwitcher.test.ts`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/lib/components/HomesSwitcher.svelte packages/editor/test/HomesSwitcher.test.ts
git commit -m "feat: show distinct icon for demo homes in switcher"
```

---

## Task 18: Full test suite verification

**Files:** none (verification only)

- [ ] **Step 1: Run the full backend suite**

Run: `cd packages/backend && uv run pytest -v`
Expected: PASS, 0 failures. Note the total test count for the summary.

- [ ] **Step 2: Run the full frontend suite**

Run: `cd packages/editor && npx vitest run`
Expected: PASS, 0 failures.

- [ ] **Step 3: Type-check the frontend**

Run: `cd packages/editor && npx svelte-check --tsconfig ./tsconfig.json`
Expected: 0 errors (warnings pre-existing in the codebase are acceptable, but nothing new introduced by this feature — specifically check there are no errors mentioning `homesStore.svelte.ts`, `NewHomeModal.svelte`, or `HomesSwitcher.svelte`).

- [ ] **Step 4: Manual smoke test**

Start the dev stack (`./dev.sh` or the project's usual run command), open the app in a browser, click "New home", select "Demo home", submit, and confirm:
- The home is created and becomes active.
- The floor plan editor shows two floors with rooms, walls, and doors (not blank).
- Chores, Inventory, Costs, Works, KB, and Consumables pages each show 30+ records.
- A few records show attachment thumbnails (chore photo, inventory manual PDF, cost receipt PDF, a done work's warranty PDF).
- The homes switcher shows the 🧪 icon next to the new demo home.

If any of these fail, treat it as a bug in a prior task and fix it there (don't patch around it here).

- [ ] **Step 5: Final commit (if smoke testing required fixes)**

```bash
git add -A
git commit -m "fix: address issues found in demo home smoke test"
```

Skip this step if step 4 required no changes.
