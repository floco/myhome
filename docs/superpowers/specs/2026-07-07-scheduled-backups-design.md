# Automated Scheduled Backups — Design Spec

**Date:** 2026-07-07
**Status:** Approved

---

## Overview

Extend the existing manual backup/restore (Settings) with a scheduled job that:

- Writes a backup zip to disk automatically on a cadence — **daily, weekly, or
  monthly**, each with a configurable time-of-day, plus a day-of-week
  (weekly) or day-of-month (monthly).
- **Prunes automatically**: keeps only the most recent **N** backups
  (configurable count); the oldest is deleted once the count is exceeded.
- Is **browsable in Settings**: a list of scheduled backups (filename,
  timestamp, size) with per-entry download and delete.
- Has a **"Run backup now"** button that creates an entry via the exact same
  code path as the scheduled job.

This is a global (instance-wide) setting, not per-home, matching how
backup/restore already operates on the whole `DATA_DIR` rather than being
scoped to a home. Config follows the existing global-config pattern already
used by `mcp_config.json` (a top-level JSON file, not part of any home's
settings document).

---

## Approach

A second, independent `asyncio` background loop (`backup_scheduler.py`),
structurally identical to the just-shipped `notification_scheduler.py`:
polls every 60 seconds, started as a second `asyncio.create_task(...)` in
`main.py`'s lifespan alongside the notification digest loop. No shared
scheduler abstraction between the two — with only two scheduled jobs in the
codebase, a generic job-runner would be premature, and would mean touching
already-shipped, tested code for marginal benefit.

---

## Data Model

New module `models_backup.py`:

```python
class BackupConfig(BaseModel):
    enabled: bool = False
    frequency: Literal["daily", "weekly", "monthly"] = "daily"
    time: str = "03:00"          # HH:MM, UTC (same convention as the notification digest)
    dayOfWeek: int = 7           # ISO weekday, 1=Monday..7=Sunday; used when frequency == "weekly"
    dayOfMonth: int = 1          # 1-31; used when frequency == "monthly", clamped to the
                                  # last day of the month if the month is shorter
    retentionCount: int = 7

class BackupEntry(BaseModel):
    filename: str
    createdAt: str                # ISO 8601
    sizeBytes: int

class BackupState(BaseModel):
    lastRunDate: str | None = None   # ISO date (YYYY-MM-DD) of the last successful run,
                                       # scheduled or manually triggered via "Run backup now"
```

Persistence (new `persistence_backup.py`, following the same atomic
tmp-file-rename pattern as `persistence_mcp.py`):

- `backup_config.json`, `backup_state.json` — both at the `DATA_DIR` root,
  alongside `mcp_config.json`.
- `{DATA_DIR}/backups/` — directory holding the actual backup zip files,
  named `myhome-backup-{YYYYMMDD-HHMMSS}.zip` (full timestamp, not just a
  date, so multiple runs on the same day — e.g. a scheduled run plus a
  manual "Run now" — don't collide).

`persistence_backup.py` also owns:
- `list_backups() -> list[BackupEntry]` — scans `backups/` for `*.zip`,
  sorted newest-first.
- `create_backup() -> BackupEntry` — builds a zip of `DATA_DIR` (see below),
  writes it into `backups/`, prunes down to `retentionCount` (deleting the
  oldest first), and returns the new entry. Used by both the scheduler and
  the "Run backup now" endpoint — one code path, no duplication.
- `delete_backup(filename) -> bool`
- `get_backup_path(filename) -> Path | None` — returns `None` if `filename`
  fails a strict validation regex (`^myhome-backup-\d{8}-\d{6}\.zip$`),
  preventing path traversal via a crafted filename in the download/delete
  routes.

**In-scope fix to existing code:** `routes/backup.py`'s current
`download_backup()` zips everything under `DATA_DIR` with no exclusions.
Once `backups/` exists as a subdirectory of `DATA_DIR`, every future
manual download would recursively bundle all prior scheduled backups inside
itself, growing without bound. The zip-building logic is extracted into a
shared helper (`_iter_backup_files(data_dir, exclude_dirs={"backups"})`)
used by both the existing manual download and the new `create_backup()`,
so both paths correctly exclude the `backups/` directory from a backup's own
contents.

---

## Backend: Scheduler

New module `backup_scheduler.py`:

```python
CHECK_INTERVAL_SECONDS = 60

def _should_run_today(config: BackupConfig, now: datetime) -> bool:
    if config.frequency == "daily":
        return True
    if config.frequency == "weekly":
        return now.isoweekday() == config.dayOfWeek
    if config.frequency == "monthly":
        last_day = calendar.monthrange(now.year, now.month)[1]
        target_day = min(config.dayOfMonth, last_day)
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
    if not _should_run_today(config, now):
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

Wired into `main.py`'s `_lifespan` alongside the existing
`notification_digest_loop` task (started/cancelled the same way).

---

## Backend: Routes

Extends `routes/backup.py`:

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/backup/config` | Returns `BackupConfig` |
| PUT | `/api/backup/config` | Saves `BackupConfig` |
| GET | `/api/backup/scheduled` | Returns `list[BackupEntry]` |
| POST | `/api/backup/scheduled/run` | Runs `create_backup()` immediately, updates `lastRunDate`, returns the new `BackupEntry`. Works regardless of `config.enabled` — a manual trigger shouldn't require the automatic schedule to be turned on. |
| GET | `/api/backup/scheduled/{filename}/download` | Streams that specific backup file |
| DELETE | `/api/backup/scheduled/{filename}` | Deletes that specific backup file |

The existing `GET /api/backup/download` and `POST /api/backup/restore`
routes are unchanged in behavior (aside from the exclusion fix above).

---

## Frontend

No new store module — the existing manual backup/restore UI lives as local
component state directly in `SettingsPage.svelte` (there's no
`backupStore.svelte.ts` today), so the scheduled-backup UI extends that same
section rather than introducing a new store, following the file's existing
convention of one local state block per settings section.

Extends the existing "Backup & Restore" card with:

- **Scheduled backup settings** sub-form: enable toggle, frequency select
  (Daily / Weekly / Monthly), time input, a day-of-week select (shown only
  when frequency is Weekly), a day-of-month number input (shown only when
  frequency is Monthly), a retention-count number input, and a Save button —
  mirroring the draft-state + `$effect`-sync + save-handler pattern already
  used by the Notifications section.
- **"Run backup now"** button, calling `POST /api/backup/scheduled/run` and
  refreshing the list on success.
- **Scheduled backups list**: fetched on mount and refreshed after run/delete;
  each row shows filename, a human-formatted timestamp, size (human-readable,
  e.g. "2.4 MB"), a Download link/button, and a Delete button with a confirm
  step (mirroring the existing delete-confirmation patterns elsewhere in this
  file, e.g. cost category deletion).

---

## Testing

- **Backend unit tests**: `_should_run_today` — daily always true; weekly
  matches only the configured ISO weekday; monthly matches the configured
  day, clamped correctly for short months (e.g. `dayOfMonth=31` in February
  matches the 28th/29th).
- **`create_backup()`**: writes a zip into `backups/`, prunes down to
  `retentionCount` (deletes oldest first), and — critically — the zip it
  writes does not itself contain the `backups/` directory.
- **Regression test**: `GET /api/backup/download` also excludes `backups/`
  from its streamed zip once backup files exist on disk.
- **`check_and_run_scheduled_backup`**: skips when disabled, skips before
  the configured time, skips on the wrong day for weekly/monthly, skips if
  already run today, runs and updates `lastRunDate` on success.
- **Routes**: config GET/PUT round-trip; scheduled list/run-now/download/
  delete; delete/download reject a filename that doesn't match the strict
  backup-filename pattern (400, not a path-traversal attempt).
- **Frontend**: `SettingsPage` tests for the new section — renders current
  config, conditional day-of-week/day-of-month fields per frequency, save
  round-trip, list rendering, run-now triggers a refresh, delete
  confirmation flow.

---

## Non-Goals

- Off-site/cloud backup upload (S3, etc.) — local `DATA_DIR` only, same as
  today's manual backup.
- Backup encryption beyond what already exists (none) — unchanged from the
  current manual backup/restore.
- Changes to the restore flow — restore still replaces `DATA_DIR` wholesale
  from an uploaded zip, unchanged.
- Sub-daily cadences (e.g. every N hours) — daily is the shortest interval.
