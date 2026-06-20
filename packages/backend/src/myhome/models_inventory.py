from __future__ import annotations
from pydantic import BaseModel


class InventoryPosition(BaseModel):
    x: float
    y: float


class InventoryPlacement(BaseModel):
    floorId: str
    roomId: str | None = None
    position: InventoryPosition


class InventoryItem(BaseModel):
    id: str
    name: str
    emoji: str = "📦"
    category: str = ""
    brand: str | None = None
    model: str | None = None
    serialNumber: str | None = None
    purchaseDate: str | None = None
    purchasePrice: float | None = None
    warrantyExpiryDate: str | None = None
    notes: str = ""
    placement: InventoryPlacement | None = None


class InventoryDocument(BaseModel):
    version: int = 1
    items: list[InventoryItem] = []


class InventoryItemCreate(BaseModel):
    name: str
    emoji: str = "📦"
    category: str = ""
    brand: str | None = None
    model: str | None = None
    serialNumber: str | None = None
    purchaseDate: str | None = None
    purchasePrice: float | None = None
    warrantyExpiryDate: str | None = None
    notes: str = ""


class InventoryItemUpdate(BaseModel):
    name: str | None = None
    emoji: str | None = None
    category: str | None = None
    brand: str | None = None
    model: str | None = None
    serialNumber: str | None = None
    purchaseDate: str | None = None
    purchasePrice: float | None = None
    warrantyExpiryDate: str | None = None
    notes: str | None = None


class PlacementUpdate(BaseModel):
    placement: InventoryPlacement | None = None
