from __future__ import annotations
from typing import Literal
from pydantic import BaseModel


class ActivityEntry(BaseModel):
    id: str
    timestamp: str  # ISO 8601 UTC
    userId: str
    username: str
    module: Literal["chores", "works", "costs", "inventory", "consumables", "kb", "locations", "properties"]
    action: Literal["create", "update", "delete", "complete", "restore", "delete_forever", "empty_trash"]
    entityLabel: str
    refId: str | None = None


class ActivityLogDocument(BaseModel):
    version: int = 1
    entries: list[ActivityEntry] = []
