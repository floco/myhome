import mimetypes
import os
import re
import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import FileResponse

from ..deps import get_current_user_id
from ..models_costs import CostEntry
from ..models_insurance import InsurancePolicy, InsurancePolicyCreate, InsurancePolicyUpdate, InsuranceDocument
from ..persistence_activity import log_activity
from ..persistence_costs import load_costs, save_costs
from ..persistence_insurance import (
    delete_all_attachments,
    delete_attachment,
    generate_pdf_thumbnail,
    get_attachment_path,
    load_insurance,
    save_attachment,
    save_insurance,
)

router = APIRouter()

_FREQUENCY_MULTIPLIER = {"monthly": 12, "quarterly": 4, "annual": 1, "other": 1}


def _annualized_amount(amount: float, frequency: str) -> float:
    return amount * _FREQUENCY_MULTIPLIER[frequency]


def _sync_cost_entry(home_id: str, policy: InsurancePolicy) -> str | None:
    costs_doc = load_costs(home_id)
    costs_doc.entries = [e for e in costs_doc.entries if e.id != policy.linkedCostEntryId]
    linked_id = None
    if policy.includeInCosts and policy.premiumAmount is not None:
        linked_id = policy.linkedCostEntryId or str(uuid.uuid4())
        costs_doc.entries.append(CostEntry(
            id=linked_id,
            categoryId="cat-insurance",
            date=policy.startDate or date.today().isoformat(),
            totalAmount=_annualized_amount(policy.premiumAmount, policy.premiumFrequency),
            contactId=policy.contactId,
            notes=f"{policy.name} ({policy.premiumFrequency})",
            sourceModule="insurance",
            sourceId=policy.id,
        ))
    save_costs(home_id, costs_doc)
    return linked_id


@router.get("/api/homes/{home_id}/insurance", response_model=InsuranceDocument)
def get_insurance(home_id: str) -> InsuranceDocument:
    return load_insurance(home_id)


@router.post("/api/homes/{home_id}/insurance", response_model=InsurancePolicy, status_code=201)
def create_policy(
    home_id: str, body: InsurancePolicyCreate,
    current_user_id: str = Depends(get_current_user_id),
) -> InsurancePolicy:
    doc = load_insurance(home_id)
    policy = InsurancePolicy(id=str(uuid.uuid4()), **body.model_dump())
    policy.linkedCostEntryId = _sync_cost_entry(home_id, policy)
    doc.policies.append(policy)
    save_insurance(home_id, doc)
    log_activity(home_id, current_user_id, "insurance", "create", policy.name, policy.id)
    return policy


@router.put("/api/homes/{home_id}/insurance/{id}", status_code=204)
def update_policy(
    home_id: str, id: str, body: InsurancePolicyUpdate,
    current_user_id: str = Depends(get_current_user_id),
) -> None:
    doc = load_insurance(home_id)
    policy = next((p for p in doc.policies if p.id == id), None)
    if not policy:
        raise HTTPException(status_code=404)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(policy, field, value)
    policy.linkedCostEntryId = _sync_cost_entry(home_id, policy)
    save_insurance(home_id, doc)
    log_activity(home_id, current_user_id, "insurance", "update", policy.name, id)


@router.delete("/api/homes/{home_id}/insurance/{id}", status_code=204)
def delete_policy(
    home_id: str, id: str,
    current_user_id: str = Depends(get_current_user_id),
) -> None:
    doc = load_insurance(home_id)
    policy = next((p for p in doc.policies if p.id == id), None)
    if policy is None:
        raise HTTPException(status_code=404)
    policy.includeInCosts = False
    _sync_cost_entry(home_id, policy)
    doc.policies = [p for p in doc.policies if p.id != id]
    save_insurance(home_id, doc)
    delete_all_attachments(home_id, id)
    log_activity(home_id, current_user_id, "insurance", "delete", policy.name, id)


_ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".webp"}


def _sanitise_filename(name: str) -> str:
    name = name.replace(" ", "_")
    name = re.sub(r"[^a-zA-Z0-9._-]", "", name)
    return name or "attachment"


_ID_RE = re.compile(r"[A-Za-z0-9_-]{1,64}")


def _validate_id(policy_id: str) -> None:
    if not _ID_RE.fullmatch(policy_id):
        raise HTTPException(status_code=400, detail="Invalid id")


def _validate_filename(filename: str) -> None:
    if not re.fullmatch(r"[A-Za-z0-9._-]+", filename) or filename.startswith("."):
        raise HTTPException(status_code=400, detail="Invalid filename")


@router.post("/api/homes/{home_id}/insurance/{id}/attachments", status_code=201)
async def upload_attachment(home_id: str, id: str, file: UploadFile) -> dict:
    _validate_id(id)
    doc = load_insurance(home_id)
    policy = next((p for p in doc.policies if p.id == id), None)
    if not policy:
        raise HTTPException(status_code=404)
    original = file.filename or ""
    ext = os.path.splitext(original)[1].lower()
    if ext not in _ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Unsupported file type")
    filename = _sanitise_filename(original)
    data = await file.read()
    save_attachment(home_id, id, filename, data)
    if ext == ".pdf":
        pdf_path = get_attachment_path(home_id, id, filename)
        thumb_path = pdf_path.with_name(pdf_path.name + ".thumb.jpg")
        generate_pdf_thumbnail(pdf_path, thumb_path)
    if filename not in policy.attachments:
        policy.attachments.append(filename)
    save_insurance(home_id, doc)
    return {"filename": filename}


@router.get("/api/homes/{home_id}/insurance/{id}/attachments/{filename}")
def get_attachment(home_id: str, id: str, filename: str) -> FileResponse:
    _validate_id(id)
    _validate_filename(filename)
    path = get_attachment_path(home_id, id, filename)
    if not path.is_file():
        raise HTTPException(status_code=404)
    media_type, _ = mimetypes.guess_type(filename)
    return FileResponse(str(path), media_type=media_type or "application/octet-stream", filename=filename)


@router.delete("/api/homes/{home_id}/insurance/{id}/attachments/{filename}", status_code=204)
def remove_attachment(home_id: str, id: str, filename: str) -> None:
    _validate_id(id)
    _validate_filename(filename)
    doc = load_insurance(home_id)
    policy = next((p for p in doc.policies if p.id == id), None)
    if not policy:
        raise HTTPException(status_code=404)
    if not delete_attachment(home_id, id, filename):
        raise HTTPException(status_code=404)
    policy.attachments = [a for a in policy.attachments if a != filename]
    save_insurance(home_id, doc)
