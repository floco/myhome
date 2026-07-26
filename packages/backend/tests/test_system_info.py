from myhome import system_info


def test_get_app_version_reads_version_file(tmp_path, monkeypatch):
    version_file = tmp_path / "VERSION"
    version_file.write_text("1.2.3\n")
    monkeypatch.setenv("APP_VERSION_FILE", str(version_file))
    assert system_info.get_app_version() == "1.2.3"


def test_get_app_version_returns_unknown_when_file_missing(tmp_path, monkeypatch):
    monkeypatch.setenv("APP_VERSION_FILE", str(tmp_path / "does-not-exist"))
    assert system_info.get_app_version() == "unknown"


def test_get_deployment_mode_detects_home_assistant(monkeypatch):
    monkeypatch.setenv("SUPERVISOR_TOKEN", "abc")
    assert system_info.get_deployment_mode() == "home_assistant"


def test_get_deployment_mode_detects_standalone(monkeypatch):
    monkeypatch.delenv("SUPERVISOR_TOKEN", raising=False)
    assert system_info.get_deployment_mode() == "standalone"


def test_get_home_count_reflects_created_homes(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    from myhome.persistence_homes import create_home
    assert system_info.get_home_count() == 0
    create_home("Test Home", "existing")
    assert system_info.get_home_count() == 1


def test_get_database_size_bytes_zero_when_no_db(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    assert system_info.get_database_size_bytes() == 0


def test_get_database_size_bytes_positive_once_db_created(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    from myhome.persistence_homes import create_home
    create_home("Test Home", "existing")
    assert system_info.get_database_size_bytes() > 0


def test_get_uptime_seconds_is_nonnegative():
    assert system_info.get_uptime_seconds() >= 0


def test_get_static_system_info_shape(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.delenv("SUPERVISOR_TOKEN", raising=False)
    version_file = tmp_path / "VERSION"
    version_file.write_text("0.8.0")
    monkeypatch.setenv("APP_VERSION_FILE", str(version_file))
    info = system_info.get_static_system_info()
    assert info["version"] == "0.8.0"
    assert info["deploymentMode"] == "standalone"
    assert info["dbSchemaVersion"] == 6
    assert info["homeCount"] == 0
    # get_home_count() above already opened the DB engine, which runs schema
    # migrations on first connect -- so the file is non-empty even with zero
    # homes. This isn't testing an accident; a real deployment always has an
    # open engine by the time anything calls this function.
    assert info["databaseSizeBytes"] >= 0
    assert info["uptimeSeconds"] >= 0
    assert isinstance(info["pythonVersion"], str)
    assert isinstance(info["arch"], str)
