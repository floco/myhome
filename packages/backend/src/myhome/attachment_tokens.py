# packages/backend/src/myhome/attachment_tokens.py
"""Short-lived, single-use tokens that let an MCP-driven agent upload or
download an attachment via a plain HTTP request (curl), without ever needing
to see a real API token. Minted by an MCP tool call (which IS authenticated
via the normal role check), consumed exactly once by the attachments
upload/download routes -- those routes are exempted from the normal auth
middleware, since the token itself is the credential (see main.py's
_EXEMPT_PATHS).

In-memory only: this process runs as a single uvicorn worker (no --workers
flag anywhere in this codebase), and tokens are short-lived by design, so
losing pending tokens on a restart is an acceptable, self-healing edge case
-- the agent just mints a new one."""
from __future__ import annotations

import secrets
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

TOKEN_TTL = timedelta(minutes=10)


class InvalidTokenError(ValueError):
    """Raised when a token is missing, expired, already used, or the wrong kind."""


@dataclass
class AttachmentTokenScope:
    kind: str  # "upload" | "download"
    home_id: str
    module: str
    item_id: str
    filename: str
    expires_at: datetime


_lock = threading.Lock()
_tokens: dict[str, AttachmentTokenScope] = {}


def _mint(kind: str, home_id: str, module: str, item_id: str, filename: str) -> tuple[str, datetime]:
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + TOKEN_TTL
    scope = AttachmentTokenScope(
        kind=kind, home_id=home_id, module=module, item_id=item_id, filename=filename, expires_at=expires_at,
    )
    with _lock:
        _tokens[token] = scope
    return token, expires_at


def mint_upload_token(home_id: str, module: str, item_id: str, filename: str) -> tuple[str, datetime]:
    return _mint("upload", home_id, module, item_id, filename)


def mint_download_token(home_id: str, module: str, item_id: str, filename: str) -> tuple[str, datetime]:
    return _mint("download", home_id, module, item_id, filename)


def consume_token(token: str, kind: str) -> AttachmentTokenScope:
    """Validate and immediately invalidate a token (single-use, regardless of
    whether it turns out to be valid) -- raises InvalidTokenError if missing,
    already used, minted for the other kind, or expired."""
    with _lock:
        scope = _tokens.pop(token, None)
    if scope is None:
        raise InvalidTokenError("Unknown or already-used upload/download link")
    if scope.kind != kind:
        raise InvalidTokenError("Token is not valid for this operation")
    if datetime.now(timezone.utc) > scope.expires_at:
        raise InvalidTokenError("This upload/download link has expired")
    return scope
