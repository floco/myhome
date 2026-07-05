import pytest


@pytest.fixture(autouse=True)
def _data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))


@pytest.fixture()
def home_id():
    from myhome.persistence_homes import create_home
    return create_home("Test Home", "existing").id


def test_create_and_list_consumable(home_id):
    from myhome.mcp_tools_consumables import _create_consumable_impl, _list_consumables_impl
    item = _create_consumable_impl(home_id, "AA Batteries", unit="packs", quantity=5.0)
    doc = _list_consumables_impl(home_id)
    assert doc["consumables"][0]["id"] == item["id"]
    assert doc["consumables"][0]["quantity"] == 5.0


def test_update_consumable(home_id):
    from myhome.mcp_tools_consumables import _create_consumable_impl, _update_consumable_impl
    item = _create_consumable_impl(home_id, "Detergent")
    updated = _update_consumable_impl(home_id, item["id"], name="Laundry Detergent")
    assert updated["name"] == "Laundry Detergent"


def test_delete_consumable(home_id):
    from myhome.mcp_tools_consumables import (
        _create_consumable_impl, _delete_consumable_impl, _list_consumables_impl,
    )
    item = _create_consumable_impl(home_id, "Old Item")
    _delete_consumable_impl(home_id, item["id"])
    assert _list_consumables_impl(home_id)["consumables"] == []


def test_delete_consumable_unknown_id_raises(home_id):
    from myhome.mcp_tools_consumables import _delete_consumable_impl
    with pytest.raises(ValueError):
        _delete_consumable_impl(home_id, "nonexistent")


def test_adjust_stock_sets_absolute_quantity_and_logs_transaction(home_id):
    from myhome.mcp_tools_consumables import _adjust_consumable_stock_impl, _create_consumable_impl, _list_consumables_impl
    item = _create_consumable_impl(home_id, "Batteries", quantity=10.0)
    result = _adjust_consumable_stock_impl(home_id, item["id"], 8.0, note="used 2")
    assert result["quantity"] == 8.0
    doc = _list_consumables_impl(home_id)
    assert len(doc["transactions"]) == 1
    assert doc["transactions"][0]["delta"] == -2.0
    assert doc["transactions"][0]["note"] == "used 2"


def test_adjust_stock_unknown_id_raises(home_id):
    from myhome.mcp_tools_consumables import _adjust_consumable_stock_impl
    with pytest.raises(ValueError):
        _adjust_consumable_stock_impl(home_id, "nonexistent", 5.0)
