# packages/backend/src/myhome/models_property_search.py
"""Models for the AI property search: named searches, suggestions inbox, runs, config.

Provider-neutral by design: the runner that executes searches is an external
process; myhome only sees an opaque ``provider`` string in run usage.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Frequency = Literal["daily", "weekly", "monthly"]
SuggestionStatus = Literal["new", "pinned", "accepted", "rejected"]
RunStatus = Literal["running", "succeeded", "failed", "usage_limited"]
SuggestionType = Literal["land", "house", "new_build"]
SearchLanguage = Literal["en", "fr"]

_TIME_PATTERN = r"^([01]\d|2[0-3]):[0-5]\d$"


class _SearchFields(BaseModel):
    name: str = Field(min_length=1)
    prompt: str = Field(min_length=1)
    enabled: bool = True
    frequency: Frequency = "daily"
    time: str = Field(default="08:00", pattern=_TIME_PATTERN)
    dayOfWeek: int = Field(default=1, ge=1, le=7)
    dayOfMonth: int = Field(default=1, ge=1, le=31)
    maxResultsPerRun: int = Field(default=10, ge=1, le=50)
    maxListingAgeDays: int = Field(default=7, ge=1, le=365)


class PropertySearch(_SearchFields):
    id: str
    createdAt: str
    runRequestedAt: str | None = None
    lastRunAt: str | None = None
    lastRunStatus: RunStatus | None = None
    lastRunError: str | None = None
    lastRunNew: int | None = None
    lastRunDuplicates: int | None = None
    lastRunEmailError: str | None = None


class PropertySearchCreate(_SearchFields):
    pass


class PropertySearchUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    prompt: str | None = Field(default=None, min_length=1)
    enabled: bool | None = None
    frequency: Frequency | None = None
    time: str | None = Field(default=None, pattern=_TIME_PATTERN)
    dayOfWeek: int | None = Field(default=None, ge=1, le=7)
    dayOfMonth: int | None = Field(default=None, ge=1, le=31)
    maxResultsPerRun: int | None = Field(default=None, ge=1, le=50)
    maxListingAgeDays: int | None = Field(default=None, ge=1, le=365)


class PropertySuggestion(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)

    id: str
    searchId: str
    runId: str
    title: str
    type: SuggestionType | None = None
    price: float | None = None
    currency: str | None = None
    landSize: float | None = None
    builtSize: float | None = None
    bedrooms: int | None = None
    bathrooms: int | None = None
    location: str = ""
    country: str | None = None
    region: str | None = None
    city: str | None = None
    sourceSite: str = ""
    listingUrl: str
    imageUrl: str | None = None
    publishedAt: str | None = None
    reason: str = ""
    status: SuggestionStatus = "new"
    createdAt: str
    acceptedPropertyId: str | None = None


class QuotaUsage(BaseModel):
    label: str
    usedPct: int | None = None


class SearchUsage(BaseModel):
    provider: str = ""
    tokensByModel: dict[str, int] = {}
    totalTokens: int = 0
    quotas: list[QuotaUsage] = []


class PropertySearchRun(BaseModel):
    id: str
    searchId: str
    slot: str
    startedAt: str
    finishedAt: str | None = None
    status: RunStatus
    error: str | None = None
    emailError: str | None = None
    sites: list[str] = []
    searchQueries: list[str] = []
    usage: SearchUsage | None = None
    receivedCount: int = 0
    newCount: int = 0
    duplicateCount: int = 0


class PropertySearchConfig(BaseModel):
    retentionDays: int = 30
    brevoApiKey: str = ""
    senderEmail: str = ""
    senderName: str = "My Home"
    recipients: list[str] = []
    appBaseUrl: str = ""
    language: SearchLanguage = "en"


class PropertySearchConfigOut(BaseModel):
    retentionDays: int
    brevoApiKeySet: bool
    senderEmail: str
    senderName: str
    recipients: list[str]
    appBaseUrl: str
    language: SearchLanguage


class PropertySearchConfigUpdate(BaseModel):
    retentionDays: int | None = Field(default=None, ge=1, le=3650)
    brevoApiKey: str | None = None
    senderEmail: str | None = None
    senderName: str | None = None
    recipients: list[str] | None = None
    appBaseUrl: str | None = None
    language: SearchLanguage | None = None
