import pytest


@pytest.fixture(autouse=True)
def _data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))


@pytest.fixture()
def home_id():
    from myhome.persistence_homes import create_home
    return create_home("Test Home", "existing").id


def test_create_and_list_entry(home_id):
    from myhome.mcp_tools_costs import _create_cost_entry_impl, _list_cost_entries_impl
    entry = _create_cost_entry_impl(home_id, "cat-electricity", "2026-07-01", 45.50)
    doc = _list_cost_entries_impl(home_id)
    assert doc["entries"][0]["id"] == entry["id"]
    assert doc["entries"][0]["totalAmount"] == 45.50


def test_update_entry(home_id):
    from myhome.mcp_tools_costs import _create_cost_entry_impl, _update_cost_entry_impl
    entry = _create_cost_entry_impl(home_id, "cat-water", "2026-07-01", 20.0)
    updated = _update_cost_entry_impl(home_id, entry["id"], notes="corrected reading")
    assert updated["notes"] == "corrected reading"


def test_update_entry_unknown_id_raises(home_id):
    from myhome.mcp_tools_costs import _update_cost_entry_impl
    with pytest.raises(ValueError):
        _update_cost_entry_impl(home_id, "nonexistent", notes="x")


def test_delete_entry(home_id):
    from myhome.mcp_tools_costs import _create_cost_entry_impl, _delete_cost_entry_impl, _list_cost_entries_impl
    entry = _create_cost_entry_impl(home_id, "cat-fuel", "2026-07-01", 60.0)
    _delete_cost_entry_impl(home_id, entry["id"])
    assert _list_cost_entries_impl(home_id)["entries"] == []


def test_delete_entry_unknown_id_raises(home_id):
    from myhome.mcp_tools_costs import _delete_cost_entry_impl
    with pytest.raises(ValueError):
        _delete_cost_entry_impl(home_id, "nonexistent")
