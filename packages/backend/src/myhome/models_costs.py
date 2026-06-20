from __future__ import annotations
from pydantic import BaseModel


class CostEntry(BaseModel):
    id: str
    categoryId: str
    date: str                      # ISO date e.g. "2025-10-14"
    totalAmount: float
    quantity: float | None = None
    unitPrice: float | None = None
    supplier: str | None = None
    notes: str = ""
    roomId: str | None = None


class CostsDocument(BaseModel):
    version: int = 1
    entries: list[CostEntry] = []


class CostEntryCreate(BaseModel):
    categoryId: str
    date: str
    totalAmount: float
    quantity: float | None = None
    unitPrice: float | None = None
    supplier: str | None = None
    notes: str = ""
    roomId: str | None = None


class CostEntryUpdate(BaseModel):
    categoryId: str | None = None
    date: str | None = None
    totalAmount: float | None = None
    quantity: float | None = None
    unitPrice: float | None = None
    supplier: str | None = None
    notes: str | None = None
    roomId: str | None = None
