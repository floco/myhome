import io
import os
import shutil
import zipfile
from datetime import date
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile
from fastapi.responses import FileResponse, StreamingResponse

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

router = APIRouter()

_MAX_RESTORE_BYTES = 500 * 1024 * 1024  # 500 MB total uncompressed


def _data_dir() -> Path:
    return Path(os.environ.get("DATA_DIR", "/data"))


def _validate_zip_entries(zf: zipfile.ZipFile, data_dir: Path) -> None:
    resolved_root = data_dir.resolve()
    total_size = 0
    for info in zf.infolist():
        name = info.filename
        # Reject absolute paths and traversal segments
        if name.startswith("/") or ".." in Path(name).parts:
            raise HTTPException(status_code=400, detail="Invalid backup file")
        # Reject symlinks (Unix external_attr encodes file type in high bits)
        if (info.external_attr >> 16) & 0o170000 == 0o120000:
            raise HTTPException(status_code=400, detail="Invalid backup file")
        # Reject entries that resolve outside DATA_DIR
        target = (data_dir / name).resolve()
        if not target.is_relative_to(resolved_root):
            raise HTTPException(status_code=400, detail="Invalid backup file")
        # info.file_size is metadata and can be forged in a crafted zip; a
        # fully hardened version would stream-extract and count bytes_written.
        # Acceptable here: endpoint is local-only, backups are self-generated.
        total_size += info.file_size
        if total_size > _MAX_RESTORE_BYTES:
            raise HTTPException(status_code=400, detail="Backup too large")


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


@router.post("/api/backup/restore", status_code=204)
async def restore_backup(file: UploadFile) -> None:
    content = await file.read()
    if not zipfile.is_zipfile(io.BytesIO(content)):
        raise HTTPException(status_code=400, detail="Invalid backup file")
    data_dir = _data_dir()
    # Validate all entries before touching DATA_DIR
    with zipfile.ZipFile(io.BytesIO(content)) as zf:
        _validate_zip_entries(zf, data_dir)
        data_dir.mkdir(parents=True, exist_ok=True)
        for child in data_dir.iterdir():
            if child.is_dir():
                shutil.rmtree(child)
            else:
                child.unlink()
        zf.extractall(data_dir)


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
