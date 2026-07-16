from myhome.models_kb import KBEntry
from myhome.persistence_kb import (
    delete_entry,
    descendant_ids,
    empty_trash,
    list_trash,
    load_all,
    load_entry,
    next_order,
    reorder_siblings,
    restore_subtree,
    save_entry,
    soft_delete_subtree,
    would_create_cycle,
)

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


def test_icon_with_embedded_newline_cannot_inject_frontmatter(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    entry = make_entry()
    entry.icon = "📄\nparentId: injected-parent\ndeletedAt: 2026-01-01T00:00:00Z"
    save_entry(HOME_ID, entry)
    loaded = load_entry(HOME_ID, "e1")
    assert loaded is not None
    assert loaded.parentId is None
    assert loaded.deletedAt is None


def test_icon_defaults_to_page_emoji(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    save_entry(HOME_ID, make_entry())
    assert load_entry(HOME_ID, "e1").icon == "📄"


def test_custom_icon_round_trips(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    entry = make_entry()
    entry.icon = "🔧"
    save_entry(HOME_ID, entry)
    assert load_entry(HOME_ID, "e1").icon == "🔧"


def test_parent_id_round_trips(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    save_entry(HOME_ID, make_entry())
    child = make_entry()
    child.id = "child"
    child.parentId = "e1"
    save_entry(HOME_ID, child)
    assert load_entry(HOME_ID, "child").parentId == "e1"


def test_entry_without_parent_id_defaults_to_none(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    save_entry(HOME_ID, make_entry())
    assert load_entry(HOME_ID, "e1").parentId is None


def test_legacy_folder_id_frontmatter_ignored_on_read(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    kb_dir = tmp_path / "homes" / HOME_ID / "kb"
    kb_dir.mkdir(parents=True, exist_ok=True)
    (kb_dir / "legacy.md").write_text(
        "---\nid: legacy\ntitle: Old entry\ncreatedAt: 2026-01-01T00:00:00Z\n"
        "updatedAt: 2026-01-01T00:00:00Z\nfolderId: some-old-folder\n---\n\nBody text",
        encoding="utf-8",
    )
    entry = load_entry(HOME_ID, "legacy")
    assert entry is not None
    assert entry.parentId is None


def test_missing_order_migrated_sequentially_by_created_at(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    kb_dir = tmp_path / "homes" / HOME_ID / "kb"
    kb_dir.mkdir(parents=True, exist_ok=True)
    for id_, created in [("a", "2026-01-02T00:00:00Z"), ("b", "2026-01-01T00:00:00Z")]:
        (kb_dir / f"{id_}.md").write_text(
            f"---\nid: {id_}\ntitle: {id_}\ncreatedAt: {created}\nupdatedAt: {created}\n---\n\n",
            encoding="utf-8",
        )
    entries = load_all(HOME_ID)
    by_id = {e.id: e for e in entries}
    assert by_id["b"].order < by_id["a"].order
    assert load_entry(HOME_ID, "b").order == by_id["b"].order


def test_deleted_entries_excluded_by_default(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    save_entry(HOME_ID, make_entry())
    soft_delete_subtree(HOME_ID, "e1")
    assert load_all(HOME_ID) == []
    assert len(load_all(HOME_ID, include_deleted=True)) == 1


def test_soft_delete_cascades_to_descendants(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    p = make_entry(); p.id = "p"
    c1 = make_entry(); c1.id = "c1"; c1.parentId = "p"
    c2 = make_entry(); c2.id = "c2"; c2.parentId = "c1"
    save_entry(HOME_ID, p); save_entry(HOME_ID, c1); save_entry(HOME_ID, c2)
    affected = soft_delete_subtree(HOME_ID, "p")
    assert set(affected) == {"p", "c1", "c2"}
    assert load_all(HOME_ID) == []


def test_descendant_ids_finds_grandchildren(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    p = make_entry(); p.id = "p"
    c1 = make_entry(); c1.id = "c1"; c1.parentId = "p"
    c2 = make_entry(); c2.id = "c2"; c2.parentId = "c1"
    save_entry(HOME_ID, p); save_entry(HOME_ID, c1); save_entry(HOME_ID, c2)
    assert set(descendant_ids(HOME_ID, "p")) == {"c1", "c2"}


def test_restore_brings_back_cascaded_descendants(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    p = make_entry(); p.id = "p"
    c1 = make_entry(); c1.id = "c1"; c1.parentId = "p"
    save_entry(HOME_ID, p); save_entry(HOME_ID, c1)
    soft_delete_subtree(HOME_ID, "p")
    restored = restore_subtree(HOME_ID, "p")
    assert set(restored) == {"p", "c1"}
    assert {e.id for e in load_all(HOME_ID)} == {"p", "c1"}


def test_restore_does_not_touch_already_live_descendant(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    p = make_entry(); p.id = "p"
    c1 = make_entry(); c1.id = "c1"; c1.parentId = "p"
    save_entry(HOME_ID, p); save_entry(HOME_ID, c1)
    soft_delete_subtree(HOME_ID, "p")
    restore_subtree(HOME_ID, "c1")
    restored = restore_subtree(HOME_ID, "p")
    assert "c1" not in restored
    assert "p" in restored


def test_list_trash_returns_only_deleted(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    a = make_entry(); a.id = "a"
    b = make_entry(); b.id = "b"
    save_entry(HOME_ID, a); save_entry(HOME_ID, b)
    soft_delete_subtree(HOME_ID, "a")
    assert [e.id for e in list_trash(HOME_ID)] == ["a"]


def test_empty_trash_permanently_removes_files(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    save_entry(HOME_ID, make_entry())
    soft_delete_subtree(HOME_ID, "e1")
    deleted = empty_trash(HOME_ID)
    assert deleted == ["e1"]
    assert not (tmp_path / "homes" / HOME_ID / "kb" / "e1.md").exists()


def test_would_create_cycle_detects_self(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    save_entry(HOME_ID, make_entry())
    assert would_create_cycle(HOME_ID, "e1", "e1") is True


def test_would_create_cycle_detects_descendant(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    a = make_entry(); a.id = "a"
    b = make_entry(); b.id = "b"; b.parentId = "a"
    save_entry(HOME_ID, a); save_entry(HOME_ID, b)
    assert would_create_cycle(HOME_ID, "a", "b") is True


def test_would_create_cycle_false_for_unrelated(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    a = make_entry(); a.id = "a"
    b = make_entry(); b.id = "b"
    save_entry(HOME_ID, a); save_entry(HOME_ID, b)
    assert would_create_cycle(HOME_ID, "a", "b") is False


def test_next_order_appends_after_existing_siblings(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    a = make_entry(); a.id = "a"; a.order = 0
    b = make_entry(); b.id = "b"; b.order = 1
    save_entry(HOME_ID, a); save_entry(HOME_ID, b)
    assert next_order(HOME_ID, None) == 2


def test_next_order_zero_for_empty_parent(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    assert next_order(HOME_ID, None) == 0


def test_reorder_siblings_sets_sequential_order(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    a = make_entry(); a.id = "a"; a.order = 0
    b = make_entry(); b.id = "b"; b.order = 1
    c = make_entry(); c.id = "c"; c.order = 2
    save_entry(HOME_ID, a); save_entry(HOME_ID, b); save_entry(HOME_ID, c)
    reorder_siblings(HOME_ID, None, ["c", "a", "b"])
    orders = {e.id: e.order for e in load_all(HOME_ID)}
    assert orders == {"c": 0, "a": 1, "b": 2}
