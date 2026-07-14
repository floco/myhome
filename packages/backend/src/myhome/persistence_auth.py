# packages/backend/src/myhome/persistence_auth.py
import json
import os
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from .db import get_engine
from .models_auth import ApiToken, OidcConfig, TokenDocument, User, UserDocument
from .schema import api_tokens as api_tokens_table, oidc_config as oidc_config_table, users as users_table


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
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(select(users_table).order_by(users_table.c.order_index)).mappings().all()
    return UserDocument(users=[
        User(
            id=r["id"], username=r["username"], password_hash=r["password_hash"], role=r["role"],
            created_at=r["created_at"], auth_provider=r["auth_provider"], oidc_sub=r["oidc_sub"],
        )
        for r in rows
    ])


def save_users(doc: UserDocument) -> None:
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(users_table.delete())
        if doc.users:
            conn.execute(users_table.insert(), [
                {
                    "id": u.id, "order_index": i, "username": u.username, "password_hash": u.password_hash,
                    "role": u.role, "created_at": u.created_at, "auth_provider": u.auth_provider,
                    "oidc_sub": u.oidc_sub,
                }
                for i, u in enumerate(doc.users)
            ])


def load_tokens() -> TokenDocument:
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(select(api_tokens_table).order_by(api_tokens_table.c.order_index)).mappings().all()
    return TokenDocument(tokens=[
        ApiToken(
            id=r["id"], name=r["name"], token_hash=r["token_hash"], role=r["role"],
            owner_id=r["owner_id"], created_at=r["created_at"], last_used_at=r["last_used_at"],
        )
        for r in rows
    ])


def save_tokens(doc: TokenDocument) -> None:
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(api_tokens_table.delete())
        if doc.tokens:
            conn.execute(api_tokens_table.insert(), [
                {
                    "id": t.id, "order_index": i, "name": t.name, "token_hash": t.token_hash,
                    "role": t.role, "owner_id": t.owner_id, "created_at": t.created_at,
                    "last_used_at": t.last_used_at,
                }
                for i, t in enumerate(doc.tokens)
            ])


def load_oidc_config() -> OidcConfig:
    engine = get_engine()
    with engine.connect() as conn:
        row = conn.execute(select(oidc_config_table).where(oidc_config_table.c.id == 1)).mappings().first()
    if row is None:
        return OidcConfig()
    return OidcConfig(
        enabled=bool(row["enabled"]), provider_name=row["provider_name"], issuer=row["issuer"],
        client_id=row["client_id"], client_secret=row["client_secret"], default_role=row["default_role"],
        scopes=json.loads(row["scopes"]),
    )


def save_oidc_config(config: OidcConfig) -> None:
    engine = get_engine()
    with engine.begin() as conn:
        stmt = sqlite_insert(oidc_config_table).values(
            id=1, enabled=config.enabled, provider_name=config.provider_name, issuer=config.issuer,
            client_id=config.client_id, client_secret=config.client_secret, default_role=config.default_role,
            scopes=json.dumps(config.scopes),
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=[oidc_config_table.c.id],
            set_={
                "enabled": stmt.excluded.enabled, "provider_name": stmt.excluded.provider_name,
                "issuer": stmt.excluded.issuer, "client_id": stmt.excluded.client_id,
                "client_secret": stmt.excluded.client_secret, "default_role": stmt.excluded.default_role,
                "scopes": stmt.excluded.scopes,
            },
        )
        conn.execute(stmt)
