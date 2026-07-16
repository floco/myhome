from __future__ import annotations

import logging
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path

from .ids import InvalidIdError
from .models_kb import KBEntry

_log = logging.getLogger(__name__)

_MISSING_ORDER = -1


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _home_dir(home_id: str) -> Path:
    # Normalize lexically (no filesystem access -- Path.resolve() follows
    # symlinks and touches disk, which CodeQL's own path-injection sink set
    # flags even before any check runs) then verify containment within
    # homes_root. This is CodeQL's own recommended py/path-injection
    # sanitizer shape: os.path.normpath + startswith against a safe root.
    homes_root = os.path.normpath(os.path.join(os.environ.get("DATA_DIR", "/data"), "homes"))
    candidate = os.path.normpath(os.path.join(homes_root, home_id))
    if not candidate.startswith(homes_root + os.sep):
        raise InvalidIdError(f"Invalid home_id: {home_id!r}")
    return Path(candidate)


def _kb_dir(home_id: str) -> Path:
    return _home_dir(home_id) / "kb"


def _entry_path(home_id: str, id: str) -> Path:
    base = os.path.normpath(str(_kb_dir(home_id)))
    candidate = os.path.normpath(os.path.join(base, f"{id}.md"))
    if not candidate.startswith(base + os.sep):
        raise InvalidIdError(f"Invalid id: {id!r}")
    return Path(candidate)


def _attachments_dir(home_id: str, entry_id: str) -> Path:
    # Same inline lexical-normalize-then-verify-containment shape as
    # _home_dir() above -- entry_id is validated at the route layer too, but
    # CodeQL's taint tracker doesn't credit a separate validator function as
    # sanitizing the value used here.
    base = os.path.normpath(str(_home_dir(home_id) / "kb-attachments"))
    candidate = os.path.normpath(os.path.join(base, entry_id))
    if not candidate.startswith(base + os.sep):
        raise InvalidIdError(f"Invalid entry_id: {entry_id!r}")
    return Path(candidate)


def _parse_frontmatter(text: str) -> tuple[dict, str]:
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---\n", 4)
    if end == -1:
        return {}, text
    meta: dict = {}
    for line in text[4:end].splitlines():
        if ": " in line:
            key, _, val = line.partition(": ")
            meta[key.strip()] = val.strip()
    body = text[end + 5:]
    return meta, body


def _build_file(entry: KBEntry) -> str:
    # Both fields are free text (title from users, icon from either the
    # EmojiPicker or an MCP caller) and get written as one frontmatter line
    # each -- an embedded newline would let a crafted value inject a fake
    # "key: value" line and smuggle in an unintended frontmatter field
    # (e.g. deletedAt, parentId) when the file is next parsed.
    title = entry.title.replace("\n", " ")
    icon = entry.icon.replace("\n", " ")
    lines = [
        "---",
        f"id: {entry.id}",
        f"title: {title}",
        f"createdAt: {entry.createdAt}",
        f"updatedAt: {entry.updatedAt}",
        f"icon: {icon}",
        f"order: {entry.order}",
    ]
    if entry.attachments:
        lines.append(f"attachments: {','.join(entry.attachments)}")
    if entry.parentId:
        lines.append(f"parentId: {entry.parentId}")
    if entry.deletedAt:
        lines.append(f"deletedAt: {entry.deletedAt}")
    lines += ["---", "", entry.content]
    return "\n".join(lines)


def _read_entry_file(path: Path) -> KBEntry | None:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    meta, body = _parse_frontmatter(text)
    if not meta.get("id") or not meta.get("title"):
        return None
    att_str = meta.get("attachments", "")
    attachments = [a for a in att_str.split(",") if a] if att_str else []
    order_raw = meta.get("order")
    return KBEntry(
        id=meta["id"],
        title=meta["title"],
        content=body.lstrip("\n"),
        createdAt=meta.get("createdAt", ""),
        updatedAt=meta.get("updatedAt", ""),
        attachments=attachments,
        parentId=meta.get("parentId") or None,
        icon=meta.get("icon") or "📄",
        order=int(order_raw) if order_raw not in (None, "") else _MISSING_ORDER,
        deletedAt=meta.get("deletedAt") or None,
    )


def _migrate_missing_order(home_id: str, entries: list[KBEntry]) -> None:
    missing = [e for e in entries if e.order == _MISSING_ORDER]
    if not missing:
        return
    missing.sort(key=lambda e: e.createdAt)
    by_parent_max: dict[str | None, int] = {}
    for e in entries:
        if e.order != _MISSING_ORDER:
            by_parent_max[e.parentId] = max(by_parent_max.get(e.parentId, -1), e.order)
    for e in missing:
        next_val = by_parent_max.get(e.parentId, -1) + 1
        by_parent_max[e.parentId] = next_val
        e.order = next_val
        save_entry(home_id, e)


def load_all(home_id: str, include_deleted: bool = False) -> list[KBEntry]:
    d = _kb_dir(home_id)
    if not d.exists():
        return []
    entries = [e for path in d.glob("*.md") if (e := _read_entry_file(path))]
    _migrate_missing_order(home_id, entries)
    if not include_deleted:
        entries = [e for e in entries if e.deletedAt is None]
    entries.sort(key=lambda e: (e.parentId or "", e.order))
    return entries


def load_entry(home_id: str, id: str) -> KBEntry | None:
    return _read_entry_file(_entry_path(home_id, id))


def save_entry(home_id: str, entry: KBEntry) -> None:
    d = _kb_dir(home_id)
    d.mkdir(parents=True, exist_ok=True)
    path = _entry_path(home_id, entry.id)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(_build_file(entry), encoding="utf-8")
    tmp.replace(path)


def delete_entry(home_id: str, id: str) -> bool:
    path = _entry_path(home_id, id)
    if not path.exists():
        return False
    path.unlink()
    att_dir = _attachments_dir(home_id, id)
    if att_dir.exists():
        shutil.rmtree(att_dir)
    return True


def _children_map(entries: list[KBEntry]) -> dict[str | None, list[KBEntry]]:
    m: dict[str | None, list[KBEntry]] = {}
    for e in entries:
        m.setdefault(e.parentId, []).append(e)
    return m


def descendant_ids(home_id: str, id: str) -> list[str]:
    entries = load_all(home_id, include_deleted=True)
    children = _children_map(entries)
    result: list[str] = []
    stack = [id]
    while stack:
        current = stack.pop()
        for child in children.get(current, []):
            result.append(child.id)
            stack.append(child.id)
    return result


def soft_delete_subtree(home_id: str, id: str) -> list[str]:
    if load_entry(home_id, id) is None:
        return []
    ids = [id] + descendant_ids(home_id, id)
    now = _now()
    affected: list[str] = []
    for eid in ids:
        e = load_entry(home_id, eid)
        if e is not None and e.deletedAt is None:
            e.deletedAt = now
            save_entry(home_id, e)
            affected.append(eid)
    return affected


def restore_subtree(home_id: str, id: str) -> list[str]:
    if load_entry(home_id, id) is None:
        return []
    ids = [id] + descendant_ids(home_id, id)
    restored: list[str] = []
    for eid in ids:
        e = load_entry(home_id, eid)
        if e is not None and e.deletedAt is not None:
            e.deletedAt = None
            save_entry(home_id, e)
            restored.append(eid)
    return restored


def list_trash(home_id: str) -> list[KBEntry]:
    return [e for e in load_all(home_id, include_deleted=True) if e.deletedAt is not None]


def empty_trash(home_id: str) -> list[str]:
    deleted: list[str] = []
    for e in list_trash(home_id):
        if delete_entry(home_id, e.id):
            deleted.append(e.id)
    return deleted


def would_create_cycle(home_id: str, entry_id: str, new_parent_id: str) -> bool:
    """True if setting entry_id's parent to new_parent_id would create a cycle
    (new_parent_id is entry_id itself, or one of entry_id's descendants)."""
    if new_parent_id == entry_id:
        return True
    entries = {e.id: e for e in load_all(home_id, include_deleted=True)}
    current: str | None = new_parent_id
    seen: set[str] = set()
    while current is not None:
        if current == entry_id:
            return True
        if current in seen:
            return False
        seen.add(current)
        e = entries.get(current)
        current = e.parentId if e else None
    return False


def next_order(home_id: str, parent_id: str | None) -> int:
    siblings = [e for e in load_all(home_id) if e.parentId == parent_id]
    return max((e.order for e in siblings), default=-1) + 1


def reorder_siblings(home_id: str, parent_id: str | None, ordered_ids: list[str]) -> None:
    siblings = {e.id: e for e in load_all(home_id) if e.parentId == parent_id}
    for index, eid in enumerate(ordered_ids):
        e = siblings.get(eid)
        if e is not None:
            e.order = index
            save_entry(home_id, e)


def get_attachment_path(home_id: str, entry_id: str, filename: str) -> Path:
    base = os.path.normpath(str(_attachments_dir(home_id, entry_id)))
    candidate = os.path.normpath(os.path.join(base, filename))
    if not candidate.startswith(base + os.sep):
        raise InvalidIdError(f"Invalid filename: {filename!r}")
    return Path(candidate)


def save_attachment(home_id: str, entry_id: str, filename: str, data: bytes) -> None:
    path = _attachments_dir(home_id, entry_id)
    base = os.path.normpath(str(path))
    candidate = os.path.normpath(os.path.join(base, filename))
    if not candidate.startswith(base + os.sep):
        raise InvalidIdError(f"Invalid filename: {filename!r}")
    path.mkdir(parents=True, exist_ok=True)
    Path(candidate).write_bytes(data)


def delete_attachment(home_id: str, entry_id: str, filename: str) -> bool:
    base = os.path.normpath(str(_attachments_dir(home_id, entry_id)))
    candidate = os.path.normpath(os.path.join(base, filename))
    if not candidate.startswith(base + os.sep):
        raise InvalidIdError(f"Invalid filename: {filename!r}")
    path = Path(candidate)
    if not path.exists():
        return False
    path.unlink()
    thumb = path.with_name(path.name + ".thumb.jpg")
    if thumb.exists():
        thumb.unlink()
    return True


def generate_pdf_thumbnail(pdf_path: Path, thumb_path: Path) -> None:
    try:
        import fitz
        doc = fitz.open(str(pdf_path))
        page = doc[0]
        mat = fitz.Matrix(1.5, 1.5)
        pix = page.get_pixmap(matrix=mat)
        pix.save(str(thumb_path))
    except Exception as exc:
        _log.warning("PDF thumbnail generation failed for %s: %s", pdf_path, exc)
