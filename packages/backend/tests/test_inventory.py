import pytest
from fastapi.testclient import TestClient
from myhome.main import app
from myhome.models_inventory import InventoryDocument, InventoryItem, InventoryPlacement, InventoryPosition
from myhome.persistence_inventory import save_inventory


def make_doc() -> InventoryDocument:
    return InventoryDocument(
        items=[
            InventoryItem(
                id="i1",
                name="Samsung TV",
                emoji="📺",
                category="Electronics",
                purchasePrice=1200.0,
                warrantyExpiryDate="2026-05-12",
            )
        ]
    )


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    return TestClient(app)


# --- GET /api/inventory ---

def test_get_inventory_empty_when_no_file(client):
    resp = client.get("/api/inventory")
    assert resp.status_code == 200
    assert resp.json()["items"] == []


def test_get_inventory_returns_saved_data(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    save_inventory(make_doc())
    resp = TestClient(app).get("/api/inventory")
    assert resp.status_code == 200
    assert resp.json()["items"][0]["id"] == "i1"


# --- POST /api/inventory/items ---

def test_create_item(client):
    payload = {
        "name": "Washing machine",
        "emoji": "🧺",
        "category": "Appliance",
        "purchasePrice": 650.0,
    }
    resp = client.post("/api/inventory/items", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Washing machine"
    assert data["emoji"] == "🧺"
    assert data["purchasePrice"] == 650.0
    assert "id" in data
    assert data["placement"] is None
    # Verify persisted
    get = client.get("/api/inventory")
    assert any(i["name"] == "Washing machine" for i in get.json()["items"])


def test_create_item_defaults(client):
    resp = client.post("/api/inventory/items", json={"name": "Generic item"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["emoji"] == "📦"
    assert data["category"] == ""
    assert data["placement"] is None


# --- PUT /api/inventory/items/{id} ---

def test_update_item_partial(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    save_inventory(make_doc())
    c = TestClient(app)
    resp = c.put("/api/inventory/items/i1", json={"name": "LG TV", "purchasePrice": 900.0})
    assert resp.status_code == 204
    item = c.get("/api/inventory").json()["items"][0]
    assert item["name"] == "LG TV"
    assert item["purchasePrice"] == 900.0
    assert item["emoji"] == "📺"          # unchanged
    assert item["category"] == "Electronics"  # unchanged


def test_update_item_404(client):
    resp = client.put("/api/inventory/items/nonexistent", json={"name": "X"})
    assert resp.status_code == 404


# --- DELETE /api/inventory/items/{id} ---

def test_delete_item(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    save_inventory(make_doc())
    c = TestClient(app)
    resp = c.delete("/api/inventory/items/i1")
    assert resp.status_code == 204
    assert c.get("/api/inventory").json()["items"] == []


def test_delete_item_404(client):
    resp = client.delete("/api/inventory/items/nonexistent")
    assert resp.status_code == 404


# --- PUT /api/inventory/items/{id}/placement ---

def test_set_placement(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    save_inventory(make_doc())
    c = TestClient(app)
    payload = {
        "placement": {
            "floorId": "f1",
            "roomId": "r1",
            "position": {"x": 3.4, "y": 2.1},
        }
    }
    resp = c.put("/api/inventory/items/i1/placement", json=payload)
    assert resp.status_code == 204
    item = c.get("/api/inventory").json()["items"][0]
    assert item["placement"]["floorId"] == "f1"
    assert item["placement"]["position"]["x"] == 3.4
    assert item["placement"]["roomId"] == "r1"


def test_clear_placement(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    doc = make_doc()
    doc.items[0].placement = InventoryPlacement(
        floorId="f1", roomId="r1", position=InventoryPosition(x=1.0, y=2.0)
    )
    save_inventory(doc)
    c = TestClient(app)
    resp = c.put("/api/inventory/items/i1/placement", json={"placement": None})
    assert resp.status_code == 204
    assert c.get("/api/inventory").json()["items"][0]["placement"] is None


def test_placement_404(client):
    resp = client.put(
        "/api/inventory/items/nonexistent/placement",
        json={"placement": None},
    )
    assert resp.status_code == 404


# --- Attachment routes ---

def test_upload_attachment(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    save_inventory(make_doc())
    c = TestClient(app)
    resp = c.post(
        "/api/inventory/items/i1/attachments",
        files={"file": ("invoice.pdf", b"%PDF-1.4 content", "application/pdf")},
    )
    assert resp.status_code == 201
    assert resp.json()["filename"] == "invoice.pdf"
    item = c.get("/api/inventory").json()["items"][0]
    assert "invoice.pdf" in item["attachments"]


def test_upload_attachment_sanitises_filename(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    save_inventory(make_doc())
    c = TestClient(app)
    resp = c.post(
        "/api/inventory/items/i1/attachments",
        files={"file": ("my invoice 2025.pdf", b"%PDF test", "application/pdf")},
    )
    assert resp.status_code == 201
    assert resp.json()["filename"] == "my_invoice_2025.pdf"


def test_upload_attachment_multiple(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    save_inventory(make_doc())
    c = TestClient(app)
    c.post("/api/inventory/items/i1/attachments", files={"file": ("invoice.pdf", b"%PDF v1", "application/pdf")})
    c.post("/api/inventory/items/i1/attachments", files={"file": ("manual.pdf", b"%PDF v2", "application/pdf")})
    item = c.get("/api/inventory").json()["items"][0]
    assert "invoice.pdf" in item["attachments"]
    assert "manual.pdf" in item["attachments"]
    assert len(item["attachments"]) == 2


def test_upload_attachment_no_duplicate(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    save_inventory(make_doc())
    c = TestClient(app)
    c.post("/api/inventory/items/i1/attachments", files={"file": ("invoice.pdf", b"%PDF v1", "application/pdf")})
    c.post("/api/inventory/items/i1/attachments", files={"file": ("invoice.pdf", b"%PDF v2", "application/pdf")})
    item = c.get("/api/inventory").json()["items"][0]
    assert item["attachments"].count("invoice.pdf") == 1


def test_upload_attachment_rejects_unsupported_type(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    save_inventory(make_doc())
    c = TestClient(app)
    resp = c.post(
        "/api/inventory/items/i1/attachments",
        files={"file": ("malware.exe", b"\x4d\x5a", "application/octet-stream")},
    )
    assert resp.status_code == 400


def test_upload_attachment_item_not_found(client):
    resp = client.post(
        "/api/inventory/items/nope/attachments",
        files={"file": ("invoice.pdf", b"%PDF test", "application/pdf")},
    )
    assert resp.status_code == 404


def test_upload_attachment_invalid_id(client):
    resp = client.post(
        "/api/inventory/items/i!1/attachments",
        files={"file": ("invoice.pdf", b"%PDF test", "application/pdf")},
    )
    assert resp.status_code == 400


def test_get_attachment(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    save_inventory(make_doc())
    c = TestClient(app)
    c.post("/api/inventory/items/i1/attachments", files={"file": ("invoice.pdf", b"%PDF-1.4 content", "application/pdf")})
    resp = c.get("/api/inventory/items/i1/attachments/invoice.pdf")
    assert resp.status_code == 200
    assert "pdf" in resp.headers["content-type"]


def test_get_attachment_not_found(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    save_inventory(make_doc())
    resp = TestClient(app).get("/api/inventory/items/i1/attachments/nope.pdf")
    assert resp.status_code == 404


def test_get_attachment_invalid_id(client):
    resp = client.get("/api/inventory/items/i!1/attachments/invoice.pdf")
    assert resp.status_code == 400


def test_get_attachment_traversal_rejected(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    save_inventory(make_doc())
    resp = TestClient(app).get("/api/inventory/items/i1/attachments/.hidden")
    assert resp.status_code == 400


def test_delete_attachment(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    save_inventory(make_doc())
    c = TestClient(app)
    c.post("/api/inventory/items/i1/attachments", files={"file": ("invoice.pdf", b"%PDF test", "application/pdf")})
    resp = c.delete("/api/inventory/items/i1/attachments/invoice.pdf")
    assert resp.status_code == 204
    item = c.get("/api/inventory").json()["items"][0]
    assert "invoice.pdf" not in item["attachments"]


def test_delete_attachment_not_found(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    save_inventory(make_doc())
    resp = TestClient(app).delete("/api/inventory/items/i1/attachments/nope.pdf")
    assert resp.status_code == 404


def test_delete_attachment_traversal_rejected(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    save_inventory(make_doc())
    resp = TestClient(app).delete("/api/inventory/items/i1/attachments/.hidden")
    assert resp.status_code == 400


def test_delete_item_cascades_attachments(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    save_inventory(make_doc())
    c = TestClient(app)
    c.post("/api/inventory/items/i1/attachments", files={"file": ("invoice.pdf", b"%PDF test", "application/pdf")})
    c.delete("/api/inventory/items/i1")
    attach_dir = tmp_path / "inventory-attachments" / "i1"
    assert not attach_dir.exists()


def _make_valid_pdf() -> bytes:
    import fitz
    doc = fitz.open()
    doc.new_page(width=200, height=200)
    return doc.write()


def _item_id(client) -> str:
    resp = client.post("/api/inventory/items", json={"name": "TV"})
    return resp.json()["id"]


def test_inv_upload_jpeg_accepted(client):
    iid = _item_id(client)
    resp = client.post(
        f"/api/inventory/items/{iid}/attachments",
        files={"file": ("photo.jpg", b"\xff\xd8\xff" + b"\x00" * 50, "image/jpeg")},
    )
    assert resp.status_code == 201
    assert resp.json()["filename"] == "photo.jpg"
    item = next(i for i in client.get("/api/inventory").json()["items"] if i["id"] == iid)
    assert "photo.jpg" in item["attachments"]


def test_inv_upload_png_accepted(client):
    iid = _item_id(client)
    resp = client.post(
        f"/api/inventory/items/{iid}/attachments",
        files={"file": ("shot.png", b"\x89PNG" + b"\x00" * 50, "image/png")},
    )
    assert resp.status_code == 201
    assert resp.json()["filename"] == "shot.png"


def test_inv_upload_webp_accepted(client):
    iid = _item_id(client)
    resp = client.post(
        f"/api/inventory/items/{iid}/attachments",
        files={"file": ("photo.webp", b"RIFF" + b"\x00" * 50, "image/webp")},
    )
    assert resp.status_code == 201


def test_inv_sanitise_preserves_extension(client):
    iid = _item_id(client)
    resp = client.post(
        f"/api/inventory/items/{iid}/attachments",
        files={"file": ("my photo 2025.jpg", b"\xff\xd8\xff" + b"\x00" * 50, "image/jpeg")},
    )
    assert resp.status_code == 201
    assert resp.json()["filename"] == "my_photo_2025.jpg"


def test_inv_upload_pdf_creates_thumbnail(client, tmp_path):
    iid = _item_id(client)
    resp = client.post(
        f"/api/inventory/items/{iid}/attachments",
        files={"file": ("manual.pdf", _make_valid_pdf(), "application/pdf")},
    )
    assert resp.status_code == 201
    thumb = tmp_path / "inventory-attachments" / iid / "manual.pdf.thumb.jpg"
    assert thumb.exists()


def test_inv_delete_pdf_removes_thumbnail(client, tmp_path):
    iid = _item_id(client)
    client.post(
        f"/api/inventory/items/{iid}/attachments",
        files={"file": ("manual.pdf", _make_valid_pdf(), "application/pdf")},
    )
    thumb = tmp_path / "inventory-attachments" / iid / "manual.pdf.thumb.jpg"
    assert thumb.exists()
    client.delete(f"/api/inventory/items/{iid}/attachments/manual.pdf")
    assert not thumb.exists()


def test_inv_get_jpeg_returns_image_content_type(client):
    iid = _item_id(client)
    client.post(
        f"/api/inventory/items/{iid}/attachments",
        files={"file": ("photo.jpg", b"\xff\xd8\xff" + b"\x00" * 50, "image/jpeg")},
    )
    resp = client.get(f"/api/inventory/items/{iid}/attachments/photo.jpg")
    assert resp.status_code == 200
    assert "image/jpeg" in resp.headers["content-type"]
