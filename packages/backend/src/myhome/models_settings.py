from __future__ import annotations
from pydantic import BaseModel


class CostCategoryPosition(BaseModel):
    x: float
    y: float


class CostCategoryPlacement(BaseModel):
    floorId: str
    position: CostCategoryPosition


class CostCategory(BaseModel):
    id: str
    name: str
    emoji: str
    unit: str | None = None
    color: str = "#4466cc"
    placement: CostCategoryPlacement | None = None


class InventoryCategory(BaseModel):
    id: str
    name: str


class WorkCategory(BaseModel):
    id: str
    name: str
    emoji: str


class Supplier(BaseModel):
    id: str
    name: str


def _default_cost_categories() -> list[CostCategory]:
    return [
        CostCategory(id="cat-fuel",        name="Fuel / Mazout",  emoji="🛢", unit="L",      color="#4466cc"),
        CostCategory(id="cat-electricity", name="Electricity",    emoji="💡", unit="kWh",    color="#44aacc"),
        CostCategory(id="cat-water",       name="Water",          emoji="💧", unit="m³",     color="#44ccaa"),
        CostCategory(id="cat-wood",        name="Wood",           emoji="🪵", unit="stère",  color="#cc8844"),
        CostCategory(id="cat-tax",         name="Property Tax",   emoji="🏠", unit=None,     color="#9966cc"),
    ]


def _default_inventory_categories() -> list[InventoryCategory]:
    return [
        InventoryCategory(id="inv-electronics", name="Electronics"),
        InventoryCategory(id="inv-furniture",   name="Furniture"),
        InventoryCategory(id="inv-appliance",   name="Appliance"),
        InventoryCategory(id="inv-tool",        name="Tool"),
        InventoryCategory(id="inv-artwork",     name="Artwork"),
        InventoryCategory(id="inv-other",       name="Other"),
    ]


def _default_work_categories() -> list[WorkCategory]:
    return [
        WorkCategory(id="wcat-plumbing",   name="Plumbing",   emoji="🔧"),
        WorkCategory(id="wcat-electrical", name="Electrical", emoji="⚡"),
        WorkCategory(id="wcat-roofing",    name="Roofing",    emoji="🏠"),
        WorkCategory(id="wcat-painting",   name="Painting",   emoji="🎨"),
        WorkCategory(id="wcat-flooring",   name="Flooring",   emoji="🪵"),
    ]


class SettingsDocument(BaseModel):
    version: int = 1
    costCategories: list[CostCategory] = []
    inventoryCategories: list[InventoryCategory] = []
    workCategories: list[WorkCategory] = []
    suppliers: list[Supplier] = []
