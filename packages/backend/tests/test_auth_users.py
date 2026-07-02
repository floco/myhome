import pytest


def test_list_users_as_admin(client):
    resp = client.get("/api/auth/users")
    assert resp.status_code == 200
    users = resp.json()
    assert any(u["username"] == "admin" for u in users)


def test_list_users_blocked_for_normal(ro_client):
    # ro_client is logged in as "rouser" (role=ro)
    resp = ro_client.get("/api/auth/users")
    assert resp.status_code == 403


def test_create_user_as_admin(client):
    resp = client.post("/api/auth/users", json={
        "username": "newbie",
        "password": "newbiepw99",
        "role": "normal",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["username"] == "newbie"
    assert data["role"] == "normal"
    assert "id" in data


def test_create_user_duplicate_username_returns_409(client):
    client.post("/api/auth/users", json={"username": "dup", "password": "dup12345", "role": "normal"})
    resp = client.post("/api/auth/users", json={"username": "DUP", "password": "dup12345", "role": "normal"})
    assert resp.status_code == 409


def test_create_user_short_password_returns_422(client):
    resp = client.post("/api/auth/users", json={"username": "x", "password": "short", "role": "normal"})
    assert resp.status_code == 422


def test_create_user_invalid_role_returns_422(client):
    resp = client.post("/api/auth/users", json={"username": "x", "password": "valid123", "role": "superuser"})
    assert resp.status_code == 422


def test_update_user_role_as_admin(client):
    create_resp = client.post("/api/auth/users", json={
        "username": "target", "password": "targetpw1", "role": "normal"
    })
    uid = create_resp.json()["id"]
    resp = client.put(f"/api/auth/users/{uid}", json={"role": "ro"})
    assert resp.status_code == 204
    users = client.get("/api/auth/users").json()
    target = next(u for u in users if u["id"] == uid)
    assert target["role"] == "ro"


def test_update_user_password_as_admin(client):
    create_resp = client.post("/api/auth/users", json={
        "username": "pwchange", "password": "oldpw1234", "role": "normal"
    })
    uid = create_resp.json()["id"]
    resp = client.put(f"/api/auth/users/{uid}", json={"password": "newpw9876"})
    assert resp.status_code == 204


def test_delete_user_as_admin(client):
    create_resp = client.post("/api/auth/users", json={
        "username": "todelete", "password": "todelete1", "role": "normal"
    })
    uid = create_resp.json()["id"]
    resp = client.delete(f"/api/auth/users/{uid}")
    assert resp.status_code == 204
    users = client.get("/api/auth/users").json()
    assert not any(u["id"] == uid for u in users)


def test_delete_self_returns_400(client):
    me = client.get("/api/auth/me").json()
    resp = client.delete(f"/api/auth/users/{me['id']}")
    assert resp.status_code == 400


def test_delete_user_cascades_tokens(client):
    create_resp = client.post("/api/auth/users", json={
        "username": "tokenowner", "password": "tokenown1", "role": "normal"
    })
    uid = create_resp.json()["id"]
    client.delete(f"/api/auth/users/{uid}")
    users = client.get("/api/auth/users").json()
    assert not any(u["id"] == uid for u in users)
