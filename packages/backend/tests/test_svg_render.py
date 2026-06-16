import pytest
from myhome.models import Floor, Wall, Opening, Room, Point
from myhome.svg_render import render_floor_svg, _choose_sweep_flag


def make_wall(id: str, x1: float, y1: float, x2: float, y2: float) -> Wall:
    return Wall(id=id, start=Point(x=x1, y=y1), end=Point(x=x2, y=y2), type="wall", thickness=0.1)


def empty_floor() -> Floor:
    return Floor(id="f1", name="Ground", order=0, walls=[], openings=[], rooms=[])


def test_empty_floor_returns_valid_svg():
    svg = render_floor_svg(empty_floor())
    assert svg.startswith('<svg xmlns="http://www.w3.org/2000/svg"')
    assert "</svg>" in svg


def test_wall_appears_in_svg():
    floor = empty_floor()
    floor.walls.append(make_wall("w1", 0, 0, 5, 0))
    svg = render_floor_svg(floor)
    assert 'class="wall"' in svg


def test_window_opening_renders_line():
    floor = empty_floor()
    floor.walls.append(make_wall("w1", 0, 0, 5, 0))
    floor.openings.append(
        Opening(id="o1", wallId="w1", type="window", offset=1.0, width=1.2)
    )
    svg = render_floor_svg(floor)
    assert 'class="window"' in svg


def test_door_opening_renders_leaf_and_arc():
    floor = empty_floor()
    floor.walls.append(make_wall("w1", 0, 0, 5, 0))
    floor.openings.append(
        Opening(id="o1", wallId="w1", type="door", offset=1.0, width=0.9, swing="left-in")
    )
    svg = render_floor_svg(floor)
    assert 'class="door-leaf"' in svg
    assert 'class="door-swing"' in svg


def test_room_polygon_renders():
    floor = empty_floor()
    room = Room(
        id="r1", label="Living", haAreaId=None, areaM2=20.0,
        polygon=[Point(x=0, y=0), Point(x=5, y=0), Point(x=5, y=4), Point(x=0, y=4)],
    )
    floor.rooms.append(room)
    svg = render_floor_svg(floor)
    assert 'class="room"' in svg
    assert 'id="room-r1"' in svg


def test_divider_renders_dashed():
    floor = empty_floor()
    floor.walls.append(
        Wall(id="d1", start=Point(x=0, y=0), end=Point(x=3, y=0), type="divider")
    )
    svg = render_floor_svg(floor)
    assert 'class="divider"' in svg
    assert "stroke-dasharray" in svg


def test_viewbox_respects_padding():
    floor = empty_floor()
    floor.walls.append(make_wall("w1", 0, 0, 10, 0))
    svg = render_floor_svg(floor, padding=1.0)
    assert "viewBox=" in svg
    # The viewBox x should be -1.0 (0 - 1.0 padding)
    import re
    m = re.search(r'viewBox="([^"]+)"', svg)
    assert m is not None
    parts = m.group(1).split()
    assert float(parts[0]) == pytest.approx(-1.0)


def test_choose_sweep_flag_returns_0_or_1():
    start = Point(x=1.0, y=0.0)
    end = Point(x=0.1, y=0.9)
    radius = 0.9
    center = Point(x=1.0, y=0.0)
    flag = _choose_sweep_flag(start, end, radius, center)
    assert flag in (0, 1)
