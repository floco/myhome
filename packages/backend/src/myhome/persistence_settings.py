import json
import os
from pathlib import Path

from .ids import InvalidIdError
from .models_settings import (
    SettingsDocument,
    _default_cost_categories,
    _default_consumable_units,
    _default_inventory_categories,
    _default_work_categories,
)


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


def _settings_file(home_id: str) -> Path:
    return _home_dir(home_id) / "settings.json"


def load_settings(home_id: str) -> SettingsDocument:
    path = _settings_file(home_id)
    if not path.exists():
        return SettingsDocument(
            costCategories=_default_cost_categories(),
            inventoryCategories=_default_inventory_categories(),
            workCategories=_default_work_categories(),
            consumableUnits=_default_consumable_units(),
        )
    with path.open() as f:
        doc = SettingsDocument.model_validate(json.load(f))
    if not doc.consumableUnits:
        doc.consumableUnits = _default_consumable_units()
    return doc


def save_settings(home_id: str, doc: SettingsDocument) -> None:
    path = _settings_file(home_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with tmp.open("w") as f:
        json.dump(doc.model_dump(), f, indent=2)
    tmp.replace(path)
