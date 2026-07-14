import pytest


@pytest.fixture(autouse=True)
def _data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))


@pytest.fixture()
def home_id():
    from myhome.persistence_homes import create_home
    return create_home("Test Home", "existing").id


def test_create_and_list_entry(home_id):
    from myhome.mcp_tools_kb import _create_kb_entry_impl, _list_kb_entries_impl
    entry = _create_kb_entry_impl(home_id, "Wifi Password", content="It's on the router")
    doc = _list_kb_entries_impl(home_id)
    assert doc["entries"][0]["id"] == entry["id"]
    assert doc["entries"][0]["title"] == "Wifi Password"


def test_update_entry_bumps_updated_at(home_id):
    from myhome.mcp_tools_kb import _create_kb_entry_impl, _update_kb_entry_impl
    entry = _create_kb_entry_impl(home_id, "Boiler Manual")
    updated = _update_kb_entry_impl(home_id, entry["id"], content="Reset button is on the side")
    assert updated["content"] == "Reset button is on the side"
    assert updated["updatedAt"] >= entry["updatedAt"]


def test_update_entry_unknown_id_raises(home_id):
    from myhome.mcp_tools_kb import _update_kb_entry_impl
    with pytest.raises(ValueError):
        _update_kb_entry_impl(home_id, "nonexistent", title="X")


def test_delete_entry(home_id):
    from myhome.mcp_tools_kb import _create_kb_entry_impl, _delete_kb_entry_impl, _list_kb_entries_impl
    entry = _create_kb_entry_impl(home_id, "Old Note")
    _delete_kb_entry_impl(home_id, entry["id"])
    assert _list_kb_entries_impl(home_id)["entries"] == []


def test_delete_entry_unknown_id_raises(home_id):
    from myhome.mcp_tools_kb import _delete_kb_entry_impl
    with pytest.raises(ValueError):
        _delete_kb_entry_impl(home_id, "nonexistent")


def test_create_and_list_folder(home_id):
    from myhome.mcp_tools_kb import _create_kb_folder_impl, _list_kb_folders_impl
    folder = _create_kb_folder_impl(home_id, "Appliances")
    doc = _list_kb_folders_impl(home_id)
    assert doc["folders"][0]["id"] == folder["id"]
    assert doc["folders"][0]["name"] == "Appliances"


def test_create_subfolder(home_id):
    from myhome.mcp_tools_kb import _create_kb_folder_impl
    parent = _create_kb_folder_impl(home_id, "Parent")
    child = _create_kb_folder_impl(home_id, "Child", parent_id=parent["id"])
    assert child["parentId"] == parent["id"]


def test_create_folder_unknown_parent_raises(home_id):
    from myhome.mcp_tools_kb import _create_kb_folder_impl
    with pytest.raises(ValueError):
        _create_kb_folder_impl(home_id, "X", parent_id="nonexistent")


def test_rename_folder(home_id):
    from myhome.mcp_tools_kb import _create_kb_folder_impl, _rename_kb_folder_impl
    folder = _create_kb_folder_impl(home_id, "Old")
    renamed = _rename_kb_folder_impl(home_id, folder["id"], "New")
    assert renamed["name"] == "New"


def test_rename_folder_unknown_id_raises(home_id):
    from myhome.mcp_tools_kb import _rename_kb_folder_impl
    with pytest.raises(ValueError):
        _rename_kb_folder_impl(home_id, "nonexistent", "New")


def test_move_folder_to_root(home_id):
    from myhome.mcp_tools_kb import _create_kb_folder_impl, _move_kb_folder_impl
    parent = _create_kb_folder_impl(home_id, "Parent")
    child = _create_kb_folder_impl(home_id, "Child", parent_id=parent["id"])
    moved = _move_kb_folder_impl(home_id, child["id"])
    assert moved["parentId"] is None


def test_move_folder_unknown_parent_raises(home_id):
    from myhome.mcp_tools_kb import _create_kb_folder_impl, _move_kb_folder_impl
    folder = _create_kb_folder_impl(home_id, "A")
    with pytest.raises(ValueError):
        _move_kb_folder_impl(home_id, folder["id"], parent_id="nonexistent")


def test_move_folder_into_own_descendant_raises(home_id):
    from myhome.mcp_tools_kb import _create_kb_folder_impl, _move_kb_folder_impl
    a = _create_kb_folder_impl(home_id, "A")
    b = _create_kb_folder_impl(home_id, "B", parent_id=a["id"])
    with pytest.raises(ValueError):
        _move_kb_folder_impl(home_id, a["id"], parent_id=b["id"])


def test_delete_folder(home_id):
    from myhome.mcp_tools_kb import _create_kb_folder_impl, _delete_kb_folder_impl, _list_kb_folders_impl
    folder = _create_kb_folder_impl(home_id, "Temp")
    _delete_kb_folder_impl(home_id, folder["id"])
    assert _list_kb_folders_impl(home_id)["folders"] == []


def test_delete_folder_with_entries_raises(home_id):
    from myhome.mcp_tools_kb import _create_kb_entry_impl, _create_kb_folder_impl, _delete_kb_folder_impl
    folder = _create_kb_folder_impl(home_id, "Has entries")
    _create_kb_entry_impl(home_id, "X", folder_id=folder["id"])
    with pytest.raises(ValueError):
        _delete_kb_folder_impl(home_id, folder["id"])


def test_delete_folder_with_subfolder_raises(home_id):
    from myhome.mcp_tools_kb import _create_kb_folder_impl, _delete_kb_folder_impl
    parent = _create_kb_folder_impl(home_id, "Parent")
    _create_kb_folder_impl(home_id, "Child", parent_id=parent["id"])
    with pytest.raises(ValueError):
        _delete_kb_folder_impl(home_id, parent["id"])


def test_create_entry_with_folder_id(home_id):
    from myhome.mcp_tools_kb import _create_kb_entry_impl, _create_kb_folder_impl
    folder = _create_kb_folder_impl(home_id, "Manuals")
    entry = _create_kb_entry_impl(home_id, "X", folder_id=folder["id"])
    assert entry["folderId"] == folder["id"]


def test_create_entry_unknown_folder_id_raises(home_id):
    from myhome.mcp_tools_kb import _create_kb_entry_impl
    with pytest.raises(ValueError):
        _create_kb_entry_impl(home_id, "X", folder_id="nonexistent")


def test_move_entry_to_folder(home_id):
    from myhome.mcp_tools_kb import _create_kb_entry_impl, _create_kb_folder_impl, _move_kb_entry_impl
    folder = _create_kb_folder_impl(home_id, "Manuals")
    entry = _create_kb_entry_impl(home_id, "X")
    moved = _move_kb_entry_impl(home_id, entry["id"], folder_id=folder["id"])
    assert moved["folderId"] == folder["id"]


def test_move_entry_unknown_folder_id_raises(home_id):
    from myhome.mcp_tools_kb import _create_kb_entry_impl, _move_kb_entry_impl
    entry = _create_kb_entry_impl(home_id, "X")
    with pytest.raises(ValueError):
        _move_kb_entry_impl(home_id, entry["id"], folder_id="nonexistent")


def test_update_entry_does_not_touch_folder_id(home_id):
    from myhome.mcp_tools_kb import (
        _create_kb_entry_impl, _create_kb_folder_impl, _move_kb_entry_impl, _update_kb_entry_impl,
    )
    folder = _create_kb_folder_impl(home_id, "Manuals")
    entry = _create_kb_entry_impl(home_id, "X")
    _move_kb_entry_impl(home_id, entry["id"], folder_id=folder["id"])
    updated = _update_kb_entry_impl(home_id, entry["id"], title="Renamed")
    assert updated["folderId"] == folder["id"]
