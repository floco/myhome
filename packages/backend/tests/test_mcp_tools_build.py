import pytest
from myhome.mcp_tools_build import (
    _create_build_task_impl,
    _list_build_phases_impl,
    _list_build_tasks_impl,
    _update_build_phase_impl,
    _update_build_task_impl,
)
from myhome.build_template import seed_default_build
from myhome.persistence_build import save_build


def _seed(home_id):
    doc = seed_default_build()
    save_build(home_id, doc)
    return doc


def _seed_env(tmp_path, monkeypatch, home_id):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    (tmp_path / "homes" / home_id).mkdir(parents=True)
    from myhome.db import get_engine
    from myhome.schema import homes as homes_table
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(homes_table.insert().values(
            id=home_id, name="Test Home", type="project", created_at="2026-01-01T00:00:00+00:00",
        ))


def test_list_build_phases_impl(tmp_path, monkeypatch, home_id="h1"):
    _seed_env(tmp_path, monkeypatch, home_id)
    _seed(home_id)
    result = _list_build_phases_impl(home_id)
    assert len(result["phases"]) == 22


def test_list_build_tasks_impl(tmp_path, monkeypatch, home_id="h1"):
    _seed_env(tmp_path, monkeypatch, home_id)
    doc = _seed(home_id)
    result = _list_build_tasks_impl(home_id, phase_id=doc.phases[0].id)
    assert len(result["tasks"]) == 5


def test_create_build_task_impl(tmp_path, monkeypatch, home_id="h1"):
    _seed_env(tmp_path, monkeypatch, home_id)
    doc = _seed(home_id)
    result = _create_build_task_impl(home_id, phase_id=doc.phases[0].id, title="Extra site visit")
    assert result["titleOverride"] == "Extra site visit"


def test_update_build_task_impl(tmp_path, monkeypatch, home_id="h1"):
    _seed_env(tmp_path, monkeypatch, home_id)
    doc = _seed(home_id)
    result = _update_build_task_impl(home_id, task_id=doc.tasks[0].id, status="in_progress")
    assert result["status"] == "in_progress"


def test_update_build_task_impl_unknown_id(tmp_path, monkeypatch, home_id="h1"):
    _seed_env(tmp_path, monkeypatch, home_id)
    _seed(home_id)
    with pytest.raises(ValueError):
        _update_build_task_impl(home_id, task_id="nope", status="in_progress")


def test_update_build_phase_impl(tmp_path, monkeypatch, home_id="h1"):
    _seed_env(tmp_path, monkeypatch, home_id)
    doc = _seed(home_id)
    result = _update_build_phase_impl(home_id, phase_id=doc.phases[0].id, status="in_progress")
    assert result["status"] == "in_progress"
