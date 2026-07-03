from myhome.models_costs import CostEntry, CostsDocument
from myhome.persistence_costs import load_costs, save_costs

HOME_ID = "test-home"


def _setup(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    (tmp_path / "homes" / HOME_ID).mkdir(parents=True)


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


def test_save_creates_file(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    save_costs(HOME_ID, make_doc())
    assert (tmp_path / "homes" / HOME_ID / "costs.json").exists()


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


def test_save_creates_data_dir_if_missing(tmp_path, monkeypatch):
    nested = tmp_path / "nested" / "data"
    monkeypatch.setenv("DATA_DIR", str(nested))
    save_costs(HOME_ID, make_doc())
    assert (nested / "homes" / HOME_ID / "costs.json").exists()
