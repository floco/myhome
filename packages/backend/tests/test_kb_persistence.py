from myhome.models_kb import KBEntry
from myhome.persistence_kb import delete_entry, load_all, load_entry, save_entry


def make_entry() -> KBEntry:
    return KBEntry(
        id="e1",
        title="How to paint",
        content="# Painting",
        createdAt="2026-06-28T10:00:00Z",
        updatedAt="2026-06-28T10:00:00Z",
    )


def test_load_all_returns_empty_when_no_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    assert load_all() == []


def test_dir_not_created_on_read(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    load_all()
    assert not (tmp_path / "kb").exists()


def test_save_creates_md_file(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    save_entry(make_entry())
    assert (tmp_path / "kb" / "e1.md").exists()


def test_md_file_has_frontmatter(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    save_entry(make_entry())
    text = (tmp_path / "kb" / "e1.md").read_text()
    assert text.startswith("---\n")
    assert "title: How to paint" in text
    assert "id: e1" in text


def test_round_trip(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    save_entry(make_entry())
    entries = load_all()
    assert len(entries) == 1
    e = entries[0]
    assert e.id == "e1"
    assert e.title == "How to paint"
    assert e.content == "# Painting"


def test_load_entry_returns_none_when_missing(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    assert load_entry("nonexistent") is None


def test_load_entry_returns_entry(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    save_entry(make_entry())
    entry = load_entry("e1")
    assert entry is not None
    assert entry.title == "How to paint"


def test_delete_entry_removes_file(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    save_entry(make_entry())
    assert delete_entry("e1") is True
    assert not (tmp_path / "kb" / "e1.md").exists()


def test_delete_entry_returns_false_when_missing(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    assert delete_entry("nonexistent") is False


def test_title_with_colon_round_trips(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    entry = KBEntry(
        id="e2",
        title="Recipe: How to cook pasta",
        content="Steps here",
        createdAt="2026-06-29T10:00:00Z",
        updatedAt="2026-06-29T10:00:00Z",
    )
    save_entry(entry)
    loaded = load_entry("e2")
    assert loaded is not None
    assert loaded.title == "Recipe: How to cook pasta"
