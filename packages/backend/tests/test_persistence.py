import json
import pytest
from myhome.models import HouseDocument, House, Floor
from myhome.persistence import load_house, save_house

HOME_ID = "test-home"


def _setup(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    (tmp_path / "homes" / HOME_ID).mkdir(parents=True)


def make_doc() -> HouseDocument:
    return HouseDocument(
        version=1,
        house=House(name="Test", units="m", gridSnap=0.1),
        floors=[Floor(id="f1", name="Ground", order=0, walls=[], openings=[], rooms=[])],
    )


def test_load_returns_none_when_missing(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    assert load_house(HOME_ID) is None


def test_save_creates_file(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    save_house(HOME_ID, make_doc())
    assert (tmp_path / "homes" / HOME_ID / "house.json").exists()


def test_round_trip(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    save_house(HOME_ID, make_doc())
    loaded = load_house(HOME_ID)
    assert loaded is not None
    assert loaded.floors[0].id == "f1"
    assert loaded.house.name == "Test"
    assert loaded.version == 1


def test_save_creates_data_dir_if_missing(tmp_path, monkeypatch):
    nested = tmp_path / "nested" / "data"
    monkeypatch.setenv("DATA_DIR", str(nested))
    save_house(HOME_ID, make_doc())
    assert (nested / "homes" / HOME_ID / "house.json").exists()
