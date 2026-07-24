# packages/backend/tests/test_mcp_tools_contacts.py
import pytest


@pytest.fixture(autouse=True)
def _data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))


@pytest.fixture()
def home_id():
    from myhome.persistence_homes import create_home
    return create_home("Test Home", "existing").id


def test_create_and_list_contact(home_id):
    from myhome.mcp_tools_contacts import _create_contact_impl, _list_contacts_impl
    contact = _create_contact_impl(home_id, "Metro Plumbing", "ctype-supplier")
    doc = _list_contacts_impl(home_id)
    assert doc["contacts"][0]["id"] == contact["id"]
    assert doc["contacts"][0]["typeId"] == "ctype-supplier"


def test_update_contact(home_id):
    from myhome.mcp_tools_contacts import _create_contact_impl, _update_contact_impl
    contact = _create_contact_impl(home_id, "Metro Plumbing", "ctype-supplier")
    updated = _update_contact_impl(home_id, contact["id"], phone="555-0000")
    assert updated["phone"] == "555-0000"


def test_delete_contact(home_id):
    from myhome.mcp_tools_contacts import _create_contact_impl, _delete_contact_impl, _list_contacts_impl
    contact = _create_contact_impl(home_id, "Old Supplier", "ctype-supplier")
    _delete_contact_impl(home_id, contact["id"])
    assert _list_contacts_impl(home_id)["contacts"] == []


def test_delete_contact_unknown_id_raises(home_id):
    from myhome.mcp_tools_contacts import _delete_contact_impl
    with pytest.raises(ValueError):
        _delete_contact_impl(home_id, "nonexistent")


def test_delete_contact_blocked_when_used(home_id):
    from myhome.mcp_tools_contacts import _create_contact_impl, _delete_contact_impl
    from myhome.mcp_tools_works import _create_work_impl
    contact = _create_contact_impl(home_id, "Metro Plumbing", "ctype-supplier")
    _create_work_impl(home_id, "Fix sink", "2026-01-01", supplier_id=contact["id"])
    with pytest.raises(ValueError, match="still referenced"):
        _delete_contact_impl(home_id, contact["id"])
