import pytest
from myhome.models_properties import Property, PropertiesDocument
from myhome.persistence_properties import save_properties


def make_doc() -> PropertiesDocument:
    return PropertiesDocument(
        properties=[Property(id="p1", name="Casa da Rua das Flores", type="house", status="watching")]
    )


def test_get_properties_empty_when_none(client, home_id):
    resp = client.get(f"/api/homes/{home_id}/properties")
    assert resp.status_code == 200
    assert resp.json()["properties"] == []


def test_get_properties_returns_saved_data(client, home_id):
    save_properties(home_id, make_doc())
    resp = client.get(f"/api/homes/{home_id}/properties")
    assert resp.status_code == 200
    assert resp.json()["properties"][0]["id"] == "p1"


def test_create_property(client, home_id):
    payload = {"name": "Terreno Norte", "type": "land"}
    resp = client.post(f"/api/homes/{home_id}/properties", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Terreno Norte"
    assert data["type"] == "land"
    assert data["status"] == "watching"
    assert data["emoji"] == "🏠"
    assert data["pros"] == []
    assert data["cons"] == []
    assert data["attachments"] == []
    assert "id" in data
    assert len(client.get(f"/api/homes/{home_id}/properties").json()["properties"]) == 1


def test_create_property_full_fields(client, home_id):
    payload = {
        "name": "Casa Sul",
        "emoji": "🏡",
        "type": "house",
        "status": "visited",
        "locationId": "loc1",
        "address": "Rua Sul 5",
        "price": 250000.0,
        "landSize": 500.0,
        "builtSize": 180.0,
        "bedrooms": 3,
        "bathrooms": 2,
        "listingUrl": "https://example.com/listing",
        "contact": "Maria, +351 912 345 678",
        "pros": ["Great light", "Walk to town"],
        "cons": ["No garage"],
        "notes": "Needs a new roof",
    }
    resp = client.post(f"/api/homes/{home_id}/properties", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["price"] == 250000.0
    assert data["locationId"] == "loc1"
    assert data["pros"] == ["Great light", "Walk to town"]
    assert data["cons"] == ["No garage"]
    assert data["bedrooms"] == 3


def test_update_property_partial(client, home_id):
    save_properties(home_id, make_doc())
    resp = client.put(f"/api/homes/{home_id}/properties/p1", json={"status": "visited", "price": 250000.0})
    assert resp.status_code == 204
    item = client.get(f"/api/homes/{home_id}/properties").json()["properties"][0]
    assert item["status"] == "visited"
    assert item["price"] == 250000.0
    assert item["name"] == "Casa da Rua das Flores"  # unchanged


def test_update_property_404(client, home_id):
    resp = client.put(f"/api/homes/{home_id}/properties/nope", json={"status": "visited"})
    assert resp.status_code == 404


def test_delete_property(client, home_id):
    save_properties(home_id, make_doc())
    resp = client.delete(f"/api/homes/{home_id}/properties/p1")
    assert resp.status_code == 204
    assert client.get(f"/api/homes/{home_id}/properties").json()["properties"] == []


def test_delete_property_404(client, home_id):
    resp = client.delete(f"/api/homes/{home_id}/properties/nope")
    assert resp.status_code == 404


def test_upload_invalid_id_rejected(client, home_id):
    save_properties(home_id, make_doc())
    resp = client.post(
        f"/api/homes/{home_id}/properties/p!1/attachments",
        files={"file": ("listing.pdf", b"%PDF test", "application/pdf")},
    )
    assert resp.status_code == 400


def test_get_attachment_traversal_rejected(client, home_id):
    save_properties(home_id, make_doc())
    resp = client.get(f"/api/homes/{home_id}/properties/p1/attachments/.hidden")
    assert resp.status_code == 400


def test_delete_attachment_traversal_rejected(client, home_id):
    save_properties(home_id, make_doc())
    resp = client.delete(f"/api/homes/{home_id}/properties/p1/attachments/.hidden")
    assert resp.status_code == 400


def test_upload_attachment(client, home_id):
    save_properties(home_id, make_doc())
    resp = client.post(
        f"/api/homes/{home_id}/properties/p1/attachments",
        files={"file": ("listing.pdf", b"%PDF-1.4 test", "application/pdf")},
    )
    assert resp.status_code == 201
    assert resp.json()["filename"] == "listing.pdf"
    item = client.get(f"/api/homes/{home_id}/properties").json()["properties"][0]
    assert "listing.pdf" in item["attachments"]


def test_upload_sanitises_filename(client, home_id):
    save_properties(home_id, make_doc())
    resp = client.post(
        f"/api/homes/{home_id}/properties/p1/attachments",
        files={"file": ("my listing 2025.pdf", b"%PDF test", "application/pdf")},
    )
    assert resp.status_code == 201
    assert resp.json()["filename"] == "my_listing_2025.pdf"


def test_upload_unsupported_type_rejected(client, home_id):
    save_properties(home_id, make_doc())
    resp = client.post(
        f"/api/homes/{home_id}/properties/p1/attachments",
        files={"file": ("notes.txt", b"hello", "text/plain")},
    )
    assert resp.status_code == 400


def test_upload_image_jpeg_accepted(client, home_id):
    save_properties(home_id, make_doc())
    resp = client.post(
        f"/api/homes/{home_id}/properties/p1/attachments",
        files={"file": ("photo.jpg", b"\xff\xd8\xff\xe0" + b"\x00" * 100, "image/jpeg")},
    )
    assert resp.status_code == 201
    item = client.get(f"/api/homes/{home_id}/properties").json()["properties"][0]
    assert "photo.jpg" in item["attachments"]


def test_upload_attachment_property_not_found(client, home_id):
    resp = client.post(
        f"/api/homes/{home_id}/properties/nope/attachments",
        files={"file": ("listing.pdf", b"%PDF test", "application/pdf")},
    )
    assert resp.status_code == 404


def test_get_attachment(client, home_id):
    save_properties(home_id, make_doc())
    client.post(
        f"/api/homes/{home_id}/properties/p1/attachments",
        files={"file": ("listing.pdf", b"%PDF-1.4 test content", "application/pdf")},
    )
    resp = client.get(f"/api/homes/{home_id}/properties/p1/attachments/listing.pdf")
    assert resp.status_code == 200
    assert "pdf" in resp.headers["content-type"]


def test_get_attachment_not_found(client, home_id):
    save_properties(home_id, make_doc())
    resp = client.get(f"/api/homes/{home_id}/properties/p1/attachments/nope.pdf")
    assert resp.status_code == 404


def test_delete_attachment(client, home_id):
    save_properties(home_id, make_doc())
    client.post(
        f"/api/homes/{home_id}/properties/p1/attachments",
        files={"file": ("listing.pdf", b"%PDF test", "application/pdf")},
    )
    resp = client.delete(f"/api/homes/{home_id}/properties/p1/attachments/listing.pdf")
    assert resp.status_code == 204
    item = client.get(f"/api/homes/{home_id}/properties").json()["properties"][0]
    assert "listing.pdf" not in item["attachments"]


def test_delete_attachment_not_found(client, home_id):
    save_properties(home_id, make_doc())
    resp = client.delete(f"/api/homes/{home_id}/properties/p1/attachments/nope.pdf")
    assert resp.status_code == 404


def test_delete_property_removes_attachments(client, tmp_path, home_id):
    save_properties(home_id, make_doc())
    client.post(
        f"/api/homes/{home_id}/properties/p1/attachments",
        files={"file": ("listing.pdf", b"%PDF test", "application/pdf")},
    )
    client.delete(f"/api/homes/{home_id}/properties/p1")
    attach_dir = tmp_path / "homes" / home_id / "properties-attachments" / "p1"
    assert not attach_dir.exists()


def _make_valid_pdf() -> bytes:
    import fitz
    doc = fitz.open()
    doc.new_page(width=200, height=200)
    return doc.write()


def test_upload_pdf_creates_thumbnail(client, tmp_path, home_id):
    save_properties(home_id, make_doc())
    pdf_bytes = _make_valid_pdf()
    resp = client.post(
        f"/api/homes/{home_id}/properties/p1/attachments",
        files={"file": ("listing.pdf", pdf_bytes, "application/pdf")},
    )
    assert resp.status_code == 201
    thumb = tmp_path / "homes" / home_id / "properties-attachments" / "p1" / "listing.pdf.thumb.jpg"
    assert thumb.exists(), "thumbnail should be created on PDF upload"
