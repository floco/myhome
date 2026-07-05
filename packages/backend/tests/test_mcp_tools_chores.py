import pytest


@pytest.fixture(autouse=True)
def _data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))


@pytest.fixture()
def home_id():
    from myhome.persistence_homes import create_home
    return create_home("Test Home", "existing").id


def test_create_and_list_chore(home_id):
    from myhome.mcp_tools_chores import _create_chore_impl, _list_chores_impl
    chore = _create_chore_impl(home_id, "Take out trash", "🗑", 7.0, "2026-07-10T00:00:00Z")
    doc = _list_chores_impl(home_id)
    assert doc["chores"][0]["id"] == chore["id"]
    assert doc["chores"][0]["frequency"] == 7  # derived from period_days since frequency=0


def test_update_chore(home_id):
    from myhome.mcp_tools_chores import _create_chore_impl, _update_chore_impl
    chore = _create_chore_impl(home_id, "Water plants", "🌱", 3.0, "2026-07-05T00:00:00Z")
    updated = _update_chore_impl(home_id, chore["id"], name="Water all plants")
    assert updated["name"] == "Water all plants"


def test_update_chore_unknown_id_raises(home_id):
    from myhome.mcp_tools_chores import _update_chore_impl
    with pytest.raises(ValueError):
        _update_chore_impl(home_id, "nonexistent", name="X")


def test_delete_chore(home_id):
    from myhome.mcp_tools_chores import _create_chore_impl, _delete_chore_impl, _list_chores_impl
    chore = _create_chore_impl(home_id, "Mow lawn", "🌿", 14.0, "2026-07-15T00:00:00Z")
    _delete_chore_impl(home_id, chore["id"])
    assert _list_chores_impl(home_id)["chores"] == []


def test_complete_chore_advances_due_date(home_id):
    from myhome.mcp_tools_chores import _complete_chore_impl, _create_chore_impl, _list_chores_impl
    chore = _create_chore_impl(
        home_id, "Vacuum", "🧹", 7.0, "2026-07-04T00:00:00Z",
        frequency_type="interval", frequency=7, frequency_metadata={"unit": "days"},
    )
    result = _complete_chore_impl(home_id, chore["id"], notes="done early")
    assert result["nextDueDate"] != "2026-07-04T00:00:00Z"
    doc = _list_chores_impl(home_id)
    assert len(doc["completions"]) == 1
    assert doc["completions"][0]["notes"] == "done early"


def test_undo_chore_completion(home_id):
    from myhome.mcp_tools_chores import _complete_chore_impl, _create_chore_impl, _list_chores_impl, _undo_chore_completion_impl
    chore = _create_chore_impl(home_id, "Dust", "🪶", 7.0, "2026-07-04T00:00:00Z")
    _complete_chore_impl(home_id, chore["id"])
    completion_id = _list_chores_impl(home_id)["completions"][0]["id"]
    _undo_chore_completion_impl(home_id, completion_id)
    assert _list_chores_impl(home_id)["completions"] == []


def test_undo_unknown_completion_raises(home_id):
    from myhome.mcp_tools_chores import _undo_chore_completion_impl
    with pytest.raises(ValueError):
        _undo_chore_completion_impl(home_id, "nonexistent")
