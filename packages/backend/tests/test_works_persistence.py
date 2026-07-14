from myhome.models_works import Work, WorksDocument
from myhome.persistence_works import (
    delete_attachment,
    get_attachment_path,
    load_works,
    save_attachment,
    save_works,
)

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


def make_doc() -> WorksDocument:
    return WorksDocument(
        works=[Work(id="w1", title="Boiler repair", status="done", date="2025-11-10")]
    )


def test_load_returns_empty_when_missing(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    doc = load_works(HOME_ID)
    assert doc.works == []


def test_round_trip(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    save_works(HOME_ID, make_doc())
    loaded = load_works(HOME_ID)
    w = loaded.works[0]
    assert w.id == "w1"
    assert w.title == "Boiler repair"
    assert w.status == "done"
    assert w.attachments == []
    assert w.placement is None


def test_round_trip_preserves_placement_and_order(tmp_path, monkeypatch):
    from myhome.models_works import WorkPlacement, WorkPosition
    _setup(tmp_path, monkeypatch)
    doc = WorksDocument(works=[
        Work(id="w1", title="Boiler repair", status="done", date="2025-11-10",
             placement=WorkPlacement(floorId="f1", position=WorkPosition(x=1.0, y=2.0))),
        Work(id="w2", title="Roof check", status="planned", date="2025-12-01"),
    ])
    save_works(HOME_ID, doc)
    loaded = load_works(HOME_ID)
    assert [w.id for w in loaded.works] == ["w1", "w2"]
    assert loaded.works[0].placement.position.x == 1.0
    assert loaded.works[1].placement is None


def test_attachment_save_and_delete(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    save_attachment(HOME_ID, "w1", "invoice.pdf", b"%PDF test")
    path = get_attachment_path(HOME_ID, "w1", "invoice.pdf")
    assert path.exists()
    assert path.read_bytes() == b"%PDF test"
    assert delete_attachment(HOME_ID, "w1", "invoice.pdf") is True
    assert not path.exists()


def test_delete_attachment_missing_returns_false(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    assert delete_attachment(HOME_ID, "w1", "nope.pdf") is False
