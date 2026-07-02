from myhome.models_consumables import (
    Consumable,
    ConsumableDocument,
    ConsumablePlacement,
    ConsumablePosition,
    ConsumableTransaction,
)
from myhome.persistence_consumables import load_consumables, save_consumables


def make_doc() -> ConsumableDocument:
    return ConsumableDocument(
        consumables=[
            Consumable(
                id="c1",
                name="AA Batteries",
                emoji="🔋",
                unit="count",
                quantity=6.0,
                minQuantity=4.0,
                placement=ConsumablePlacement(
                    floorId="f1",
                    roomId="r1",
                    position=ConsumablePosition(x=2.0, y=3.5),
                ),
            )
        ],
        transactions=[
            ConsumableTransaction(
                id="t1",
                consumableId="c1",
                delta=6.0,
                quantityAfter=6.0,
                note="initial stock",
                timestamp="2026-07-02T10:00:00Z",
            )
        ],
    )


def test_load_returns_empty_when_missing(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    doc = load_consumables()
    assert doc.consumables == []
    assert doc.transactions == []


def test_save_creates_file(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    save_consumables(make_doc())
    assert (tmp_path / "consumables.json").exists()


def test_round_trip(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    save_consumables(make_doc())
    loaded = load_consumables()
    assert loaded.consumables[0].id == "c1"
    assert loaded.consumables[0].quantity == 6.0
    assert loaded.consumables[0].placement.position.x == 2.0
    assert loaded.transactions[0].delta == 6.0


def test_consumable_without_placement_round_trips(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    doc = ConsumableDocument(consumables=[Consumable(id="c2", name="Soap")])
    save_consumables(doc)
    loaded = load_consumables()
    assert loaded.consumables[0].placement is None


def test_save_creates_data_dir_if_missing(tmp_path, monkeypatch):
    nested = tmp_path / "nested" / "data"
    monkeypatch.setenv("DATA_DIR", str(nested))
    save_consumables(make_doc())
    assert (nested / "consumables.json").exists()
