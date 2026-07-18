import pytest


@pytest.fixture(autouse=True)
def _data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))


@pytest.fixture()
def home_id():
    from myhome.persistence_homes import create_home
    return create_home("Test Home", "project").id


def test_list_locations_returns_seeded_defaults(home_id):
    from myhome.mcp_tools_locations import _list_locations_impl
    doc = _list_locations_impl(home_id)
    assert len(doc["criteria"]) == 11
    assert doc["locations"] == []


def test_create_and_list_location(home_id):
    from myhome.mcp_tools_locations import _create_location_impl, _list_locations_impl
    item = _create_location_impl(home_id, "Ljubljana", emoji="🇸🇮")
    doc = _list_locations_impl(home_id)
    assert doc["locations"][0]["id"] == item["id"]
    assert doc["locations"][0]["emoji"] == "🇸🇮"


def test_update_location(home_id):
    from myhome.mcp_tools_locations import _create_location_impl, _update_location_impl
    item = _create_location_impl(home_id, "Ljubljana")
    updated = _update_location_impl(home_id, item["id"], name="Ljubljana Region")
    assert updated["name"] == "Ljubljana Region"


def test_delete_location(home_id):
    from myhome.mcp_tools_locations import _create_location_impl, _delete_location_impl, _list_locations_impl
    item = _create_location_impl(home_id, "Old Place")
    _delete_location_impl(home_id, item["id"])
    assert _list_locations_impl(home_id)["locations"] == []


def test_delete_location_unknown_id_raises(home_id):
    from myhome.mcp_tools_locations import _delete_location_impl
    with pytest.raises(ValueError):
        _delete_location_impl(home_id, "nonexistent")


def test_create_update_delete_criterion(home_id):
    from myhome.mcp_tools_locations import (
        _create_location_criterion_impl, _update_location_criterion_impl,
        _delete_location_criterion_impl, _list_locations_impl,
    )
    item = _create_location_criterion_impl(home_id, "Internet Speed", weight="high")
    assert item["weight"] == "high"
    updated = _update_location_criterion_impl(home_id, item["id"], weight="low")
    assert updated["weight"] == "low"
    _delete_location_criterion_impl(home_id, item["id"])
    doc = _list_locations_impl(home_id)
    assert all(c["id"] != item["id"] for c in doc["criteria"])


def test_set_location_rating_and_clear(home_id):
    from myhome.mcp_tools_locations import _create_location_impl, _list_locations_impl, _set_location_rating_impl
    location = _create_location_impl(home_id, "Zagreb")
    doc = _list_locations_impl(home_id)
    criterion_id = doc["criteria"][0]["id"]
    rating = _set_location_rating_impl(home_id, location["id"], criterion_id, score=4, note="Nice city")
    assert rating["score"] == 4
    cleared = _set_location_rating_impl(home_id, location["id"], criterion_id, score=None, note="")
    assert cleared["score"] is None


def test_set_location_rating_unknown_location_raises(home_id):
    from myhome.mcp_tools_locations import _list_locations_impl, _set_location_rating_impl
    doc = _list_locations_impl(home_id)
    criterion_id = doc["criteria"][0]["id"]
    with pytest.raises(ValueError):
        _set_location_rating_impl(home_id, "nonexistent", criterion_id, score=3)
