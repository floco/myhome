import pytest


@pytest.fixture(autouse=True)
def _data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))


def test_list_homes_empty_initially():
    from myhome.mcp_tools_homes import _list_homes_impl
    assert _list_homes_impl() == []


def test_create_home():
    from myhome.mcp_tools_homes import _create_home_impl, _list_homes_impl
    home = _create_home_impl("Lake House", "existing")
    assert home["name"] == "Lake House"
    assert home["type"] == "existing"
    assert _list_homes_impl()[0]["id"] == home["id"]


def test_create_home_rejects_invalid_type():
    from myhome.mcp_tools_homes import _create_home_impl
    with pytest.raises(ValueError):
        _create_home_impl("Bad", "mansion")


def test_update_home_renames():
    from myhome.mcp_tools_homes import _create_home_impl, _update_home_impl
    home = _create_home_impl("Old Name", "existing")
    updated = _update_home_impl(home["id"], name="New Name")
    assert updated["name"] == "New Name"


def test_update_home_unknown_id_raises():
    from myhome.mcp_tools_homes import _update_home_impl
    with pytest.raises(ValueError):
        _update_home_impl("nonexistent", name="X")


def test_delete_home():
    from myhome.mcp_tools_homes import _create_home_impl, _delete_home_impl, _list_homes_impl
    home = _create_home_impl("Temp", "existing")
    result = _delete_home_impl(home["id"])
    assert result == {"deleted": home["id"]}
    assert _list_homes_impl() == []


def test_delete_home_unknown_id_raises():
    from myhome.mcp_tools_homes import _delete_home_impl
    with pytest.raises(ValueError):
        _delete_home_impl("nonexistent")


def test_create_demo_home():
    from myhome.mcp_tools_homes import _create_demo_home_impl, _list_homes_impl
    home = _create_demo_home_impl("My Demo")
    assert home["name"] == "My Demo"
    assert home["type"] == "demo"
    assert _list_homes_impl()[0]["id"] == home["id"]


def test_create_demo_home_defaults_name():
    from myhome.mcp_tools_homes import _create_demo_home_impl
    home = _create_demo_home_impl()
    assert home["name"] == "Demo Home"
