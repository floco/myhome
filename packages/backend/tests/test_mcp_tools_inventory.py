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


def test_create_item_resolves_category_owner_store_by_name(home_id):
    from myhome.mcp_tools_inventory import _create_inventory_item_impl
    from myhome.persistence_settings import load_settings

    item = _create_inventory_item_impl(home_id, "Drill", category="Tools", owner="Alice", store="Ikea")
    settings_doc = load_settings(home_id)
    assert item["categoryId"] == next(c.id for c in settings_doc.inventoryCategories if c.name == "Tools")
    assert item["ownerId"] == next(o.id for o in settings_doc.owners if o.name == "Alice")
    assert item["storeId"] == next(s.id for s in settings_doc.stores if s.name == "Ikea")


def test_create_item_reuses_existing_owner_on_second_call(home_id):
    from myhome.mcp_tools_inventory import _create_inventory_item_impl
    from myhome.persistence_settings import load_settings

    _create_inventory_item_impl(home_id, "Drill", owner="Alice")
    _create_inventory_item_impl(home_id, "Sander", owner="Alice")
    settings_doc = load_settings(home_id)
    assert len([o for o in settings_doc.owners if o.name == "Alice"]) == 1


def test_create_item_blank_category_owner_store_stays_none(home_id):
    from myhome.mcp_tools_inventory import _create_inventory_item_impl

    item = _create_inventory_item_impl(home_id, "Mystery Box")
    assert item["categoryId"] is None
    assert item["ownerId"] is None
    assert item["storeId"] is None
