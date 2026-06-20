from fastapi import APIRouter
from ..models_settings import CostCategory, InventoryCategory, SettingsDocument
from ..persistence_settings import load_settings, save_settings

router = APIRouter()


@router.get("/api/settings", response_model=SettingsDocument)
def get_settings() -> SettingsDocument:
    return load_settings()


@router.put("/api/settings/cost-categories", status_code=204)
def put_cost_categories(body: list[CostCategory]) -> None:
    doc = load_settings()
    doc.costCategories = body
    save_settings(doc)


@router.put("/api/settings/inventory-categories", status_code=204)
def put_inventory_categories(body: list[InventoryCategory]) -> None:
    doc = load_settings()
    doc.inventoryCategories = body
    save_settings(doc)
