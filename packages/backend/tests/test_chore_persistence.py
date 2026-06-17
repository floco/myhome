import pytest
from myhome.models_chores import ChoreDocument, Chore, Assignment
from myhome.persistence_chores import load_chores, save_chores


def make_doc() -> ChoreDocument:
    return ChoreDocument(
        version=1,
        chores=[
            Chore(
                id="c1",
                name="🧹 Sweep",
                emoji="🧹",
                periodDays=14,
                nextDueDate="2027-01-01T00:00:00Z",
            )
        ],
        assignments=[
            Assignment(id="a1", choreId="c1", roomId="r1", position={"x": 1.0, "y": 2.0})
        ],
    )


def test_load_returns_empty_when_missing(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    doc = load_chores()
    assert doc.chores == []
    assert doc.assignments == []


def test_save_creates_file(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    save_chores(make_doc())
    assert (tmp_path / "chores.json").exists()


def test_round_trip(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    save_chores(make_doc())
    loaded = load_chores()
    assert loaded.chores[0].id == "c1"
    assert loaded.chores[0].emoji == "🧹"
    assert loaded.assignments[0].roomId == "r1"
    assert loaded.assignments[0].position.x == 1.0


def test_save_creates_data_dir_if_missing(tmp_path, monkeypatch):
    nested = tmp_path / "nested" / "data"
    monkeypatch.setenv("DATA_DIR", str(nested))
    save_chores(make_doc())
    assert (nested / "chores.json").exists()
