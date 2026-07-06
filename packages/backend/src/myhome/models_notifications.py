from __future__ import annotations
from typing import Literal
from pydantic import BaseModel


class Notification(BaseModel):
    type: Literal["chore", "low_stock", "warranty"]
    refId: str
    title: str
    detail: str
    severity: Literal["info", "warning", "critical"]


class NotificationState(BaseModel):
    version: int = 1
    warrantyNotified: dict[str, str] = {}
    lastPushDigestDate: str | None = None
