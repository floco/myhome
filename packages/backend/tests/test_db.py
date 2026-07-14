from sqlalchemy import text

from myhome.db import get_engine


def test_get_engine_creates_db_file(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    get_engine()
    assert (tmp_path / "myhome.db").exists()


def test_get_engine_returns_cached_instance_for_same_data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    assert get_engine() is get_engine()


def test_get_engine_sets_wal_mode(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    engine = get_engine()
    with engine.connect() as conn:
        mode = conn.execute(text("PRAGMA journal_mode")).scalar()
    assert mode == "wal"


def test_get_engine_enables_foreign_keys(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    engine = get_engine()
    with engine.connect() as conn:
        enabled = conn.execute(text("PRAGMA foreign_keys")).scalar()
    assert enabled == 1


def test_get_engine_bootstraps_schema_version(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    engine = get_engine()
    with engine.connect() as conn:
        version = conn.execute(text("SELECT version FROM schema_version")).scalar()
    assert version == 1


def test_get_engine_creates_separate_db_per_data_dir(tmp_path, monkeypatch):
    dir_a, dir_b = tmp_path / "a", tmp_path / "b"
    monkeypatch.setenv("DATA_DIR", str(dir_a))
    engine_a = get_engine()
    monkeypatch.setenv("DATA_DIR", str(dir_b))
    engine_b = get_engine()
    assert engine_a is not engine_b
    assert (dir_a / "myhome.db").exists()
    assert (dir_b / "myhome.db").exists()


def test_get_engine_evicts_oldest_beyond_cache_limit(tmp_path, monkeypatch):
    first_path = tmp_path / "dir0"
    monkeypatch.setenv("DATA_DIR", str(first_path))
    first_engine = get_engine()
    for i in range(1, 9):
        monkeypatch.setenv("DATA_DIR", str(tmp_path / f"dir{i}"))
        get_engine()
    monkeypatch.setenv("DATA_DIR", str(first_path))
    assert get_engine() is not first_engine
