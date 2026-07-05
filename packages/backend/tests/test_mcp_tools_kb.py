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
