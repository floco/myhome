import json
import os

import httpx
from fastapi import APIRouter

router = APIRouter()

_HA_BASE = "http://supervisor/core/api"


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
