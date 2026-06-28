from __future__ import annotations
from pydantic import BaseModel


class KBEntry(BaseModel):
    id: str
    title: str
    content: str = ""
    createdAt: str
    updatedAt: str


class KBDocument(BaseModel):
    version: int = 1
    entries: list[KBEntry] = []


class KBCreate(BaseModel):
    title: str
    content: str = ""


class KBUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
