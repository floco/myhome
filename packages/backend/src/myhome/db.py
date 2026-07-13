# packages/backend/src/myhome/db.py
"""Owns the SQLite engine for the persistence layer.

Engines are cached per resolved DATA_DIR path rather than as a single
process-wide singleton -- this is what lets tests, which
monkeypatch.setenv("DATA_DIR", str(tmp_path)) per test, transparently get
an isolated fresh database with no fixture changes. The cache is bounded
(_MAX_CACHED_ENGINES) so a long-running test suite that touches hundreds
of distinct tmp_path DATA_DIRs doesn't accumulate open SQLite file handles
forever; in a real deployment DATA_DIR never changes, so the cache holds
exactly one engine for the process lifetime.
"""
from __future__ import annotations

import os
from collections import OrderedDict
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine

from .migrations import run_migrations
from .schema import metadata

_MAX_CACHED_ENGINES = 8
_engines: "OrderedDict[str, Engine]" = OrderedDict()


def _db_path() -> Path:
    return Path(os.environ.get("DATA_DIR", "/data")) / "myhome.db"


def get_engine() -> Engine:
    path = str(_db_path())
    if path in _engines:
        _engines.move_to_end(path)
        return _engines[path]

    Path(path).parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{path}", connect_args={"check_same_thread": False})

    @event.listens_for(engine, "connect")
    def _set_pragmas(dbapi_conn, _record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    metadata.create_all(engine)
    run_migrations(engine)

    _engines[path] = engine
    if len(_engines) > _MAX_CACHED_ENGINES:
        _, evicted = _engines.popitem(last=False)
        evicted.dispose()
    return engine
