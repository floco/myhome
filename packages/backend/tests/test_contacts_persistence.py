# packages/backend/tests/test_contacts_persistence.py
from myhome.models_contacts import Contact, ContactsDocument
from myhome.persistence_contacts import load_contacts, save_contacts

HOME_ID = "test-home"


def _setup(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    (tmp_path / "homes" / HOME_ID).mkdir(parents=True)
    from myhome.db import get_engine
    from myhome.schema import homes as homes_table
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(homes_table.insert().values(
            id=HOME_ID, name="Test Home", type="existing", created_at="2026-01-01T00:00:00+00:00",
        ))


def make_doc() -> ContactsDocument:
    return ContactsDocument(contacts=[
        Contact(id="c1", name="Metro Plumbing", typeId="ctype-supplier"),
    ])


def test_load_returns_empty_when_missing(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    doc = load_contacts(HOME_ID)
    assert doc.contacts == []


def test_round_trip(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    save_contacts(HOME_ID, make_doc())
    loaded = load_contacts(HOME_ID)
    c = loaded.contacts[0]
    assert c.id == "c1"
    assert c.name == "Metro Plumbing"
    assert c.typeId == "ctype-supplier"
    assert c.companyName is None


def test_round_trip_preserves_order(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    doc = ContactsDocument(contacts=[
        Contact(id="c1", name="A", typeId="ctype-supplier"),
        Contact(id="c2", name="B", typeId="ctype-contractor"),
    ])
    save_contacts(HOME_ID, doc)
    loaded = load_contacts(HOME_ID)
    assert [c.id for c in loaded.contacts] == ["c1", "c2"]
