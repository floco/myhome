"""Shared filename/id validation for MCP attachment tools. The REST attachment
routes (routes/inventory.py etc.) each already duplicate an identical set of these
helpers per file; this is the one shared copy used by mcp_tools_attachments.py so
it doesn't need to import a private helper out of an unrelated route module."""
from __future__ import annotations

import re

ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".webp"}

_ID_RE = re.compile(r"[A-Za-z0-9_-]{1,64}")
_FILENAME_RE = re.compile(r"[A-Za-z0-9._-]+")


def sanitise_filename(name: str) -> str:
    name = name.replace(" ", "_")
    name = re.sub(r"[^a-zA-Z0-9._-]", "", name)
    return name or "attachment"


def validate_id(value: str) -> None:
    if not _ID_RE.fullmatch(value):
        raise ValueError(f"Invalid id {value!r}")


def validate_filename(filename: str) -> None:
    if not _FILENAME_RE.fullmatch(filename) or filename.startswith("."):
        raise ValueError(f"Invalid filename {filename!r}")
