from myhome.models_costs import CostEntry, CostsDocument
from myhome.persistence_costs import load_costs, save_costs


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
                supplier="Butagaz",
                roomId="r1",
            )
        ]
    )


def test_load_returns_empty_when_missing(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    doc = load_costs()
    assert doc.entries == []


def test_save_creates_file(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    save_costs(make_doc())
    assert (tmp_path / "costs.json").exists()


def test_round_trip(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    save_costs(make_doc())
    loaded = load_costs()
    e = loaded.entries[0]
    assert e.id == "e1"
    assert e.totalAmount == 1650.0
    assert e.quantity == 1500.0
    assert e.unitPrice == 1.10
    assert e.supplier == "Butagaz"
    assert e.roomId == "r1"


def test_lump_sum_entry_round_trips(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    doc = CostsDocument(
        entries=[CostEntry(id="e2", categoryId="cat-tax", date="2025-03-01", totalAmount=1648.0)]
    )
    save_costs(doc)
    loaded = load_costs()
    e = loaded.entries[0]
    assert e.quantity is None
    assert e.unitPrice is None
    assert e.supplier is None


def test_save_creates_data_dir_if_missing(tmp_path, monkeypatch):
    nested = tmp_path / "nested" / "data"
    monkeypatch.setenv("DATA_DIR", str(nested))
    save_costs(make_doc())
    assert (nested / "costs.json").exists()
