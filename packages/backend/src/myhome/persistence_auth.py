# packages/backend/src/myhome/persistence_auth.py
import json
import os
from pathlib import Path

from .models_auth import OidcConfig, OidcConfigDocument, TokenDocument, UserDocument


def _users_file() -> Path:
    return Path(os.environ.get("DATA_DIR", "/data")) / "users.json"


def _tokens_file() -> Path:
    return Path(os.environ.get("DATA_DIR", "/data")) / "tokens.json"


def _oidc_config_file() -> Path:
    return Path(os.environ.get("DATA_DIR", "/data")) / "oidc_config.json"


def initial_admin_password_file() -> Path:
    return Path(os.environ.get("DATA_DIR", "/data")) / ".initial-admin-password"


def clear_initial_admin_password() -> None:
    """Delete the one-time first-boot password file, if present.

    Called on every successful login: the file only exists to hand the
    generated admin password to the operator once, so as soon as *any*
    login succeeds it has served its purpose and should stop existing on
    disk (bounds the plaintext-at-rest window instead of leaving it there
    indefinitely).
    """
    initial_admin_password_file().unlink(missing_ok=True)


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


def load_oidc_config() -> OidcConfig:
    path = _oidc_config_file()
    if not path.exists():
        return OidcConfig()
    with path.open() as f:
        return OidcConfigDocument.model_validate(json.load(f)).config


def save_oidc_config(config: OidcConfig) -> None:
    path = _oidc_config_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with tmp.open("w") as f:
        json.dump(OidcConfigDocument(config=config).model_dump(), f, indent=2)
    tmp.replace(path)
