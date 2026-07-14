from myhome.models_settings import (
    CostCategory,
    InventoryCategory,
    SettingsDocument,
)
from myhome.persistence_settings import load_settings, save_settings

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


def test_load_returns_defaults_when_file_missing(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    doc = load_settings(HOME_ID)
    assert len(doc.costCategories) == 5
    assert doc.costCategories[0].name == "Fuel / Mazout"
    assert len(doc.inventoryCategories) == 6


def test_round_trip(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    doc = SettingsDocument(
        costCategories=[CostCategory(id="c1", name="Fuel", emoji="🛢", unit="L", color="#4466cc")],
        inventoryCategories=[InventoryCategory(id="i1", name="Electronics")],
    )
    save_settings(HOME_ID, doc)
    loaded = load_settings(HOME_ID)
    assert loaded.costCategories[0].id == "c1"
    assert loaded.costCategories[0].unit == "L"
    assert loaded.inventoryCategories[0].name == "Electronics"


def test_round_trip_preserves_all_category_lists_and_notifications(tmp_path, monkeypatch):
    from myhome.models_settings import (
        ConsumableCategory, NotificationSettings, Supplier, WorkCategory,
    )
    _setup(tmp_path, monkeypatch)
    doc = SettingsDocument(
        costCategories=[
            CostCategory(id="c1", name="Fuel", emoji="🛢", unit="L", color="#111111"),
            CostCategory(id="c2", name="Water", emoji="💧", unit="m3", color="#222222"),
        ],
        inventoryCategories=[InventoryCategory(id="i1", name="Electronics")],
        workCategories=[WorkCategory(id="w1", name="Plumbing", emoji="🔧")],
        suppliers=[Supplier(id="s1", name="Acme")],
        consumableUnits=["count", "L"],
        consumableCategories=[ConsumableCategory(id="cc1", name="Cleaning", emoji="🧽")],
        notifications=NotificationSettings(
            enabled=False, choresDueSoonThreshold=0.5, warrantyDaysThreshold=45,
            haPushEnabled=True, haNotifyService="notify.mobile_app", haPushTime="09:30",
        ),
    )
    save_settings(HOME_ID, doc)
    loaded = load_settings(HOME_ID)
    assert [c.id for c in loaded.costCategories] == ["c1", "c2"]
    assert loaded.workCategories[0].name == "Plumbing"
    assert loaded.suppliers[0].name == "Acme"
    assert loaded.consumableUnits == ["count", "L"]
    assert loaded.consumableCategories[0].emoji == "🧽"
    assert loaded.notifications.enabled is False
    assert loaded.notifications.haNotifyService == "notify.mobile_app"
    assert loaded.notifications.haPushTime == "09:30"
