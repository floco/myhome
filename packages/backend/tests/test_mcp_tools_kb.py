import pytest


@pytest.fixture(autouse=True)
def _data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))


@pytest.fixture()
def home_id():
    from myhome.persistence_homes import create_home
    return create_home("Test Home", "existing").id


def test_create_and_list_entry(home_id):
    from myhome.mcp_tools_kb import _create_kb_entry_impl, _list_kb_entries_impl
    entry = _create_kb_entry_impl(home_id, "Wifi Password", content="It's on the router")
    doc = _list_kb_entries_impl(home_id)
    assert doc["entries"][0]["id"] == entry["id"]
    assert doc["entries"][0]["title"] == "Wifi Password"
    assert doc["entries"][0]["icon"] == "📄"
    assert doc["entries"][0]["parentId"] is None


def test_create_entry_with_custom_icon(home_id):
    from myhome.mcp_tools_kb import _create_kb_entry_impl
    entry = _create_kb_entry_impl(home_id, "Boiler", icon="🔧")
    assert entry["icon"] == "🔧"


def test_create_child_entry(home_id):
    from myhome.mcp_tools_kb import _create_kb_entry_impl
    parent = _create_kb_entry_impl(home_id, "Appliances")
    child = _create_kb_entry_impl(home_id, "Boiler", parent_id=parent["id"])
    assert child["parentId"] == parent["id"]


def test_create_entry_unknown_parent_raises(home_id):
    from myhome.mcp_tools_kb import _create_kb_entry_impl
    with pytest.raises(ValueError):
        _create_kb_entry_impl(home_id, "X", parent_id="nonexistent")


def test_update_entry_bumps_updated_at(home_id):
    from myhome.mcp_tools_kb import _create_kb_entry_impl, _update_kb_entry_impl
    entry = _create_kb_entry_impl(home_id, "Boiler Manual")
    updated = _update_kb_entry_impl(home_id, entry["id"], content="Reset button is on the side")
    assert updated["content"] == "Reset button is on the side"
    assert updated["updatedAt"] >= entry["updatedAt"]


def test_update_entry_icon(home_id):
    from myhome.mcp_tools_kb import _create_kb_entry_impl, _update_kb_entry_impl
    entry = _create_kb_entry_impl(home_id, "Boiler")
    updated = _update_kb_entry_impl(home_id, entry["id"], icon="🔧")
    assert updated["icon"] == "🔧"


def test_update_entry_unknown_id_raises(home_id):
    from myhome.mcp_tools_kb import _update_kb_entry_impl
    with pytest.raises(ValueError):
        _update_kb_entry_impl(home_id, "nonexistent", title="X")


def test_move_entry(home_id):
    from myhome.mcp_tools_kb import _create_kb_entry_impl, _move_kb_entry_impl
    parent = _create_kb_entry_impl(home_id, "Appliances")
    entry = _create_kb_entry_impl(home_id, "Boiler")
    moved = _move_kb_entry_impl(home_id, entry["id"], parent["id"])
    assert moved["parentId"] == parent["id"]


def test_move_entry_to_root(home_id):
    from myhome.mcp_tools_kb import _create_kb_entry_impl, _move_kb_entry_impl
    parent = _create_kb_entry_impl(home_id, "Appliances")
    entry = _create_kb_entry_impl(home_id, "Boiler", parent_id=parent["id"])
    moved = _move_kb_entry_impl(home_id, entry["id"], None)
    assert moved["parentId"] is None


def test_move_entry_into_own_descendant_raises(home_id):
    from myhome.mcp_tools_kb import _create_kb_entry_impl, _move_kb_entry_impl
    a = _create_kb_entry_impl(home_id, "A")
    b = _create_kb_entry_impl(home_id, "B", parent_id=a["id"])
    with pytest.raises(ValueError):
        _move_kb_entry_impl(home_id, a["id"], b["id"])


def test_delete_entry(home_id):
    from myhome.mcp_tools_kb import _create_kb_entry_impl, _delete_kb_entry_impl, _list_kb_entries_impl
    entry = _create_kb_entry_impl(home_id, "Old Note")
    result = _delete_kb_entry_impl(home_id, entry["id"])
    assert result["deletedCount"] == 1
    assert _list_kb_entries_impl(home_id)["entries"] == []


def test_delete_entry_cascades_to_children(home_id):
    from myhome.mcp_tools_kb import _create_kb_entry_impl, _delete_kb_entry_impl
    parent = _create_kb_entry_impl(home_id, "Parent")
    _create_kb_entry_impl(home_id, "Child", parent_id=parent["id"])
    result = _delete_kb_entry_impl(home_id, parent["id"])
    assert result["deletedCount"] == 2


def test_delete_entry_unknown_id_raises(home_id):
    from myhome.mcp_tools_kb import _delete_kb_entry_impl
    with pytest.raises(ValueError):
        _delete_kb_entry_impl(home_id, "nonexistent")


def test_list_kb_trash(home_id):
    from myhome.mcp_tools_kb import _create_kb_entry_impl, _delete_kb_entry_impl, _list_kb_trash_impl
    entry = _create_kb_entry_impl(home_id, "Old Note")
    _delete_kb_entry_impl(home_id, entry["id"])
    trash = _list_kb_trash_impl(home_id)
    assert trash["entries"][0]["id"] == entry["id"]


def test_restore_kb_entry(home_id):
    from myhome.mcp_tools_kb import (
        _create_kb_entry_impl, _delete_kb_entry_impl, _list_kb_entries_impl, _restore_kb_entry_impl,
    )
    entry = _create_kb_entry_impl(home_id, "Old Note")
    _delete_kb_entry_impl(home_id, entry["id"])
    result = _restore_kb_entry_impl(home_id, entry["id"])
    assert result["restoredCount"] == 1
    assert _list_kb_entries_impl(home_id)["entries"][0]["id"] == entry["id"]


def test_restore_kb_entry_not_trashed_raises(home_id):
    from myhome.mcp_tools_kb import _create_kb_entry_impl, _restore_kb_entry_impl
    entry = _create_kb_entry_impl(home_id, "Live Note")
    with pytest.raises(ValueError):
        _restore_kb_entry_impl(home_id, entry["id"])


def test_permanently_delete_kb_entry(home_id):
    from myhome.mcp_tools_kb import (
        _create_kb_entry_impl, _delete_kb_entry_impl, _list_kb_trash_impl, _permanently_delete_kb_entry_impl,
    )
    entry = _create_kb_entry_impl(home_id, "Old Note")
    _delete_kb_entry_impl(home_id, entry["id"])
    _permanently_delete_kb_entry_impl(home_id, entry["id"])
    assert _list_kb_trash_impl(home_id)["entries"] == []


def test_permanently_delete_live_entry_raises(home_id):
    from myhome.mcp_tools_kb import _create_kb_entry_impl, _permanently_delete_kb_entry_impl
    entry = _create_kb_entry_impl(home_id, "Live Note")
    with pytest.raises(ValueError):
        _permanently_delete_kb_entry_impl(home_id, entry["id"])


def test_empty_kb_trash(home_id):
    from myhome.mcp_tools_kb import (
        _create_kb_entry_impl, _delete_kb_entry_impl, _empty_kb_trash_impl, _list_kb_trash_impl,
    )
    a = _create_kb_entry_impl(home_id, "A")
    b = _create_kb_entry_impl(home_id, "B")
    _delete_kb_entry_impl(home_id, a["id"])
    _delete_kb_entry_impl(home_id, b["id"])
    result = _empty_kb_trash_impl(home_id)
    assert result["deletedCount"] == 2
    assert _list_kb_trash_impl(home_id)["entries"] == []


def test_add_kb_bookmark_appends_card_and_bumps_updated_at(home_id, monkeypatch):
    import socket

    import respx
    from httpx import Response
    from myhome.mcp_tools_kb import _add_kb_bookmark_impl, _create_kb_entry_impl

    monkeypatch.setattr(
        socket, "getaddrinfo",
        lambda *a, **k: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 0))],
    )
    entry = _create_kb_entry_impl(home_id, "Notes", content="Existing content")
    with respx.mock:
        respx.get("http://93.184.216.34/page").mock(
            return_value=Response(
                200, headers={"content-type": "text/html"},
                html='<meta property="og:title" content="OG Title">',
            )
        )
        result = _add_kb_bookmark_impl(home_id, entry["id"], "http://example.com/page")
    assert "Existing content" in result["content"]
    assert 'class="kb-bookmark"' in result["content"]
    assert "OG Title" in result["content"]
    assert result["updatedAt"] != entry["updatedAt"]


def test_add_kb_bookmark_title_and_description_override_fetched_values(home_id, monkeypatch):
    import socket

    import respx
    from httpx import Response
    from myhome.mcp_tools_kb import _add_kb_bookmark_impl, _create_kb_entry_impl

    monkeypatch.setattr(
        socket, "getaddrinfo",
        lambda *a, **k: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 0))],
    )
    entry = _create_kb_entry_impl(home_id, "Notes")
    with respx.mock:
        respx.get("http://93.184.216.34/page").mock(
            return_value=Response(
                200, headers={"content-type": "text/html"},
                html='<meta property="og:title" content="Fetched Title">',
            )
        )
        result = _add_kb_bookmark_impl(
            home_id, entry["id"], "http://example.com/page",
            title="Custom Title", description="Custom Desc",
        )
    assert "Custom Title" in result["content"]
    assert "Custom Desc" in result["content"]
    assert "Fetched Title" not in result["content"]


def test_add_kb_bookmark_unknown_entry_id_raises(home_id):
    from myhome.mcp_tools_kb import _add_kb_bookmark_impl
    with pytest.raises(ValueError):
        _add_kb_bookmark_impl(home_id, "nonexistent", "http://example.com")
