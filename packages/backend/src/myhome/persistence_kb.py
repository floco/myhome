from __future__ import annotations

import logging
import os
import shutil
from pathlib import Path

from .models_kb import KBEntry

_log = logging.getLogger(__name__)


def _home_dir(home_id: str) -> Path:
    return Path(os.environ.get("DATA_DIR", "/data")) / "homes" / home_id


def _kb_dir(home_id: str) -> Path:
    return _home_dir(home_id) / "kb"


def _entry_path(home_id: str, id: str) -> Path:
    return _kb_dir(home_id) / f"{id}.md"


def _attachments_dir(home_id: str, entry_id: str) -> Path:
    return _home_dir(home_id) / "kb-attachments" / entry_id


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
    title = entry.title.replace("\n", " ")
    lines = [
        "---",
        f"id: {entry.id}",
        f"title: {title}",
        f"createdAt: {entry.createdAt}",
        f"updatedAt: {entry.updatedAt}",
    ]
    if entry.attachments:
        lines.append(f"attachments: {','.join(entry.attachments)}")
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
    return KBEntry(
        id=meta["id"],
        title=meta["title"],
        content=body.lstrip("\n"),
        createdAt=meta.get("createdAt", ""),
        updatedAt=meta.get("updatedAt", ""),
        attachments=attachments,
    )


def load_all(home_id: str) -> list[KBEntry]:
    d = _kb_dir(home_id)
    if not d.exists():
        return []
    entries = [e for path in d.glob("*.md") if (e := _read_entry_file(path))]
    entries.sort(key=lambda e: e.createdAt)
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


def save_attachment(home_id: str, entry_id: str, filename: str, data: bytes) -> None:
    path = _attachments_dir(home_id, entry_id)
    path.mkdir(parents=True, exist_ok=True)
    (path / filename).write_bytes(data)


def delete_attachment(home_id: str, entry_id: str, filename: str) -> bool:
    path = _attachments_dir(home_id, entry_id) / filename
    if not path.exists():
        return False
    path.unlink()
    thumb = path.parent / (filename + ".thumb.jpg")
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
