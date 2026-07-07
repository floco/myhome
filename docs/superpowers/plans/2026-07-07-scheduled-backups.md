# Automated Scheduled Backups Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a scheduled backup job (daily/weekly/monthly, configurable retention) that writes backups to disk automatically, prunes old ones, and is browsable/downloadable/deletable from Settings, alongside a "Run backup now" manual trigger.

**Architecture:** A new `persistence_backup.py` owns backup config/state persistence and the actual zip-creation/listing/pruning/deletion logic (shared by both the scheduler and the manual "run now" route). A second independent `asyncio` background loop (`backup_scheduler.py`), structurally identical to the existing `notification_scheduler.py`, polls every 60 seconds. The existing manual `download_backup()` is refactored to share the same file-selection logic so it correctly excludes the new `backups/` subdirectory from its own contents.

**Tech Stack:** FastAPI, Pydantic, pytest, Svelte 5, Vitest.

**Reference spec:** `docs/superpowers/specs/2026-07-07-scheduled-backups-design.md`

---

## Task 1: `BackupConfig` / `BackupEntry` / `BackupState` models

**Files:**
- Create: `packages/backend/src/myhome/models_backup.py`
- Test: `packages/backend/tests/test_backup_persistence.py` (new)

- [ ] **Step 1: Write the failing test**

Create `packages/backend/tests/test_backup_persistence.py`:

```python
from myhome.models_backup import BackupConfig, BackupEntry, BackupState


def test_backup_config_defaults():
    config = BackupConfig()
    assert config.enabled is False
    assert config.frequency == "daily"
    assert config.time == "03:00"
    assert config.dayOfWeek == 7
    assert config.dayOfMonth == 1
    assert config.retentionCount == 7


def test_backup_entry_requires_fields():
    entry = BackupEntry(filename="myhome-backup-20260707-030000.zip", createdAt="2026-07-07T03:00:00+00:00", sizeBytes=1024)
    assert entry.sizeBytes == 1024


def test_backup_state_defaults():
    assert BackupState().lastRunDate is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/backend && pytest tests/test_backup_persistence.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'myhome.models_backup'`

- [ ] **Step 3: Write minimal implementation**

Create `packages/backend/src/myhome/models_backup.py`:

```python
from __future__ import annotations
from typing import Literal
from pydantic import BaseModel


class BackupConfig(BaseModel):
    enabled: bool = False
    frequency: Literal["daily", "weekly", "monthly"] = "daily"
    time: str = "03:00"
    dayOfWeek: int = 7
    dayOfMonth: int = 1
    retentionCount: int = 7


class BackupEntry(BaseModel):
    filename: str
    createdAt: str
    sizeBytes: int


class BackupState(BaseModel):
    lastRunDate: str | None = None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd packages/backend && pytest tests/test_backup_persistence.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add packages/backend/src/myhome/models_backup.py packages/backend/tests/test_backup_persistence.py
git commit -m "feat: add BackupConfig, BackupEntry, BackupState models"
```

---

## Task 2: Backup config/state persistence

**Files:**
- Create: `packages/backend/src/myhome/persistence_backup.py`
- Test: `packages/backend/tests/test_backup_persistence.py`

- [ ] **Step 1: Write the failing test**

Add to `packages/backend/tests/test_backup_persistence.py`:

```python
from myhome.persistence_backup import (
    load_backup_config,
    load_backup_state,
    save_backup_config,
    save_backup_state,
)


def test_load_backup_config_returns_defaults_when_no_file(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    config = load_backup_config()
    assert config.enabled is False
    assert config.retentionCount == 7


def test_save_and_load_backup_config_round_trips(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    save_backup_config(BackupConfig(enabled=True, frequency="weekly", dayOfWeek=3, retentionCount=14))
    config = load_backup_config()
    assert config.enabled is True
    assert config.frequency == "weekly"
    assert config.dayOfWeek == 3
    assert config.retentionCount == 14


def test_load_backup_state_returns_defaults_when_no_file(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    assert load_backup_state().lastRunDate is None


def test_save_and_load_backup_state_round_trips(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    save_backup_state(BackupState(lastRunDate="2026-07-07"))
    assert load_backup_state().lastRunDate == "2026-07-07"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/backend && pytest tests/test_backup_persistence.py -v -k "config_persist or state_persist or returns_defaults or round_trips"`
Expected: FAIL with `ModuleNotFoundError: No module named 'myhome.persistence_backup'`

- [ ] **Step 3: Write minimal implementation**

Create `packages/backend/src/myhome/persistence_backup.py`:

```python
import json
import os
from pathlib import Path

from .models_backup import BackupConfig, BackupState


def _data_dir() -> Path:
    return Path(os.environ.get("DATA_DIR", "/data"))


def _backups_dir() -> Path:
    return _data_dir() / "backups"


def _config_file() -> Path:
    return _data_dir() / "backup_config.json"


def _state_file() -> Path:
    return _data_dir() / "backup_state.json"


def load_backup_config() -> BackupConfig:
    path = _config_file()
    if not path.exists():
        return BackupConfig()
    with path.open() as f:
        return BackupConfig.model_validate(json.load(f))


def save_backup_config(config: BackupConfig) -> None:
    path = _config_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with tmp.open("w") as f:
        json.dump(config.model_dump(), f, indent=2)
    tmp.replace(path)


def load_backup_state() -> BackupState:
    path = _state_file()
    if not path.exists():
        return BackupState()
    with path.open() as f:
        return BackupState.model_validate(json.load(f))


def save_backup_state(state: BackupState) -> None:
    path = _state_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with tmp.open("w") as f:
        json.dump(state.model_dump(), f, indent=2)
    tmp.replace(path)
```

Add the `BackupConfig` import at the top of the test file:

```python
from myhome.models_backup import BackupConfig, BackupEntry, BackupState
```

(This import already exists from Task 1 — just confirm `BackupConfig` is in the import list before running.)

- [ ] **Step 4: Run test to verify it passes**

Run: `cd packages/backend && pytest tests/test_backup_persistence.py -v`
Expected: PASS (7 tests total)

- [ ] **Step 5: Commit**

```bash
git add packages/backend/src/myhome/persistence_backup.py packages/backend/tests/test_backup_persistence.py
git commit -m "feat: add backup config/state persistence"
```

---

## Task 3: Shared file-selection helper + fix `download_backup` to exclude `backups/`

**Files:**
- Modify: `packages/backend/src/myhome/persistence_backup.py`
- Modify: `packages/backend/src/myhome/routes/backup.py`
- Test: `packages/backend/tests/test_backup.py`

- [ ] **Step 1: Write the failing test**

Add to `packages/backend/tests/test_backup.py`:

```python
def test_download_backup_excludes_scheduled_backups_directory(client, tmp_path):
    (tmp_path / "house.json").write_text('{"floors": []}')
    backups_dir = tmp_path / "backups"
    backups_dir.mkdir()
    (backups_dir / "myhome-backup-20260101-000000.zip").write_bytes(b"old-backup-content")

    resp = client.get("/api/backup/download")

    names = zipfile.ZipFile(io.BytesIO(resp.content)).namelist()
    assert "house.json" in names
    assert not any(n.startswith("backups/") for n in names)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/backend && pytest tests/test_backup.py -v -k excludes_scheduled_backups_directory`
Expected: FAIL — `backups/myhome-backup-20260101-000000.zip` appears in `names`

- [ ] **Step 3: Write minimal implementation**

Add to `packages/backend/src/myhome/persistence_backup.py` (after the imports, before the config functions):

```python
from collections.abc import Iterator


def iter_backup_files(data_dir: Path, exclude_dirs: frozenset[str] = frozenset()) -> Iterator[tuple[Path, Path]]:
    if not data_dir.exists():
        return
    resolved_root = data_dir.resolve()
    for path in data_dir.rglob("*"):
        if path.is_symlink() or not path.is_file():
            continue
        if not path.resolve().is_relative_to(resolved_root):
            continue
        rel = path.relative_to(data_dir)
        if rel.parts and rel.parts[0] in exclude_dirs:
            continue
        yield path, rel
```

Update `packages/backend/src/myhome/routes/backup.py`'s `download_backup()` to use it:

```python
from ..persistence_backup import iter_backup_files
```

```python
@router.get("/api/backup/download")
def download_backup() -> StreamingResponse:
    data_dir = _data_dir()
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for path, rel in iter_backup_files(data_dir, exclude_dirs=frozenset({"backups"})):
            zf.write(path, rel)
    buf.seek(0)
    filename = f"myhome-backup-{date.today().isoformat()}.zip"
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
```

This replaces the old inline `for path in data_dir.rglob("*"): ...` loop in `download_backup()` entirely — delete the old loop body along with the `resolved_root = data_dir.resolve()` line that preceded it in that function (the resolution logic now lives in `iter_backup_files`).

- [ ] **Step 4: Run test to verify it passes**

Run: `cd packages/backend && pytest tests/test_backup.py -v`
Expected: PASS (all tests in the file, including the pre-existing ones — confirms the refactor didn't change behavior for the non-`backups/` case)

- [ ] **Step 5: Commit**

```bash
git add packages/backend/src/myhome/persistence_backup.py packages/backend/src/myhome/routes/backup.py packages/backend/tests/test_backup.py
git commit -m "fix: exclude backups/ directory from manual backup download"
```

---

## Task 4: `create_backup()` + `list_backups()` + pruning

**Files:**
- Modify: `packages/backend/src/myhome/persistence_backup.py`
- Test: `packages/backend/tests/test_backup_persistence.py`

- [ ] **Step 1: Write the failing test**

Add to `packages/backend/tests/test_backup_persistence.py`:

```python
import zipfile

from myhome.persistence_backup import create_backup, list_backups


def test_create_backup_writes_zip_and_excludes_backups_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    (tmp_path / "house.json").write_text('{"floors": []}')

    entry = create_backup()

    assert entry.filename.startswith("myhome-backup-")
    assert entry.filename.endswith(".zip")
    assert entry.sizeBytes > 0

    backup_path = tmp_path / "backups" / entry.filename
    assert backup_path.exists()
    names = zipfile.ZipFile(backup_path).namelist()
    assert "house.json" in names
    assert not any(n.startswith("backups/") for n in names)


def test_create_backup_prunes_to_retention_count(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    save_backup_config(BackupConfig(retentionCount=2))
    backups_dir = tmp_path / "backups"
    backups_dir.mkdir()
    (backups_dir / "myhome-backup-20260101-000000.zip").write_bytes(b"a")
    (backups_dir / "myhome-backup-20260102-000000.zip").write_bytes(b"b")
    (backups_dir / "myhome-backup-20260103-000000.zip").write_bytes(b"c")

    create_backup()  # 4th backup, timestamped "now" -- definitely the newest

    entries = list_backups()
    assert len(entries) == 2
    filenames = {e.filename for e in entries}
    assert "myhome-backup-20260101-000000.zip" not in filenames
    assert "myhome-backup-20260102-000000.zip" not in filenames
    assert "myhome-backup-20260103-000000.zip" in filenames  # 2nd-newest survives


def test_list_backups_sorted_newest_first(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    backups_dir = tmp_path / "backups"
    backups_dir.mkdir()
    (backups_dir / "myhome-backup-20260101-000000.zip").write_bytes(b"a")
    (backups_dir / "myhome-backup-20260301-000000.zip").write_bytes(b"b")
    (backups_dir / "myhome-backup-20260201-000000.zip").write_bytes(b"c")

    entries = list_backups()
    assert [e.filename for e in entries] == [
        "myhome-backup-20260301-000000.zip",
        "myhome-backup-20260201-000000.zip",
        "myhome-backup-20260101-000000.zip",
    ]


def test_list_backups_empty_when_no_backups_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    assert list_backups() == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/backend && pytest tests/test_backup_persistence.py -v -k "create_backup or list_backups"`
Expected: FAIL with `ImportError: cannot import name 'create_backup'`

- [ ] **Step 3: Write minimal implementation**

Add to `packages/backend/src/myhome/persistence_backup.py`:

```python
import re
from datetime import datetime, timezone

from .models_backup import BackupEntry

_FILENAME_RE = re.compile(r"^myhome-backup-(\d{8})-(\d{6})\.zip$")


def _parse_backup_filename(filename: str) -> datetime | None:
    m = _FILENAME_RE.match(filename)
    if not m:
        return None
    date_part, time_part = m.groups()
    return datetime.strptime(date_part + time_part, "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc)


def list_backups() -> list[BackupEntry]:
    backups_dir = _backups_dir()
    if not backups_dir.exists():
        return []
    entries: list[BackupEntry] = []
    for path in backups_dir.glob("myhome-backup-*.zip"):
        dt = _parse_backup_filename(path.name)
        if dt is None:
            continue
        entries.append(BackupEntry(filename=path.name, createdAt=dt.isoformat(), sizeBytes=path.stat().st_size))
    entries.sort(key=lambda e: e.filename, reverse=True)
    return entries


def _prune_backups(retention_count: int) -> None:
    for entry in list_backups()[retention_count:]:
        (_backups_dir() / entry.filename).unlink(missing_ok=True)


def create_backup() -> BackupEntry:
    data_dir = _data_dir()
    backups_dir = _backups_dir()
    backups_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    filename = f"myhome-backup-{timestamp}.zip"
    path = backups_dir / filename
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        for file_path, rel in iter_backup_files(data_dir, exclude_dirs=frozenset({"backups"})):
            zf.write(file_path, rel)
    entry = BackupEntry(
        filename=filename,
        createdAt=datetime.now(timezone.utc).isoformat(),
        sizeBytes=path.stat().st_size,
    )
    config = load_backup_config()
    _prune_backups(config.retentionCount)
    return entry
```

Add `import zipfile` to the top of `persistence_backup.py` alongside the existing `import json` / `import os` lines.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd packages/backend && pytest tests/test_backup_persistence.py -v`
Expected: PASS (all tests in the file)

- [ ] **Step 5: Commit**

```bash
git add packages/backend/src/myhome/persistence_backup.py packages/backend/tests/test_backup_persistence.py
git commit -m "feat: add create_backup, list_backups, and retention pruning"
```

---

## Task 5: `get_backup_path()` + `delete_backup()`

**Files:**
- Modify: `packages/backend/src/myhome/persistence_backup.py`
- Test: `packages/backend/tests/test_backup_persistence.py`

- [ ] **Step 1: Write the failing test**

Add to `packages/backend/tests/test_backup_persistence.py`:

```python
from myhome.persistence_backup import delete_backup, get_backup_path


def test_get_backup_path_rejects_invalid_filename(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    assert get_backup_path("../etc/passwd") is None
    assert get_backup_path("not-a-backup.zip") is None


def test_get_backup_path_returns_none_for_missing_file(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    assert get_backup_path("myhome-backup-20260101-000000.zip") is None


def test_get_backup_path_returns_path_for_existing_file(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    (tmp_path / "house.json").write_text("{}")
    entry = create_backup()
    path = get_backup_path(entry.filename)
    assert path is not None
    assert path.exists()


def test_delete_backup_removes_file(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    (tmp_path / "house.json").write_text("{}")
    entry = create_backup()
    assert delete_backup(entry.filename) is True
    assert not (tmp_path / "backups" / entry.filename).exists()


def test_delete_backup_returns_false_for_missing_file(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    assert delete_backup("myhome-backup-20260101-000000.zip") is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/backend && pytest tests/test_backup_persistence.py -v -k "get_backup_path or delete_backup"`
Expected: FAIL with `ImportError: cannot import name 'get_backup_path'`

- [ ] **Step 3: Write minimal implementation**

Add to `packages/backend/src/myhome/persistence_backup.py`:

```python
def get_backup_path(filename: str) -> Path | None:
    if _parse_backup_filename(filename) is None:
        return None
    path = _backups_dir() / filename
    if not path.exists():
        return None
    return path


def delete_backup(filename: str) -> bool:
    path = get_backup_path(filename)
    if path is None:
        return False
    path.unlink()
    return True
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd packages/backend && pytest tests/test_backup_persistence.py -v`
Expected: PASS (full file)

- [ ] **Step 5: Commit**

```bash
git add packages/backend/src/myhome/persistence_backup.py packages/backend/tests/test_backup_persistence.py
git commit -m "feat: add get_backup_path and delete_backup"
```

---

## Task 6: Routes — config, scheduled list, run-now, download-one, delete

**Files:**
- Modify: `packages/backend/src/myhome/routes/backup.py`
- Test: `packages/backend/tests/test_backup.py`

- [ ] **Step 1: Write the failing test**

Add to `packages/backend/tests/test_backup.py`:

```python
def test_get_backup_config_returns_defaults(client):
    resp = client.get("/api/backup/config")
    assert resp.status_code == 200
    data = resp.json()
    assert data["enabled"] is False
    assert data["frequency"] == "daily"


def test_put_backup_config_round_trips(client):
    resp = client.put("/api/backup/config", json={
        "enabled": True, "frequency": "monthly", "time": "04:30",
        "dayOfWeek": 7, "dayOfMonth": 15, "retentionCount": 10,
    })
    assert resp.status_code == 200
    data = client.get("/api/backup/config").json()
    assert data["frequency"] == "monthly"
    assert data["dayOfMonth"] == 15
    assert data["retentionCount"] == 10


def test_run_backup_now_creates_entry_and_appears_in_list(client, tmp_path):
    (tmp_path / "house.json").write_text("{}")
    resp = client.post("/api/backup/scheduled/run")
    assert resp.status_code == 200
    entry = resp.json()
    assert entry["filename"].startswith("myhome-backup-")

    list_resp = client.get("/api/backup/scheduled")
    filenames = [e["filename"] for e in list_resp.json()]
    assert entry["filename"] in filenames


def test_download_scheduled_backup_returns_the_file(client, tmp_path):
    (tmp_path / "house.json").write_text('{"marker": true}')
    entry = client.post("/api/backup/scheduled/run").json()

    resp = client.get(f"/api/backup/scheduled/{entry['filename']}/download")
    assert resp.status_code == 200
    names = zipfile.ZipFile(io.BytesIO(resp.content)).namelist()
    assert "house.json" in names


def test_download_scheduled_backup_404_for_unknown_filename(client):
    resp = client.get("/api/backup/scheduled/myhome-backup-20260101-000000.zip/download")
    assert resp.status_code == 404


def test_download_scheduled_backup_404_for_invalid_filename(client):
    resp = client.get("/api/backup/scheduled/not-a-backup.zip/download")
    assert resp.status_code == 404


def test_delete_scheduled_backup(client, tmp_path):
    (tmp_path / "house.json").write_text("{}")
    entry = client.post("/api/backup/scheduled/run").json()

    resp = client.delete(f"/api/backup/scheduled/{entry['filename']}")
    assert resp.status_code == 204

    filenames = [e["filename"] for e in client.get("/api/backup/scheduled").json()]
    assert entry["filename"] not in filenames


def test_delete_scheduled_backup_404_for_unknown_filename(client):
    resp = client.delete("/api/backup/scheduled/myhome-backup-20260101-000000.zip")
    assert resp.status_code == 404
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/backend && pytest tests/test_backup.py -v -k "backup_config or scheduled_backup"`
Expected: FAIL — all 404 (routes don't exist)

- [ ] **Step 3: Write minimal implementation**

Modify `packages/backend/src/myhome/routes/backup.py`. Update the imports:

```python
from ..models_backup import BackupConfig, BackupEntry
from ..persistence_backup import (
    create_backup,
    delete_backup,
    get_backup_path,
    iter_backup_files,
    list_backups,
    load_backup_config,
    load_backup_state,
    save_backup_config,
    save_backup_state,
)
```

Add these routes at the end of the file:

```python
@router.get("/api/backup/config", response_model=BackupConfig)
def get_backup_config() -> BackupConfig:
    return load_backup_config()


@router.put("/api/backup/config", response_model=BackupConfig)
def put_backup_config(body: BackupConfig) -> BackupConfig:
    save_backup_config(body)
    return body


@router.get("/api/backup/scheduled", response_model=list[BackupEntry])
def get_scheduled_backups() -> list[BackupEntry]:
    return list_backups()


@router.post("/api/backup/scheduled/run", response_model=BackupEntry)
def run_backup_now() -> BackupEntry:
    entry = create_backup()
    state = load_backup_state()
    state.lastRunDate = date.today().isoformat()
    save_backup_state(state)
    return entry


@router.get("/api/backup/scheduled/{filename}/download")
def download_scheduled_backup(filename: str):
    path = get_backup_path(filename)
    if path is None:
        raise HTTPException(status_code=404)
    return FileResponse(path, media_type="application/zip", filename=filename)


@router.delete("/api/backup/scheduled/{filename}", status_code=204)
def delete_scheduled_backup(filename: str) -> None:
    if not delete_backup(filename):
        raise HTTPException(status_code=404)
```

Add `FileResponse` to the existing `from fastapi.responses import StreamingResponse` import line, making it:

```python
from fastapi.responses import FileResponse, StreamingResponse
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd packages/backend && pytest tests/test_backup.py -v`
Expected: PASS (full file)

- [ ] **Step 5: Commit**

```bash
git add packages/backend/src/myhome/routes/backup.py packages/backend/tests/test_backup.py
git commit -m "feat: add backup config, scheduled list, run-now, download, delete routes"
```

---

## Task 7: `backup_scheduler.py`

**Files:**
- Create: `packages/backend/src/myhome/backup_scheduler.py`
- Test: `packages/backend/tests/test_backup_scheduler.py` (new)

- [ ] **Step 1: Write the failing test**

Create `packages/backend/tests/test_backup_scheduler.py`:

```python
from datetime import datetime, timezone

from myhome.backup_scheduler import _should_run_today, check_and_run_scheduled_backup
from myhome.models_backup import BackupConfig, BackupState
from myhome.persistence_backup import list_backups, load_backup_state, save_backup_config, save_backup_state


def test_should_run_today_daily_always_true():
    now = datetime(2026, 7, 7, tzinfo=timezone.utc)
    assert _should_run_today("daily", day_of_week=1, day_of_month=1, now=now) is True


def test_should_run_today_weekly_matches_configured_day():
    # 2026-07-07 is a Tuesday (isoweekday 2)
    now = datetime(2026, 7, 7, tzinfo=timezone.utc)
    assert _should_run_today("weekly", day_of_week=2, day_of_month=1, now=now) is True
    assert _should_run_today("weekly", day_of_week=3, day_of_month=1, now=now) is False


def test_should_run_today_monthly_matches_configured_day():
    now = datetime(2026, 7, 15, tzinfo=timezone.utc)
    assert _should_run_today("monthly", day_of_week=1, day_of_month=15, now=now) is True
    assert _should_run_today("monthly", day_of_week=1, day_of_month=16, now=now) is False


def test_should_run_today_monthly_clamps_to_last_day_of_short_month():
    # February 2026 (not a leap year) has 28 days
    now = datetime(2026, 2, 28, tzinfo=timezone.utc)
    assert _should_run_today("monthly", day_of_week=1, day_of_month=31, now=now) is True


async def test_check_and_run_scheduled_backup_skips_when_disabled(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    await check_and_run_scheduled_backup(now=datetime.now(timezone.utc))
    assert list_backups() == []


async def test_check_and_run_scheduled_backup_skips_before_configured_time(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    save_backup_config(BackupConfig(enabled=True, time="20:00"))
    now = datetime(2026, 7, 7, 9, 0, tzinfo=timezone.utc)
    await check_and_run_scheduled_backup(now=now)
    assert list_backups() == []


async def test_check_and_run_scheduled_backup_skips_wrong_day_for_weekly(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    save_backup_config(BackupConfig(enabled=True, frequency="weekly", dayOfWeek=1, time="00:00"))
    now = datetime(2026, 7, 7, 9, 0, tzinfo=timezone.utc)  # Tuesday; configured for Monday
    await check_and_run_scheduled_backup(now=now)
    assert list_backups() == []


async def test_check_and_run_scheduled_backup_skips_if_already_run_today(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    save_backup_config(BackupConfig(enabled=True, time="00:00"))
    save_backup_state(BackupState(lastRunDate="2026-07-07"))
    now = datetime(2026, 7, 7, 9, 0, tzinfo=timezone.utc)
    await check_and_run_scheduled_backup(now=now)
    assert list_backups() == []


async def test_check_and_run_scheduled_backup_runs_and_marks_state(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    (tmp_path / "house.json").write_text("{}")
    save_backup_config(BackupConfig(enabled=True, time="00:00"))
    now = datetime(2026, 7, 7, 9, 0, tzinfo=timezone.utc)

    await check_and_run_scheduled_backup(now=now)

    assert len(list_backups()) == 1
    assert load_backup_state().lastRunDate == "2026-07-07"
```

This project's `pyproject.toml` sets `asyncio_mode = "auto"`, so the plain `async def test_...` functions are picked up automatically — no `@pytest.mark.asyncio` needed (same convention as `test_notification_scheduler.py`).

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/backend && pytest tests/test_backup_scheduler.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'myhome.backup_scheduler'`

- [ ] **Step 3: Write minimal implementation**

Create `packages/backend/src/myhome/backup_scheduler.py`:

```python
from __future__ import annotations

import asyncio
import calendar
import logging
from datetime import datetime, timezone

from .persistence_backup import create_backup, load_backup_config, load_backup_state, save_backup_state

log = logging.getLogger(__name__)

CHECK_INTERVAL_SECONDS = 60


def _should_run_today(frequency: str, day_of_week: int, day_of_month: int, now: datetime) -> bool:
    if frequency == "daily":
        return True
    if frequency == "weekly":
        return now.isoweekday() == day_of_week
    if frequency == "monthly":
        last_day = calendar.monthrange(now.year, now.month)[1]
        target_day = min(day_of_month, last_day)
        return now.day == target_day
    return False


async def check_and_run_scheduled_backup(now: datetime | None = None) -> None:
    now = now or datetime.now(timezone.utc)
    today = now.date().isoformat()
    config = load_backup_config()
    if not config.enabled:
        return
    state = load_backup_state()
    if state.lastRunDate == today:
        return
    if now.strftime("%H:%M") < config.time:
        return
    if not _should_run_today(config.frequency, config.dayOfWeek, config.dayOfMonth, now):
        return
    create_backup()
    state.lastRunDate = today
    save_backup_state(state)


async def scheduled_backup_loop() -> None:
    while True:
        await asyncio.sleep(CHECK_INTERVAL_SECONDS)
        try:
            await check_and_run_scheduled_backup()
        except Exception:
            log.exception("scheduled backup loop iteration failed")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd packages/backend && pytest tests/test_backup_scheduler.py -v`
Expected: PASS (10 tests)

- [ ] **Step 5: Commit**

```bash
git add packages/backend/src/myhome/backup_scheduler.py packages/backend/tests/test_backup_scheduler.py
git commit -m "feat: add scheduled backup background loop"
```

---

## Task 8: Wire backup scheduler into app lifespan

**Files:**
- Modify: `packages/backend/src/myhome/main.py`

There is no new isolated test for this task: `check_and_run_scheduled_backup` is already fully covered in Task 7, and "does the app still boot" is already exercised by every other test in the suite via the `client` fixture (which runs the full lifespan on each test). This task's verification is Step 2: run the full suite and confirm nothing broke.

- [ ] **Step 1: Write the implementation**

In `packages/backend/src/myhome/main.py`, add the import:

```python
from .backup_scheduler import scheduled_backup_loop
```

(place it alphabetically among the existing single-module imports, i.e. right before `from .deps import ...`)

Update `_lifespan`:

```python
@asynccontextmanager
async def _lifespan(app: FastAPI):
    # The MCP session manager's background task group is NOT started just by
    # mounting mcp_asgi_app -- Starlette never forwards ASGI lifespan events into
    # mounted sub-apps, so it must be entered here explicitly.
    async with mcp.session_manager.run():
        digest_task = asyncio.create_task(notification_digest_loop())
        backup_task = asyncio.create_task(scheduled_backup_loop())
        try:
            yield
        finally:
            digest_task.cancel()
            backup_task.cancel()
```

- [ ] **Step 2: Run the full suite to confirm nothing broke**

Run: `cd packages/backend && pytest tests/ -v`
Expected: PASS (full suite)

- [ ] **Step 3: Commit**

```bash
git add packages/backend/src/myhome/main.py
git commit -m "feat: start scheduled backup loop on app startup"
```

---

## Task 9: Frontend — wire test fetch mocks + Scheduled Backups config section

**Files:**
- Modify: `packages/editor/test/SettingsPage.test.ts`
- Modify: `packages/editor/src/lib/components/SettingsPage.svelte`

Once `SettingsPage.svelte` fetches `GET /api/backup/config` and `GET /api/backup/scheduled` unconditionally on mount, **every** test in `SettingsPage.test.ts` that mounts the component needs those two URLs handled, or the component throws parsing `.json()` on the file's existing catch-all `Response(null, { status: 200 })`. This task does both pieces together since neither is independently useful (the mock fix has nothing to answer until the component makes the calls; the component change breaks every test until the mock is fixed).

- [ ] **Step 1: Add a shared fetch-mock helper**

In `packages/editor/test/SettingsPage.test.ts`, add this function right after `makeAuthStore` (before the first `describe` block):

```ts
function mockBoilerplateEndpoints(url: string): { ok: boolean; json: () => Promise<unknown> } | null {
  if (url === "/api/backup/config") {
    return {
      ok: true,
      json: async () => ({
        enabled: false, frequency: "daily", time: "03:00",
        dayOfWeek: 7, dayOfMonth: 1, retentionCount: 7,
      }),
    };
  }
  if (url === "/api/backup/scheduled") {
    return { ok: true, json: async () => [] };
  }
  return null;
}
```

- [ ] **Step 2: Wire the helper into every existing mock definition**

Three edits, each using find-and-replace-all since the anchor text is byte-identical across occurrences:

Edit A — 7 occurrences of the plain signature. Old text:
```ts
    fetchMock = vi.fn().mockImplementation((url: string) => {
```
New text:
```ts
    fetchMock = vi.fn().mockImplementation((url: string) => {
      const boiler = mockBoilerplateEndpoints(url);
      if (boiler) return Promise.resolve(boiler);
```
Apply as a **replace-all** across the file (all 7 occurrences get the same two lines inserted).

Edit B — 3 occurrences of the `opts` signature. Old text:
```ts
    fetchMock = vi.fn().mockImplementation((url: string, opts?: RequestInit) => {
```
New text:
```ts
    fetchMock = vi.fn().mockImplementation((url: string, opts?: RequestInit) => {
      const boiler = mockBoilerplateEndpoints(url);
      if (boiler) return Promise.resolve(boiler);
```
Apply as a **replace-all** (all 3 occurrences).

Edit C — 1 occurrence in the Notifications describe block's `beforeEach`. Old text:
```ts
    globalThis.fetch = vi.fn().mockImplementation((url: string) => {
```
New text:
```ts
    globalThis.fetch = vi.fn().mockImplementation((url: string) => {
      const boiler = mockBoilerplateEndpoints(url);
      if (boiler) return Promise.resolve(boiler);
```

- [ ] **Step 3: Run the full SettingsPage test file to verify it still passes (before touching the component)**

Run: `cd packages/editor && npx vitest run SettingsPage.test.ts`
Expected: PASS (25/25 — this step is purely additive plumbing; nothing calls the new URLs yet, so behavior is unchanged)

- [ ] **Step 4: Write the failing tests for the new section**

Add to the `"SettingsPage — Backup & Restore"` describe block (after the existing `restoreError`/`restoreSuccess` tests, before its closing `});`):

```ts
  it("renders the Scheduled Backups section with defaults", async () => {
    const app = mount(SettingsPage, { target, props: { store: makeStore(), authStore: makeAuthStore() } });
    await new Promise((r) => setTimeout(r, 0));
    flushSync();

    expect(target.textContent).toContain("Scheduled Backups");
    expect((target.querySelector(".backup-enable-toggle") as HTMLInputElement).checked).toBe(false);
    unmount(app);
  });

  it("shows day-of-week only for weekly and day-of-month only for monthly", async () => {
    fetchMock = vi.fn().mockImplementation((url: string) => {
      if (url === "/api/backup/config") {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            enabled: true, frequency: "weekly", time: "03:00",
            dayOfWeek: 3, dayOfMonth: 1, retentionCount: 7,
          }),
        });
      }
      const boiler = mockBoilerplateEndpoints(url);
      if (boiler) return Promise.resolve(boiler);
      return Promise.resolve(new Response(null, { status: 200 }));
    });
    globalThis.fetch = fetchMock;
    const app = mount(SettingsPage, { target, props: { store: makeStore(), authStore: makeAuthStore() } });
    await new Promise((r) => setTimeout(r, 0));
    flushSync();

    const labels = Array.from(target.querySelectorAll(".modal-label")).map((el) => el.textContent);
    expect(labels).toContain("Day of week");
    expect(labels).not.toContain("Day of month");

    unmount(app);
  });

  it("saves scheduled backup config via PUT /api/backup/config", async () => {
    const app = mount(SettingsPage, { target, props: { store: makeStore(), authStore: makeAuthStore() } });
    await new Promise((r) => setTimeout(r, 0));
    flushSync();

    const enableToggle = target.querySelector(".backup-enable-toggle") as HTMLInputElement;
    enableToggle.click();
    flushSync();

    const saveBtn = Array.from(target.querySelectorAll("button")).find((b) => b.textContent?.trim() === "Save")!;
    (saveBtn as HTMLButtonElement).click();
    await new Promise((r) => setTimeout(r, 0));

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/backup/config",
      expect.objectContaining({ method: "PUT" }),
    );
    unmount(app);
  });

  it("Run backup now calls POST /api/backup/scheduled/run", async () => {
    const app = mount(SettingsPage, { target, props: { store: makeStore(), authStore: makeAuthStore() } });
    await new Promise((r) => setTimeout(r, 0));
    flushSync();

    const runBtn = Array.from(target.querySelectorAll("button")).find((b) => b.textContent?.includes("Run backup now"))!;
    (runBtn as HTMLButtonElement).click();
    await new Promise((r) => setTimeout(r, 0));

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/backup/scheduled/run",
      expect.objectContaining({ method: "POST" }),
    );
    unmount(app);
  });
```

- [ ] **Step 5: Run tests to verify they fail**

Run: `cd packages/editor && npx vitest run SettingsPage.test.ts -t "Scheduled Backups|day-of-week only|scheduled backup config|Run backup now"`
Expected: FAIL — no "Scheduled Backups" text, no `.backup-enable-toggle` element yet

- [ ] **Step 6: Write minimal implementation**

In `packages/editor/src/lib/components/SettingsPage.svelte`, add script state right after the existing `// --- Backup & Restore ---` block's declarations (after `let fileInputEl: HTMLInputElement | undefined = $state();`):

```ts
  // --- Scheduled backups ---
  interface ScheduledBackupConfig {
    enabled: boolean;
    frequency: "daily" | "weekly" | "monthly";
    time: string;
    dayOfWeek: number;
    dayOfMonth: number;
    retentionCount: number;
  }
  interface ScheduledBackupEntry {
    filename: string;
    createdAt: string;
    sizeBytes: number;
  }

  function defaultBackupConfig(): ScheduledBackupConfig {
    return { enabled: false, frequency: "daily", time: "03:00", dayOfWeek: 7, dayOfMonth: 1, retentionCount: 7 };
  }

  const WEEKDAY_OPTIONS = [
    { value: 1, label: "Monday" }, { value: 2, label: "Tuesday" }, { value: 3, label: "Wednesday" },
    { value: 4, label: "Thursday" }, { value: 5, label: "Friday" }, { value: 6, label: "Saturday" },
    { value: 7, label: "Sunday" },
  ];

  let scheduledConfig = $state<ScheduledBackupConfig>(defaultBackupConfig());
  let scheduledConfigLoaded = $state(false);
  let scheduledConfigError = $state<string | null>(null);
  let scheduledConfigSaving = $state(false);
  let scheduledDayOfMonthStr = $state(String(defaultBackupConfig().dayOfMonth));
  let scheduledRetentionCountStr = $state(String(defaultBackupConfig().retentionCount));
  let scheduledBackups = $state<ScheduledBackupEntry[]>([]);
  let runningBackupNow = $state(false);
  let confirmDeleteBackupFilename = $state<string | null>(null);

  async function loadScheduledBackupConfig(): Promise<void> {
    const resp = await fetch("/api/backup/config");
    if (resp.ok) {
      scheduledConfig = await resp.json();
      scheduledDayOfMonthStr = String(scheduledConfig.dayOfMonth);
      scheduledRetentionCountStr = String(scheduledConfig.retentionCount);
    }
    scheduledConfigLoaded = true;
  }

  async function loadScheduledBackups(): Promise<void> {
    const resp = await fetch("/api/backup/scheduled");
    if (resp.ok) scheduledBackups = await resp.json();
  }

  loadScheduledBackupConfig();
  loadScheduledBackups();

  async function saveScheduledBackupConfig(): Promise<void> {
    scheduledConfigError = null;
    scheduledConfigSaving = true;
    try {
      const resp = await fetch("/api/backup/config", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ...scheduledConfig,
          dayOfMonth: parseInt(scheduledDayOfMonthStr, 10) || 1,
          retentionCount: parseInt(scheduledRetentionCountStr, 10) || 1,
        }),
      });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      scheduledConfig = await resp.json();
      scheduledDayOfMonthStr = String(scheduledConfig.dayOfMonth);
      scheduledRetentionCountStr = String(scheduledConfig.retentionCount);
    } catch (e) {
      scheduledConfigError = e instanceof Error ? e.message : String(e);
    } finally {
      scheduledConfigSaving = false;
    }
  }

  async function runBackupNow(): Promise<void> {
    runningBackupNow = true;
    scheduledConfigError = null;
    try {
      const resp = await fetch("/api/backup/scheduled/run", { method: "POST" });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      await loadScheduledBackups();
    } catch (e) {
      scheduledConfigError = e instanceof Error ? e.message : String(e);
    } finally {
      runningBackupNow = false;
    }
  }

  function formatBackupSize(bytes: number): string {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  }
```

Add the markup inside the existing Backup & Restore `<Card>`, right after the existing `{#if restoreSuccess}...{/if}` line and before the `</Card>` close:

```svelte
      <h3 class="subsection-title" style="margin-top: var(--space-4)">Scheduled Backups</h3>
      {#if scheduledConfigLoaded}
        <label class="module-row">
          <input class="backup-enable-toggle" type="checkbox" bind:checked={scheduledConfig.enabled} />
          <span class="mod-label">Enable scheduled backups</span>
        </label>
        {#if scheduledConfig.enabled}
          <div class="modal-form" style="margin-top: var(--space-3)">
            <div class="modal-field">
              <span class="modal-label">Frequency</span>
              <select bind:value={scheduledConfig.frequency} class="modal-select">
                <option value="daily">Daily</option>
                <option value="weekly">Weekly</option>
                <option value="monthly">Monthly</option>
              </select>
            </div>
            {#if scheduledConfig.frequency === "weekly"}
              <div class="modal-field">
                <span class="modal-label">Day of week</span>
                <select bind:value={scheduledConfig.dayOfWeek} class="modal-select">
                  {#each WEEKDAY_OPTIONS as opt (opt.value)}
                    <option value={opt.value}>{opt.label}</option>
                  {/each}
                </select>
              </div>
            {/if}
            {#if scheduledConfig.frequency === "monthly"}
              <div class="modal-field">
                <span class="modal-label">Day of month</span>
                <Input type="number" bind:value={scheduledDayOfMonthStr} />
              </div>
            {/if}
            <div class="modal-field">
              <span class="modal-label">Time (UTC, HH:MM)</span>
              <Input bind:value={scheduledConfig.time} placeholder="03:00" />
            </div>
            <div class="modal-field">
              <span class="modal-label">Keep last N backups</span>
              <Input type="number" bind:value={scheduledRetentionCountStr} />
            </div>
          </div>
        {/if}
        {#if scheduledConfigError}<div class="error">{scheduledConfigError}</div>{/if}
        <div class="modal-actions">
          <Button onclick={saveScheduledBackupConfig} disabled={scheduledConfigSaving}>
            {scheduledConfigSaving ? "Saving…" : "Save"}
          </Button>
          <Button variant="secondary" onclick={runBackupNow} disabled={runningBackupNow}>
            {runningBackupNow ? "Running…" : "Run backup now"}
          </Button>
        </div>
      {/if}
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `cd packages/editor && npx vitest run SettingsPage.test.ts`
Expected: PASS (29/29 — 25 pre-existing + 4 new)

- [ ] **Step 8: Commit**

```bash
git add packages/editor/test/SettingsPage.test.ts packages/editor/src/lib/components/SettingsPage.svelte
git commit -m "feat: add Scheduled Backups config section to Settings"
```

---

## Task 10: Frontend — scheduled backups list (render, download, delete)

**Files:**
- Modify: `packages/editor/test/SettingsPage.test.ts`
- Modify: `packages/editor/src/lib/components/SettingsPage.svelte`

- [ ] **Step 1: Write the failing test**

Add to the `"SettingsPage — Backup & Restore"` describe block:

```ts
  it("renders the scheduled backups list and deletes an entry after confirmation", async () => {
    fetchMock = vi.fn().mockImplementation((url: string) => {
      if (url === "/api/backup/scheduled") {
        return Promise.resolve({
          ok: true,
          json: async () => [
            { filename: "myhome-backup-20260701-030000.zip", createdAt: "2026-07-01T03:00:00Z", sizeBytes: 2048 },
          ],
        });
      }
      const boiler = mockBoilerplateEndpoints(url);
      if (boiler) return Promise.resolve(boiler);
      return Promise.resolve(new Response(null, { status: 200 }));
    });
    globalThis.fetch = fetchMock;
    const app = mount(SettingsPage, { target, props: { store: makeStore(), authStore: makeAuthStore() } });
    await new Promise((r) => setTimeout(r, 0));
    flushSync();

    expect(target.textContent).toContain("2.0 KB");

    const deleteBtn = target.querySelector(".backup-row .icon-action.danger") as HTMLButtonElement;
    deleteBtn.click();
    flushSync();
    expect(target.textContent).toContain("Delete?");

    const confirmBtn = Array.from(target.querySelectorAll(".backup-row .icon-action.danger")).find((b) => b.textContent === "✓")!;
    (confirmBtn as HTMLButtonElement).click();
    await new Promise((r) => setTimeout(r, 0));

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/backup/scheduled/myhome-backup-20260701-030000.zip",
      expect.objectContaining({ method: "DELETE" }),
    );
    unmount(app);
  });
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/editor && npx vitest run SettingsPage.test.ts -t "renders the scheduled backups list"`
Expected: FAIL — no `.backup-row` elements exist yet

- [ ] **Step 3: Write minimal implementation**

Add to `SettingsPage.svelte`'s script, after `formatBackupSize`:

```ts
  async function downloadScheduledBackup(filename: string): Promise<void> {
    const resp = await fetch(`/api/backup/scheduled/${filename}/download`);
    if (!resp.ok) return;
    const blob = await resp.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  async function deleteScheduledBackup(filename: string): Promise<void> {
    await fetch(`/api/backup/scheduled/${filename}`, { method: "DELETE" });
    confirmDeleteBackupFilename = null;
    await loadScheduledBackups();
  }
```

Add the list markup right after the `{#if scheduledConfigLoaded}...{/if}` block from Task 9, still inside the same `<Card>`:

```svelte
      {#if scheduledBackups.length > 0}
        <div class="table-wrapper" style="margin-top: var(--space-3)">
          <table>
            <thead>
              <tr><th>Created</th><th>Size</th><th></th></tr>
            </thead>
            <tbody>
              {#each scheduledBackups as backup (backup.filename)}
                <tr class="backup-row">
                  <td>{new Date(backup.createdAt).toLocaleString()}</td>
                  <td>{formatBackupSize(backup.sizeBytes)}</td>
                  <td class="actions">
                    {#if confirmDeleteBackupFilename === backup.filename}
                      <span class="confirm-text">Delete?</span>
                      <button class="icon-action danger" onclick={() => deleteScheduledBackup(backup.filename)}>✓</button>
                      <button class="icon-action" onclick={() => { confirmDeleteBackupFilename = null; }}>✕</button>
                    {:else}
                      <button class="icon-action" onclick={() => downloadScheduledBackup(backup.filename)} title="Download">⬇</button>
                      <button class="icon-action danger" onclick={() => { confirmDeleteBackupFilename = backup.filename; }} title="Delete">🗑</button>
                    {/if}
                  </td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      {/if}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd packages/editor && npx vitest run SettingsPage.test.ts`
Expected: PASS (30/30)

- [ ] **Step 5: Commit**

```bash
git add packages/editor/test/SettingsPage.test.ts packages/editor/src/lib/components/SettingsPage.svelte
git commit -m "feat: add scheduled backups list with download and delete"
```

---

## Final Verification

- [ ] Run the full backend suite: `cd packages/backend && pytest tests/ -v` — expect all green, including the ~35 new tests added across Tasks 1–8.
- [ ] Run the full frontend suite: `cd packages/editor && npx vitest run` — expect all green, including the new tests from Tasks 9–10.
- [ ] Manually verify: enable scheduled backups, set frequency to "Weekly" and confirm the day-of-week field appears (and day-of-month doesn't); switch to "Monthly" and confirm the reverse; save; click "Run backup now" and confirm a new row appears in the list with a plausible size; click Download on a row and confirm a zip downloads; click Delete, confirm, and confirm the row disappears.
- [ ] Update `ROADMAP.md`: move "Automated scheduled backups" out of "To Be Confirmed" into "Recently Completed", linking this plan and the design spec, following the same format used for the notification center in the current file.
