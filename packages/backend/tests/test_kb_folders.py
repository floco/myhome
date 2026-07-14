import pytest
from myhome.persistence_kb_folders import (
    create_folder, delete_folder, get_folder, list_folders, move_folder, rename_folder, would_create_cycle,
)


@pytest.fixture(autouse=True)
def _data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))


@pytest.fixture()
def home_id():
    from myhome.persistence_homes import create_home
    return create_home("Test Home", "existing").id


def test_create_and_list_folder(home_id):
    folder = create_folder(home_id, "Appliances")
    folders = list_folders(home_id)
    assert len(folders) == 1
    assert folders[0].id == folder.id
    assert folders[0].name == "Appliances"
    assert folders[0].parentId is None


def test_create_subfolder(home_id):
    parent = create_folder(home_id, "Parent")
    child = create_folder(home_id, "Child", parent_id=parent.id)
    assert child.parentId == parent.id


def test_list_folders_sorted_by_name(home_id):
    create_folder(home_id, "Zebra")
    create_folder(home_id, "Apple")
    folders = list_folders(home_id)
    assert [f.name for f in folders] == ["Apple", "Zebra"]


def test_get_folder_missing_returns_none(home_id):
    assert get_folder(home_id, "nonexistent") is None


def test_rename_folder(home_id):
    folder = create_folder(home_id, "Old")
    renamed = rename_folder(home_id, folder.id, "New")
    assert renamed.name == "New"
    assert get_folder(home_id, folder.id).name == "New"


def test_rename_folder_missing_returns_none(home_id):
    assert rename_folder(home_id, "nonexistent", "New") is None


def test_move_folder(home_id):
    parent = create_folder(home_id, "Parent")
    child = create_folder(home_id, "Child")
    moved = move_folder(home_id, child.id, parent.id)
    assert moved.parentId == parent.id
    assert get_folder(home_id, child.id).parentId == parent.id


def test_move_folder_to_root(home_id):
    parent = create_folder(home_id, "Parent")
    child = create_folder(home_id, "Child", parent_id=parent.id)
    moved = move_folder(home_id, child.id, None)
    assert moved.parentId is None


def test_move_folder_missing_returns_none(home_id):
    assert move_folder(home_id, "nonexistent", None) is None


def test_delete_folder(home_id):
    folder = create_folder(home_id, "Temp")
    assert delete_folder(home_id, folder.id) is True
    assert list_folders(home_id) == []


def test_delete_folder_missing_returns_false(home_id):
    assert delete_folder(home_id, "nonexistent") is False


def test_would_create_cycle_self(home_id):
    folder = create_folder(home_id, "A")
    assert would_create_cycle(home_id, folder.id, folder.id) is True


def test_would_create_cycle_descendant(home_id):
    a = create_folder(home_id, "A")
    b = create_folder(home_id, "B", parent_id=a.id)
    c = create_folder(home_id, "C", parent_id=b.id)
    assert would_create_cycle(home_id, a.id, c.id) is True


def test_would_create_cycle_unrelated_is_false(home_id):
    a = create_folder(home_id, "A")
    b = create_folder(home_id, "B")
    assert would_create_cycle(home_id, a.id, b.id) is False
