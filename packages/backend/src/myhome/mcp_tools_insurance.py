from __future__ import annotations

import uuid

from mcp.server.fastmcp import Context

from .mcp_server import _require_role, _resolve_home_id, mcp
from .models_insurance import InsurancePolicy
from .persistence_insurance import load_insurance, save_insurance

_VALID_FREQUENCIES = ("monthly", "quarterly", "annual", "other")


def _list_insurance_policies_impl(home_id: str | None) -> dict:
    resolved = _resolve_home_id(home_id)
    return load_insurance(resolved).model_dump()


def _create_insurance_policy_impl(
    home_id: str | None,
    name: str,
    category_id: str,
    contact_id: str | None = None,
    policy_number: str | None = None,
    coverage_summary: str = "",
    conditions_url: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    premium_amount: float | None = None,
    premium_frequency: str = "annual",
    include_in_costs: bool = False,
    alternatives: str = "",
    notes: str = "",
) -> dict:
    if premium_frequency not in _VALID_FREQUENCIES:
        raise ValueError(f"premium_frequency must be one of {_VALID_FREQUENCIES}")
    resolved = _resolve_home_id(home_id)
    doc = load_insurance(resolved)
    policy = InsurancePolicy(
        id=str(uuid.uuid4()), name=name, categoryId=category_id, contactId=contact_id,
        policyNumber=policy_number, coverageSummary=coverage_summary, conditionsUrl=conditions_url,
        startDate=start_date, endDate=end_date, premiumAmount=premium_amount,
        premiumFrequency=premium_frequency, includeInCosts=include_in_costs,
        alternatives=alternatives, notes=notes,
    )
    doc.policies.append(policy)
    save_insurance(resolved, doc)
    return policy.model_dump()


def _update_insurance_policy_impl(home_id: str | None, policy_id: str, **fields) -> dict:
    if fields.get("premiumFrequency") is not None and fields["premiumFrequency"] not in _VALID_FREQUENCIES:
        raise ValueError(f"premium_frequency must be one of {_VALID_FREQUENCIES}")
    resolved = _resolve_home_id(home_id)
    doc = load_insurance(resolved)
    policy = next((p for p in doc.policies if p.id == policy_id), None)
    if policy is None:
        raise ValueError(f"Unknown policy_id {policy_id!r}")
    for field, value in fields.items():
        if value is not None:
            setattr(policy, field, value)
    save_insurance(resolved, doc)
    return policy.model_dump()


def _delete_insurance_policy_impl(home_id: str | None, policy_id: str) -> dict:
    resolved = _resolve_home_id(home_id)
    doc = load_insurance(resolved)
    before = len(doc.policies)
    doc.policies = [p for p in doc.policies if p.id != policy_id]
    if len(doc.policies) == before:
        raise ValueError(f"Unknown policy_id {policy_id!r}")
    save_insurance(resolved, doc)
    return {"deleted": policy_id}


@mcp.tool()
async def list_insurance_policies(ctx: Context, home_id: str | None = None) -> dict:
    """List insurance policies for a home (home, auto, health, life, travel, liability, etc.)."""
    await _require_role(ctx.request_context.request, "ro")
    return _list_insurance_policies_impl(home_id)


@mcp.tool()
async def create_insurance_policy(
    ctx: Context,
    name: str,
    category_id: str,
    home_id: str | None = None,
    contact_id: str | None = None,
    policy_number: str | None = None,
    coverage_summary: str = "",
    conditions_url: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    premium_amount: float | None = None,
    premium_frequency: str = "annual",
    include_in_costs: bool = False,
    alternatives: str = "",
    notes: str = "",
) -> dict:
    """Create an insurance policy. premium_frequency is 'monthly', 'quarterly', 'annual', or 'other'.
    category_id should match an id from get_settings's insuranceCategories. Note: unlike the web UI,
    this tool does NOT sync include_in_costs=True policies into the Costs module -- that sync only
    runs through the HTTP route layer. Use the app UI or REST API if the Costs sync matters."""
    await _require_role(ctx.request_context.request, "normal")
    return _create_insurance_policy_impl(
        home_id, name, category_id, contact_id, policy_number, coverage_summary, conditions_url,
        start_date, end_date, premium_amount, premium_frequency, include_in_costs, alternatives, notes,
    )


@mcp.tool()
async def update_insurance_policy(
    ctx: Context,
    policy_id: str,
    home_id: str | None = None,
    name: str | None = None,
    category_id: str | None = None,
    contact_id: str | None = None,
    policy_number: str | None = None,
    coverage_summary: str | None = None,
    conditions_url: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    premium_amount: float | None = None,
    premium_frequency: str | None = None,
    include_in_costs: bool | None = None,
    alternatives: str | None = None,
    notes: str | None = None,
) -> dict:
    """Update fields on an existing insurance policy. See create_insurance_policy's note about Costs sync."""
    await _require_role(ctx.request_context.request, "normal")
    return _update_insurance_policy_impl(
        home_id, policy_id, name=name, categoryId=category_id, contactId=contact_id,
        policyNumber=policy_number, coverageSummary=coverage_summary, conditionsUrl=conditions_url,
        startDate=start_date, endDate=end_date, premiumAmount=premium_amount,
        premiumFrequency=premium_frequency, includeInCosts=include_in_costs,
        alternatives=alternatives, notes=notes,
    )


@mcp.tool()
async def delete_insurance_policy(ctx: Context, policy_id: str, home_id: str | None = None) -> dict:
    """Delete an insurance policy."""
    await _require_role(ctx.request_context.request, "normal")
    return _delete_insurance_policy_impl(home_id, policy_id)
