import stat

from myhome.main import _first_boot


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
