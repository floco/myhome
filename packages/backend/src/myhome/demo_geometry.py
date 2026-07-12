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
