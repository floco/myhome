from fastapi.testclient import TestClient

from myhome.main import app


def test_generic_attachment_upload_requires_auth(home_id):
    bare = TestClient(app)
    resp = bare.post(f"/api/homes/{home_id}/attachments/inventory/some-item", files={"file": ("photo.jpg", b"x", "image/jpeg")})
    assert resp.status_code == 401


def test_generic_attachment_get_requires_auth(home_id):
    bare = TestClient(app)
    resp = bare.get(f"/api/homes/{home_id}/attachments/inventory/some-item/photo.jpg")
    assert resp.status_code == 401


def test_generic_attachment_delete_requires_auth(home_id):
    bare = TestClient(app)
    resp = bare.delete(f"/api/homes/{home_id}/attachments/inventory/some-item/photo.jpg")
    assert resp.status_code == 401


def test_generic_attachment_upload_unknown_module_returns_404(client, home_id):
    item_id = client.post(f"/api/homes/{home_id}/inventory/items", json={"name": "Drill"}).json()["id"]
    resp = client.post(
        f"/api/homes/{home_id}/attachments/not-a-module/{item_id}",
        files={"file": ("photo.jpg", b"x", "image/jpeg")},
    )
    assert resp.status_code == 404
