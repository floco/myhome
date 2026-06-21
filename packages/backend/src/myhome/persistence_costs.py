import json
import os
from pathlib import Path

from .models_costs import CostsDocument


def _costs_file() -> Path:
    data_dir = Path(os.environ.get("DATA_DIR", "/data"))
    return data_dir / "costs.json"


def load_costs() -> CostsDocument:
    path = _costs_file()
    if not path.exists():
        return CostsDocument()
    with path.open() as f:
        raw = json.load(f)
    # Migration: entries saved before 2026-06-21 used "supplier" (freeform string).
    # Pydantic v2 ignores unknown fields, so old entries load with supplierId=None automatically.
    return CostsDocument.model_validate(raw)


def save_costs(doc: CostsDocument) -> None:
    path = _costs_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with tmp.open("w") as f:
        json.dump(doc.model_dump(), f, indent=2)
    tmp.replace(path)
