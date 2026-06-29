import io
import os
import shutil
import zipfile
from datetime import date
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

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
    resolved_root = data_dir.resolve()
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        if data_dir.exists():
            for path in data_dir.rglob("*"):
                if path.is_symlink() or not path.is_file():
                    continue
                if not path.resolve().is_relative_to(resolved_root):
                    continue
                zf.write(path, path.relative_to(data_dir))
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
