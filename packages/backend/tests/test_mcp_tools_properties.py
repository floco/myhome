import pytest


@pytest.fixture(autouse=True)
def _data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))


@pytest.fixture()
def home_id():
    from myhome.persistence_homes import create_home
    return create_home("Test Home", "existing").id


def test_create_and_list_property(home_id):
    from myhome.mcp_tools_properties import _create_property_impl, _list_properties_impl
    item = _create_property_impl(home_id, "Terreno Norte", "land")
    doc = _list_properties_impl(home_id)
    assert doc["properties"][0]["id"] == item["id"]
    assert doc["properties"][0]["status"] == "watching"


def test_create_property_rejects_invalid_type(home_id):
    from myhome.mcp_tools_properties import _create_property_impl
    with pytest.raises(ValueError):
        _create_property_impl(home_id, "Bad", "castle")


def test_create_property_rejects_invalid_status(home_id):
    from myhome.mcp_tools_properties import _create_property_impl
    with pytest.raises(ValueError):
        _create_property_impl(home_id, "Bad", "land", status="nope")


def test_update_property_transitions_status(home_id):
    from myhome.mcp_tools_properties import _create_property_impl, _update_property_impl
    item = _create_property_impl(home_id, "Casa Sul", "house")
    updated = _update_property_impl(home_id, item["id"], status="visited")
    assert updated["status"] == "visited"


def test_update_property_rejects_invalid_status(home_id):
    from myhome.mcp_tools_properties import _create_property_impl, _update_property_impl
    item = _create_property_impl(home_id, "Casa Sul", "house")
    with pytest.raises(ValueError):
        _update_property_impl(home_id, item["id"], status="nope")


def test_delete_property(home_id):
    from myhome.mcp_tools_properties import _create_property_impl, _delete_property_impl, _list_properties_impl
    item = _create_property_impl(home_id, "Old Listing", "land")
    _delete_property_impl(home_id, item["id"])
    assert _list_properties_impl(home_id)["properties"] == []


def test_delete_property_unknown_id_raises(home_id):
    from myhome.mcp_tools_properties import _delete_property_impl
    with pytest.raises(ValueError):
        _delete_property_impl(home_id, "nonexistent")
