from __future__ import annotations

import os
from pathlib import Path

from .models_kb import KBEntry


def _kb_dir() -> Path:
    return Path(os.environ.get("DATA_DIR", "/data")) / "kb"


def _entry_path(id: str) -> Path:
    return _kb_dir() / f"{id}.md"


def _parse_frontmatter(text: str) -> tuple[dict, str]:
    """Parse simple YAML-style frontmatter from a .md file."""
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
    title = entry.title.replace("\n", " ")
    return (
        f"---\n"
        f"id: {entry.id}\n"
        f"title: {title}\n"
        f"createdAt: {entry.createdAt}\n"
        f"updatedAt: {entry.updatedAt}\n"
        f"---\n\n"
        f"{entry.content}"
    )


def _read_entry_file(path: Path) -> KBEntry | None:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    meta, body = _parse_frontmatter(text)
    if not meta.get("id") or not meta.get("title"):
        return None
    return KBEntry(
        id=meta["id"],
        title=meta["title"],
        content=body.lstrip("\n"),
        createdAt=meta.get("createdAt", ""),
        updatedAt=meta.get("updatedAt", ""),
    )


def load_all() -> list[KBEntry]:
    """Return all entries sorted oldest-first."""
    d = _kb_dir()
    if not d.exists():
        return []
    entries = [e for path in d.glob("*.md") if (e := _read_entry_file(path))]
    entries.sort(key=lambda e: e.createdAt)
    return entries


def load_entry(id: str) -> KBEntry | None:
    return _read_entry_file(_entry_path(id))


def save_entry(entry: KBEntry) -> None:
    d = _kb_dir()
    d.mkdir(parents=True, exist_ok=True)
    path = _entry_path(entry.id)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(_build_file(entry), encoding="utf-8")
    tmp.replace(path)


def delete_entry(id: str) -> bool:
    path = _entry_path(id)
    if not path.exists():
        return False
    path.unlink()
    return True
