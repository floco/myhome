# packages/backend/src/myhome/persistence_mcp.py
from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from .db import get_engine
from .models_mcp import McpConfig
from .schema import mcp_config as mcp_config_table


def load_mcp_config() -> McpConfig:
    engine = get_engine()
    with engine.connect() as conn:
        row = conn.execute(select(mcp_config_table).where(mcp_config_table.c.id == 1)).mappings().first()
    if row is None:
        return McpConfig()
    return McpConfig(enabled=bool(row["enabled"]))


def save_mcp_config(config: McpConfig) -> None:
    engine = get_engine()
    with engine.begin() as conn:
        stmt = sqlite_insert(mcp_config_table).values(id=1, enabled=config.enabled)
        stmt = stmt.on_conflict_do_update(
            index_elements=[mcp_config_table.c.id], set_={"enabled": stmt.excluded.enabled},
        )
        conn.execute(stmt)
