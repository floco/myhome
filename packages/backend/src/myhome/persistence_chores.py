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
        doc = ChoreDocument.model_validate(json.load(f))
    # Migration: fill in missing assignment nextDueDates from parent chore
    chore_map = {c.id: c for c in doc.chores}
    for a in doc.assignments:
        if not a.nextDueDate:
            parent = chore_map.get(a.choreId)
            a.nextDueDate = parent.nextDueDate if parent else ""
    return doc


def save_chores(doc: ChoreDocument) -> None:
    path = _chores_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with tmp.open("w") as f:
        json.dump(doc.model_dump(), f, indent=2)
    tmp.replace(path)
