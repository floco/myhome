from myhome.models_inventory import InventoryDocument, InventoryItem, InventoryPlacement, InventoryPosition
from myhome.persistence_inventory import load_inventory, save_inventory


def make_doc() -> InventoryDocument:
    return InventoryDocument(
        version=1,
        items=[
            InventoryItem(
                id="i1",
                name="Samsung TV",
                emoji="📺",
                category="Electronics",
                purchasePrice=1200.0,
                warrantyExpiryDate="2026-05-12",
                placement=InventoryPlacement(
                    floorId="f1",
                    roomId="r1",
                    position=InventoryPosition(x=3.4, y=2.1),
                ),
            )
        ],
    )


def test_load_returns_empty_when_missing(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    doc = load_inventory()
    assert doc.items == []


def test_save_creates_file(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    save_inventory(make_doc())
    assert (tmp_path / "inventory.json").exists()


def test_round_trip(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    save_inventory(make_doc())
    loaded = load_inventory()
    assert loaded.items[0].id == "i1"
    assert loaded.items[0].emoji == "📺"
    assert loaded.items[0].purchasePrice == 1200.0
    assert loaded.items[0].placement.position.x == 3.4
    assert loaded.items[0].placement.roomId == "r1"


def test_item_without_placement_round_trips(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    doc = InventoryDocument(
        items=[InventoryItem(id="i2", name="Chair", emoji="🪑")]
    )
    save_inventory(doc)
    loaded = load_inventory()
    assert loaded.items[0].placement is None


def test_save_creates_data_dir_if_missing(tmp_path, monkeypatch):
    nested = tmp_path / "nested" / "data"
    monkeypatch.setenv("DATA_DIR", str(nested))
    save_inventory(make_doc())
    assert (nested / "inventory.json").exists()
