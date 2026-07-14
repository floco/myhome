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
    assert "id" in data
    assert "createdAt" in data
    assert "updatedAt" in data


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


def test_delete_entry(client, home_id):
    resp = client.post(f"/api/homes/{home_id}/kb", json={"title": "To delete", "content": ""})
    entry_id = resp.json()["id"]
    resp = client.delete(f"/api/homes/{home_id}/kb/{entry_id}")
    assert resp.status_code == 204
    assert client.get(f"/api/homes/{home_id}/kb").json()["entries"] == []


def test_delete_entry_not_found(client, home_id):
    resp = client.delete(f"/api/homes/{home_id}/kb/nonexistent")
    assert resp.status_code == 404


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
    client.delete(f"/api/homes/{home_id}/kb/{eid}")
    assert not att_dir.exists()


def test_entry_folder_id_round_trips_through_frontmatter(home_id):
    entry = make_entry()
    entry.folderId = "f1"
    save_entry(home_id, entry)
    from myhome.persistence_kb import load_entry
    loaded = load_entry(home_id, "e1")
    assert loaded.folderId == "f1"


def test_entry_without_folder_id_defaults_to_none(home_id):
    save_entry(home_id, make_entry())
    from myhome.persistence_kb import load_entry
    loaded = load_entry(home_id, "e1")
    assert loaded.folderId is None
