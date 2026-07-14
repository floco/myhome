# packages/backend/tests/test_persistence.py
from myhome.models import Floor, House, HouseDocument
from myhome.persistence import load_house, save_house

HOME_ID = "test-home"


def _setup(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    # house_documents FK-references homes.id (for cascade-delete-on-home-
    # delete), so a row must exist there before save_house().
    from myhome.db import get_engine
    from myhome.schema import homes as homes_table
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(homes_table.insert().values(
            id=HOME_ID, name="Test Home", type="existing", created_at="2026-01-01T00:00:00+00:00",
        ))


def make_doc() -> HouseDocument:
    return HouseDocument(
        version=1,
        house=House(name="Test", units="m", gridSnap=0.1),
        floors=[Floor(id="f1", name="Ground", order=0, walls=[], openings=[], rooms=[])],
    )


def test_load_returns_none_when_missing(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    assert load_house(HOME_ID) is None


def test_round_trip(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    save_house(HOME_ID, make_doc())
    loaded = load_house(HOME_ID)
    assert loaded is not None
    assert loaded.floors[0].id == "f1"
    assert loaded.house.name == "Test"
    assert loaded.version == 1


def test_save_overwrites_existing_document(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    save_house(HOME_ID, make_doc())
    updated = make_doc()
    updated.house.name = "Renamed"
    save_house(HOME_ID, updated)
    assert load_house(HOME_ID).house.name == "Renamed"
