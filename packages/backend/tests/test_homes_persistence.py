# packages/backend/tests/test_homes_persistence.py
from myhome.persistence_homes import (
    create_home,
    delete_home,
    load_homes,
    patch_home,
    save_homes,
)


def test_load_returns_empty_when_no_data(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    assert load_homes().homes == []


def test_create_home_adds_to_registry_and_creates_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    home = create_home("Rue des Lilas", "existing")
    assert home.name == "Rue des Lilas"
    assert home.type == "existing"
    assert "chores" in home.enabledModules
    assert (tmp_path / "homes" / home.id).is_dir()
    doc = load_homes()
    assert len(doc.homes) == 1
    assert doc.homes[0].id == home.id
    assert doc.homes[0].enabledModules == home.enabledModules


def test_create_project_home_has_limited_modules(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    home = create_home("Dream House", "project")
    assert "chores" not in home.enabledModules
    assert "works" in home.enabledModules
    assert "kb" in home.enabledModules
    assert "plan" in home.enabledModules


def test_patch_home_name(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    home = create_home("Old Name", "existing")
    updated = patch_home(home.id, name="New Name", home_type=None, enabled_modules=None)
    assert updated is not None
    assert updated.name == "New Name"
    assert load_homes().homes[0].name == "New Name"


def test_patch_home_enabled_modules(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    home = create_home("Test", "existing")
    updated = patch_home(home.id, name=None, home_type=None, enabled_modules=["home", "plan"])
    assert updated.enabledModules == ["home", "plan"]
    assert load_homes().homes[0].enabledModules == ["home", "plan"]


def test_patch_home_returns_none_for_unknown_id(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    assert patch_home("nonexistent", name="X", home_type=None, enabled_modules=None) is None


def test_delete_home_removes_from_registry_and_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    home = create_home("Test", "existing")
    home_dir = tmp_path / "homes" / home.id
    assert home_dir.is_dir()
    assert delete_home(home.id) is True
    assert not home_dir.exists()
    assert load_homes().homes == []


def test_delete_home_returns_false_for_unknown_id(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    assert delete_home("nonexistent") is False


def test_save_homes_preserves_untouched_homes(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    home_a = create_home("Home A", "existing")
    home_b = create_home("Home B", "existing")
    patch_home(home_a.id, name="Home A Renamed", home_type=None, enabled_modules=None)
    doc = load_homes()
    ids = {h.id for h in doc.homes}
    assert ids == {home_a.id, home_b.id}
    names = {h.id: h.name for h in doc.homes}
    assert names[home_a.id] == "Home A Renamed"
    assert names[home_b.id] == "Home B"


def test_delete_one_home_does_not_remove_another(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    home_a = create_home("Home A", "existing")
    home_b = create_home("Home B", "existing")
    delete_home(home_a.id)
    remaining = load_homes().homes
    assert len(remaining) == 1
    assert remaining[0].id == home_b.id


def test_save_homes_direct_round_trip(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    from myhome.models_homes import Home, HomesDocument
    doc = HomesDocument(homes=[
        Home(id="h1", name="A", type="existing", enabledModules=["home", "chores"], createdAt="2026-01-01T00:00:00+00:00"),
    ])
    save_homes(doc)
    loaded = load_homes()
    assert len(loaded.homes) == 1
    assert loaded.homes[0].enabledModules == ["home", "chores"]
