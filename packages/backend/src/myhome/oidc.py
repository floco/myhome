# packages/backend/src/myhome/oidc.py
from __future__ import annotations

import httpx
from authlib.common.security import generate_token
from authlib.integrations.httpx_client import AsyncOAuth2Client
from fastapi import HTTPException

from .models_auth import OidcConfig

_discovery_cache: dict[str, dict] = {}


async def fetch_discovery(issuer: str) -> dict:
    """Fetch and cache the issuer's OpenID discovery document."""
    if issuer in _discovery_cache:
        return _discovery_cache[issuer]
    url = issuer.rstrip("/") + "/.well-known/openid-configuration"
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(url)
        resp.raise_for_status()
    doc = resp.json()
    _discovery_cache[issuer] = doc
    return doc


def clear_discovery_cache() -> None:
    """Test hook: force the next fetch_discovery call to hit the network."""
    _discovery_cache.clear()


async def validate_issuer_reachable(issuer: str) -> None:
    try:
        await fetch_discovery(issuer)
    except httpx.HTTPError as e:
        raise HTTPException(422, f"Could not reach issuer's discovery document: {e}") from e


async def build_authorization_url(
    config: OidcConfig, redirect_uri: str,
) -> tuple[str, str, str, str]:
    """Returns (authorization_url, state, code_verifier, nonce)."""
    discovery = await fetch_discovery(config.issuer)
    code_verifier = generate_token(48)
    nonce = generate_token(20)
    client = AsyncOAuth2Client(
        config.client_id, config.client_secret,
        scope=" ".join(config.scopes),
        code_challenge_method="S256",
    )
    url, state = client.create_authorization_url(
        discovery["authorization_endpoint"],
        redirect_uri=redirect_uri, code_verifier=code_verifier, nonce=nonce,
    )
    return url, state, code_verifier, nonce
