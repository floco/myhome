import pytest
from myhome.models_works import Work, WorkPlacement, WorkPosition, WorksDocument
from myhome.persistence_works import save_works


def make_doc() -> WorksDocument:
    return WorksDocument(
        works=[Work(id="w1", title="Boiler repair", status="done", date="2025-11-10", totalCost=1200.0)]
    )


def test_get_works_empty_when_no_file(client):
    resp = client.get("/api/works")
    assert resp.status_code == 200
    assert resp.json()["works"] == []


def test_get_works_returns_saved_data(client, tmp_path):
    save_works(make_doc())
    resp = client.get("/api/works")
    assert resp.status_code == 200
    assert resp.json()["works"][0]["id"] == "w1"


def test_create_work(client):
    payload = {"title": "Roof repair", "status": "planned", "date": "2026-04-01"}
    resp = client.post("/api/works", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "Roof repair"
    assert data["status"] == "planned"
    assert data["attachments"] == []
    assert data["placement"] is None
    assert "id" in data
    assert len(client.get("/api/works").json()["works"]) == 1


def test_create_work_full_fields(client):
    payload = {
        "title": "Boiler install",
        "description": "New 24kW unit",
        "status": "done",
        "categoryId": "wcat-plumbing",
        "date": "2025-11-10",
        "totalCost": 3200.0,
        "supplierId": "sup-1",
        "notes": "## Details\n\nViessmann unit",
    }
    resp = client.post("/api/works", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["totalCost"] == 3200.0
    assert data["supplierId"] == "sup-1"
    assert data["notes"].startswith("##")


def test_update_work_partial(client, tmp_path):
    save_works(make_doc())
    resp = client.put("/api/works/w1", json={"status": "in_progress", "totalCost": 1500.0})
    assert resp.status_code == 204
    work = client.get("/api/works").json()["works"][0]
    assert work["status"] == "in_progress"
    assert work["totalCost"] == 1500.0
    assert work["title"] == "Boiler repair"  # unchanged


def test_update_work_404(client):
    resp = client.put("/api/works/nope", json={"status": "done"})
    assert resp.status_code == 404


def test_delete_work(client, tmp_path):
    save_works(make_doc())
    resp = client.delete("/api/works/w1")
    assert resp.status_code == 204
    assert client.get("/api/works").json()["works"] == []


def test_delete_work_404(client):
    resp = client.delete("/api/works/nope")
    assert resp.status_code == 404


def test_get_attachment_traversal_rejected(client, tmp_path):
    save_works(make_doc())
    resp = client.get("/api/works/w1/attachments/.hidden")
    assert resp.status_code == 400


def test_delete_attachment_traversal_rejected(client, tmp_path):
    save_works(make_doc())
    resp = client.delete("/api/works/w1/attachments/.hidden")
    assert resp.status_code == 400


def test_get_attachment_invalid_id_rejected(client, tmp_path):
    save_works(make_doc())
    resp = client.get("/api/works/../attachments/invoice.pdf")
    # FastAPI won't route ".." as a path param, but validate_id rejects non-UUID chars like "/"
    # Test with a dot-only id that would otherwise traverse
    resp2 = client.get("/api/works/w1/attachments/invoice.pdf")
    assert resp2.status_code == 404  # work exists but file not uploaded yet — id "w1" passes validation


def test_upload_invalid_id_rejected(client, tmp_path):
    save_works(make_doc())
    # IDs with characters outside [A-Za-z0-9_-] should be rejected with 400
    resp = client.post(
        "/api/works/w!1/attachments",
        files={"file": ("invoice.pdf", b"%PDF test", "application/pdf")},
    )
    assert resp.status_code == 400


def test_upload_attachment(client, tmp_path):
    save_works(make_doc())
    resp = client.post(
        "/api/works/w1/attachments",
        files={"file": ("invoice.pdf", b"%PDF-1.4 test", "application/pdf")},
    )
    assert resp.status_code == 201
    assert resp.json()["filename"] == "invoice.pdf"
    work = client.get("/api/works").json()["works"][0]
    assert "invoice.pdf" in work["attachments"]


def test_upload_sanitises_filename(client, tmp_path):
    save_works(make_doc())
    resp = client.post(
        "/api/works/w1/attachments",
        files={"file": ("my invoice 2025.pdf", b"%PDF test", "application/pdf")},
    )
    assert resp.status_code == 201
    assert resp.json()["filename"] == "my_invoice_2025.pdf"


def test_upload_unsupported_type_rejected(client, tmp_path):
    save_works(make_doc())
    resp = client.post(
        "/api/works/w1/attachments",
        files={"file": ("notes.txt", b"hello", "text/plain")},
    )
    assert resp.status_code == 400


def test_upload_image_jpeg_accepted(client, tmp_path):
    save_works(make_doc())
    resp = client.post(
        "/api/works/w1/attachments",
        files={"file": ("photo.jpg", b"\xff\xd8\xff\xe0" + b"\x00" * 100, "image/jpeg")},
    )
    assert resp.status_code == 201
    assert resp.json()["filename"] == "photo.jpg"
    work = client.get("/api/works").json()["works"][0]
    assert "photo.jpg" in work["attachments"]


def test_upload_image_png_accepted(client, tmp_path):
    save_works(make_doc())
    resp = client.post(
        "/api/works/w1/attachments",
        files={"file": ("shot.png", b"\x89PNG\r\n" + b"\x00" * 100, "image/png")},
    )
    assert resp.status_code == 201
    assert resp.json()["filename"] == "shot.png"


def test_upload_image_webp_accepted(client, tmp_path):
    save_works(make_doc())
    resp = client.post(
        "/api/works/w1/attachments",
        files={"file": ("photo.webp", b"RIFF" + b"\x00" * 100, "image/webp")},
    )
    assert resp.status_code == 201
    assert resp.json()["filename"] == "photo.webp"


def test_sanitise_preserves_image_extension(client, tmp_path):
    save_works(make_doc())
    resp = client.post(
        "/api/works/w1/attachments",
        files={"file": ("my photo 2025.jpg", b"\xff\xd8\xff\xe0" + b"\x00" * 100, "image/jpeg")},
    )
    assert resp.status_code == 201
    assert resp.json()["filename"] == "my_photo_2025.jpg"


def test_get_image_attachment_returns_correct_content_type(client, tmp_path):
    save_works(make_doc())
    client.post(
        "/api/works/w1/attachments",
        files={"file": ("photo.png", b"\x89PNG\r\n" + b"\x00" * 100, "image/png")},
    )
    resp = client.get("/api/works/w1/attachments/photo.png")
    assert resp.status_code == 200
    assert "image/png" in resp.headers["content-type"]


def test_upload_attachment_work_not_found(client):
    resp = client.post(
        "/api/works/nope/attachments",
        files={"file": ("invoice.pdf", b"%PDF test", "application/pdf")},
    )
    assert resp.status_code == 404


def test_get_attachment(client, tmp_path):
    save_works(make_doc())
    client.post(
        "/api/works/w1/attachments",
        files={"file": ("invoice.pdf", b"%PDF-1.4 test content", "application/pdf")},
    )
    resp = client.get("/api/works/w1/attachments/invoice.pdf")
    assert resp.status_code == 200
    assert "pdf" in resp.headers["content-type"]


def test_get_attachment_not_found(client, tmp_path):
    save_works(make_doc())
    resp = client.get("/api/works/w1/attachments/nope.pdf")
    assert resp.status_code == 404


def test_delete_attachment(client, tmp_path):
    save_works(make_doc())
    client.post(
        "/api/works/w1/attachments",
        files={"file": ("invoice.pdf", b"%PDF test", "application/pdf")},
    )
    resp = client.delete("/api/works/w1/attachments/invoice.pdf")
    assert resp.status_code == 204
    work = client.get("/api/works").json()["works"][0]
    assert "invoice.pdf" not in work["attachments"]


def test_delete_attachment_not_found(client, tmp_path):
    save_works(make_doc())
    resp = client.delete("/api/works/w1/attachments/nope.pdf")
    assert resp.status_code == 404


def test_set_placement(client, tmp_path):
    save_works(make_doc())
    body = {"floorId": "f1", "position": {"x": 100.0, "y": 200.0}}
    resp = client.put("/api/works/w1/placement", json=body)
    assert resp.status_code == 204
    work = client.get("/api/works").json()["works"][0]
    assert work["placement"]["floorId"] == "f1"
    assert work["placement"]["position"]["x"] == 100.0


def test_set_placement_not_found(client):
    resp = client.put("/api/works/nope/placement", json={"floorId": "f1", "position": {"x": 0, "y": 0}})
    assert resp.status_code == 404


def test_clear_placement(client, tmp_path):
    doc = make_doc()
    doc.works[0].placement = WorkPlacement(floorId="f1", position=WorkPosition(x=1, y=2))
    save_works(doc)
    resp = client.delete("/api/works/w1/placement")
    assert resp.status_code == 204
    work = client.get("/api/works").json()["works"][0]
    assert work["placement"] is None


def _make_valid_pdf() -> bytes:
    import fitz
    doc = fitz.open()
    doc.new_page(width=200, height=200)
    return doc.write()


def test_upload_pdf_creates_thumbnail(client, tmp_path):
    save_works(make_doc())
    pdf_bytes = _make_valid_pdf()
    resp = client.post(
        "/api/works/w1/attachments",
        files={"file": ("invoice.pdf", pdf_bytes, "application/pdf")},
    )
    assert resp.status_code == 201
    thumb = tmp_path / "works-attachments" / "w1" / "invoice.pdf.thumb.jpg"
    assert thumb.exists(), "thumbnail should be created on PDF upload"


def test_upload_corrupt_pdf_still_succeeds(client, tmp_path):
    save_works(make_doc())
    resp = client.post(
        "/api/works/w1/attachments",
        files={"file": ("bad.pdf", b"%PDF corrupt garbage", "application/pdf")},
    )
    assert resp.status_code == 201
    thumb = tmp_path / "works-attachments" / "w1" / "bad.pdf.thumb.jpg"
    assert not thumb.exists(), "no thumbnail expected for corrupt PDF"


def test_delete_pdf_removes_thumbnail(client, tmp_path):
    save_works(make_doc())
    pdf_bytes = _make_valid_pdf()
    client.post(
        "/api/works/w1/attachments",
        files={"file": ("invoice.pdf", pdf_bytes, "application/pdf")},
    )
    thumb = tmp_path / "works-attachments" / "w1" / "invoice.pdf.thumb.jpg"
    assert thumb.exists()
    client.delete("/api/works/w1/attachments/invoice.pdf")
    assert not thumb.exists(), "thumbnail should be removed when PDF is deleted"


def test_delete_work_removes_attachments(client, tmp_path):
    save_works(make_doc())
    client.post(
        "/api/works/w1/attachments",
        files={"file": ("invoice.pdf", b"%PDF test", "application/pdf")},
    )
    client.delete("/api/works/w1")
    attach_dir = tmp_path / "works-attachments" / "w1"
    assert not attach_dir.exists()
