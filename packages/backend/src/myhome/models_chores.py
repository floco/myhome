from __future__ import annotations
from pydantic import BaseModel


class Position(BaseModel):
    x: float
    y: float


class Chore(BaseModel):
    id: str
    donetickId: int | None = None
    name: str
    emoji: str
    periodDays: float
    nextDueDate: str   # ISO 8601
    description: str = ""


class Assignment(BaseModel):
    id: str
    choreId: str
    roomId: str | None = None
    position: Position | None = None


class ChoreDocument(BaseModel):
    version: int = 1
    chores: list[Chore] = []
    assignments: list[Assignment] = []


class ChoreCreate(BaseModel):
    name: str
    emoji: str
    periodDays: float
    nextDueDate: str
    description: str = ""
    donetickId: int | None = None


class ChoreUpdate(BaseModel):
    name: str | None = None
    emoji: str | None = None
    periodDays: float | None = None
    nextDueDate: str | None = None
    description: str | None = None


class AssignmentCreate(BaseModel):
    choreId: str
    roomId: str | None = None
    position: Position | None = None


class AssignmentUpdate(BaseModel):
    position: Position | None = None


class ImportRequest(BaseModel):
    token: str


class ImportResponse(BaseModel):
    imported: int
