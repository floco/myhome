# packages/backend/tests/test_homes_persistence.py
import shutil
import pytest
from myhome.models_homes import Home, HomesDocument
from myhome.persistence_homes import (
    load_homes,
    save_homes,
    create_home,
    patch_home,
    delete_home,
    migrate_legacy_if_needed,
)


def test_load_returns_empty_when_no_file(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    doc = load_homes()
    assert doc.homes == []


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


def test_patch_home_returns_none_for_unknown_id(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    result = patch_home("nonexistent", name="X", home_type=None, enabled_modules=None)
    assert result is None


def test_delete_home_removes_from_registry_and_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    home = create_home("Test", "existing")
    home_dir = tmp_path / "homes" / home.id
    assert home_dir.is_dir()
    result = delete_home(home.id)
    assert result is True
    assert not home_dir.exists()
    assert load_homes().homes == []


def test_delete_home_returns_false_for_unknown_id(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    assert delete_home("nonexistent") is False


def test_migrate_legacy_moves_files_and_creates_registry(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    (tmp_path / "house.json").write_text('{"version":1,"house":{},"floors":[]}')
    (tmp_path / "chores.json").write_text('{"version":1,"chores":[],"assignments":[]}')
    migrate_legacy_if_needed()
    doc = load_homes()
    assert len(doc.homes) == 1
    assert doc.homes[0].id == "default"
    assert doc.homes[0].type == "existing"
    assert (tmp_path / "homes" / "default" / "house.json").exists()
    assert (tmp_path / "homes" / "default" / "chores.json").exists()
    assert not (tmp_path / "house.json").exists()


def test_migrate_is_idempotent(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    (tmp_path / "house.json").write_text('{}')
    migrate_legacy_if_needed()
    migrate_legacy_if_needed()
    assert len(load_homes().homes) == 1


def test_migrate_does_nothing_when_no_legacy_files(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    migrate_legacy_if_needed()
    assert not (tmp_path / "homes.json").exists()
