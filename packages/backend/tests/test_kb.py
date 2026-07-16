import pytest
from myhome.models_kb import KBEntry
from myhome.persistence_kb import save_entry


def make_entry() -> KBEntry:
    return KBEntry(
        id="e1",
        title="How to paint",
        content="# Painting",
        createdAt="2026-06-28T10:00:00Z",
        updatedAt="2026-06-28T10:00:00Z",
    )


def test_get_kb_empty_when_no_dir(client, home_id):
    resp = client.get(f"/api/homes/{home_id}/kb")
    assert resp.status_code == 200
    assert resp.json()["entries"] == []


def test_get_kb_returns_saved_data(client, home_id):
    save_entry(home_id, make_entry())
    resp = client.get(f"/api/homes/{home_id}/kb")
    assert resp.status_code == 200
    assert resp.json()["entries"][0]["id"] == "e1"


def test_create_entry(client, home_id):
    payload = {"title": "How to paint", "content": "# Painting"}
    resp = client.post(f"/api/homes/{home_id}/kb", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "How to paint"
    assert data["content"] == "# Painting"
    assert data["icon"] == "📄"
    assert data["parentId"] is None
    assert data["order"] == 0
    assert "id" in data
    assert "createdAt" in data
    assert "updatedAt" in data


def test_create_entry_with_custom_icon(client, home_id):
    resp = client.post(f"/api/homes/{home_id}/kb", json={"title": "X", "content": "", "icon": "🔧"})
    assert resp.json()["icon"] == "🔧"


def test_create_child_page(client, home_id):
    parent = client.post(f"/api/homes/{home_id}/kb", json={"title": "Parent", "content": ""}).json()
    resp = client.post(f"/api/homes/{home_id}/kb", json={"title": "Child", "content": "", "parentId": parent["id"]})
    assert resp.status_code == 201
    assert resp.json()["parentId"] == parent["id"]
    assert resp.json()["order"] == 0


def test_create_second_child_gets_next_order(client, home_id):
    parent = client.post(f"/api/homes/{home_id}/kb", json={"title": "Parent", "content": ""}).json()
    client.post(f"/api/homes/{home_id}/kb", json={"title": "C1", "content": "", "parentId": parent["id"]})
    resp = client.post(f"/api/homes/{home_id}/kb", json={"title": "C2", "content": "", "parentId": parent["id"]})
    assert resp.json()["order"] == 1


def test_create_child_unknown_parent_404(client, home_id):
    resp = client.post(f"/api/homes/{home_id}/kb", json={"title": "X", "content": "", "parentId": "nonexistent"})
    assert resp.status_code == 404


def test_create_child_under_trashed_parent_404(client, home_id):
    parent = client.post(f"/api/homes/{home_id}/kb", json={"title": "Parent", "content": ""}).json()
    client.delete(f"/api/homes/{home_id}/kb/{parent['id']}")
    resp = client.post(f"/api/homes/{home_id}/kb", json={"title": "X", "content": "", "parentId": parent["id"]})
    assert resp.status_code == 404


def test_update_entry(client, home_id):
    resp = client.post(f"/api/homes/{home_id}/kb", json={"title": "Old title", "content": ""})
    entry_id = resp.json()["id"]
    resp = client.put(f"/api/homes/{home_id}/kb/{entry_id}", json={"title": "New title"})
    assert resp.status_code == 204
    entries = client.get(f"/api/homes/{home_id}/kb").json()["entries"]
    assert entries[0]["title"] == "New title"


def test_update_entry_not_found(client, home_id):
    resp = client.put(f"/api/homes/{home_id}/kb/nonexistent", json={"title": "x"})
    assert resp.status_code == 404


def test_update_entry_icon(client, home_id):
    entry_id = client.post(f"/api/homes/{home_id}/kb", json={"title": "X", "content": ""}).json()["id"]
    resp = client.put(f"/api/homes/{home_id}/kb/{entry_id}", json={"icon": "🔧"})
    assert resp.status_code == 204
    entries = client.get(f"/api/homes/{home_id}/kb").json()["entries"]
    assert entries[0]["icon"] == "🔧"


def test_move_entry_to_new_parent(client, home_id):
    parent = client.post(f"/api/homes/{home_id}/kb", json={"title": "Parent", "content": ""}).json()
    entry_id = client.post(f"/api/homes/{home_id}/kb", json={"title": "X", "content": ""}).json()["id"]
    resp = client.put(f"/api/homes/{home_id}/kb/{entry_id}", json={"parentId": parent["id"]})
    assert resp.status_code == 204
    entries = client.get(f"/api/homes/{home_id}/kb").json()["entries"]
    assert next(e for e in entries if e["id"] == entry_id)["parentId"] == parent["id"]


def test_move_entry_back_to_root(client, home_id):
    parent = client.post(f"/api/homes/{home_id}/kb", json={"title": "Parent", "content": ""}).json()
    entry_id = client.post(f"/api/homes/{home_id}/kb", json={"title": "X", "content": "", "parentId": parent["id"]}).json()["id"]
    resp = client.put(f"/api/homes/{home_id}/kb/{entry_id}", json={"parentId": None})
    assert resp.status_code == 204
    entries = client.get(f"/api/homes/{home_id}/kb").json()["entries"]
    assert next(e for e in entries if e["id"] == entry_id)["parentId"] is None


def test_move_entry_unknown_parent_404(client, home_id):
    entry_id = client.post(f"/api/homes/{home_id}/kb", json={"title": "X", "content": ""}).json()["id"]
    resp = client.put(f"/api/homes/{home_id}/kb/{entry_id}", json={"parentId": "nonexistent"})
    assert resp.status_code == 404


def test_move_entry_into_own_descendant_rejected(client, home_id):
    a = client.post(f"/api/homes/{home_id}/kb", json={"title": "A", "content": ""}).json()
    b = client.post(f"/api/homes/{home_id}/kb", json={"title": "B", "content": "", "parentId": a["id"]}).json()
    resp = client.put(f"/api/homes/{home_id}/kb/{a['id']}", json={"parentId": b["id"]})
    assert resp.status_code == 400


def test_move_entry_into_self_rejected(client, home_id):
    a = client.post(f"/api/homes/{home_id}/kb", json={"title": "A", "content": ""}).json()
    resp = client.put(f"/api/homes/{home_id}/kb/{a['id']}", json={"parentId": a["id"]})
    assert resp.status_code == 400


def test_reorder_siblings(client, home_id):
    a = client.post(f"/api/homes/{home_id}/kb", json={"title": "A", "content": ""}).json()
    b = client.post(f"/api/homes/{home_id}/kb", json={"title": "B", "content": ""}).json()
    c = client.post(f"/api/homes/{home_id}/kb", json={"title": "C", "content": ""}).json()
    resp = client.put(f"/api/homes/{home_id}/kb/reorder", json={"parentId": None, "orderedIds": [c["id"], a["id"], b["id"]]})
    assert resp.status_code == 204
    entries = client.get(f"/api/homes/{home_id}/kb").json()["entries"]
    order = {e["id"]: e["order"] for e in entries}
    assert order[c["id"]] < order[a["id"]] < order[b["id"]]


def test_reorder_siblings_mismatched_ids_rejected(client, home_id):
    a = client.post(f"/api/homes/{home_id}/kb", json={"title": "A", "content": ""}).json()
    resp = client.put(f"/api/homes/{home_id}/kb/reorder", json={"parentId": None, "orderedIds": [a["id"], "bogus"]})
    assert resp.status_code == 400


def test_delete_entry(client, home_id):
    resp = client.post(f"/api/homes/{home_id}/kb", json={"title": "To delete", "content": ""})
    entry_id = resp.json()["id"]
    resp = client.delete(f"/api/homes/{home_id}/kb/{entry_id}")
    assert resp.status_code == 200
    assert resp.json() == {"deletedCount": 1}
    assert client.get(f"/api/homes/{home_id}/kb").json()["entries"] == []


def test_delete_entry_not_found(client, home_id):
    resp = client.delete(f"/api/homes/{home_id}/kb/nonexistent")
    assert resp.status_code == 404


def test_delete_entry_cascades_to_children(client, home_id):
    parent = client.post(f"/api/homes/{home_id}/kb", json={"title": "Parent", "content": ""}).json()
    client.post(f"/api/homes/{home_id}/kb", json={"title": "Child", "content": "", "parentId": parent["id"]})
    resp = client.delete(f"/api/homes/{home_id}/kb/{parent['id']}")
    assert resp.json() == {"deletedCount": 2}
    assert client.get(f"/api/homes/{home_id}/kb").json()["entries"] == []


def test_deleted_entry_appears_in_trash(client, home_id):
    entry_id = client.post(f"/api/homes/{home_id}/kb", json={"title": "X", "content": ""}).json()["id"]
    client.delete(f"/api/homes/{home_id}/kb/{entry_id}")
    trash = client.get(f"/api/homes/{home_id}/kb/trash").json()["entries"]
    assert trash[0]["id"] == entry_id


def test_restore_entry(client, home_id):
    entry_id = client.post(f"/api/homes/{home_id}/kb", json={"title": "X", "content": ""}).json()["id"]
    client.delete(f"/api/homes/{home_id}/kb/{entry_id}")
    resp = client.post(f"/api/homes/{home_id}/kb/trash/{entry_id}/restore")
    assert resp.status_code == 200
    assert resp.json() == {"restoredCount": 1}
    assert client.get(f"/api/homes/{home_id}/kb").json()["entries"][0]["id"] == entry_id
    assert client.get(f"/api/homes/{home_id}/kb/trash").json()["entries"] == []


def test_restore_cascades_to_trashed_descendants(client, home_id):
    parent = client.post(f"/api/homes/{home_id}/kb", json={"title": "Parent", "content": ""}).json()
    client.post(f"/api/homes/{home_id}/kb", json={"title": "Child", "content": "", "parentId": parent["id"]})
    client.delete(f"/api/homes/{home_id}/kb/{parent['id']}")
    resp = client.post(f"/api/homes/{home_id}/kb/trash/{parent['id']}/restore")
    assert resp.json() == {"restoredCount": 2}
    assert len(client.get(f"/api/homes/{home_id}/kb").json()["entries"]) == 2


def test_restore_not_found_for_live_entry(client, home_id):
    entry_id = client.post(f"/api/homes/{home_id}/kb", json={"title": "X", "content": ""}).json()["id"]
    resp = client.post(f"/api/homes/{home_id}/kb/trash/{entry_id}/restore")
    assert resp.status_code == 404


def test_permanently_delete_from_trash(client, tmp_path, home_id):
    entry_id = client.post(f"/api/homes/{home_id}/kb", json={"title": "X", "content": ""}).json()["id"]
    client.delete(f"/api/homes/{home_id}/kb/{entry_id}")
    resp = client.delete(f"/api/homes/{home_id}/kb/trash/{entry_id}")
    assert resp.status_code == 204
    assert client.get(f"/api/homes/{home_id}/kb/trash").json()["entries"] == []
    assert not (tmp_path / "homes" / home_id / "kb" / f"{entry_id}.md").exists()


def test_permanently_delete_live_entry_rejected(client, home_id):
    entry_id = client.post(f"/api/homes/{home_id}/kb", json={"title": "X", "content": ""}).json()["id"]
    resp = client.delete(f"/api/homes/{home_id}/kb/trash/{entry_id}")
    assert resp.status_code == 404
    assert client.get(f"/api/homes/{home_id}/kb").json()["entries"][0]["id"] == entry_id


def test_empty_trash(client, home_id):
    a = client.post(f"/api/homes/{home_id}/kb", json={"title": "A", "content": ""}).json()["id"]
    b = client.post(f"/api/homes/{home_id}/kb", json={"title": "B", "content": ""}).json()["id"]
    client.delete(f"/api/homes/{home_id}/kb/{a}")
    client.delete(f"/api/homes/{home_id}/kb/{b}")
    resp = client.post(f"/api/homes/{home_id}/kb/trash/empty")
    assert resp.status_code == 200
    assert resp.json() == {"deletedCount": 2}
    assert client.get(f"/api/homes/{home_id}/kb/trash").json()["entries"] == []


def _make_valid_pdf() -> bytes:
    import fitz
    doc = fitz.open()
    doc.new_page(width=200, height=200)
    return doc.write()


def _entry_id(client, home_id) -> str:
    resp = client.post(f"/api/homes/{home_id}/kb", json={"title": "Test entry", "content": "Hello"})
    return resp.json()["id"]


def test_kb_attachments_empty_by_default(client, home_id):
    eid = _entry_id(client, home_id)
    entry = next(e for e in client.get(f"/api/homes/{home_id}/kb").json()["entries"] if e["id"] == eid)
    assert entry["attachments"] == []


def test_kb_upload_jpeg_accepted(client, home_id):
    eid = _entry_id(client, home_id)
    resp = client.post(
        f"/api/homes/{home_id}/kb/{eid}/attachments",
        files={"file": ("photo.jpg", b"\xff\xd8\xff" + b"\x00" * 50, "image/jpeg")},
    )
    assert resp.status_code == 201
    assert resp.json()["filename"] == "photo.jpg"
    entry = next(e for e in client.get(f"/api/homes/{home_id}/kb").json()["entries"] if e["id"] == eid)
    assert "photo.jpg" in entry["attachments"]


def test_kb_upload_unsupported_rejected(client, home_id):
    eid = _entry_id(client, home_id)
    resp = client.post(
        f"/api/homes/{home_id}/kb/{eid}/attachments",
        files={"file": ("x.docx", b"\x00" * 50, "application/vnd.openxmlformats")},
    )
    assert resp.status_code == 400


def test_kb_upload_pdf_creates_thumbnail(client, tmp_path, home_id):
    eid = _entry_id(client, home_id)
    resp = client.post(
        f"/api/homes/{home_id}/kb/{eid}/attachments",
        files={"file": ("note.pdf", _make_valid_pdf(), "application/pdf")},
    )
    assert resp.status_code == 201
    thumb = tmp_path / "homes" / home_id / "kb-attachments" / eid / "note.pdf.thumb.jpg"
    assert thumb.exists()


def test_kb_delete_attachment_removes_thumb(client, tmp_path, home_id):
    eid = _entry_id(client, home_id)
    client.post(f"/api/homes/{home_id}/kb/{eid}/attachments",
        files={"file": ("note.pdf", _make_valid_pdf(), "application/pdf")})
    thumb = tmp_path / "homes" / home_id / "kb-attachments" / eid / "note.pdf.thumb.jpg"
    assert thumb.exists()
    client.delete(f"/api/homes/{home_id}/kb/{eid}/attachments/note.pdf")
    assert not thumb.exists()


def test_kb_get_jpeg_returns_image_content_type(client, home_id):
    eid = _entry_id(client, home_id)
    client.post(f"/api/homes/{home_id}/kb/{eid}/attachments",
        files={"file": ("photo.jpg", b"\xff\xd8\xff" + b"\x00" * 50, "image/jpeg")})
    resp = client.get(f"/api/homes/{home_id}/kb/{eid}/attachments/photo.jpg")
    assert resp.status_code == 200
    assert "image/jpeg" in resp.headers["content-type"]


def test_kb_attachments_persist_after_entry_update(client, home_id):
    eid = _entry_id(client, home_id)
    client.post(f"/api/homes/{home_id}/kb/{eid}/attachments",
        files={"file": ("photo.jpg", b"\xff\xd8\xff" + b"\x00" * 50, "image/jpeg")})
    client.put(f"/api/homes/{home_id}/kb/{eid}", json={"title": "Updated title"})
    entry = next(e for e in client.get(f"/api/homes/{home_id}/kb").json()["entries"] if e["id"] == eid)
    assert "photo.jpg" in entry["attachments"]


def test_kb_delete_entry_removes_attachment_dir(client, tmp_path, home_id):
    eid = _entry_id(client, home_id)
    client.post(f"/api/homes/{home_id}/kb/{eid}/attachments",
        files={"file": ("photo.jpg", b"\xff\xd8\xff" + b"\x00" * 50, "image/jpeg")})
    att_dir = tmp_path / "homes" / home_id / "kb-attachments" / eid
    assert att_dir.exists()
    # DELETE on the live entry is a soft delete now -- the attachment dir survives
    # until the entry is permanently deleted from Trash.
    client.delete(f"/api/homes/{home_id}/kb/{eid}")
    assert att_dir.exists()
    client.delete(f"/api/homes/{home_id}/kb/trash/{eid}")
    assert not att_dir.exists()
