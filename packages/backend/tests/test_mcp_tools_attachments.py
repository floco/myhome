import base64

import pytest


@pytest.fixture(autouse=True)
def _data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))


@pytest.fixture()
def home_id():
    from myhome.persistence_homes import create_home
    return create_home("Test Home", "existing").id


_ALL_MODULES = [
    "inventory", "kb", "works", "costs", "properties", "build", "chores", "insurance",
]


def _make_item(home_id: str, module: str) -> str:
    """Create one parent item in `module` and return its id (a task id for
    'build')."""
    if module == "inventory":
        from myhome.mcp_tools_inventory import _create_inventory_item_impl
        return _create_inventory_item_impl(home_id, "Drill")["id"]
    if module == "kb":
        from myhome.mcp_tools_kb import _create_kb_entry_impl
        return _create_kb_entry_impl(home_id, "Page")["id"]
    if module == "works":
        from myhome.mcp_tools_works import _create_work_impl
        return _create_work_impl(home_id, "Roof repair", "2026-01-01")["id"]
    if module == "costs":
        from myhome.mcp_tools_costs import _create_cost_entry_impl
        return _create_cost_entry_impl(home_id, "cat1", "2026-01-01", 100.0)["id"]
    if module == "properties":
        from myhome.mcp_tools_properties import _create_property_impl
        return _create_property_impl(home_id, "Lakeview", "house")["id"]
    if module == "build":
        from myhome.build_template import seed_default_build
        from myhome.mcp_tools_build import _create_build_task_impl
        from myhome.persistence_build import load_build, save_build
        save_build(home_id, seed_default_build())
        phase_id = load_build(home_id).phases[0].id
        return _create_build_task_impl(home_id, phase_id, "Frame walls")["id"]
    if module == "chores":
        from myhome.mcp_tools_chores import _create_chore_impl
        return _create_chore_impl(home_id, "Mow lawn", "🌱", 7, "2026-01-01")["id"]
    if module == "insurance":
        from myhome.mcp_tools_insurance import _create_insurance_policy_impl
        return _create_insurance_policy_impl(home_id, "Home Policy", "cat1")["id"]
    raise ValueError(module)


@pytest.mark.parametrize("module", _ALL_MODULES)
def test_upload_attachment_adds_filename_to_item(home_id, module):
    from myhome.mcp_tools_attachments import _MODULES, _upload_attachment_impl
    item_id = _make_item(home_id, module)
    data = base64.b64encode(b"fake-bytes").decode()
    result = _upload_attachment_impl(home_id, module, item_id, "photo.jpg", data)
    assert result == {"filename": "photo.jpg"}
    item, _save = _MODULES[module].find(home_id, item_id)
    assert "photo.jpg" in item.attachments


@pytest.mark.parametrize("module", _ALL_MODULES)
def test_upload_attachment_writes_original_bytes_to_disk(home_id, module):
    from myhome.mcp_tools_attachments import _MODULES, _upload_attachment_impl
    item_id = _make_item(home_id, module)
    original = b"fake-bytes-for-" + module.encode()
    data = base64.b64encode(original).decode()
    _upload_attachment_impl(home_id, module, item_id, "doc.pdf", data)
    path = _MODULES[module].get_attachment_path(home_id, item_id, "doc.pdf")
    assert path.read_bytes() == original


def test_upload_attachment_unknown_module_raises(home_id):
    from myhome.mcp_tools_attachments import _upload_attachment_impl
    data = base64.b64encode(b"x").decode()
    with pytest.raises(ValueError, match="Unknown module"):
        _upload_attachment_impl(home_id, "not-a-module", "x", "a.jpg", data)


def test_upload_attachment_unknown_item_id_raises(home_id):
    from myhome.mcp_tools_attachments import _upload_attachment_impl
    data = base64.b64encode(b"x").decode()
    with pytest.raises(ValueError, match="Unknown item_id"):
        _upload_attachment_impl(home_id, "inventory", "nonexistent", "a.jpg", data)


def test_upload_attachment_disallowed_extension_raises(home_id):
    from myhome.mcp_tools_attachments import _upload_attachment_impl
    from myhome.mcp_tools_inventory import _create_inventory_item_impl
    item_id = _create_inventory_item_impl(home_id, "Drill")["id"]
    data = base64.b64encode(b"x").decode()
    with pytest.raises(ValueError, match="not supported"):
        _upload_attachment_impl(home_id, "inventory", item_id, "malware.exe", data)


def test_upload_attachment_invalid_base64_raises(home_id):
    from myhome.mcp_tools_attachments import _upload_attachment_impl
    from myhome.mcp_tools_inventory import _create_inventory_item_impl
    item_id = _create_inventory_item_impl(home_id, "Drill")["id"]
    with pytest.raises(ValueError, match="Invalid base64"):
        _upload_attachment_impl(home_id, "inventory", item_id, "photo.jpg", "not valid base64!!")


def test_upload_attachment_bumps_kb_updated_at(home_id):
    from myhome.mcp_tools_attachments import _upload_attachment_impl
    from myhome.mcp_tools_kb import _create_kb_entry_impl
    from myhome.persistence_kb import load_entry
    entry = _create_kb_entry_impl(home_id, "Page")
    data = base64.b64encode(b"x").decode()
    _upload_attachment_impl(home_id, "kb", entry["id"], "photo.jpg", data)
    reloaded = load_entry(home_id, entry["id"])
    assert reloaded.updatedAt != entry["updatedAt"]
