from __future__ import annotations
from typing import Literal
from pydantic import BaseModel


class Point(BaseModel):
    x: float
    y: float


class Wall(BaseModel):
    id: str
    start: Point
    end: Point
    thickness: float | None = None
    type: Literal["wall", "divider"]


class Opening(BaseModel):
    id: str
    wallId: str
    type: Literal["door", "window"]
    offset: float
    width: float
    swing: Literal["left-in", "right-in", "left-out", "right-out"] | None = None


class Room(BaseModel):
    id: str
    label: str
    haAreaId: str | None = None
    polygon: list[Point] | None = None
    areaM2: float


class FurnitureObject(BaseModel):
    id: str
    templateId: str
    x: float
    y: float
    width: float
    height: float
    rotation: float = 0.0


class Floor(BaseModel):
    id: str
    name: str
    order: int
    walls: list[Wall]
    openings: list[Opening]
    rooms: list[Room]
    furnitureObjects: list[FurnitureObject] = []


class House(BaseModel):
    name: str
    units: Literal["m"] = "m"
    gridSnap: float = 0.1


class HouseDocument(BaseModel):
    version: int = 1
    house: House
    floors: list[Floor]
