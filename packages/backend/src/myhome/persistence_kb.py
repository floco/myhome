import json
import os
from pathlib import Path

from .models_kb import KBDocument


def _kb_file() -> Path:
    data_dir = Path(os.environ.get("DATA_DIR", "/data"))
    return data_dir / "kb.json"


def load_kb() -> KBDocument:
    path = _kb_file()
    if not path.exists():
        return KBDocument()
    with path.open() as f:
        return KBDocument.model_validate(json.load(f))


def save_kb(doc: KBDocument) -> None:
    path = _kb_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with tmp.open("w") as f:
        json.dump(doc.model_dump(), f, indent=2)
    tmp.replace(path)
