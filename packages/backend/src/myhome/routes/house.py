from fastapi import APIRouter, HTTPException
from ..models import HouseDocument
from ..persistence import load_house, save_house

router = APIRouter()


@router.get("/api/house", response_model=HouseDocument)
def get_house() -> HouseDocument:
    doc = load_house()
    if doc is None:
        raise HTTPException(status_code=404, detail="No house document found")
    return doc


@router.put("/api/house", status_code=204)
def put_house(doc: HouseDocument) -> None:
    save_house(doc)
