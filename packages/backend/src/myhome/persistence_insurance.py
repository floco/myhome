import json
from pathlib import Path

from sqlalchemy import select

from . import attachment_storage
from .attachment_storage import generate_pdf_thumbnail
from .db import get_engine
from .models_insurance import InsurancePolicy, InsuranceDocument
from .schema import insurance_policies as insurance_policies_table

_MODULE = "insurance"


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
    return attachment_storage.get_attachment_path(home_id, _MODULE, policy_id, filename)


def save_attachment(home_id: str, policy_id: str, filename: str, data: bytes) -> None:
    attachment_storage.save_attachment(home_id, _MODULE, policy_id, filename, data)


def delete_attachment(home_id: str, policy_id: str, filename: str) -> bool:
    return attachment_storage.delete_attachment(home_id, _MODULE, policy_id, filename)


def delete_all_attachments(home_id: str, policy_id: str) -> None:
    attachment_storage.delete_all_attachments(home_id, _MODULE, policy_id)


def reset_insurance(home_id: str) -> None:
    save_insurance(home_id, InsuranceDocument())
    attachment_storage.delete_all_module_attachments(home_id, _MODULE)
