from __future__ import annotations
import math
from .models import Floor, Wall, Opening, Room, Point


def render_floor_svg(floor: Floor, padding: float = 0.5) -> str:
    bounds = _compute_bounds(floor.walls, padding)

    rooms_svg = "\n".join(
        _render_room(r) for r in floor.rooms if r.polygon is not None
    )

    wall_walls = [w for w in floor.walls if w.type == "wall"]
    dividers = [w for w in floor.walls if w.type == "divider"]

    walls_svg = "\n".join(
        _render_wall(w, [o for o in floor.openings if o.wallId == w.id])
        for w in wall_walls
    )
    dividers_svg = "\n".join(_render_divider(w) for w in dividers)
    openings_svg = "\n".join(
        _render_opening(w, o)
        for w in wall_walls
        for o in floor.openings
        if o.wallId == w.id
    )

    vb = (
        f"{_fmt(bounds['minX'])} {_fmt(bounds['minY'])} "
        f"{_fmt(bounds['width'])} {_fmt(bounds['height'])}"
    )
    return "\n".join([
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{vb}">',
        '<g class="rooms">',
        rooms_svg,
        "</g>",
        '<g class="walls">',
        walls_svg,
        "</g>",
        '<g class="dividers">',
        dividers_svg,
        "</g>",
        '<g class="openings">',
        openings_svg,
        "</g>",
        "</svg>",
    ])


def _compute_bounds(walls: list[Wall], padding: float) -> dict[str, float]:
    min_x = min_y = math.inf
    max_x = max_y = -math.inf
    for w in walls:
        for p in [w.start, w.end]:
            min_x = min(min_x, p.x)
            min_y = min(min_y, p.y)
            max_x = max(max_x, p.x)
            max_y = max(max_y, p.y)
    if not math.isfinite(min_x):
        min_x = min_y = max_x = max_y = 0.0
    return {
        "minX": min_x - padding,
        "minY": min_y - padding,
        "width": max_x - min_x + padding * 2,
        "height": max_y - min_y + padding * 2,
    }


def _render_room(room: Room) -> str:
    assert room.polygon is not None
    d = _polygon_to_path(room.polygon)
    ha_area = _escape_attr(room.haAreaId or "")
    room_id = _escape_attr(room.id)
    return f'<path id="room-{room_id}" data-ha-area="{ha_area}" class="room" d="{d}" />'


def _render_divider(wall: Wall) -> str:
    d = _polyline_to_path([wall.start, wall.end])
    return f'<path class="divider" d="{d}" stroke-dasharray="0.1 0.1" />'


def _render_wall(wall: Wall, openings: list[Opening]) -> str:
    dir_x, dir_y, length = _wall_direction(wall)
    if length < 1e-9:
        return ""
    thickness = wall.thickness if wall.thickness is not None else 0.1
    perp_x = -dir_y * (thickness / 2)
    perp_y = dir_x * (thickness / 2)

    gaps = sorted(
        [
            {
                "from": _clamp(o.offset, 0.0, length),
                "to": _clamp(o.offset + o.width, 0.0, length),
            }
            for o in openings
        ],
        key=lambda g: g["from"],
    )

    segments: list[dict[str, float]] = []
    cursor = 0.0
    for gap in gaps:
        if gap["from"] > cursor:
            segments.append({"from": cursor, "to": gap["from"]})
        cursor = max(cursor, gap["to"])
    if cursor < length:
        segments.append({"from": cursor, "to": length})

    parts = []
    for seg in segments:
        p1 = _point_along(wall.start, dir_x, dir_y, seg["from"])
        p2 = _point_along(wall.start, dir_x, dir_y, seg["to"])
        corners = [
            Point(x=p1.x + perp_x, y=p1.y + perp_y),
            Point(x=p2.x + perp_x, y=p2.y + perp_y),
            Point(x=p2.x - perp_x, y=p2.y - perp_y),
            Point(x=p1.x - perp_x, y=p1.y - perp_y),
        ]
        parts.append(f'<path class="wall" d="{_polygon_to_path(corners)}" />')
    return "\n".join(parts)


def _render_opening(wall: Wall, opening: Opening) -> str:
    dir_x, dir_y, length = _wall_direction(wall)
    from_ = _clamp(opening.offset, 0.0, length)
    to = _clamp(opening.offset + opening.width, from_, length)
    render_width = to - from_
    p1 = _point_along(wall.start, dir_x, dir_y, from_)
    p2 = _point_along(wall.start, dir_x, dir_y, to)
    if opening.type == "window":
        return (
            f'<line class="window" '
            f'x1="{_fmt(p1.x)}" y1="{_fmt(p1.y)}" '
            f'x2="{_fmt(p2.x)}" y2="{_fmt(p2.y)}" />'
        )
    return _render_door(p1, p2, dir_x, dir_y, opening.swing or "left-in", render_width)


def _render_door(
    p1: Point, p2: Point, dir_x: float, dir_y: float, swing: str, width: float
) -> str:
    if width < 1e-9:
        return ""
    perp_left = Point(x=-dir_y, y=dir_x)
    perp_right = Point(x=dir_y, y=-dir_x)
    is_left_hinge = swing in ("left-in", "left-out")
    is_in_swing = swing in ("left-in", "right-in")
    hinge = p1 if is_left_hinge else p2
    other = p2 if is_left_hinge else p1
    perp = perp_left if is_in_swing else perp_right
    open_end = Point(x=hinge.x + perp.x * width, y=hinge.y + perp.y * width)
    leaf = (
        f'<line class="door-leaf" '
        f'x1="{_fmt(hinge.x)}" y1="{_fmt(hinge.y)}" '
        f'x2="{_fmt(open_end.x)}" y2="{_fmt(open_end.y)}" />'
    )
    sweep = _choose_sweep_flag(other, open_end, width, hinge)
    arc = (
        f'<path class="door-swing" '
        f'd="M {_fmt(other.x)} {_fmt(other.y)} '
        f'A {_fmt(width)} {_fmt(width)} 0 0 {sweep} '
        f'{_fmt(open_end.x)} {_fmt(open_end.y)}" />'
    )
    return f"{leaf}\n{arc}"


def _choose_sweep_flag(
    start: Point, end: Point, radius: float, desired_center: Point
) -> int:
    x1p = (start.x - end.x) / 2
    y1p = (start.y - end.y) / 2
    mid_x = (start.x + end.x) / 2
    mid_y = (start.y + end.y) / 2
    sum_sq = x1p * x1p + y1p * y1p
    term = max((radius * radius - sum_sq) / sum_sq if sum_sq > 1e-12 else 0.0, 0.0)
    factor = math.sqrt(term)
    center0 = Point(x=mid_x - factor * y1p, y=mid_y + factor * x1p)
    center1 = Point(x=mid_x + factor * y1p, y=mid_y - factor * x1p)
    d0 = math.hypot(center0.x - desired_center.x, center0.y - desired_center.y)
    d1 = math.hypot(center1.x - desired_center.x, center1.y - desired_center.y)
    return 0 if d0 <= d1 else 1


def _wall_direction(wall: Wall) -> tuple[float, float, float]:
    dx = wall.end.x - wall.start.x
    dy = wall.end.y - wall.start.y
    length = math.hypot(dx, dy)
    if length < 1e-9:
        return 0.0, 0.0, length
    return dx / length, dy / length, length


def _point_along(start: Point, dir_x: float, dir_y: float, distance: float) -> Point:
    return Point(x=start.x + dir_x * distance, y=start.y + dir_y * distance)


def _clamp(v: float, lo: float, hi: float) -> float:
    return min(max(v, lo), max(lo, hi))


def _polygon_to_path(points: list[Point]) -> str:
    parts = [f"M {_fmt(points[0].x)} {_fmt(points[0].y)}"]
    for p in points[1:]:
        parts.append(f"L {_fmt(p.x)} {_fmt(p.y)}")
    parts.append("Z")
    return " ".join(parts)


def _polyline_to_path(points: list[Point]) -> str:
    parts = [f"M {_fmt(points[0].x)} {_fmt(points[0].y)}"]
    for p in points[1:]:
        parts.append(f"L {_fmt(p.x)} {_fmt(p.y)}")
    return " ".join(parts)


def _fmt(n: float) -> str:
    return str(round(n * 1000) / 1000)


def _escape_attr(s: str) -> str:
    return s.replace("&", "&amp;").replace('"', "&quot;")
