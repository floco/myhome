from myhome.models_costs import CostEntry, CostsDocument
from myhome.persistence_costs import load_costs, save_costs

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


def make_doc() -> CostsDocument:
    return CostsDocument(
        entries=[
            CostEntry(
                id="e1",
                categoryId="cat-fuel",
                date="2025-10-14",
                totalAmount=1650.0,
                quantity=1500.0,
                unitPrice=1.10,
                supplierId="sup-butagaz",
                roomId="r1",
            )
        ]
    )


def test_load_returns_empty_when_missing(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    doc = load_costs(HOME_ID)
    assert doc.entries == []


def test_round_trip(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    save_costs(HOME_ID, make_doc())
    loaded = load_costs(HOME_ID)
    e = loaded.entries[0]
    assert e.id == "e1"
    assert e.totalAmount == 1650.0
    assert e.quantity == 1500.0
    assert e.unitPrice == 1.10
    assert e.supplierId == "sup-butagaz"
    assert e.roomId == "r1"


def test_lump_sum_entry_round_trips(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    doc = CostsDocument(
        entries=[CostEntry(id="e2", categoryId="cat-tax", date="2025-03-01", totalAmount=1648.0)]
    )
    save_costs(HOME_ID, doc)
    loaded = load_costs(HOME_ID)
    e = loaded.entries[0]
    assert e.quantity is None
    assert e.unitPrice is None
    assert e.supplierId is None


def test_round_trip_preserves_order(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    doc = CostsDocument(entries=[
        CostEntry(id="e1", categoryId="cat-fuel", date="2025-01-01", totalAmount=100.0),
        CostEntry(id="e2", categoryId="cat-water", date="2025-02-01", totalAmount=50.0),
    ])
    save_costs(HOME_ID, doc)
    loaded = load_costs(HOME_ID)
    assert [e.id for e in loaded.entries] == ["e1", "e2"]
