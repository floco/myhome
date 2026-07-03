from myhome.models_works import Work, WorksDocument
from myhome.persistence_works import (
    delete_attachment,
    get_attachment_path,
    load_works,
    save_attachment,
    save_works,
)

HOME_ID = "test-home"


def _setup(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    (tmp_path / "homes" / HOME_ID).mkdir(parents=True)


def make_doc() -> WorksDocument:
    return WorksDocument(
        works=[Work(id="w1", title="Boiler repair", status="done", date="2025-11-10")]
    )


def test_load_returns_empty_when_missing(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    doc = load_works(HOME_ID)
    assert doc.works == []


def test_file_not_created_on_read(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    load_works(HOME_ID)
    assert not (tmp_path / "homes" / HOME_ID / "works.json").exists()


def test_save_creates_file(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    save_works(HOME_ID, make_doc())
    assert (tmp_path / "homes" / HOME_ID / "works.json").exists()


def test_round_trip(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    save_works(HOME_ID, make_doc())
    loaded = load_works(HOME_ID)
    w = loaded.works[0]
    assert w.id == "w1"
    assert w.title == "Boiler repair"
    assert w.status == "done"
    assert w.attachments == []
    assert w.placement is None


def test_attachment_save_and_delete(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    save_attachment(HOME_ID, "w1", "invoice.pdf", b"%PDF test")
    path = get_attachment_path(HOME_ID, "w1", "invoice.pdf")
    assert path.exists()
    assert path.read_bytes() == b"%PDF test"
    assert delete_attachment(HOME_ID, "w1", "invoice.pdf") is True
    assert not path.exists()


def test_delete_attachment_missing_returns_false(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    assert delete_attachment(HOME_ID, "w1", "nope.pdf") is False
