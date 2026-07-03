from myhome.models_kb import KBEntry
from myhome.persistence_kb import delete_entry, load_all, load_entry, save_entry

HOME_ID = "test-home"


def _setup(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    (tmp_path / "homes" / HOME_ID).mkdir(parents=True)


def make_entry() -> KBEntry:
    return KBEntry(
        id="e1",
        title="How to paint",
        content="# Painting",
        createdAt="2026-06-28T10:00:00Z",
        updatedAt="2026-06-28T10:00:00Z",
    )


def test_load_all_returns_empty_when_no_dir(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    assert load_all(HOME_ID) == []


def test_dir_not_created_on_read(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    load_all(HOME_ID)
    assert not (tmp_path / "homes" / HOME_ID / "kb").exists()


def test_save_creates_md_file(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    save_entry(HOME_ID, make_entry())
    assert (tmp_path / "homes" / HOME_ID / "kb" / "e1.md").exists()


def test_md_file_has_frontmatter(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    save_entry(HOME_ID, make_entry())
    text = (tmp_path / "homes" / HOME_ID / "kb" / "e1.md").read_text()
    assert text.startswith("---\n")
    assert "title: How to paint" in text
    assert "id: e1" in text


def test_round_trip(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    save_entry(HOME_ID, make_entry())
    entries = load_all(HOME_ID)
    assert len(entries) == 1
    e = entries[0]
    assert e.id == "e1"
    assert e.title == "How to paint"
    assert e.content == "# Painting"


def test_load_entry_returns_none_when_missing(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    assert load_entry(HOME_ID, "nonexistent") is None


def test_load_entry_returns_entry(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    save_entry(HOME_ID, make_entry())
    entry = load_entry(HOME_ID, "e1")
    assert entry is not None
    assert entry.title == "How to paint"


def test_delete_entry_removes_file(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    save_entry(HOME_ID, make_entry())
    assert delete_entry(HOME_ID, "e1") is True
    assert not (tmp_path / "homes" / HOME_ID / "kb" / "e1.md").exists()


def test_delete_entry_returns_false_when_missing(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    assert delete_entry(HOME_ID, "nonexistent") is False


def test_title_with_colon_round_trips(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    entry = KBEntry(
        id="e2",
        title="Recipe: How to cook pasta",
        content="Steps here",
        createdAt="2026-06-29T10:00:00Z",
        updatedAt="2026-06-29T10:00:00Z",
    )
    save_entry(HOME_ID, entry)
    loaded = load_entry(HOME_ID, "e2")
    assert loaded is not None
    assert loaded.title == "Recipe: How to cook pasta"
