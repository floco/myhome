from myhome.models_settings import (
    CostCategory,
    InventoryCategory,
    SettingsDocument,
)
from myhome.persistence_settings import load_settings, save_settings

HOME_ID = "test-home"


def _setup(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    (tmp_path / "homes" / HOME_ID).mkdir(parents=True)


def test_load_returns_defaults_when_file_missing(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    doc = load_settings(HOME_ID)
    assert len(doc.costCategories) == 5
    assert doc.costCategories[0].name == "Fuel / Mazout"
    assert len(doc.inventoryCategories) == 6


def test_load_does_not_create_file_when_missing(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    load_settings(HOME_ID)
    assert not (tmp_path / "homes" / HOME_ID / "settings.json").exists()


def test_save_creates_file(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    save_settings(HOME_ID, SettingsDocument(
        costCategories=[CostCategory(id="c1", name="Fuel", emoji="🛢", unit="L", color="#4466cc")],
        inventoryCategories=[],
    ))
    assert (tmp_path / "homes" / HOME_ID / "settings.json").exists()


def test_round_trip(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    doc = SettingsDocument(
        costCategories=[CostCategory(id="c1", name="Fuel", emoji="🛢", unit="L", color="#4466cc")],
        inventoryCategories=[InventoryCategory(id="i1", name="Electronics")],
    )
    save_settings(HOME_ID, doc)
    loaded = load_settings(HOME_ID)
    assert loaded.costCategories[0].id == "c1"
    assert loaded.costCategories[0].unit == "L"
    assert loaded.inventoryCategories[0].name == "Electronics"


def test_save_creates_data_dir_if_missing(tmp_path, monkeypatch):
    nested = tmp_path / "nested" / "data"
    monkeypatch.setenv("DATA_DIR", str(nested))
    save_settings(HOME_ID, SettingsDocument())
    assert (nested / "homes" / HOME_ID / "settings.json").exists()
