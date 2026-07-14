from __future__ import annotations

import logging
import os
import shutil
from pathlib import Path

from .ids import InvalidIdError
from .models_kb import KBEntry

_log = logging.getLogger(__name__)


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
    if entry.folderId:
        lines.append(f"folderId: {entry.folderId}")
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
        folderId=meta.get("folderId") or None,
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
