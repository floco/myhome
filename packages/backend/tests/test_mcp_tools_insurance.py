import pytest


@pytest.fixture(autouse=True)
def _data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))


@pytest.fixture()
def home_id():
    from myhome.persistence_homes import create_home
    return create_home("Test Home", "existing").id


def test_create_and_list_policy(home_id):
    from myhome.mcp_tools_insurance import _create_insurance_policy_impl, _list_insurance_policies_impl
    policy = _create_insurance_policy_impl(home_id, name="Home Insurance", category_id="icat-home", premium_frequency="monthly")
    doc = _list_insurance_policies_impl(home_id)
    assert doc["policies"][0]["id"] == policy["id"]
    assert doc["policies"][0]["name"] == "Home Insurance"


def test_create_policy_rejects_invalid_frequency(home_id):
    from myhome.mcp_tools_insurance import _create_insurance_policy_impl
    with pytest.raises(ValueError):
        _create_insurance_policy_impl(home_id, name="Bad", category_id="icat-home", premium_frequency="nope")


def test_update_policy(home_id):
    from myhome.mcp_tools_insurance import _create_insurance_policy_impl, _update_insurance_policy_impl
    policy = _create_insurance_policy_impl(home_id, name="Home Insurance", category_id="icat-home", premium_frequency="monthly")
    updated = _update_insurance_policy_impl(home_id, policy["id"], premiumAmount=45.0)
    assert updated["premiumAmount"] == 45.0


def test_update_policy_unknown_id_raises(home_id):
    from myhome.mcp_tools_insurance import _update_insurance_policy_impl
    with pytest.raises(ValueError):
        _update_insurance_policy_impl(home_id, "nope", premiumAmount=1.0)


def test_delete_policy(home_id):
    from myhome.mcp_tools_insurance import _create_insurance_policy_impl, _delete_insurance_policy_impl, _list_insurance_policies_impl
    policy = _create_insurance_policy_impl(home_id, name="Home Insurance", category_id="icat-home", premium_frequency="monthly")
    result = _delete_insurance_policy_impl(home_id, policy["id"])
    assert result == {"deleted": policy["id"]}
    assert _list_insurance_policies_impl(home_id)["policies"] == []


def test_delete_policy_unknown_id_raises(home_id):
    from myhome.mcp_tools_insurance import _delete_insurance_policy_impl
    with pytest.raises(ValueError):
        _delete_insurance_policy_impl(home_id, "nonexistent")
