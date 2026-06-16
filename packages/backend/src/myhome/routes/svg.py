from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from ..persistence import load_house
from ..svg_render import render_floor_svg

router = APIRouter()


@router.get("/api/house/floors/{floor_id}/svg")
def get_floor_svg(floor_id: str) -> Response:
    doc = load_house()
    if doc is None:
        raise HTTPException(status_code=404, detail="No house document found")
    floor = next((f for f in doc.floors if f.id == floor_id), None)
    if floor is None:
        raise HTTPException(status_code=404, detail="Floor not found")
    return Response(content=render_floor_svg(floor), media_type="image/svg+xml")
