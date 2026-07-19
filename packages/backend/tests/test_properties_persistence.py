from myhome.models_properties import Property, PropertiesDocument
from myhome.persistence_properties import (
    delete_attachment,
    get_attachment_path,
    load_properties,
    save_attachment,
    save_properties,
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


def make_doc() -> PropertiesDocument:
    return PropertiesDocument(
        properties=[Property(id="p1", name="Casa da Rua das Flores", type="house", status="watching")]
    )


def test_load_returns_empty_when_missing(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    doc = load_properties(HOME_ID)
    assert doc.properties == []


def test_round_trip(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    save_properties(HOME_ID, make_doc())
    loaded = load_properties(HOME_ID)
    p = loaded.properties[0]
    assert p.id == "p1"
    assert p.name == "Casa da Rua das Flores"
    assert p.type == "house"
    assert p.status == "watching"
    assert p.pros == []
    assert p.cons == []
    assert p.attachments == []


def test_round_trip_preserves_full_fields_and_order(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    doc = PropertiesDocument(properties=[
        Property(
            id="p1", name="Terreno Norte", type="land", status="proposal_made",
            locationId="loc1", address="Rua Norte 5", price=90000.0, landSize=850.0,
            listingUrl="https://example.com/listing", contact="Maria, +351 912 345 678",
            pros=["Great light", "Walk to town"], cons=["No garage"], notes="Needs survey",
        ),
        Property(id="p2", name="Casa Sul", type="house", status="watching"),
    ])
    save_properties(HOME_ID, doc)
    loaded = load_properties(HOME_ID)
    assert [p.id for p in loaded.properties] == ["p1", "p2"]
    first = loaded.properties[0]
    assert first.locationId == "loc1"
    assert first.price == 90000.0
    assert first.landSize == 850.0
    assert first.pros == ["Great light", "Walk to town"]
    assert first.cons == ["No garage"]
    assert first.notes == "Needs survey"


def test_attachment_save_and_delete(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    save_attachment(HOME_ID, "p1", "listing.pdf", b"%PDF test")
    path = get_attachment_path(HOME_ID, "p1", "listing.pdf")
    assert path.exists()
    assert path.read_bytes() == b"%PDF test"
    assert delete_attachment(HOME_ID, "p1", "listing.pdf") is True
    assert not path.exists()


def test_delete_attachment_missing_returns_false(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    assert delete_attachment(HOME_ID, "p1", "nope.pdf") is False
