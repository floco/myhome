import pytest


@pytest.fixture(autouse=True)
def _data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))


@pytest.fixture()
def home_id():
    from myhome.persistence_homes import create_home
    return create_home("Test Home", "existing").id


def test_create_and_list_item(home_id):
    from myhome.mcp_tools_inventory import _create_inventory_item_impl, _list_inventory_items_impl
    item = _create_inventory_item_impl(home_id, "Drill", category="Tool", brand="Bosch")
    doc = _list_inventory_items_impl(home_id)
    assert doc["items"][0]["id"] == item["id"]
    assert doc["items"][0]["brand"] == "Bosch"


def test_update_item(home_id):
    from myhome.mcp_tools_inventory import _create_inventory_item_impl, _update_inventory_item_impl
    item = _create_inventory_item_impl(home_id, "TV")
    updated = _update_inventory_item_impl(home_id, item["id"], notes="In living room")
    assert updated["notes"] == "In living room"


def test_update_item_unknown_id_raises(home_id):
    from myhome.mcp_tools_inventory import _update_inventory_item_impl
    with pytest.raises(ValueError):
        _update_inventory_item_impl(home_id, "nonexistent", notes="x")


def test_delete_item(home_id):
    from myhome.mcp_tools_inventory import (
        _create_inventory_item_impl, _delete_inventory_item_impl, _list_inventory_items_impl,
    )
    item = _create_inventory_item_impl(home_id, "Old Fridge")
    _delete_inventory_item_impl(home_id, item["id"])
    assert _list_inventory_items_impl(home_id)["items"] == []


def test_delete_item_unknown_id_raises(home_id):
    from myhome.mcp_tools_inventory import _delete_inventory_item_impl
    with pytest.raises(ValueError):
        _delete_inventory_item_impl(home_id, "nonexistent")
