from __future__ import annotations
from typing import Literal
from pydantic import BaseModel


class InsurancePolicy(BaseModel):
    id: str
    name: str
    categoryId: str
    contactId: str | None = None
    policyNumber: str | None = None
    coverageSummary: str = ""
    conditionsUrl: str | None = None
    startDate: str | None = None
    endDate: str | None = None
    premiumAmount: float | None = None
    premiumFrequency: Literal["monthly", "quarterly", "annual", "other"] = "annual"
    includeInCosts: bool = False
    alternatives: str = ""
    notes: str = ""
    attachments: list[str] = []
    linkedCostEntryId: str | None = None


class InsuranceDocument(BaseModel):
    version: int = 1
    policies: list[InsurancePolicy] = []


class InsurancePolicyCreate(BaseModel):
    name: str
    categoryId: str
    contactId: str | None = None
    policyNumber: str | None = None
    coverageSummary: str = ""
    conditionsUrl: str | None = None
    startDate: str | None = None
    endDate: str | None = None
    premiumAmount: float | None = None
    premiumFrequency: Literal["monthly", "quarterly", "annual", "other"] = "annual"
    includeInCosts: bool = False
    alternatives: str = ""
    notes: str = ""


class InsurancePolicyUpdate(BaseModel):
    name: str | None = None
    categoryId: str | None = None
    contactId: str | None = None
    policyNumber: str | None = None
    coverageSummary: str | None = None
    conditionsUrl: str | None = None
    startDate: str | None = None
    endDate: str | None = None
    premiumAmount: float | None = None
    premiumFrequency: Literal["monthly", "quarterly", "annual", "other"] | None = None
    includeInCosts: bool | None = None
    alternatives: str | None = None
    notes: str | None = None
