from fastapi.testclient import TestClient

from myhome.attachment_tokens import mint_download_token, mint_upload_token
from myhome.main import app


def test_upload_via_token_requires_no_auth_and_links_attachment(client, home_id):
    item_id = client.post(f"/api/homes/{home_id}/inventory/items", json={"name": "Drill"}).json()["id"]
    token, _expires_at = mint_upload_token(home_id, "inventory", item_id, "photo.jpg")

    bare = TestClient(app)
    resp = bare.post(f"/api/attachments/upload/{token}", content=b"fake-jpeg-bytes")
    assert resp.status_code == 201
    assert resp.json() == {"filename": "photo.jpg"}

    item = client.get(f"/api/homes/{home_id}/inventory").json()["items"][0]
    assert "photo.jpg" in item["attachments"]


def test_upload_via_token_is_single_use(client, home_id):
    item_id = client.post(f"/api/homes/{home_id}/inventory/items", json={"name": "Drill"}).json()["id"]
    token, _expires_at = mint_upload_token(home_id, "inventory", item_id, "photo.jpg")

    bare = TestClient(app)
    first = bare.post(f"/api/attachments/upload/{token}", content=b"fake-jpeg-bytes")
    assert first.status_code == 201
    second = bare.post(f"/api/attachments/upload/{token}", content=b"fake-jpeg-bytes")
    assert second.status_code == 404


def test_upload_via_token_unknown_item_raises(home_id):
    token, _expires_at = mint_upload_token(home_id, "inventory", "nonexistent", "photo.jpg")
    bare = TestClient(app)
    resp = bare.post(f"/api/attachments/upload/{token}", content=b"fake-jpeg-bytes")
    assert resp.status_code == 404


def test_download_via_token_requires_no_auth_and_serves_file(client, home_id):
    item_id = client.post(f"/api/homes/{home_id}/inventory/items", json={"name": "Drill"}).json()["id"]
    upload_token, _ = mint_upload_token(home_id, "inventory", item_id, "manual.pdf")
    bare = TestClient(app)
    bare.post(f"/api/attachments/upload/{upload_token}", content=b"%PDF-1.4 fake pdf")

    download_token, _ = mint_download_token(home_id, "inventory", item_id, "manual.pdf")
    resp = bare.get(f"/api/attachments/download/{download_token}")
    assert resp.status_code == 200
    assert resp.content == b"%PDF-1.4 fake pdf"
    assert resp.headers["content-type"] == "application/pdf"


def test_download_via_token_is_single_use(client, home_id):
    item_id = client.post(f"/api/homes/{home_id}/inventory/items", json={"name": "Drill"}).json()["id"]
    upload_token, _ = mint_upload_token(home_id, "inventory", item_id, "manual.pdf")
    bare = TestClient(app)
    bare.post(f"/api/attachments/upload/{upload_token}", content=b"%PDF-1.4 fake pdf")

    download_token, _ = mint_download_token(home_id, "inventory", item_id, "manual.pdf")
    first = bare.get(f"/api/attachments/download/{download_token}")
    assert first.status_code == 200
    second = bare.get(f"/api/attachments/download/{download_token}")
    assert second.status_code == 404


def test_download_via_token_missing_file_raises(home_id):
    token, _ = mint_download_token(home_id, "inventory", "some-item", "nonexistent.jpg")
    bare = TestClient(app)
    resp = bare.get(f"/api/attachments/download/{token}")
    assert resp.status_code == 404


def test_upload_via_unknown_token_raises():
    bare = TestClient(app)
    resp = bare.post("/api/attachments/upload/not-a-real-token", content=b"x")
    assert resp.status_code == 404


def test_download_via_unknown_token_raises():
    bare = TestClient(app)
    resp = bare.get("/api/attachments/download/not-a-real-token")
    assert resp.status_code == 404
