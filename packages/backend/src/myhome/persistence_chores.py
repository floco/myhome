import json
import os
from pathlib import Path

from .models_chores import ChoreDocument


def _chores_file() -> Path:
    data_dir = Path(os.environ.get("DATA_DIR", "/data"))
    return data_dir / "chores.json"


def load_chores() -> ChoreDocument:
    path = _chores_file()
    if not path.exists():
        return ChoreDocument()
    with path.open() as f:
        return ChoreDocument.model_validate(json.load(f))


def save_chores(doc: ChoreDocument) -> None:
    path = _chores_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with tmp.open("w") as f:
        json.dump(doc.model_dump(), f, indent=2)
    tmp.replace(path)
