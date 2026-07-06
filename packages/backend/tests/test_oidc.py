import httpx
import pytest
import respx
from fastapi import HTTPException
from myhome import oidc
from myhome.models_auth import OidcConfig

DISCOVERY = {
    "authorization_endpoint": "https://idp.example.test/authorize",
    "token_endpoint": "https://idp.example.test/token",
    "jwks_uri": "https://idp.example.test/jwks",
}


@pytest.fixture(autouse=True)
def _clear_discovery_cache():
    oidc.clear_discovery_cache()
    yield
    oidc.clear_discovery_cache()


async def test_fetch_discovery_caches_result():
    with respx.mock:
        route = respx.get("https://idp.example.test/.well-known/openid-configuration").mock(
            return_value=httpx.Response(200, json=DISCOVERY)
        )
        first = await oidc.fetch_discovery("https://idp.example.test")
        second = await oidc.fetch_discovery("https://idp.example.test")
    assert first == DISCOVERY
    assert second == DISCOVERY
    assert route.call_count == 1


async def test_fetch_discovery_rejects_non_https_issuer():
    with pytest.raises(HTTPException) as exc_info:
        await oidc.fetch_discovery("http://idp.example.test")
    assert exc_info.value.status_code == 422


async def test_validate_issuer_reachable_raises_on_failure():
    with respx.mock:
        respx.get("https://idp.example.test/.well-known/openid-configuration").mock(
            return_value=httpx.Response(500)
        )
        with pytest.raises(HTTPException) as exc_info:
            await oidc.validate_issuer_reachable("https://idp.example.test")
    assert exc_info.value.status_code == 422


async def test_build_authorization_url_includes_pkce_and_state():
    config = OidcConfig(
        enabled=True, provider_name="TestIdP", issuer="https://idp.example.test",
        client_id="cid", client_secret="csecret", default_role="normal",
        scopes=["openid", "profile", "email"],
    )
    with respx.mock:
        respx.get("https://idp.example.test/.well-known/openid-configuration").mock(
            return_value=httpx.Response(200, json=DISCOVERY)
        )
        url, state, code_verifier, nonce = await oidc.build_authorization_url(
            config, "https://myhome.example/api/auth/oidc/callback",
        )
    assert url.startswith("https://idp.example.test/authorize")
    assert "code_challenge=" in url
    assert "code_challenge_method=S256" in url
    assert f"state={state}" in url
    assert f"nonce={nonce}" in url
    assert len(code_verifier) > 20


import time

from authlib.jose import JsonWebKey
from authlib.jose import jwt as authlib_jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa


def _generate_rsa_keypair() -> tuple[bytes, bytes]:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return private_pem, public_pem


def _make_jwks(public_pem: bytes, kid: str) -> dict:
    jwk = JsonWebKey.import_key(public_pem, {"kid": kid})
    return {"keys": [jwk.as_dict()]}


def _make_id_token(private_pem: bytes, kid: str, claims: dict) -> str:
    header = {"alg": "RS256", "kid": kid}
    token = authlib_jwt.encode(header, claims, private_pem)
    return token.decode("utf-8")


async def test_exchange_code_for_claims_happy_path():
    private_pem, public_pem = _generate_rsa_keypair()
    kid = "test-key-1"
    config = OidcConfig(
        enabled=True, provider_name="TestIdP", issuer="https://idp.example.test",
        client_id="cid", client_secret="csecret", default_role="normal",
        scopes=["openid", "profile", "email"],
    )
    claims_in = {
        "iss": "https://idp.example.test", "aud": "cid", "sub": "sub-123",
        "exp": int(time.time()) + 3600, "nonce": "test-nonce-abc",
        "preferred_username": "alice", "email": "alice@example.test",
    }
    id_token = _make_id_token(private_pem, kid, claims_in)

    with respx.mock:
        respx.get("https://idp.example.test/.well-known/openid-configuration").mock(
            return_value=httpx.Response(200, json=DISCOVERY)
        )
        respx.get("https://idp.example.test/jwks").mock(
            return_value=httpx.Response(200, json=_make_jwks(public_pem, kid))
        )
        respx.post("https://idp.example.test/token").mock(
            return_value=httpx.Response(200, json={
                "access_token": "at-123", "id_token": id_token, "token_type": "Bearer",
            })
        )
        claims = await oidc.exchange_code_for_claims(
            config, "https://myhome.example/api/auth/oidc/callback",
            code="authcode123", code_verifier="verifier123", nonce="test-nonce-abc",
        )
    assert claims["preferred_username"] == "alice"
    assert claims["sub"] == "sub-123"


async def test_exchange_code_for_claims_rejects_bad_nonce():
    private_pem, public_pem = _generate_rsa_keypair()
    kid = "test-key-1"
    config = OidcConfig(
        enabled=True, provider_name="TestIdP", issuer="https://idp.example.test",
        client_id="cid", client_secret="csecret", default_role="normal",
        scopes=["openid", "profile", "email"],
    )
    claims_in = {
        "iss": "https://idp.example.test", "aud": "cid", "sub": "sub-123",
        "exp": int(time.time()) + 3600, "nonce": "the-real-nonce",
        "preferred_username": "alice",
    }
    id_token = _make_id_token(private_pem, kid, claims_in)

    with respx.mock:
        respx.get("https://idp.example.test/.well-known/openid-configuration").mock(
            return_value=httpx.Response(200, json=DISCOVERY)
        )
        respx.get("https://idp.example.test/jwks").mock(
            return_value=httpx.Response(200, json=_make_jwks(public_pem, kid))
        )
        respx.post("https://idp.example.test/token").mock(
            return_value=httpx.Response(200, json={
                "access_token": "at-123", "id_token": id_token, "token_type": "Bearer",
            })
        )
        with pytest.raises(HTTPException):
            await oidc.exchange_code_for_claims(
                config, "https://myhome.example/api/auth/oidc/callback",
                code="authcode123", code_verifier="verifier123", nonce="wrong-nonce",
            )


def test_extract_username_prefers_preferred_username():
    assert oidc.extract_username({"preferred_username": "bob", "email": "b@x.test"}) == "bob"


def test_extract_username_falls_back_to_email_local_part():
    assert oidc.extract_username({"email": "carol@example.test"}) == "carol"


def test_extract_username_raises_when_neither_present():
    with pytest.raises(HTTPException):
        oidc.extract_username({"sub": "no-username-or-email"})
