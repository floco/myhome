from myhome.models_build import (
    BuildDocument, BuildPhase, BuildProject, BuildTask, BuildTaskDependency,
)


def test_build_project_defaults():
    p = BuildProject(id="p1", createdAt="2026-01-01T00:00:00+00:00", updatedAt="2026-01-01T00:00:00+00:00")
    assert p.status == "planning"
    assert p.plannedBudget is None
    assert p.notes == ""


def test_build_phase_defaults():
    ph = BuildPhase(id="ph1", displayOrder=0, nameKey="build.phases.planning.name")
    assert ph.status == "not_started"
    assert ph.nameOverride is None


def test_build_task_defaults():
    t = BuildTask(id="t1", phaseId="ph1", displayOrder=0, titleKey="build.tasks.siteSurvey.title")
    assert t.status == "not_started"
    assert t.validationRequired is False
    assert t.validationStatus == "not_required"
    assert t.attachments == []


def test_build_task_dependency():
    d = BuildTaskDependency(id="d1", predecessorTaskId="t1", successorTaskId="t2")
    assert d.predecessorTaskId == "t1"


def test_build_document_defaults():
    doc = BuildDocument()
    assert doc.project is None
    assert doc.phases == []
    assert doc.tasks == []
    assert doc.dependencies == []
