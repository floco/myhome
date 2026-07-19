# packages/backend/src/myhome/models_properties.py
from __future__ import annotations
from typing import Literal
from pydantic import BaseModel

PropertyType = Literal["land", "house", "new_build"]
PropertyStatus = Literal["watching", "visited", "proposal_made", "purchased", "rejected"]


class Property(BaseModel):
    id: str
    name: str
    emoji: str = "🏠"
    type: PropertyType
    status: PropertyStatus = "watching"
    locationId: str | None = None
    address: str = ""
    price: float | None = None
    landSize: float | None = None
    builtSize: float | None = None
    bedrooms: int | None = None
    bathrooms: int | None = None
    listingUrl: str | None = None
    contact: str = ""
    pros: list[str] = []
    cons: list[str] = []
    notes: str = ""
    attachments: list[str] = []


class PropertiesDocument(BaseModel):
    version: int = 1
    properties: list[Property] = []


class PropertyCreate(BaseModel):
    name: str
    emoji: str = "🏠"
    type: PropertyType
    status: PropertyStatus = "watching"
    locationId: str | None = None
    address: str = ""
    price: float | None = None
    landSize: float | None = None
    builtSize: float | None = None
    bedrooms: int | None = None
    bathrooms: int | None = None
    listingUrl: str | None = None
    contact: str = ""
    pros: list[str] = []
    cons: list[str] = []
    notes: str = ""


class PropertyUpdate(BaseModel):
    name: str | None = None
    emoji: str | None = None
    type: PropertyType | None = None
    status: PropertyStatus | None = None
    locationId: str | None = None
    address: str | None = None
    price: float | None = None
    landSize: float | None = None
    builtSize: float | None = None
    bedrooms: int | None = None
    bathrooms: int | None = None
    listingUrl: str | None = None
    contact: str | None = None
    pros: list[str] | None = None
    cons: list[str] | None = None
    notes: str | None = None
