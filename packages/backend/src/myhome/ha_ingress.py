# packages/backend/src/myhome/ha_ingress.py
"""HA Supervisor ingress trust: silently authenticate a user who reaches
MyHome through Home Assistant's ingress proxy, using the identity Supervisor
asserts. See docs/superpowers/specs/2026-07-21-ha-ingress-trust-design.md.

Supervisor validates the browser's own HA session before ever forwarding to
the add-on, then attaches X-Remote-User-Id/-Name/-Display-Name headers. Per
HA's own guidance, these are only safe to trust if traffic is also confirmed
to originate from Supervisor's fixed internal proxy address -- otherwise
anyone who could reach the container directly could forge them.
"""
from __future__ import annotations

import os
import secrets
from datetime import datetime, timezone

from fastapi import Request

from .models_auth import User
from .persistence_auth import initial_admin_password_file, load_users, save_users

SUPERVISOR_INGRESS_IP = "172.30.32.2"


def _ingress_trust_satisfied(request: Request) -> tuple[str, str, str] | None:
    """Return (ha_user_id, ha_username, ha_display_name) if this request is
    trustworthy as genuine HA Supervisor ingress traffic, else None."""
    if not os.environ.get("SUPERVISOR_TOKEN"):
        return None
    if request.client is None or request.client.host != SUPERVISOR_INGRESS_IP:
        return None
    ha_user_id = request.headers.get("x-remote-user-id")
    ha_username = request.headers.get("x-remote-user-name")
    ha_display_name = request.headers.get("x-remote-user-display-name")
    if not (ha_user_id and ha_username and ha_display_name):
        return None
    return (ha_user_id, ha_username, ha_display_name)


def _unique_username(base: str, existing: set[str]) -> str:
    if base not in existing:
        return base
    suffix = 2
    while f"{base}-{suffix}" in existing:
        suffix += 1
    return f"{base}-{suffix}"


async def resolve_ha_ingress_user(request: Request) -> tuple[str, str] | None:
    """Resolve or provision a MyHome user for genuine HA ingress traffic.

    Returns (user_id, role), or None if this request isn't trusted ingress
    traffic (see _ingress_trust_satisfied). Matching is by ha_user_id only --
    never by username, and never onto an existing local/oidc-provider account
    (same account-takeover-hardening rule as OIDC's oidc_sub matching).
    """
    trust = _ingress_trust_satisfied(request)
    if trust is None:
        return None
    ha_user_id, ha_username, _ha_display_name = trust

    doc = load_users()
    existing = next((u for u in doc.users if u.ha_user_id == ha_user_id), None)
    if existing is not None:
        return (existing.id, existing.role)

    password_file = initial_admin_password_file()
    is_first_ever = password_file.exists()
    role = "admin" if is_first_ever else "normal"

    existing_usernames = {u.username for u in doc.users}
    username = _unique_username(ha_username, existing_usernames)

    new_user = User(
        id=secrets.token_hex(8),
        username=username,
        password_hash=None,
        role=role,
        created_at=datetime.now(timezone.utc).isoformat(),
        auth_provider="ha_ingress",
        ha_user_id=ha_user_id,
    )

    if is_first_ever:
        doc.users = [
            u for u in doc.users
            if not (u.username == "admin" and u.auth_provider == "local")
        ]
        password_file.unlink(missing_ok=True)

    doc.users.append(new_user)
    save_users(doc)
    return (new_user.id, role)
