from fastapi import APIRouter, HTTPException
from ..models_settings import CostCategory, CostCategoryPlacement, InventoryCategory, SettingsDocument
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


@router.put("/api/settings/cost-categories/{id}/placement", status_code=204)
def put_cost_category_placement(id: str, body: CostCategoryPlacement | None) -> None:
    doc = load_settings()
    cat = next((c for c in doc.costCategories if c.id == id), None)
    if cat is None:
        raise HTTPException(status_code=404)
    cat.placement = body
    save_settings(doc)


@router.delete("/api/settings/cost-categories/{id}/placement", status_code=204)
def delete_cost_category_placement(id: str) -> None:
    doc = load_settings()
    cat = next((c for c in doc.costCategories if c.id == id), None)
    if cat is None:
        raise HTTPException(status_code=404)
    cat.placement = None
    save_settings(doc)
