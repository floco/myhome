# packages/backend/src/myhome/main.py
import os
import secrets
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from .deps import ROLE_ORDER, get_user_from_request
from .routes import auth, backup, chores, consumables, costs, ha, homes, house, inventory, kb, settings, svg, works

app = FastAPI(title="MyHome Backend", version="0.1.0")


# ── First boot ────────────────────────────────────────────────────────────

def _first_boot() -> None:
    data_dir = Path(os.environ.get("DATA_DIR", "/data"))
    if not data_dir.exists():
        return  # DATA_DIR not yet mounted (CI/test import without fixture)
    if (data_dir / "users.json").exists():
        return
    from passlib.context import CryptContext

    from .models_auth import User, UserDocument
    from .persistence_auth import save_users

    pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
    password = secrets.token_urlsafe(12)
    admin = User(
        id=secrets.token_hex(8),
        username="admin",
        password_hash=pwd_ctx.hash(password),
        role="admin",
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    save_users(UserDocument(users=[admin]))
    print(f"[myhome] First boot — admin password: {password}", flush=True)


_first_boot()

from .persistence_homes import migrate_legacy_if_needed
migrate_legacy_if_needed()


# ── Auth middleware ────────────────────────────────────────────────────────

_EXEMPT_PATHS = {"/api/auth/login", "/api/auth/refresh"}


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    if request.url.path in _EXEMPT_PATHS:
        return await call_next(request)
    user = await get_user_from_request(request)
    if user is None:
        return JSONResponse({"detail": "Authentication required"}, status_code=401)
    user_id, role = user
    if (
        request.method in ("POST", "PUT", "DELETE", "PATCH")
        and not request.url.path.startswith("/api/auth/")
        and ROLE_ORDER.get(role, -1) < ROLE_ORDER["normal"]
    ):
        return JSONResponse({"detail": "Insufficient permissions"}, status_code=403)
    request.state.user = user
    return await call_next(request)


# ── Routers ───────────────────────────────────────────────────────────────

app.include_router(auth.router)
app.include_router(homes.router)
app.include_router(house.router)
app.include_router(svg.router)
app.include_router(ha.router)
app.include_router(chores.router)
app.include_router(inventory.router)
app.include_router(settings.router)
app.include_router(costs.router)
app.include_router(works.router)
app.include_router(kb.router)
app.include_router(backup.router)
app.include_router(consumables.router)


# ── Static files ──────────────────────────────────────────────────────────

_static_dir = Path(os.environ.get("STATIC_DIR", "/app/static"))
if _static_dir.exists():
    from fastapi.staticfiles import StaticFiles

    app.mount("/", StaticFiles(directory=str(_static_dir), html=True), name="static")
