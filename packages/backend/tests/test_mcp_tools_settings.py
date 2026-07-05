import pytest


@pytest.fixture(autouse=True)
def _data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))


def test_get_settings_returns_default_categories():
    from myhome.mcp_tools_settings import _get_settings_impl
    from myhome.persistence_homes import create_home

    home = create_home("Test Home", "existing")
    doc = _get_settings_impl(home.id)
    assert any(c["name"] == "Electricity" for c in doc["costCategories"])
    assert doc["consumableUnits"] == ["count", "L", "mL", "kg", "g", "packs", "rolls", "pairs"]
