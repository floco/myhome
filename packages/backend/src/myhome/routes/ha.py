import json
import os

import httpx
from fastapi import APIRouter, HTTPException

router = APIRouter()

_HA_BASE = "http://supervisor/core/api"

_ALLOWED_ENTITY_DOMAINS = {"binary_sensor", "cover"}


def _auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


@router.get("/api/ha/areas")
async def get_ha_areas() -> list[dict]:
    token = os.environ.get("SUPERVISOR_TOKEN")
    if not token:
        return []
    try:
        async with httpx.AsyncClient() as client:
            # Try the area registry list endpoint (HA 2023.x+)
            resp = await client.get(
                f"{_HA_BASE}/config/area_registry/list",
                headers=_auth_headers(token),
                timeout=5.0,
            )
            if resp.status_code == 200:
                data = resp.json()
                return [
                    {"area_id": a.get("area_id", a.get("id", "")), "name": a.get("name", "")}
                    for a in data
                    if a.get("area_id") or a.get("id")
                ]
            # Fallback: template API works in all HA versions
            template = (
                "[{%- for a in areas() -%}"
                "{%- if not loop.first -%},{%- endif -%}"
                '{\"area_id\":\"{{ a }}\",\"name\":\"{{ area_name(a) | replace(\'\"\', \'\\\\"\') }}\"}'
                "{%- endfor -%}]"
            )
            resp2 = await client.post(
                f"{_HA_BASE}/template",
                headers=_auth_headers(token),
                json={"template": template},
                timeout=5.0,
            )
            if resp2.status_code == 200:
                return json.loads(resp2.text)
    except Exception:
        pass
    return []


@router.get("/api/ha/entities")
async def get_ha_entities(area_id: str, domain: str) -> list[dict]:
    if domain not in _ALLOWED_ENTITY_DOMAINS:
        raise HTTPException(status_code=400, detail="unsupported domain")
    token = os.environ.get("SUPERVISOR_TOKEN")
    if not token:
        return []
    # area_id/domain are passed as Jinja `variables`, not string-interpolated into
    # the template source -- interpolating user-controlled query params directly
    # into the template text would be a server-side template injection hole.
    template = (
        "[{%- for e in area_entities(area_id) if e.startswith(domain + '.') -%}"
        "{%- if not loop.first -%},{%- endif -%}"
        '{"entity_id":"{{ e }}","name":"{{ (state_attr(e, \'friendly_name\') or e) '
        "| replace('\"', '\\\\\"') }}\"}"
        "{%- endfor -%}]"
    )
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{_HA_BASE}/template",
                headers=_auth_headers(token),
                json={"template": template, "variables": {"area_id": area_id, "domain": domain}},
                timeout=5.0,
            )
            if resp.status_code == 200:
                return json.loads(resp.text)
    except Exception:
        pass
    return []


async def call_ha_service(domain: str, service: str, data: dict) -> None:
    token = os.environ.get("SUPERVISOR_TOKEN")
    if not token:
        raise RuntimeError("SUPERVISOR_TOKEN not set")
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{_HA_BASE}/services/{domain}/{service}",
            headers=_auth_headers(token),
            json=data,
            timeout=5.0,
        )
        resp.raise_for_status()
