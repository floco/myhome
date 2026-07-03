from myhome.models_inventory import InventoryDocument, InventoryItem, InventoryPlacement, InventoryPosition
from myhome.persistence_inventory import load_inventory, save_inventory

HOME_ID = "test-home"


def _setup(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    (tmp_path / "homes" / HOME_ID).mkdir(parents=True)


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
    _setup(tmp_path, monkeypatch)
    doc = load_inventory(HOME_ID)
    assert doc.items == []


def test_save_creates_file(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    save_inventory(HOME_ID, make_doc())
    assert (tmp_path / "homes" / HOME_ID / "inventory.json").exists()


def test_round_trip(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    save_inventory(HOME_ID, make_doc())
    loaded = load_inventory(HOME_ID)
    assert loaded.items[0].id == "i1"
    assert loaded.items[0].emoji == "📺"
    assert loaded.items[0].purchasePrice == 1200.0
    assert loaded.items[0].placement.position.x == 3.4
    assert loaded.items[0].placement.roomId == "r1"


def test_item_without_placement_round_trips(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    doc = InventoryDocument(
        items=[InventoryItem(id="i2", name="Chair", emoji="🪑")]
    )
    save_inventory(HOME_ID, doc)
    loaded = load_inventory(HOME_ID)
    assert loaded.items[0].placement is None


def test_save_creates_data_dir_if_missing(tmp_path, monkeypatch):
    nested = tmp_path / "nested" / "data"
    monkeypatch.setenv("DATA_DIR", str(nested))
    save_inventory(HOME_ID, make_doc())
    assert (nested / "homes" / HOME_ID / "inventory.json").exists()
