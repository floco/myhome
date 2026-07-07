from __future__ import annotations
from typing import Literal
from pydantic import BaseModel


class BackupConfig(BaseModel):
    enabled: bool = False
    frequency: Literal["daily", "weekly", "monthly"] = "daily"
    time: str = "03:00"
    dayOfWeek: int = 7
    dayOfMonth: int = 1
    retentionCount: int = 7


class BackupEntry(BaseModel):
    filename: str
    createdAt: str
    sizeBytes: int


class BackupState(BaseModel):
    lastRunDate: str | None = None
