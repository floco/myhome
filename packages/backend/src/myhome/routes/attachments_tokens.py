# packages/backend/src/myhome/routes/attachments_tokens.py
"""Token-authenticated attachment upload/download routes for the MCP
two-phase flow: the MCP tools request_attachment_upload / get_attachment mint
a short-lived single-use token (attachment_tokens.py) and hand the agent a
URL pointing here. These routes are exempted from the normal cookie/Bearer
auth middleware (see main.py's _EXEMPT_PATHS) -- the token itself is the
credential, consumed exactly once to do the actual save-and-link, or to
serve the file."""
from __future__ import annotations

import mimetypes
import os

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse

from ..attachment_modules import get_adapter
from ..attachment_tokens import InvalidTokenError, consume_token

router = APIRouter()


@router.post("/api/attachments/upload/{token}", status_code=201)
async def upload_via_token(token: str, request: Request) -> dict:
    try:
        scope = consume_token(token, "upload")
    except InvalidTokenError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    adapter = get_adapter(scope.module)
    item, save = adapter.find(scope.home_id, scope.item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Item no longer exists")
    data = await request.body()
    adapter.save_attachment(scope.home_id, scope.item_id, scope.filename, data)
    ext = os.path.splitext(scope.filename.lower())[1]
    if ext == ".pdf":
        pdf_path = adapter.get_attachment_path(scope.home_id, scope.item_id, scope.filename)
        thumb_path = pdf_path.with_name(pdf_path.name + ".thumb.jpg")
        adapter.generate_pdf_thumbnail(pdf_path, thumb_path)
    if scope.filename not in item.attachments:
        item.attachments.append(scope.filename)
    save()
    return {"filename": scope.filename}


@router.get("/api/attachments/download/{token}")
def download_via_token(token: str) -> FileResponse:
    try:
        scope = consume_token(token, "download")
    except InvalidTokenError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    adapter = get_adapter(scope.module)
    path = adapter.get_attachment_path(scope.home_id, scope.item_id, scope.filename)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Attachment not found")
    media_type, _ = mimetypes.guess_type(scope.filename)
    return FileResponse(
        str(path), media_type=media_type or "application/octet-stream",
        content_disposition_type="attachment", filename=scope.filename,
    )
