import json
import os
import shutil
from pathlib import Path

from .models_works import WorksDocument


def _works_file() -> Path:
    data_dir = Path(os.environ.get("DATA_DIR", "/data"))
    return data_dir / "works.json"


def _attachments_dir(work_id: str) -> Path:
    data_dir = Path(os.environ.get("DATA_DIR", "/data"))
    return data_dir / "works-attachments" / work_id


def load_works() -> WorksDocument:
    path = _works_file()
    if not path.exists():
        return WorksDocument()
    with path.open() as f:
        return WorksDocument.model_validate(json.load(f))


def save_works(doc: WorksDocument) -> None:
    path = _works_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with tmp.open("w") as f:
        json.dump(doc.model_dump(), f, indent=2)
    tmp.replace(path)


def get_attachment_path(work_id: str, filename: str) -> Path:
    return _attachments_dir(work_id) / filename


def save_attachment(work_id: str, filename: str, data: bytes) -> None:
    path = _attachments_dir(work_id)
    path.mkdir(parents=True, exist_ok=True)
    (path / filename).write_bytes(data)


def delete_attachment(work_id: str, filename: str) -> bool:
    path = _attachments_dir(work_id) / filename
    if not path.exists():
        return False
    path.unlink()
    return True


def delete_all_attachments(work_id: str) -> None:
    path = _attachments_dir(work_id)
    if path.exists():
        shutil.rmtree(path)
