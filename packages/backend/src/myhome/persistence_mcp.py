import json
import os
from pathlib import Path

from .models_mcp import McpConfig


def _mcp_config_file() -> Path:
    return Path(os.environ.get("DATA_DIR", "/data")) / "mcp_config.json"


def load_mcp_config() -> McpConfig:
    path = _mcp_config_file()
    if not path.exists():
        return McpConfig()
    with path.open() as f:
        return McpConfig.model_validate(json.load(f))


def save_mcp_config(config: McpConfig) -> None:
    path = _mcp_config_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with tmp.open("w") as f:
        json.dump(config.model_dump(), f, indent=2)
    tmp.replace(path)
