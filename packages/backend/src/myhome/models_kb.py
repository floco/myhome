from __future__ import annotations
from pydantic import BaseModel


class KBEntry(BaseModel):
    id: str
    title: str
    content: str = ""
    createdAt: str
    updatedAt: str
    attachments: list[str] = []
    parentId: str | None = None
    icon: str = "📄"
    order: int = 0
    deletedAt: str | None = None


class KBDocument(BaseModel):
    version: int = 1
    entries: list[KBEntry] = []


class KBTrashDocument(BaseModel):
    entries: list[KBEntry] = []


class KBCreate(BaseModel):
    title: str
    content: str = ""
    parentId: str | None = None
    icon: str = "📄"


class KBUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
    parentId: str | None = None
    icon: str | None = None


class KBReorder(BaseModel):
    parentId: str | None = None
    orderedIds: list[str]
