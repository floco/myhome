from __future__ import annotations
from typing import Literal
from pydantic import BaseModel


class Notification(BaseModel):
    type: Literal["chore", "low_stock", "warranty", "build_task_due", "build_validation", "build_phase_complete"]
    refId: str
    title: str
    detail: str
    severity: Literal["info", "warning", "critical"]


class NotificationState(BaseModel):
    version: int = 1
    warrantyNotified: dict[str, str] = {}
    buildPhasesNotified: list[str] = []
    lastPushDigestDate: str | None = None
