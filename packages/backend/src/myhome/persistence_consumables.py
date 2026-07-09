import json
import os
from pathlib import Path

from .ids import InvalidIdError
from .models_consumables import ConsumableDocument


def _home_dir(home_id: str) -> Path:
    # Resolve then verify containment within homes_root -- this is CodeQL's
    # own recommended py/path-injection sanitizer shape (normalize, then
    # check startswith against the safe root) rather than a bare regex
    # check, which its taint tracker does not recognize as a barrier.
    homes_root = (Path(os.environ.get("DATA_DIR", "/data")) / "homes").resolve()
    candidate = (homes_root / home_id).resolve()
    if not str(candidate).startswith(str(homes_root) + os.sep):
        raise InvalidIdError(f"Invalid home_id: {home_id!r}")
    return candidate


def _consumables_file(home_id: str) -> Path:
    return _home_dir(home_id) / "consumables.json"


def load_consumables(home_id: str) -> ConsumableDocument:
    path = _consumables_file(home_id)
    if not path.exists():
        return ConsumableDocument()
    with path.open() as f:
        return ConsumableDocument.model_validate(json.load(f))


def save_consumables(home_id: str, doc: ConsumableDocument) -> None:
    path = _consumables_file(home_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with tmp.open("w") as f:
        json.dump(doc.model_dump(), f, indent=2)
    tmp.replace(path)
