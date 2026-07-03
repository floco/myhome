from fastapi import APIRouter, HTTPException
from ..models import HouseDocument
from ..persistence import load_house, save_house

router = APIRouter()


@router.get("/api/homes/{home_id}/house", response_model=HouseDocument)
def get_house(home_id: str) -> HouseDocument:
    doc = load_house(home_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="No house document found")
    return doc


@router.put("/api/homes/{home_id}/house", status_code=204)
def put_house(home_id: str, doc: HouseDocument) -> None:
    save_house(home_id, doc)
