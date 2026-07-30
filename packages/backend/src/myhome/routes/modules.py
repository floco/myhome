# packages/backend/src/myhome/routes/modules.py
from fastapi import APIRouter, HTTPException

from ..deps import require_auth
from ..persistence_activity import log_activity
from ..persistence_build import delete_build_project
from ..persistence_chores import reset_chores
from ..persistence_consumables import reset_consumables
from ..persistence_contacts import reset_contacts
from ..persistence_costs import reset_costs
from ..persistence_homes import load_homes
from ..persistence_insurance import reset_insurance
from ..persistence_inventory import reset_inventory
from ..persistence_kb import reset_kb
from ..persistence_locations import reset_locations
from ..persistence_properties import reset_properties
from ..persistence_works import reset_works

router = APIRouter()

RESET_HANDLERS = {
    "chores": reset_chores,
    "inventory": reset_inventory,
    "consumables": reset_consumables,
    "works": reset_works,
    "kb": reset_kb,
    "costs": reset_costs,
    "locations": reset_locations,
    "properties": reset_properties,
    "build": delete_build_project,
    "contacts": reset_contacts,
    "insurance": reset_insurance,
}


@router.post("/api/homes/{home_id}/modules/{module_id}/reset", status_code=204)
def reset_module_route(
    home_id: str, module_id: str,
    current_user: tuple[str, str] = require_auth("admin"),
) -> None:
    handler = RESET_HANDLERS.get(module_id)
    if handler is None:
        raise HTTPException(status_code=400, detail=f"Unknown or non-resettable module: {module_id!r}")
    home = next((h for h in load_homes().homes if h.id == home_id), None)
    if home is None:
        raise HTTPException(status_code=404)
    handler(home_id)
    log_activity(home_id, current_user[0], module_id, "reset", module_id)
