import json
import logging
import os
import shutil
from pathlib import Path

from sqlalchemy import select

from .db import get_engine
from .ids import InvalidIdError
from .models_insurance import InsurancePolicy, InsuranceDocument
from .schema import insurance_policies as insurance_policies_table

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


def _attachments_dir(home_id: str, policy_id: str) -> Path:
    # Same inline lexical-normalize-then-verify-containment shape as
    # _home_dir() above -- policy_id is validated at the route layer too, but
    # CodeQL's taint tracker doesn't credit a separate validator function as
    # sanitizing the value used here.
    base = os.path.normpath(str(_home_dir(home_id) / "insurance-attachments"))
    candidate = os.path.normpath(os.path.join(base, policy_id))
    if not candidate.startswith(base + os.sep):
        raise InvalidIdError(f"Invalid policy_id: {policy_id!r}")
    return Path(candidate)


def load_insurance(home_id: str) -> InsuranceDocument:
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(
            select(insurance_policies_table).where(insurance_policies_table.c.home_id == home_id)
            .order_by(insurance_policies_table.c.order_index)
        ).mappings().all()
    return InsuranceDocument(policies=[
        InsurancePolicy(
            id=r["id"], name=r["name"], categoryId=r["category_id"], contactId=r["contact_id"],
            policyNumber=r["policy_number"], coverageSummary=r["coverage_summary"],
            conditionsUrl=r["conditions_url"], startDate=r["start_date"], endDate=r["end_date"],
            premiumAmount=r["premium_amount"], premiumFrequency=r["premium_frequency"],
            includeInCosts=bool(r["include_in_costs"]), alternatives=r["alternatives"],
            notes=r["notes"], attachments=json.loads(r["attachments"]),
            linkedCostEntryId=r["linked_cost_entry_id"],
        )
        for r in rows
    ])


def save_insurance(home_id: str, doc: InsuranceDocument) -> None:
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(insurance_policies_table.delete().where(insurance_policies_table.c.home_id == home_id))
        if doc.policies:
            conn.execute(insurance_policies_table.insert(), [
                {
                    "id": p.id, "home_id": home_id, "order_index": i, "name": p.name,
                    "category_id": p.categoryId, "contact_id": p.contactId,
                    "policy_number": p.policyNumber, "coverage_summary": p.coverageSummary,
                    "conditions_url": p.conditionsUrl, "start_date": p.startDate, "end_date": p.endDate,
                    "premium_amount": p.premiumAmount, "premium_frequency": p.premiumFrequency,
                    "include_in_costs": p.includeInCosts, "alternatives": p.alternatives,
                    "notes": p.notes, "attachments": json.dumps(p.attachments),
                    "linked_cost_entry_id": p.linkedCostEntryId,
                }
                for i, p in enumerate(doc.policies)
            ])


def get_attachment_path(home_id: str, policy_id: str, filename: str) -> Path:
    base = os.path.normpath(str(_attachments_dir(home_id, policy_id)))
    candidate = os.path.normpath(os.path.join(base, filename))
    if not candidate.startswith(base + os.sep):
        raise InvalidIdError(f"Invalid filename: {filename!r}")
    return Path(candidate)


def save_attachment(home_id: str, policy_id: str, filename: str, data: bytes) -> None:
    path = _attachments_dir(home_id, policy_id)
    base = os.path.normpath(str(path))
    candidate = os.path.normpath(os.path.join(base, filename))
    if not candidate.startswith(base + os.sep):
        raise InvalidIdError(f"Invalid filename: {filename!r}")
    path.mkdir(parents=True, exist_ok=True)
    Path(candidate).write_bytes(data)


def delete_attachment(home_id: str, policy_id: str, filename: str) -> bool:
    base = os.path.normpath(str(_attachments_dir(home_id, policy_id)))
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


def delete_all_attachments(home_id: str, policy_id: str) -> None:
    path = _attachments_dir(home_id, policy_id)
    if path.exists():
        shutil.rmtree(path)


def reset_insurance(home_id: str) -> None:
    save_insurance(home_id, InsuranceDocument())
    attachments_root = _home_dir(home_id) / "insurance-attachments"
    if attachments_root.exists():
        shutil.rmtree(attachments_root)


def generate_pdf_thumbnail(pdf_path: Path, thumb_path: Path) -> None:
    try:
        import fitz  # pymupdf
        doc = fitz.open(str(pdf_path))
        page = doc[0]
        mat = fitz.Matrix(1.5, 1.5)
        pix = page.get_pixmap(matrix=mat)
        pix.save(str(thumb_path))
    except Exception as exc:
        _log.warning("PDF thumbnail generation failed for %s: %s", pdf_path, exc)
