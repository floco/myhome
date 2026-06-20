import json
import os
from pathlib import Path

from .models_settings import (
    SettingsDocument,
    _default_cost_categories,
    _default_inventory_categories,
)


def _settings_file() -> Path:
    data_dir = Path(os.environ.get("DATA_DIR", "/data"))
    return data_dir / "settings.json"


def load_settings() -> SettingsDocument:
    path = _settings_file()
    if not path.exists():
        return SettingsDocument(
            costCategories=_default_cost_categories(),
            inventoryCategories=_default_inventory_categories(),
        )
    with path.open() as f:
        return SettingsDocument.model_validate(json.load(f))


def save_settings(doc: SettingsDocument) -> None:
    path = _settings_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with tmp.open("w") as f:
        json.dump(doc.model_dump(), f, indent=2)
    tmp.replace(path)
