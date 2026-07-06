# packages/backend/src/myhome/oidc.py
from __future__ import annotations

import httpx
from authlib.common.security import generate_token
from authlib.integrations.httpx_client import AsyncOAuth2Client
from authlib.jose import jwt as authlib_jwt
from authlib.jose.errors import JoseError
from fastapi import HTTPException

from .models_auth import OidcConfig

_discovery_cache: dict[str, dict] = {}


async def fetch_discovery(issuer: str) -> dict:
    """Fetch and cache the issuer's OpenID discovery document."""
    if not issuer.startswith("https://"):
        raise HTTPException(422, "Issuer must be an https:// URL")
    if issuer in _discovery_cache:
        return _discovery_cache[issuer]
    url = issuer.rstrip("/") + "/.well-known/openid-configuration"
    async with httpx.AsyncClient(timeout=10.0, follow_redirects=False) as client:
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


async def exchange_code_for_claims(
    config: OidcConfig, redirect_uri: str, code: str, code_verifier: str, nonce: str,
) -> dict:
    """Exchanges the auth code for tokens and returns validated ID token claims."""
    discovery = await fetch_discovery(config.issuer)
    client = AsyncOAuth2Client(config.client_id, config.client_secret)
    token = await client.fetch_token(
        discovery["token_endpoint"], code=code,
        redirect_uri=redirect_uri, code_verifier=code_verifier,
    )
    id_token = token.get("id_token")
    if not id_token:
        raise HTTPException(400, "IdP response did not include an id_token")

    async with httpx.AsyncClient(timeout=10.0, follow_redirects=False) as http_client:
        jwks_resp = await http_client.get(discovery["jwks_uri"])
        jwks_resp.raise_for_status()
    jwks = jwks_resp.json()

    try:
        claims = authlib_jwt.decode(
            id_token, jwks,
            claims_options={
                "iss": {"essential": True, "value": config.issuer},
                "aud": {"essential": True, "value": config.client_id},
                "exp": {"essential": True},
            },
        )
        claims.validate()
    except JoseError as e:
        raise HTTPException(400, f"Invalid ID token: {e}") from e

    if claims.get("nonce") != nonce:
        raise HTTPException(400, "Invalid nonce")

    return dict(claims)


def extract_username(claims: dict) -> str:
    username = claims.get("preferred_username")
    if username:
        return username
    email = claims.get("email")
    if email:
        return email.split("@")[0]
    raise HTTPException(400, "ID token has neither preferred_username nor email claim")
