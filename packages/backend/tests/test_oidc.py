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
