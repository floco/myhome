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


@pytest.mark.parametrize("door_kind", ["hinged", None])
def test_hinged_door_renders_one_leaf_and_arc(door_kind):
    floor = empty_floor()
    floor.walls.append(make_wall("w1", 0, 0, 5, 0))
    floor.openings.append(
        Opening(id="o1", wallId="w1", type="door", offset=1.0, width=0.9, swing="left-in", doorKind=door_kind)
    )
    svg = render_floor_svg(floor)
    assert svg.count('class="door-leaf"') == 1
    assert svg.count('class="door-swing"') == 1


def test_swinging_door_renders_two_leaves_and_arcs_from_one_hinge():
    floor = empty_floor()
    floor.walls.append(make_wall("w1", 0, 0, 5, 0))
    floor.openings.append(
        Opening(id="o1", wallId="w1", type="door", offset=1.0, width=0.9, swing="left-in", doorKind="swinging")
    )
    svg = render_floor_svg(floor)
    assert svg.count('class="door-leaf"') == 2
    assert svg.count('class="door-swing"') == 2
    import re
    leaves = re.findall(r'<line class="door-leaf" x1="([^"]+)" y1="([^"]+)"', svg)
    assert leaves[0] == leaves[1]  # both leaves share the same hinge point


def test_sliding_door_renders_a_bar_with_no_arc():
    floor = empty_floor()
    floor.walls.append(make_wall("w1", 0, 0, 5, 0))
    floor.openings.append(
        Opening(id="o1", wallId="w1", type="door", offset=1.0, width=0.9, doorKind="sliding")
    )
    svg = render_floor_svg(floor)
    assert 'class="door-sliding"' in svg
    assert 'class="door-leaf"' not in svg
    assert 'class="door-swing"' not in svg


def test_garage_door_renders_five_ticks_with_no_arc():
    floor = empty_floor()
    floor.walls.append(make_wall("w1", 0, 0, 5, 0))
    floor.openings.append(
        Opening(id="o1", wallId="w1", type="door", offset=1.0, width=0.9, doorKind="garage")
    )
    svg = render_floor_svg(floor)
    assert svg.count('class="door-garage"') == 5
    assert 'class="door-swing"' not in svg


def test_double_door_renders_two_independent_leaves_and_arcs():
    floor = empty_floor()
    floor.walls.append(make_wall("w1", 0, 0, 5, 0))
    floor.openings.append(
        Opening(id="o1", wallId="w1", type="door", offset=1.0, width=1.6, doorKind="double")
    )
    svg = render_floor_svg(floor)
    assert svg.count('class="door-leaf"') == 2
    assert svg.count('class="door-swing"') == 2
    import re
    leaves = re.findall(r'<line class="door-leaf" x1="([\d.-]+)" y1="([\d.-]+)"', svg)
    hinge_xs = sorted(float(x) for x, _ in leaves)
    assert hinge_xs[0] == pytest.approx(1.0)
    assert hinge_xs[1] == pytest.approx(2.6)


def test_double_door_swings_out_when_swing_is_out():
    floor = empty_floor()
    floor.walls.append(make_wall("w1", 0, 0, 5, 0))
    floor.openings.append(
        Opening(id="o1", wallId="w1", type="door", offset=1.0, width=1.6, doorKind="double", swing="out")
    )
    svg = render_floor_svg(floor)
    import re
    leaves = re.findall(r'<line class="door-leaf" x1="[\d.-]+" y1="[\d.-]+" x2="[\d.-]+" y2="([\d.-]+)"', svg)
    # wall is horizontal along +x; "out" perpendicular is -y for this convention.
    for y2 in leaves:
        assert float(y2) < 0


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


def test_garden_border_renders_dashed_separately_from_divider():
    floor = empty_floor()
    floor.walls.append(
        Wall(id="gb1", start=Point(x=0, y=0), end=Point(x=5, y=0), type="garden")
    )
    svg = render_floor_svg(floor)
    assert '<g class="garden-borders">' in svg
    assert 'class="garden-border"' in svg
    assert 'class="divider"' not in svg
    assert 'class="wall"' not in svg


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
