from __future__ import annotations

import uuid
from datetime import datetime, timezone

from .models_build import BuildDocument, BuildPhase, BuildProject, BuildTask, BuildTaskDependency


def _phase(slug: str) -> dict:
    return {"nameKey": f"build.phases.{slug}.name", "descriptionKey": f"build.phases.{slug}.description"}


def _task(slug: str, validation_required: bool = False) -> dict:
    return {
        "titleKey": f"build.tasks.{slug}.title",
        "descriptionKey": f"build.tasks.{slug}.description",
        "validationRequired": validation_required,
    }


PHASES: list[dict] = [
    {"slug": "planning", **_phase("planning"), "tasks": [
        _task("siteSurvey"), _task("architecturalPlans"), _task("buildingPermits", True),
        _task("budgetFinancingApproval"), _task("contractorSelection"),
    ]},
    {"slug": "sitePreparation", **_phase("sitePreparation"), "tasks": [
        _task("siteClearing"), _task("temporaryUtilities"), _task("surveyStaking", True),
    ]},
    {"slug": "foundation", **_phase("foundation"), "tasks": [
        _task("excavation", True), _task("formsReinforcement"), _task("foundationPour", True),
    ]},
    {"slug": "framing", **_phase("framing"), "tasks": [
        _task("floorFraming"), _task("wallFraming"), _task("roofFraming", True),
    ]},
    {"slug": "roofing", **_phase("roofing"), "tasks": [
        _task("roofUnderlayment"), _task("roofCovering", True), _task("roofVentilation"),
    ]},
    {"slug": "windowsExteriorDoors", **_phase("windowsExteriorDoors"), "tasks": [
        _task("windowInstallation"), _task("exteriorDoorInstallation"), _task("exteriorTrimCaulking"),
    ]},
    {"slug": "exteriorEnvelope", **_phase("exteriorEnvelope"), "tasks": [
        _task("weatherResistiveBarrier"), _task("exteriorCladding"), _task("exteriorWaterproofingInspection", True),
    ]},
    {"slug": "plumbingRoughIn", **_phase("plumbingRoughIn"), "tasks": [
        _task("plumbingLayout"), _task("waterHeaterRoughIn"), _task("plumbingRoughInInstallation", True),
    ]},
    {"slug": "electricalRoughIn", **_phase("electricalRoughIn"), "tasks": [
        _task("electricalLayout"), _task("serviceEntranceConnection", True), _task("electricalRoughInInstallation", True),
    ]},
    {"slug": "hvacRoughIn", **_phase("hvacRoughIn"), "tasks": [
        _task("hvacLayout"), _task("equipmentInstallation"), _task("hvacRoughInInstallation", True),
    ]},
    {"slug": "insulation", **_phase("insulation"), "tasks": [
        _task("insulationInstallation"), _task("insulationInspection", True),
    ]},
    {"slug": "drywall", **_phase("drywall"), "tasks": [
        _task("drywallHanging"), _task("drywallFinishing"),
    ]},
    {"slug": "interiorFinishes", **_phase("interiorFinishes"), "tasks": [
        _task("interiorDoorInstallation"), _task("trimMillwork"),
    ]},
    {"slug": "flooring", **_phase("flooring"), "tasks": [
        _task("floorPreparation"), _task("flooringInstallation"),
    ]},
    {"slug": "kitchen", **_phase("kitchen"), "tasks": [
        _task("kitchenCabinetInstallation"), _task("countertopInstallation"), _task("kitchenApplianceInstallation", True),
    ]},
    {"slug": "bathrooms", **_phase("bathrooms"), "tasks": [
        _task("bathroomFixtureInstallation", True), _task("bathroomVentilation"), _task("bathroomWaterproofingTiling"),
    ]},
    {"slug": "painting", **_phase("painting"), "tasks": [
        _task("surfacePreparation"), _task("paintApplication"),
    ]},
    {"slug": "exteriorWorks", **_phase("exteriorWorks"), "tasks": [
        _task("hardscaping"), _task("fencingBoundaryWalls"),
    ]},
    {"slug": "landscaping", **_phase("landscaping"), "tasks": [
        _task("finalGrading"), _task("plantingSeeding"),
    ]},
    {"slug": "finalInspections", **_phase("finalInspections"), "tasks": [
        _task("finalBuildingInspection", True), _task("safetySystemsCheck", True),
    ]},
    {"slug": "punchList", **_phase("punchList"), "tasks": [
        _task("punchListWalkthrough"), _task("punchListResolution", True),
    ]},
    {"slug": "handover", **_phase("handover"), "tasks": [
        _task("finalWalkthrough"), _task("documentsKeysHandover"),
    ]},
]

# Phases whose first task depends on a different set of predecessor phases
# than "the immediately preceding phase in the list" (the default rule).
# Models real parallel construction work: the three rough-in trades all
# start once framing is closed in, not sequentially after each other; and
# insulation can't proceed until all three rough-ins are complete.
FAN_IN: dict[str, list[str]] = {
    "plumbingRoughIn": ["framing"],
    "electricalRoughIn": ["framing"],
    "hvacRoughIn": ["framing"],
    "insulation": ["plumbingRoughIn", "electricalRoughIn", "hvacRoughIn"],
}


def seed_default_build(planned_start_date: str | None = None) -> BuildDocument:
    now = datetime.now(timezone.utc).isoformat()
    project = BuildProject(
        id=str(uuid.uuid4()), status="planning", plannedStartDate=planned_start_date,
        createdAt=now, updatedAt=now,
    )
    phases: list[BuildPhase] = []
    tasks: list[BuildTask] = []
    dependencies: list[BuildTaskDependency] = []
    last_task_id_by_phase_slug: dict[str, str] = {}

    for phase_index, phase_def in enumerate(PHASES):
        phase_id = str(uuid.uuid4())
        phases.append(BuildPhase(
            id=phase_id, displayOrder=phase_index,
            nameKey=phase_def["nameKey"], descriptionKey=phase_def["descriptionKey"],
        ))

        prev_task_id: str | None = None
        first_task_id: str | None = None
        for task_index, task_def in enumerate(phase_def["tasks"]):
            task_id = str(uuid.uuid4())
            if task_index == 0:
                first_task_id = task_id
            tasks.append(BuildTask(
                id=task_id, phaseId=phase_id, displayOrder=task_index,
                titleKey=task_def["titleKey"], descriptionKey=task_def["descriptionKey"],
                validationRequired=task_def["validationRequired"],
            ))
            if prev_task_id is not None:
                dependencies.append(BuildTaskDependency(
                    id=str(uuid.uuid4()), predecessorTaskId=prev_task_id, successorTaskId=task_id,
                ))
            prev_task_id = task_id

        if prev_task_id is not None:
            last_task_id_by_phase_slug[phase_def["slug"]] = prev_task_id

        if first_task_id is not None:
            predecessor_slugs = FAN_IN.get(phase_def["slug"])
            if predecessor_slugs is None and phase_index > 0:
                predecessor_slugs = [PHASES[phase_index - 1]["slug"]]
            for pred_slug in predecessor_slugs or []:
                pred_task_id = last_task_id_by_phase_slug.get(pred_slug)
                if pred_task_id is not None:
                    dependencies.append(BuildTaskDependency(
                        id=str(uuid.uuid4()), predecessorTaskId=pred_task_id, successorTaskId=first_task_id,
                    ))

    return BuildDocument(project=project, phases=phases, tasks=tasks, dependencies=dependencies)
