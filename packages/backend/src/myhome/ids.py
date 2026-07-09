# packages/backend/src/myhome/ids.py
from __future__ import annotations

import re

_SAFE_ID_RE = re.compile(r"[A-Za-z0-9_-]{1,64}")


class InvalidIdError(ValueError):
    """Raised when a caller-supplied id fails safe-id validation.

    These ids are interpolated into filesystem paths (home_id, entry ids,
    filenames), so an unvalidated value is a path-traversal / injection
    vector rather than just a data-quality issue.
    """


def validate_safe_id(value: str, *, label: str = "id") -> str:
    if not _SAFE_ID_RE.fullmatch(value):
        raise InvalidIdError(f"Invalid {label}: {value!r}")
    return value
