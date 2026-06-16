import os
import httpx
from fastapi import APIRouter

router = APIRouter()


@router.get("/api/ha/areas")
async def get_ha_areas() -> list:
    token = os.environ.get("SUPERVISOR_TOKEN")
    if not token:
        return []
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "http://supervisor/core/api/config/area_registry",
                headers={"Authorization": f"Bearer {token}"},
                timeout=5.0,
            )
            resp.raise_for_status()
            return resp.json()
    except Exception:
        return []
