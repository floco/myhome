from myhome.models_kb import KBEntry, KBDocument
from myhome.persistence_kb import load_kb, save_kb


def make_doc() -> KBDocument:
    return KBDocument(
        entries=[KBEntry(id="e1", title="How to paint", content="# Painting", createdAt="2026-06-28T10:00:00Z", updatedAt="2026-06-28T10:00:00Z")]
    )


def test_load_returns_empty_when_missing(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    doc = load_kb()
    assert doc.entries == []


def test_file_not_created_on_read(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    load_kb()
    assert not (tmp_path / "kb.json").exists()


def test_save_creates_file(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    save_kb(make_doc())
    assert (tmp_path / "kb.json").exists()


def test_round_trip(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    save_kb(make_doc())
    loaded = load_kb()
    e = loaded.entries[0]
    assert e.id == "e1"
    assert e.title == "How to paint"
    assert e.content == "# Painting"
