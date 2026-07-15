# packages/backend/src/myhome/main.py
import asyncio
import os
import secrets
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from .backup_scheduler import scheduled_backup_loop
from .deps import ROLE_ORDER, get_user_from_request
from .ids import InvalidIdError
from .mcp_app import mcp_asgi_app
from .mcp_server import mcp
from .notification_scheduler import notification_digest_loop
from .persistence_mcp import load_mcp_config
from .routes import activity, auth, backup, chores, consumables, costs, ha, homes, house, inventory, kb, mcp_config, notifications, settings, svg, works


@asynccontextmanager
async def _lifespan(app: FastAPI):
    # The MCP session manager's background task group is NOT started just by
    # mounting mcp_asgi_app -- Starlette never forwards ASGI lifespan events into
    # mounted sub-apps, so it must be entered here explicitly.
    async with mcp.session_manager.run():
        digest_task = asyncio.create_task(notification_digest_loop())
        backup_task = asyncio.create_task(scheduled_backup_loop())
        try:
            yield
        finally:
            digest_task.cancel()
            backup_task.cancel()


app = FastAPI(title="MyHome Backend", version="0.1.0", lifespan=_lifespan)


@app.exception_handler(InvalidIdError)
async def _invalid_id_handler(request: Request, exc: InvalidIdError) -> JSONResponse:
    return JSONResponse({"detail": str(exc)}, status_code=400)


# ── First boot ────────────────────────────────────────────────────────────

def _first_boot() -> None:
    data_dir = Path(os.environ.get("DATA_DIR", "/data"))
    if not data_dir.exists():
        return  # DATA_DIR not yet mounted (CI/test import without fixture)
    from .persistence_auth import load_users

    if load_users().users:
        return
    from passlib.context import CryptContext

    from .models_auth import User, UserDocument
    from .persistence_auth import initial_admin_password_file, save_users

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

    # Hand the generated password to the operator via a 0600 file rather than
    # stdout, since container logs are routinely shipped to log aggregators
    # and retained indefinitely -- a much larger and longer-lived exposure
    # than a single file on the data volume. clear_initial_admin_password()
    # deletes this file as soon as any login succeeds, so the plaintext-at-
    # rest window is bounded to "until first use", not permanent. Some
    # one-time credential handoff to a human operator is unavoidable for
    # auto-generated first-boot credentials (see e.g. kubeadm join tokens,
    # Vaultwarden's admin token); this is that handoff, deliberately scoped
    # as tightly as the UX allows. (CodeQL alert #124, py/clear-text-storage-
    # sensitive-data, dismissed as won't-fix for this reason.)
    password_file = initial_admin_password_file()
    password_file.write_text(password + "\n")
    os.chmod(password_file, 0o600)
    print(f"[myhome] First boot — admin password written to {password_file}", flush=True)


_first_boot()


# ── Auth middleware ────────────────────────────────────────────────────────

_EXEMPT_PATHS = {
    "/api/auth/login", "/api/auth/refresh",
    "/api/auth/oidc/status", "/api/auth/oidc/login", "/api/auth/oidc/callback",
}


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    path = request.url.path
    if path in _EXEMPT_PATHS:
        return await call_next(request)
    if not (path.startswith("/api/") or path.startswith("/mcp")):
        # Static frontend assets (including the SPA shell at "/") are public --
        # every real route is registered under /api/, so this only ever
        # matches static files. The SPA itself decides whether to show the
        # login screen based on 401s from its own /api/auth/me call; it can't
        # do that if the shell/JS bundle never loads in the first place (e.g.
        # a Home Assistant ingress request, which never carries our cookies).
        return await call_next(request)
    user = await get_user_from_request(request)
    if user is None:
        return JSONResponse({"detail": "Authentication required"}, status_code=401)
    user_id, role = user
    if (
        request.method in ("POST", "PUT", "DELETE", "PATCH")
        and not request.url.path.startswith("/api/auth/")
        and not request.url.path.startswith("/mcp")
        and ROLE_ORDER.get(role, -1) < ROLE_ORDER["normal"]
    ):
        return JSONResponse({"detail": "Insufficient permissions"}, status_code=403)
    request.state.user = user
    return await call_next(request)


# ── MCP gate ──────────────────────────────────────────────────────────────
# The MCP tool surface is always mounted, but only reachable while enabled in
# Settings. Authentication still applies either way (auth_middleware above runs
# first) -- this only controls whether an *authenticated* request gets a real
# response or a 404.

async def _gated_mcp_app(scope, receive, send):
    if scope["type"] == "http" and not load_mcp_config().enabled:
        response = JSONResponse({"detail": "MCP server is disabled"}, status_code=404)
        await response(scope, receive, send)
        return
    await mcp_asgi_app(scope, receive, send)


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
app.include_router(notifications.router)
app.include_router(mcp_config.router)
app.include_router(activity.router)

app.mount("/mcp", _gated_mcp_app)


# ── Static files ──────────────────────────────────────────────────────────

_static_dir = Path(os.environ.get("STATIC_DIR", "/app/static"))
if _static_dir.exists():
    from fastapi.staticfiles import StaticFiles

    app.mount("/", StaticFiles(directory=str(_static_dir), html=True), name="static")
