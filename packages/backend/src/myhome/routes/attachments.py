# packages/backend/src/myhome/routes/attachments.py
"""Generic attachment routes shared by every module: upload / get / delete,
all keyed by (home_id, module, item_id). Replaces the 8 near-identical
per-module attachment routes that used to live in routes/inventory.py,
routes/chores.py, routes/costs.py, routes/works.py, routes/kb.py,
routes/build.py, routes/insurance.py, and routes/properties.py -- normal
session-cookie/Bearer-token auth via the app-wide auth_middleware, same as
every other /api/ route (see routes/attachments_tokens.py for the separate,
token-authenticated routes used by the MCP two-phase upload/download flow)."""
from __future__ import annotations

import mimetypes
import os

from fastapi import APIRouter, HTTPException, UploadFile
from fastapi.responses import FileResponse

from ..attachment_modules import get_adapter
from ..attachment_validation import ALLOWED_EXTENSIONS, sanitise_filename, validate_filename, validate_id

router = APIRouter()


def _validated_id(value: str) -> None:
    try:
        validate_id(value)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _validated_filename(value: str) -> None:
    try:
        validate_filename(value)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _get_adapter_or_404(module: str):
    try:
        return get_adapter(module)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/api/homes/{home_id}/attachments/{module}/{item_id}", status_code=201)
async def upload_attachment(home_id: str, module: str, item_id: str, file: UploadFile) -> dict:
    _validated_id(item_id)
    adapter = _get_adapter_or_404(module)
    item, save = adapter.find(home_id, item_id)
    if item is None:
        raise HTTPException(status_code=404)
    original = file.filename or ""
    ext = os.path.splitext(original.lower())[1]
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="File type not supported")
    filename = sanitise_filename(original)
    _validated_filename(filename)
    data = await file.read()
    adapter.save_attachment(home_id, item_id, filename, data)
    if ext == ".pdf":
        pdf_path = adapter.get_attachment_path(home_id, item_id, filename)
        thumb_path = pdf_path.with_name(pdf_path.name + ".thumb.jpg")
        adapter.generate_pdf_thumbnail(pdf_path, thumb_path)
    if filename not in item.attachments:
        item.attachments.append(filename)
    save()
    return {"filename": filename}


@router.get("/api/homes/{home_id}/attachments/{module}/{item_id}/{filename}")
def get_attachment(home_id: str, module: str, item_id: str, filename: str) -> FileResponse:
    _validated_id(item_id)
    _validated_filename(filename)
    adapter = _get_adapter_or_404(module)
    path = adapter.get_attachment_path(home_id, item_id, filename)
    if not path.is_file():
        raise HTTPException(status_code=404)
    media_type, _ = mimetypes.guess_type(filename)
    return FileResponse(str(path), media_type=media_type or "application/octet-stream", content_disposition_type="inline")


@router.delete("/api/homes/{home_id}/attachments/{module}/{item_id}/{filename}", status_code=204)
def remove_attachment(home_id: str, module: str, item_id: str, filename: str) -> None:
    _validated_id(item_id)
    _validated_filename(filename)
    adapter = _get_adapter_or_404(module)
    item, save = adapter.find(home_id, item_id)
    if item is None:
        raise HTTPException(status_code=404)
    if not adapter.delete_attachment(home_id, item_id, filename):
        raise HTTPException(status_code=404)
    item.attachments = [a for a in item.attachments if a != filename]
    save()
