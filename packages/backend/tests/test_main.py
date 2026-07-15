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
