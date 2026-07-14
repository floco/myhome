from myhome.models_chores import ChoreDocument, Chore, Assignment
from myhome.persistence_chores import load_chores, save_chores

HOME_ID = "test-home"


def _setup(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    (tmp_path / "homes" / HOME_ID).mkdir(parents=True)
    # Per-home tables FK-reference homes.id (for cascade-delete-on-home-
    # delete), so a row must exist there before any per-home table insert.
    from myhome.db import get_engine
    from myhome.schema import homes as homes_table
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(homes_table.insert().values(
            id=HOME_ID, name="Test Home", type="existing", created_at="2026-01-01T00:00:00+00:00",
        ))


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
    _setup(tmp_path, monkeypatch)
    doc = load_chores(HOME_ID)
    assert doc.chores == []
    assert doc.assignments == []


def test_round_trip(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    save_chores(HOME_ID, make_doc())
    loaded = load_chores(HOME_ID)
    assert loaded.chores[0].id == "c1"
    assert loaded.chores[0].emoji == "🧹"
    assert loaded.assignments[0].roomId == "r1"
    assert loaded.assignments[0].position.x == 1.0


def test_round_trip_preserves_completions_and_order(tmp_path, monkeypatch):
    from myhome.models_chores import CompletionRecord
    _setup(tmp_path, monkeypatch)
    doc = ChoreDocument(
        chores=[
            Chore(id="c1", name="Sweep", emoji="🧹", periodDays=7, nextDueDate="2027-01-01T00:00:00Z"),
            Chore(id="c2", name="Mop", emoji="🪣", periodDays=14, nextDueDate="2027-01-08T00:00:00Z"),
        ],
        completions=[
            CompletionRecord(id="comp1", choreId="c1", completedAt="2026-12-25T00:00:00Z", scheduledDue="2026-12-24T00:00:00Z"),
        ],
    )
    save_chores(HOME_ID, doc)
    loaded = load_chores(HOME_ID)
    assert [c.id for c in loaded.chores] == ["c1", "c2"]
    assert loaded.completions[0].choreId == "c1"
    assert loaded.completions[0].scheduledDue == "2026-12-24T00:00:00Z"


def test_assignment_without_position_round_trips(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    doc = ChoreDocument(
        chores=[Chore(id="c1", name="Sweep", emoji="🧹", periodDays=7, nextDueDate="2027-01-01T00:00:00Z")],
        assignments=[Assignment(id="a1", choreId="c1")],
    )
    save_chores(HOME_ID, doc)
    loaded = load_chores(HOME_ID)
    assert loaded.assignments[0].position is None
