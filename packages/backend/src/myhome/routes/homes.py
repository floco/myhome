# packages/backend/src/myhome/routes/homes.py
from fastapi import APIRouter, HTTPException

from ..models_homes import Home, HomeCreate, HomePatch
from ..persistence_homes import (
    load_homes,
    create_home,
    patch_home,
    delete_home,
)

router = APIRouter()


@router.get("/api/homes", response_model=list[Home])
def get_homes() -> list[Home]:
    return load_homes().homes


@router.post("/api/homes", response_model=Home, status_code=201)
def post_homes(body: HomeCreate) -> Home:
    return create_home(body.name, body.type)


@router.patch("/api/homes/{home_id}", response_model=Home)
def patch_home_route(home_id: str, body: HomePatch) -> Home:
    home = patch_home(home_id, body.name, body.type, body.enabledModules)
    if home is None:
        raise HTTPException(status_code=404)
    return home


@router.delete("/api/homes/{home_id}", status_code=204)
def delete_home_route(home_id: str) -> None:
    if not delete_home(home_id):
        raise HTTPException(status_code=404)
