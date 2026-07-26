from fastapi import APIRouter

from ..deps import require_auth
from ..system_info import check_for_update, get_static_system_info

router = APIRouter()


@router.get("/api/system/info")
async def get_system_info(current_user: tuple[str, str] = require_auth()) -> dict:
    info = get_static_system_info()
    info["updateCheck"] = await check_for_update(info["version"])
    return info
