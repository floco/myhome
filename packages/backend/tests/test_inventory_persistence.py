from myhome.models_inventory import InventoryDocument, InventoryItem, InventoryPlacement, InventoryPosition
from myhome.persistence_inventory import load_inventory, save_inventory

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


def test_round_trip_preserves_order(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    doc = InventoryDocument(items=[
        InventoryItem(id="i1", name="TV"),
        InventoryItem(id="i2", name="Toaster"),
    ])
    save_inventory(HOME_ID, doc)
    loaded = load_inventory(HOME_ID)
    assert [i.id for i in loaded.items] == ["i1", "i2"]
