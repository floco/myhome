# packages/backend/src/myhome/models_homes.py
from __future__ import annotations
from typing import Literal
from pydantic import BaseModel

ALL_MODULE_IDS: list[str] = [
    "home", "plan", "chores", "inventory", "consumables",
    "works", "kb", "costs",
    "locations", "properties", "budget", "visits", "contacts", "checklist",
]

DEFAULT_EXISTING_MODULES: list[str] = [
    "home", "plan", "chores", "inventory", "consumables", "works", "kb", "costs",
]

DEFAULT_PROJECT_MODULES: list[str] = ["home", "plan", "works", "kb"]


class Home(BaseModel):
    id: str
    name: str
    type: Literal["existing", "project"]
    enabledModules: list[str]
    createdAt: str


class HomeCreate(BaseModel):
    name: str
    type: Literal["existing", "project"]


class HomePatch(BaseModel):
    name: str | None = None
    type: Literal["existing", "project"] | None = None
    enabledModules: list[str] | None = None


class HomesDocument(BaseModel):
    version: int = 1
    homes: list[Home] = []
