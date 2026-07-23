from __future__ import annotations
from typing import Literal
from pydantic import BaseModel

BuildProjectStatus = Literal["planning", "in_progress", "completed", "on_hold"]
BuildPhaseStatus = Literal["not_started", "in_progress", "completed"]
BuildTaskStatus = Literal["not_started", "ready", "in_progress", "waiting", "blocked", "completed"]
ValidationStatus = Literal["not_required", "pending_validation", "passed", "failed"]


class BuildProject(BaseModel):
    id: str
    status: BuildProjectStatus = "planning"
    plannedStartDate: str | None = None
    plannedCompletionDate: str | None = None
    actualCompletionDate: str | None = None
    plannedBudget: float | None = None
    notes: str = ""
    createdAt: str
    updatedAt: str


class BuildPhase(BaseModel):
    id: str
    displayOrder: int
    nameKey: str | None = None
    nameOverride: str | None = None
    descriptionKey: str | None = None
    descriptionOverride: str | None = None
    status: BuildPhaseStatus = "not_started"
    plannedStartDate: str | None = None
    plannedEndDate: str | None = None
    actualStartDate: str | None = None
    actualEndDate: str | None = None


class BuildTask(BaseModel):
    id: str
    phaseId: str
    parentTaskId: str | None = None
    displayOrder: int
    titleKey: str | None = None
    titleOverride: str | None = None
    descriptionKey: str | None = None
    descriptionOverride: str | None = None
    status: BuildTaskStatus = "not_started"
    plannedStartDate: str | None = None
    plannedDueDate: str | None = None
    actualCompletionDate: str | None = None
    plannedCost: float | None = None
    actualCost: float | None = None
    contractorId: str | None = None
    validationRequired: bool = False
    validationStatus: ValidationStatus = "not_required"
    notes: str = ""
    attachments: list[str] = []


class BuildTaskDependency(BaseModel):
    id: str
    predecessorTaskId: str
    successorTaskId: str


class BuildDocument(BaseModel):
    version: int = 1
    project: BuildProject | None = None
    phases: list[BuildPhase] = []
    tasks: list[BuildTask] = []
    dependencies: list[BuildTaskDependency] = []


class BuildProjectUpdate(BaseModel):
    status: BuildProjectStatus | None = None
    plannedStartDate: str | None = None
    plannedCompletionDate: str | None = None
    actualCompletionDate: str | None = None
    plannedBudget: float | None = None
    notes: str | None = None


class BuildPhaseUpdate(BaseModel):
    nameOverride: str | None = None
    descriptionOverride: str | None = None
    status: BuildPhaseStatus | None = None
    plannedStartDate: str | None = None
    plannedEndDate: str | None = None
    actualStartDate: str | None = None
    actualEndDate: str | None = None


class BuildTaskCreate(BaseModel):
    phaseId: str
    parentTaskId: str | None = None
    titleOverride: str
    descriptionOverride: str = ""
    status: BuildTaskStatus = "not_started"
    plannedStartDate: str | None = None
    plannedDueDate: str | None = None
    plannedCost: float | None = None
    contractorId: str | None = None
    validationRequired: bool = False
    notes: str = ""


class BuildTaskUpdate(BaseModel):
    titleOverride: str | None = None
    descriptionOverride: str | None = None
    status: BuildTaskStatus | None = None
    plannedStartDate: str | None = None
    plannedDueDate: str | None = None
    actualCompletionDate: str | None = None
    plannedCost: float | None = None
    actualCost: float | None = None
    contractorId: str | None = None
    validationRequired: bool | None = None
    validationStatus: ValidationStatus | None = None
    notes: str | None = None


class BuildDependencyCreate(BaseModel):
    predecessorTaskId: str
    successorTaskId: str
