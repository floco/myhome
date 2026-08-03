# packages/backend/src/myhome/attachment_storage.py
"""Generic on-disk storage for every module's attachments. Every module's
attachment tree lives at {DATA_DIR}/homes/{home_id}/{module}-attachments/{item_id}/
-- this is the one place that computes those paths and touches disk, used by
the generic attachments REST routes, the MCP attachment tools, and each
module's own persistence_*.py (via thin per-module wrappers, so existing call
sites keep working unchanged) instead of each keeping its own byte-identical
copy of this logic."""
from __future__ import annotations

import logging
import os
import shutil
from pathlib import Path

from .ids import InvalidIdError

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


def module_attachments_root(home_id: str, module: str) -> Path:
    """The {module}-attachments/ directory for a home, e.g. .../kb-attachments/."""
    return _home_dir(home_id) / f"{module}-attachments"


def attachments_dir(home_id: str, module: str, item_id: str) -> Path:
    # Same inline lexical-normalize-then-verify-containment shape as
    # _home_dir() above -- item_id is validated at the route layer too, but
    # CodeQL's taint tracker doesn't credit a separate validator function as
    # sanitizing the value used here.
    base = os.path.normpath(str(module_attachments_root(home_id, module)))
    candidate = os.path.normpath(os.path.join(base, item_id))
    if not candidate.startswith(base + os.sep):
        raise InvalidIdError(f"Invalid item_id: {item_id!r}")
    return Path(candidate)


def get_attachment_path(home_id: str, module: str, item_id: str, filename: str) -> Path:
    base = os.path.normpath(str(attachments_dir(home_id, module, item_id)))
    candidate = os.path.normpath(os.path.join(base, filename))
    if not candidate.startswith(base + os.sep):
        raise InvalidIdError(f"Invalid filename: {filename!r}")
    return Path(candidate)


def save_attachment(home_id: str, module: str, item_id: str, filename: str, data: bytes) -> None:
    path = attachments_dir(home_id, module, item_id)
    base = os.path.normpath(str(path))
    candidate = os.path.normpath(os.path.join(base, filename))
    if not candidate.startswith(base + os.sep):
        raise InvalidIdError(f"Invalid filename: {filename!r}")
    path.mkdir(parents=True, exist_ok=True)
    Path(candidate).write_bytes(data)


def delete_attachment(home_id: str, module: str, item_id: str, filename: str) -> bool:
    base = os.path.normpath(str(attachments_dir(home_id, module, item_id)))
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


def delete_all_attachments(home_id: str, module: str, item_id: str) -> None:
    path = attachments_dir(home_id, module, item_id)
    if path.exists():
        shutil.rmtree(path)


def delete_all_module_attachments(home_id: str, module: str) -> None:
    """Wipe every item's attachments for a module at once -- used by each
    module's reset_X()."""
    path = module_attachments_root(home_id, module)
    if path.exists():
        shutil.rmtree(path)


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
