from __future__ import annotations
from typing import Literal
from pydantic import BaseModel


class WorkPosition(BaseModel):
    x: float
    y: float


class WorkPlacement(BaseModel):
    floorId: str
    position: WorkPosition


class Work(BaseModel):
    id: str
    title: str
    description: str = ""
    status: Literal["planned", "in_progress", "done"] = "planned"
    categoryId: str | None = None
    date: str
    totalCost: float | None = None
    supplierId: str | None = None
    notes: str = ""
    attachments: list[str] = []
    placement: WorkPlacement | None = None


class WorksDocument(BaseModel):
    version: int = 1
    works: list[Work] = []


class WorkCreate(BaseModel):
    title: str
    description: str = ""
    status: Literal["planned", "in_progress", "done"] = "planned"
    categoryId: str | None = None
    date: str
    totalCost: float | None = None
    supplierId: str | None = None
    notes: str = ""


class WorkUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    status: Literal["planned", "in_progress", "done"] | None = None
    categoryId: str | None = None
    date: str | None = None
    totalCost: float | None = None
    supplierId: str | None = None
    notes: str | None = None
