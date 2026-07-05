from __future__ import annotations

from starlette.requests import Request

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

from .deps import ROLE_ORDER, get_user_from_request
from .persistence_homes import load_homes

# streamable_http_path="/" — this FastMCP instance is mounted at "/mcp" by main.py
# (via mcp_app.py), so its own internal route should be registered at the mount's
# root, not at another nested "/mcp".
#
# transport_security disables FastMCP's own DNS-rebinding Host-header check, which
# by default only allows "127.0.0.1"/"localhost". This addon is normally reached
# over a LAN hostname or via Home Assistant's ingress proxy, so that check would
# reject every legitimate request. Our own auth middleware (main.py) already
# requires a valid session cookie or Bearer API token on every request before it
# reaches any MCP code, so this SDK-level check is redundant defense-in-depth we
# can't afford given our deployment target.
mcp = FastMCP(
    "MyHome",
    streamable_http_path="/",
    transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
)


async def _require_role(request: Request | None, min_role: str) -> tuple[str, str]:
    """Resolve the caller's (user_id, role) from the incoming HTTP request and
    enforce a minimum role. Raises PermissionError if unauthenticated or
    under-scoped; FastMCP surfaces this to the MCP client as a tool error."""
    user = await get_user_from_request(request) if request is not None else None
    if user is None:
        raise PermissionError("Authentication required")
    user_id, role = user
    if ROLE_ORDER.get(role, -1) < ROLE_ORDER[min_role]:
        raise PermissionError(
            f"This action requires the '{min_role}' role or higher; your API token is scoped to '{role}'"
        )
    return user_id, role


def _resolve_home_id(home_id: str | None) -> str:
    """Resolve an optional home_id tool argument to a concrete home id.
    Auto-resolves when exactly one home exists; otherwise requires an explicit,
    valid home_id (call list_homes to discover valid ids)."""
    homes = load_homes().homes
    if home_id is not None:
        if not any(h.id == home_id for h in homes):
            valid = [(h.id, h.name) for h in homes]
            raise ValueError(f"Unknown home_id {home_id!r}. Valid homes: {valid}")
        return home_id
    if not homes:
        raise ValueError("No homes exist yet. Call create_home first.")
    if len(homes) == 1:
        return homes[0].id
    valid = [(h.id, h.name) for h in homes]
    raise ValueError(f"home_id is required when multiple homes exist. Valid homes: {valid}")
