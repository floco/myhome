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


class ContactType(BaseModel):
    id: str
    name: str


class ConsumableCategory(BaseModel):
    id: str
    name: str
    emoji: str


class InsuranceCategory(BaseModel):
    id: str
    name: str
    emoji: str


class Owner(BaseModel):
    id: str
    name: str


class Store(BaseModel):
    id: str
    name: str


class NotificationSettings(BaseModel):
    enabled: bool = True
    choresDueSoonThreshold: float = 0.25
    warrantyDaysThreshold: int = 30
    buildTaskDueSoonThreshold: int = 7
    haPushEnabled: bool = False
    haNotifyService: str | None = None
    haPushTime: str = "08:00"


def _default_consumable_units() -> list[str]:
    return ["count", "L", "mL", "kg", "g", "packs", "rolls", "pairs"]


def _default_cost_categories() -> list[CostCategory]:
    return [
        CostCategory(id="cat-fuel",        name="Fuel / Mazout",  emoji="🛢", unit="L",      color="#4466cc"),
        CostCategory(id="cat-electricity", name="Electricity",    emoji="💡", unit="kWh",    color="#44aacc"),
        CostCategory(id="cat-water",       name="Water",          emoji="💧", unit="m³",     color="#44ccaa"),
        CostCategory(id="cat-wood",        name="Wood",           emoji="🪵", unit="stère",  color="#cc8844"),
        CostCategory(id="cat-tax",         name="Property Tax",   emoji="🏠", unit=None,     color="#9966cc"),
        CostCategory(id="cat-insurance",   name="Insurance",      emoji="🛡️", unit=None,     color="#7a5cc4"),
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


def _default_insurance_categories() -> list[InsuranceCategory]:
    return [
        InsuranceCategory(id="icat-home",      name="Home",      emoji="🏠"),
        InsuranceCategory(id="icat-auto",      name="Auto",      emoji="🚗"),
        InsuranceCategory(id="icat-health",    name="Health",    emoji="⚕️"),
        InsuranceCategory(id="icat-life",      name="Life",      emoji="❤️"),
        InsuranceCategory(id="icat-travel",    name="Travel",    emoji="✈️"),
        InsuranceCategory(id="icat-liability", name="Liability", emoji="🛡️"),
    ]


def _default_contact_types() -> list[ContactType]:
    return [
        ContactType(id="ctype-contractor", name="Contractor"),
        ContactType(id="ctype-supplier", name="Supplier"),
        ContactType(id="ctype-service", name="Service Provider"),
        ContactType(id="ctype-agent", name="Agent"),
        ContactType(id="ctype-notary", name="Notary"),
        ContactType(id="ctype-other", name="Other"),
    ]


class SettingsDocument(BaseModel):
    version: int = 1
    costCategories: list[CostCategory] = []
    inventoryCategories: list[InventoryCategory] = []
    workCategories: list[WorkCategory] = []
    contactTypes: list[ContactType] = []
    consumableUnits: list[str] = []
    consumableCategories: list[ConsumableCategory] = []
    insuranceCategories: list[InsuranceCategory] = []
    owners: list[Owner] = []
    stores: list[Store] = []
    notifications: NotificationSettings = NotificationSettings()
