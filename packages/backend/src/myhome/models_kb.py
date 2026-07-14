from __future__ import annotations
from pydantic import BaseModel


class KBEntry(BaseModel):
    id: str
    title: str
    content: str = ""
    createdAt: str
    updatedAt: str
    attachments: list[str] = []
    folderId: str | None = None


class KBFolder(BaseModel):
    id: str
    name: str
    parentId: str | None = None


class KBDocument(BaseModel):
    version: int = 1
    entries: list[KBEntry] = []
    folders: list[KBFolder] = []


class KBCreate(BaseModel):
    title: str
    content: str = ""
    folderId: str | None = None


class KBUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
    folderId: str | None = None


class KBFolderCreate(BaseModel):
    name: str
    parentId: str | None = None


class KBFolderUpdate(BaseModel):
    name: str | None = None
    parentId: str | None = None
