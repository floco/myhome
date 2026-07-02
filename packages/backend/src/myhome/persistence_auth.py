# packages/backend/src/myhome/persistence_auth.py
import json
import os
from pathlib import Path

from .models_auth import TokenDocument, UserDocument


def _users_file() -> Path:
    return Path(os.environ.get("DATA_DIR", "/data")) / "users.json"


def _tokens_file() -> Path:
    return Path(os.environ.get("DATA_DIR", "/data")) / "tokens.json"


def load_users() -> UserDocument:
    path = _users_file()
    if not path.exists():
        return UserDocument()
    with path.open() as f:
        return UserDocument.model_validate(json.load(f))


def save_users(doc: UserDocument) -> None:
    path = _users_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with tmp.open("w") as f:
        json.dump(doc.model_dump(), f, indent=2)
    tmp.replace(path)


def load_tokens() -> TokenDocument:
    path = _tokens_file()
    if not path.exists():
        return TokenDocument()
    with path.open() as f:
        return TokenDocument.model_validate(json.load(f))


def save_tokens(doc: TokenDocument) -> None:
    path = _tokens_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with tmp.open("w") as f:
        json.dump(doc.model_dump(), f, indent=2)
    tmp.replace(path)
