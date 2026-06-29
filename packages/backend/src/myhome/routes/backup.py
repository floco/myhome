import io
import os
import shutil
import zipfile
from datetime import date
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

router = APIRouter()


def _data_dir() -> Path:
    return Path(os.environ.get("DATA_DIR", "/data"))


@router.get("/api/backup/download")
def download_backup() -> StreamingResponse:
    data_dir = _data_dir()
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        if data_dir.exists():
            for path in data_dir.rglob("*"):
                if path.is_file():
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
    data_dir.mkdir(parents=True, exist_ok=True)
    for child in data_dir.iterdir():
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()
    with zipfile.ZipFile(io.BytesIO(content)) as zf:
        zf.extractall(data_dir)
