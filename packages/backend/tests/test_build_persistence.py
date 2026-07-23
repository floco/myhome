from myhome.models_build import BuildDocument, BuildPhase, BuildProject, BuildTask, BuildTaskDependency
from myhome.persistence_build import (
    delete_all_attachments,
    delete_attachment,
    delete_build_project,
    get_attachment_path,
    load_build,
    save_attachment,
    save_build,
)

HOME_ID = "test-home"


def _setup(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    (tmp_path / "homes" / HOME_ID).mkdir(parents=True)
    from myhome.db import get_engine
    from myhome.schema import homes as homes_table
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(homes_table.insert().values(
            id=HOME_ID, name="Test Home", type="project", created_at="2026-01-01T00:00:00+00:00",
        ))


def make_doc() -> BuildDocument:
    project = BuildProject(id="proj1", status="in_progress", plannedBudget=250000.0,
                            createdAt="2026-01-01T00:00:00+00:00", updatedAt="2026-01-01T00:00:00+00:00")
    phase = BuildPhase(id="ph1", displayOrder=0, nameKey="build.phases.planning.name", status="in_progress")
    task1 = BuildTask(id="t1", phaseId="ph1", displayOrder=0, titleKey="build.tasks.siteSurvey.title",
                       status="completed", plannedCost=500.0, actualCost=480.0)
    task2 = BuildTask(id="t2", phaseId="ph1", displayOrder=1, titleKey="build.tasks.buildingPermits.title",
                       validationRequired=True, validationStatus="pending_validation")
    dep = BuildTaskDependency(id="d1", predecessorTaskId="t1", successorTaskId="t2")
    return BuildDocument(project=project, phases=[phase], tasks=[task1, task2], dependencies=[dep])


def test_load_returns_empty_when_no_project(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    doc = load_build(HOME_ID)
    assert doc.project is None
    assert doc.phases == []
    assert doc.tasks == []
    assert doc.dependencies == []


def test_round_trip(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    save_build(HOME_ID, make_doc())
    loaded = load_build(HOME_ID)
    assert loaded.project.id == "proj1"
    assert loaded.project.plannedBudget == 250000.0
    assert [p.id for p in loaded.phases] == ["ph1"]
    assert [t.id for t in loaded.tasks] == ["t1", "t2"]
    assert loaded.tasks[0].actualCost == 480.0
    assert loaded.tasks[1].validationStatus == "pending_validation"
    assert len(loaded.dependencies) == 1
    assert loaded.dependencies[0].predecessorTaskId == "t1"


def test_delete_build_project_cascades(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    save_build(HOME_ID, make_doc())
    delete_build_project(HOME_ID)
    loaded = load_build(HOME_ID)
    assert loaded.project is None
    assert loaded.phases == []
    assert loaded.tasks == []
    assert loaded.dependencies == []


def test_attachment_save_and_delete(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    save_attachment(HOME_ID, "t1", "photo.jpg", b"fake-jpeg-bytes")
    path = get_attachment_path(HOME_ID, "t1", "photo.jpg")
    assert path.exists()
    assert delete_attachment(HOME_ID, "t1", "photo.jpg") is True
    assert not path.exists()


def test_delete_all_attachments(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    save_attachment(HOME_ID, "t1", "photo.jpg", b"data")
    delete_all_attachments(HOME_ID, "t1")
    assert not get_attachment_path(HOME_ID, "t1", "photo.jpg").exists()
