from fastapi import APIRouter, HTTPException
from ..models_settings import (
    ConsumableCategory,
    CostCategory,
    CostCategoryPlacement,
    InventoryCategory,
    WorkCategory,
    Supplier,
    SettingsDocument,
)
from ..persistence_settings import load_settings, save_settings

router = APIRouter()


@router.get("/api/homes/{home_id}/settings", response_model=SettingsDocument)
def get_settings(home_id: str) -> SettingsDocument:
    return load_settings(home_id)


@router.put("/api/homes/{home_id}/settings/cost-categories", status_code=204)
def put_cost_categories(home_id: str, body: list[CostCategory]) -> None:
    doc = load_settings(home_id)
    doc.costCategories = body
    save_settings(home_id, doc)


@router.put("/api/homes/{home_id}/settings/inventory-categories", status_code=204)
def put_inventory_categories(home_id: str, body: list[InventoryCategory]) -> None:
    doc = load_settings(home_id)
    doc.inventoryCategories = body
    save_settings(home_id, doc)


@router.put("/api/homes/{home_id}/settings/cost-categories/{id}/placement", status_code=204)
def put_cost_category_placement(home_id: str, id: str, body: CostCategoryPlacement | None) -> None:
    doc = load_settings(home_id)
    cat = next((c for c in doc.costCategories if c.id == id), None)
    if cat is None:
        raise HTTPException(status_code=404)
    cat.placement = body
    save_settings(home_id, doc)


@router.delete("/api/homes/{home_id}/settings/cost-categories/{id}/placement", status_code=204)
def delete_cost_category_placement(home_id: str, id: str) -> None:
    doc = load_settings(home_id)
    cat = next((c for c in doc.costCategories if c.id == id), None)
    if cat is None:
        raise HTTPException(status_code=404)
    cat.placement = None
    save_settings(home_id, doc)


@router.put("/api/homes/{home_id}/settings/work-categories", status_code=204)
def put_work_categories(home_id: str, body: list[WorkCategory]) -> None:
    doc = load_settings(home_id)
    doc.workCategories = body
    save_settings(home_id, doc)


@router.put("/api/homes/{home_id}/settings/suppliers", status_code=204)
def put_suppliers(home_id: str, body: list[Supplier]) -> None:
    doc = load_settings(home_id)
    doc.suppliers = body
    save_settings(home_id, doc)


@router.put("/api/homes/{home_id}/settings/consumable-units", status_code=204)
def put_consumable_units(home_id: str, body: list[str]) -> None:
    doc = load_settings(home_id)
    doc.consumableUnits = body
    save_settings(home_id, doc)


@router.put("/api/homes/{home_id}/settings/consumable-categories", status_code=204)
def put_consumable_categories(home_id: str, body: list[ConsumableCategory]) -> None:
    doc = load_settings(home_id)
    doc.consumableCategories = body
    save_settings(home_id, doc)
