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
