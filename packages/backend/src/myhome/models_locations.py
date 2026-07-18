# packages/backend/src/myhome/models_locations.py
from __future__ import annotations
from typing import Literal
from pydantic import BaseModel

Weight = Literal["low", "medium", "high"]


class LocationCriterion(BaseModel):
    id: str
    name: str
    description: str = ""
    weight: Weight = "medium"


class Location(BaseModel):
    id: str
    name: str
    emoji: str = "📍"


class LocationRating(BaseModel):
    locationId: str
    criterionId: str
    score: int | None = None
    note: str = ""


class LocationsDocument(BaseModel):
    version: int = 1
    criteria: list[LocationCriterion] = []
    locations: list[Location] = []
    ratings: list[LocationRating] = []


class LocationCriterionCreate(BaseModel):
    name: str
    description: str = ""
    weight: Weight = "medium"


class LocationCriterionUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    weight: Weight | None = None


class LocationCreate(BaseModel):
    name: str
    emoji: str = "📍"


class LocationUpdate(BaseModel):
    name: str | None = None
    emoji: str | None = None


class ReorderRequest(BaseModel):
    orderedIds: list[str]


class RatingUpdate(BaseModel):
    score: int | None = None
    note: str = ""
