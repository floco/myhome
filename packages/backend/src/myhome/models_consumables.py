from __future__ import annotations
from pydantic import BaseModel


class ConsumablePosition(BaseModel):
    x: float
    y: float


class ConsumablePlacement(BaseModel):
    floorId: str
    roomId: str | None = None
    position: ConsumablePosition


class Consumable(BaseModel):
    id: str
    name: str
    emoji: str = "🛒"
    unit: str = "count"
    quantity: float = 0.0
    minQuantity: float = 1.0
    categoryId: str | None = None
    description: str = ""
    placement: ConsumablePlacement | None = None


class ConsumableTransaction(BaseModel):
    id: str
    consumableId: str
    delta: float
    quantityAfter: float
    note: str = ""
    timestamp: str


class ConsumableDocument(BaseModel):
    version: int = 1
    consumables: list[Consumable] = []
    transactions: list[ConsumableTransaction] = []


class ConsumableCreate(BaseModel):
    name: str
    emoji: str = "🛒"
    unit: str = "count"
    quantity: float = 0.0
    minQuantity: float = 1.0
    categoryId: str | None = None
    description: str = ""


class ConsumableUpdate(BaseModel):
    name: str | None = None
    emoji: str | None = None
    unit: str | None = None
    minQuantity: float | None = None
    categoryId: str | None = None
    description: str | None = None


class StockUpdate(BaseModel):
    quantity: float
    note: str = ""


class ConsumablePlacementUpdate(BaseModel):
    placement: ConsumablePlacement | None = None
