import stat

from fastapi.testclient import TestClient

from myhome.main import _first_boot, app


def test_first_boot_writes_password_file_not_stdout(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    _first_boot()

    password_file = tmp_path / ".initial-admin-password"
    assert password_file.exists()
    password = password_file.read_text().strip()
    assert len(password) > 8

    captured = capsys.readouterr()
    assert password not in captured.out
    assert "First boot" in captured.out

    mode = stat.S_IMODE(password_file.stat().st_mode)
    assert mode == 0o600


def test_first_boot_is_noop_when_users_already_exist(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    _first_boot()
    password_file = tmp_path / ".initial-admin-password"
    first_password = password_file.read_text()

    password_file.unlink()
    _first_boot()

    assert not password_file.exists()
    assert first_password  # sanity: first boot did generate something


def test_non_api_paths_are_not_gated_by_auth_middleware(tmp_path, monkeypatch):
    # A completely fresh visitor (no cookies at all -- e.g. Home Assistant's
    # ingress proxy, which never carries our own session cookies) must still
    # be able to load the SPA shell/static assets, since that's the only way
    # the login page itself can ever render. Only /api/* and /mcp are
    # protected; the client-side app is what decides to show the login
    # screen once its own calls to /api/auth/me come back 401.
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("SECRET_KEY", "test-secret-key-for-tests-only")
    tc = TestClient(app)
    resp = tc.get("/")
    assert resp.status_code != 401
    assert resp.json() != {"detail": "Authentication required"}


def test_api_paths_still_require_auth(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("SECRET_KEY", "test-secret-key-for-tests-only")
    tc = TestClient(app)
    resp = tc.get("/api/homes")
    assert resp.status_code == 401
    assert resp.json() == {"detail": "Authentication required"}


def test_ingress_trust_silently_authenticates_and_sets_cookies(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("SECRET_KEY", "test-secret-key-for-tests-only")
    monkeypatch.setenv("SUPERVISOR_TOKEN", "test-token")
    _first_boot()
    tc = TestClient(app, client=("172.30.32.2", 12345))

    resp = tc.get("/api/auth/me", headers={
        "X-Remote-User-Id": "ha-1",
        "X-Remote-User-Name": "jane",
        "X-Remote-User-Display-Name": "Jane Doe",
    })

    assert resp.status_code == 200
    assert resp.json()["username"] == "jane"
    assert resp.json()["role"] == "admin"  # first-ever ingress login
    assert "myhome_access" in resp.cookies
    assert "myhome_refresh" in resp.cookies


def test_ingress_trust_does_not_apply_without_supervisor_token(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("SECRET_KEY", "test-secret-key-for-tests-only")
    monkeypatch.delenv("SUPERVISOR_TOKEN", raising=False)
    tc = TestClient(app, client=("172.30.32.2", 12345))

    resp = tc.get("/api/auth/me", headers={
        "X-Remote-User-Id": "ha-1",
        "X-Remote-User-Name": "jane",
        "X-Remote-User-Display-Name": "Jane Doe",
    })

    assert resp.status_code == 401


def test_ingress_trust_does_not_apply_from_wrong_source_ip(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("SECRET_KEY", "test-secret-key-for-tests-only")
    monkeypatch.setenv("SUPERVISOR_TOKEN", "test-token")
    tc = TestClient(app, client=("10.0.0.5", 12345))

    resp = tc.get("/api/auth/me", headers={
        "X-Remote-User-Id": "ha-1",
        "X-Remote-User-Name": "jane",
        "X-Remote-User-Display-Name": "Jane Doe",
    })

    assert resp.status_code == 401


def test_ingress_trust_session_persists_via_cookie_on_next_request(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("SECRET_KEY", "test-secret-key-for-tests-only")
    monkeypatch.setenv("SUPERVISOR_TOKEN", "test-token")
    tc = TestClient(app, client=("172.30.32.2", 12345))

    first = tc.get("/api/auth/me", headers={
        "X-Remote-User-Id": "ha-1",
        "X-Remote-User-Name": "jane",
        "X-Remote-User-Display-Name": "Jane Doe",
    })
    assert first.status_code == 200

    # No ingress headers this time -- must still work purely off the cookie
    # the first request set.
    second = tc.get("/api/auth/me")
    assert second.status_code == 200
    assert second.json()["username"] == "jane"
