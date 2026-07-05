import pytest


@pytest.fixture(autouse=True)
def _data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))


@pytest.fixture()
def home_id():
    from myhome.persistence_homes import create_home
    return create_home("Test Home", "existing").id


def test_create_and_list_work(home_id):
    from myhome.mcp_tools_works import _create_work_impl, _list_works_impl
    work = _create_work_impl(home_id, "Repaint fence", "2026-08-01")
    doc = _list_works_impl(home_id)
    assert doc["works"][0]["id"] == work["id"]
    assert doc["works"][0]["status"] == "planned"


def test_create_work_rejects_invalid_status(home_id):
    from myhome.mcp_tools_works import _create_work_impl
    with pytest.raises(ValueError):
        _create_work_impl(home_id, "Bad", "2026-08-01", status="nope")


def test_update_work_transitions_status(home_id):
    from myhome.mcp_tools_works import _create_work_impl, _update_work_impl
    work = _create_work_impl(home_id, "Replace gutters", "2026-08-01")
    updated = _update_work_impl(home_id, work["id"], status="in_progress")
    assert updated["status"] == "in_progress"


def test_update_work_rejects_invalid_status(home_id):
    from myhome.mcp_tools_works import _create_work_impl, _update_work_impl
    work = _create_work_impl(home_id, "Repaint fence", "2026-08-01")
    with pytest.raises(ValueError):
        _update_work_impl(home_id, work["id"], status="nope")


def test_delete_work(home_id):
    from myhome.mcp_tools_works import _create_work_impl, _delete_work_impl, _list_works_impl
    work = _create_work_impl(home_id, "Old Project", "2026-08-01")
    _delete_work_impl(home_id, work["id"])
    assert _list_works_impl(home_id)["works"] == []


def test_delete_work_unknown_id_raises(home_id):
    from myhome.mcp_tools_works import _delete_work_impl
    with pytest.raises(ValueError):
        _delete_work_impl(home_id, "nonexistent")
