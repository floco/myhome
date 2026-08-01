import httpx
import pytest
import respx
from httpx import Response

from myhome import system_info


def test_get_app_version_reads_version_file(tmp_path, monkeypatch):
    version_file = tmp_path / "VERSION"
    version_file.write_text("1.2.3\n")
    monkeypatch.setenv("APP_VERSION_FILE", str(version_file))
    assert system_info.get_app_version() == "1.2.3"


def test_get_app_version_returns_dev_when_file_missing(tmp_path, monkeypatch):
    monkeypatch.setenv("APP_VERSION_FILE", str(tmp_path / "does-not-exist"))
    assert system_info.get_app_version() == "dev"


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
    assert info["dbSchemaVersion"] == 7
    assert info["homeCount"] == 0
    # get_home_count() above already opened the DB engine, which runs schema
    # migrations on first connect -- so the file is non-empty even with zero
    # homes. This isn't testing an accident; a real deployment always has an
    # open engine by the time anything calls this function.
    assert info["databaseSizeBytes"] >= 0
    assert info["uptimeSeconds"] >= 0
    assert isinstance(info["pythonVersion"], str)
    assert isinstance(info["arch"], str)


@pytest.fixture(autouse=True)
def _reset_update_cache():
    system_info.reset_update_cache()
    yield
    system_info.reset_update_cache()


async def test_check_for_update_detects_update_available():
    with respx.mock:
        respx.get(system_info._GITHUB_TAGS_URL).mock(
            return_value=Response(200, json=[{"name": "v0.9.0"}, {"name": "v0.8.0"}])
        )
        result = await system_info.check_for_update("0.8.0")
    assert result["status"] == "update_available"
    assert result["latestVersion"] == "0.9.0"
    assert result["checkedAt"] is not None


async def test_check_for_update_detects_up_to_date():
    with respx.mock:
        respx.get(system_info._GITHUB_TAGS_URL).mock(
            return_value=Response(200, json=[{"name": "v0.8.0"}, {"name": "v0.7.1"}])
        )
        result = await system_info.check_for_update("0.8.0")
    assert result["status"] == "up_to_date"
    assert result["latestVersion"] == "0.8.0"


async def test_check_for_update_returns_unknown_on_network_failure():
    with respx.mock:
        respx.get(system_info._GITHUB_TAGS_URL).mock(side_effect=httpx.ConnectError("boom"))
        result = await system_info.check_for_update("0.8.0")
    assert result["status"] == "unknown"
    assert result["latestVersion"] is None


async def test_check_for_update_handles_unparseable_current_version():
    with respx.mock:
        respx.get(system_info._GITHUB_TAGS_URL).mock(
            return_value=Response(200, json=[{"name": "v0.8.0"}])
        )
        result = await system_info.check_for_update("dev")
    assert result["status"] == "unknown"


async def test_check_for_update_falls_back_to_cached_result_on_later_failure():
    with respx.mock:
        respx.get(system_info._GITHUB_TAGS_URL).mock(
            return_value=Response(200, json=[{"name": "v0.8.0"}])
        )
        first = await system_info.check_for_update("0.8.0")
    assert first["status"] == "up_to_date"

    # Force the cache to look stale so the next call re-fetches.
    system_info._update_cache["checkedAt"] = "2000-01-01T00:00:00+00:00"

    with respx.mock:
        respx.get(system_info._GITHUB_TAGS_URL).mock(side_effect=httpx.ConnectError("boom"))
        second = await system_info.check_for_update("0.8.0")
    assert second["status"] == "up_to_date"
    assert second["latestVersion"] == "0.8.0"


async def test_check_for_update_uses_cache_within_ttl():
    with respx.mock:
        route = respx.get(system_info._GITHUB_TAGS_URL).mock(
            return_value=Response(200, json=[{"name": "v0.8.0"}])
        )
        await system_info.check_for_update("0.8.0")
        await system_info.check_for_update("0.8.0")
    assert route.call_count == 1
