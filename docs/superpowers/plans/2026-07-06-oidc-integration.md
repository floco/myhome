# OIDC Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let users log into MyHome via an external OIDC provider (Keycloak, Authentik, Google Workspace, etc.), federating into MyHome's existing local JWT session rather than replacing it.

**Architecture:** A new `oidc.py` module wraps Authlib's low-level `AsyncOAuth2Client` for discovery, PKCE authorization-code flow, and ID-token/JWKS validation. `routes/auth.py` gains five endpoints (`/oidc/status`, `/oidc/config` GET/PUT, `/oidc/login`, `/oidc/callback`) that drive the flow and mint MyHome's existing local session cookies on success — `deps.py`/`require_auth` are untouched. `User.password_hash` becomes optional to support OIDC-only accounts. Frontend gets an SSO button on the login page and a new admin-only Settings card for provider configuration.

**Tech Stack:** FastAPI, Authlib (new dependency), Pydantic, Svelte 5, Vitest, pytest + respx (HTTP mocking)

**Reference:** `docs/superpowers/specs/2026-07-06-oidc-integration-design.md`

---

### Task 1: Add Authlib dependency

**Files:**
- Modify: `packages/backend/pyproject.toml`

- [ ] **Step 1: Add the dependency**

In `packages/backend/pyproject.toml`, add `"authlib>=1.3"` to the `dependencies` list (after `"passlib[bcrypt]>=1.7"`, before the `bcrypt` pin comment):

```toml
dependencies = [
    "fastapi>=0.115",
    "pydantic>=2.0",
    "uvicorn[standard]>=0.34",
    "httpx>=0.27",
    "python-multipart>=0.0.9",
    "pymupdf>=1.24",
    "python-jose[cryptography]>=3.3",
    "passlib[bcrypt]>=1.7",
    "authlib>=1.3",
    # passlib 1.7.4 (latest, unmaintained) probes bcrypt.__about__.__version__,
    # which bcrypt removed in 4.1 -- pin below that to avoid a warning on every hash/verify.
    "bcrypt>=4.0,<4.1",
    "mcp>=1.28",
]
```

- [ ] **Step 2: Install it**

Run: `cd packages/backend && pip install -e ".[dev]"`
Expected: Authlib installs successfully; `python -c "import authlib; print(authlib.__version__)"` prints a version `>=1.3`.

- [ ] **Step 3: Commit**

```bash
git add packages/backend/pyproject.toml
git commit -m "chore: add authlib dependency for OIDC integration"
```

---

### Task 2: Extend `User` model and add `OidcConfig` models

**Files:**
- Modify: `packages/backend/src/myhome/models_auth.py`
- Test: `packages/backend/tests/test_auth_persistence.py`

- [ ] **Step 1: Write the failing tests**

Add to `packages/backend/tests/test_auth_persistence.py` (top-level, alongside existing tests):

```python
from myhome.models_auth import OidcConfig, OidcConfigDocument


def test_user_password_hash_defaults_to_none():
    user = User(id="u1", username="alice", role="admin", created_at="2026-01-01T00:00:00+00:00")
    assert user.password_hash is None
    assert user.auth_provider == "local"


def test_oidc_config_defaults():
    config = OidcConfig()
    assert config.enabled is False
    assert config.scopes == ["openid", "profile", "email"]
    assert config.default_role == "normal"


def test_oidc_config_document_defaults():
    doc = OidcConfigDocument()
    assert doc.version == 1
    assert doc.config.enabled is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd packages/backend && pytest tests/test_auth_persistence.py -v -k "password_hash_defaults or oidc_config"`
Expected: FAIL — `password_hash` is a required field, `OidcConfig`/`OidcConfigDocument` don't exist yet.

- [ ] **Step 3: Update `models_auth.py`**

```python
# packages/backend/src/myhome/models_auth.py
from __future__ import annotations
from pydantic import BaseModel


class User(BaseModel):
    id: str
    username: str
    password_hash: str | None = None
    role: str  # "admin" | "normal" | "ro"
    created_at: str  # ISO-8601
    auth_provider: str = "local"  # "local" | "oidc"


class UserDocument(BaseModel):
    version: int = 1
    users: list[User] = []


class ApiToken(BaseModel):
    id: str
    name: str
    token_hash: str  # sha256 hex of the raw token
    role: str  # "admin" | "normal" | "ro"
    owner_id: str
    created_at: str  # ISO-8601
    last_used_at: str | None = None


class TokenDocument(BaseModel):
    version: int = 1
    tokens: list[ApiToken] = []


class OidcConfig(BaseModel):
    enabled: bool = False
    provider_name: str = ""
    issuer: str = ""
    client_id: str = ""
    client_secret: str = ""
    default_role: str = "normal"  # "admin" | "normal" | "ro"
    scopes: list[str] = ["openid", "profile", "email"]


class OidcConfigDocument(BaseModel):
    version: int = 1
    config: OidcConfig = OidcConfig()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd packages/backend && pytest tests/test_auth_persistence.py -v -k "password_hash_defaults or oidc_config"`
Expected: PASS (3 tests)

- [ ] **Step 5: Run the full existing auth test suite to check for regressions**

Run: `cd packages/backend && pytest tests/test_auth.py tests/test_auth_users.py tests/test_auth_tokens.py tests/test_auth_roles.py tests/test_auth_persistence.py -v`
Expected: All PASS — `password_hash` becoming optional doesn't break any existing test since they all still pass a value explicitly.

- [ ] **Step 6: Commit**

```bash
git add packages/backend/src/myhome/models_auth.py packages/backend/tests/test_auth_persistence.py
git commit -m "feat(auth): make User.password_hash optional, add auth_provider and OidcConfig models"
```

---

### Task 3: OIDC config persistence

**Files:**
- Modify: `packages/backend/src/myhome/persistence_auth.py`
- Test: `packages/backend/tests/test_auth_persistence.py`

- [ ] **Step 1: Write the failing tests**

Add to `packages/backend/tests/test_auth_persistence.py`:

```python
from myhome.persistence_auth import load_oidc_config, save_oidc_config


def test_load_oidc_config_returns_default_when_no_file(data_dir):
    config = load_oidc_config()
    assert config.enabled is False
    assert config.issuer == ""


def test_save_and_load_oidc_config_roundtrip(data_dir):
    save_oidc_config(OidcConfig(
        enabled=True, provider_name="Keycloak", issuer="https://auth.example.com/realms/home",
        client_id="myhome", client_secret="s3cret", default_role="ro",
        scopes=["openid", "profile", "email"],
    ))
    loaded = load_oidc_config()
    assert loaded.enabled is True
    assert loaded.provider_name == "Keycloak"
    assert loaded.issuer == "https://auth.example.com/realms/home"
    assert loaded.client_secret == "s3cret"
    assert loaded.default_role == "ro"


def test_save_oidc_config_atomic_write(data_dir):
    save_oidc_config(OidcConfig(enabled=True, provider_name="Test", issuer="https://x.test"))
    assert (data_dir / "oidc_config.json").exists()
    assert not (data_dir / "oidc_config.tmp").exists()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd packages/backend && pytest tests/test_auth_persistence.py -v -k oidc_config`
Expected: FAIL — `load_oidc_config`/`save_oidc_config` don't exist yet (ImportError).

- [ ] **Step 3: Implement in `persistence_auth.py`**

```python
# packages/backend/src/myhome/persistence_auth.py
import json
import os
from pathlib import Path

from .models_auth import OidcConfig, OidcConfigDocument, TokenDocument, UserDocument


def _users_file() -> Path:
    return Path(os.environ.get("DATA_DIR", "/data")) / "users.json"


def _tokens_file() -> Path:
    return Path(os.environ.get("DATA_DIR", "/data")) / "tokens.json"


def _oidc_config_file() -> Path:
    return Path(os.environ.get("DATA_DIR", "/data")) / "oidc_config.json"


def load_users() -> UserDocument:
    path = _users_file()
    if not path.exists():
        return UserDocument()
    with path.open() as f:
        return UserDocument.model_validate(json.load(f))


def save_users(doc: UserDocument) -> None:
    path = _users_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with tmp.open("w") as f:
        json.dump(doc.model_dump(), f, indent=2)
    tmp.replace(path)


def load_tokens() -> TokenDocument:
    path = _tokens_file()
    if not path.exists():
        return TokenDocument()
    with path.open() as f:
        return TokenDocument.model_validate(json.load(f))


def save_tokens(doc: TokenDocument) -> None:
    path = _tokens_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with tmp.open("w") as f:
        json.dump(doc.model_dump(), f, indent=2)
    tmp.replace(path)


def load_oidc_config() -> OidcConfig:
    path = _oidc_config_file()
    if not path.exists():
        return OidcConfig()
    with path.open() as f:
        return OidcConfigDocument.model_validate(json.load(f)).config


def save_oidc_config(config: OidcConfig) -> None:
    path = _oidc_config_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with tmp.open("w") as f:
        json.dump(OidcConfigDocument(config=config).model_dump(), f, indent=2)
    tmp.replace(path)
```

Also add `from myhome.models_auth import OidcConfig` to the imports at the top of `test_auth_persistence.py` (alongside the existing `OidcConfigDocument` import added in Task 2).

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd packages/backend && pytest tests/test_auth_persistence.py -v`
Expected: PASS (all tests in the file)

- [ ] **Step 5: Commit**

```bash
git add packages/backend/src/myhome/persistence_auth.py packages/backend/tests/test_auth_persistence.py
git commit -m "feat(auth): add oidc_config.json persistence"
```

---

### Task 4: Exempt OIDC public endpoints from the global auth middleware

**Files:**
- Modify: `packages/backend/src/myhome/main.py`
- Test: `packages/backend/tests/test_auth_oidc.py` (new file)

The global `auth_middleware` in `main.py` currently 401s any request whose path isn't in `_EXEMPT_PATHS`. The OIDC status/login/callback endpoints must be reachable by an unauthenticated browser (they're how authentication *starts*), so they need to join that exemption set.

- [ ] **Step 1: Write the failing test**

Create `packages/backend/tests/test_auth_oidc.py`:

```python
import pytest
from fastapi.testclient import TestClient
from myhome.main import app


@pytest.fixture()
def fresh(tmp_path, monkeypatch):
    """Unauthenticated client, no users/config seeded."""
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("SECRET_KEY", "test-secret-key-for-tests-only")
    return TestClient(app, raise_server_exceptions=True)


def test_oidc_status_reachable_without_auth(fresh):
    resp = fresh.get("/api/auth/oidc/status")
    assert resp.status_code == 200
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/backend && pytest tests/test_auth_oidc.py -v`
Expected: FAIL with 401 (route doesn't exist yet either, but the middleware exemption is what this task adds — this test will keep failing through Task 4 and only pass once Task 6 adds the route; that's expected, move on).

- [ ] **Step 3: Update `_EXEMPT_PATHS` in `main.py`**

In `packages/backend/src/myhome/main.py`, change:

```python
_EXEMPT_PATHS = {"/api/auth/login", "/api/auth/refresh"}
```

to:

```python
_EXEMPT_PATHS = {
    "/api/auth/login", "/api/auth/refresh",
    "/api/auth/oidc/status", "/api/auth/oidc/login", "/api/auth/oidc/callback",
}
```

- [ ] **Step 4: Run the test again**

Run: `cd packages/backend && pytest tests/test_auth_oidc.py -v`
Expected: Still FAILS, now with a 404 instead of 401 (path exempted from auth, but route doesn't exist until Task 6). This confirms the exemption itself is working — leave this test in place, it'll pass once Task 6 lands the route.

- [ ] **Step 5: Commit**

```bash
git add packages/backend/src/myhome/main.py packages/backend/tests/test_auth_oidc.py
git commit -m "feat(auth): exempt OIDC public endpoints from the global auth gate"
```

---

### Task 5: `oidc.py` — discovery and authorization URL

**Files:**
- Create: `packages/backend/src/myhome/oidc.py`
- Test: `packages/backend/tests/test_oidc.py` (new file, unit tests for the module — separate from the route-level `test_auth_oidc.py`)

- [ ] **Step 1: Write the failing tests**

Create `packages/backend/tests/test_oidc.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd packages/backend && pytest tests/test_oidc.py -v`
Expected: FAIL — `myhome.oidc` module doesn't exist yet (`ModuleNotFoundError`). (This project's `pytest.ini_options` sets `asyncio_mode = "auto"`, so the plain `async def test_...` functions above run automatically under `pytest-asyncio` with no marker needed.)

- [ ] **Step 3: Create `oidc.py`**

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd packages/backend && pytest tests/test_oidc.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add packages/backend/src/myhome/oidc.py packages/backend/tests/test_oidc.py
git commit -m "feat(auth): add oidc.py discovery + PKCE authorization URL builder"
```

---

### Task 6: `oidc.py` — token exchange and ID-token validation

**Files:**
- Modify: `packages/backend/src/myhome/oidc.py`
- Modify: `packages/backend/tests/test_oidc.py`

- [ ] **Step 1: Write the failing test**

Add to `packages/backend/tests/test_oidc.py`:

```python
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
```

Add `from fastapi import HTTPException` and `import respx` to the top of `test_oidc.py` if not already present from Task 5 (respx was used there already; add the `HTTPException` import at module level and drop the inline `from fastapi import HTTPException` inside `test_validate_issuer_reachable_raises_on_failure` from Task 5 since it's now a top-level import — keep both working either way).

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd packages/backend && pytest tests/test_oidc.py -v -k "exchange_code or extract_username"`
Expected: FAIL — `exchange_code_for_claims`/`extract_username` don't exist yet.

- [ ] **Step 3: Extend `oidc.py`**

Append to `packages/backend/src/myhome/oidc.py` (add these imports to the top alongside the existing ones, then the two functions at the end):

```python
from authlib.jose import jwt as authlib_jwt
from authlib.jose.errors import JoseError
```

```python
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

    async with httpx.AsyncClient(timeout=10.0) as http_client:
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd packages/backend && pytest tests/test_oidc.py -v`
Expected: PASS (all tests in the file)

- [ ] **Step 5: Commit**

```bash
git add packages/backend/src/myhome/oidc.py packages/backend/tests/test_oidc.py
git commit -m "feat(auth): add oidc.py token exchange and ID-token validation"
```

---

### Task 7: OIDC config endpoints (`status`, `GET config`, `PUT config`)

**Files:**
- Modify: `packages/backend/src/myhome/routes/auth.py`
- Modify: `packages/backend/tests/test_auth_oidc.py`

- [ ] **Step 1: Write the failing tests**

Add to `packages/backend/tests/test_auth_oidc.py` (below the existing `test_oidc_status_reachable_without_auth`):

```python
import httpx
import respx
from myhome.models_auth import OidcConfig
from myhome.persistence_auth import save_oidc_config


def test_oidc_status_reflects_saved_config(fresh, tmp_path, monkeypatch):
    save_oidc_config(OidcConfig(enabled=True, provider_name="Keycloak", issuer="https://x.test"))
    resp = fresh.get("/api/auth/oidc/status")
    assert resp.status_code == 200
    assert resp.json() == {"enabled": True, "provider_name": "Keycloak"}


def test_oidc_status_defaults_to_disabled(fresh):
    resp = fresh.get("/api/auth/oidc/status")
    assert resp.json() == {"enabled": False, "provider_name": ""}


def test_get_oidc_config_requires_admin(client, ro_client):
    resp = ro_client.get("/api/auth/oidc/config")
    assert resp.status_code == 403
    resp = client.get("/api/auth/oidc/config")
    assert resp.status_code == 200


def test_get_oidc_config_masks_secret(client):
    save_oidc_config(OidcConfig(enabled=True, provider_name="Keycloak", issuer="https://x.test", client_secret="realsecret"))
    resp = client.get("/api/auth/oidc/config")
    data = resp.json()
    assert data["client_secret"] == "••••••••"
    assert "realsecret" not in resp.text


def test_get_oidc_config_empty_secret_shows_empty(client):
    resp = client.get("/api/auth/oidc/config")
    assert resp.json()["client_secret"] == ""


def test_put_oidc_config_disabled_skips_discovery_check(client):
    resp = client.put("/api/auth/oidc/config", json={
        "enabled": False, "provider_name": "Keycloak", "issuer": "https://unreachable.invalid",
        "client_id": "cid", "default_role": "normal", "scopes": ["openid", "profile", "email"],
    })
    assert resp.status_code == 200


def test_put_oidc_config_enabled_validates_discovery(client):
    with respx.mock:
        respx.get("https://good.test/.well-known/openid-configuration").mock(
            return_value=httpx.Response(200, json={
                "authorization_endpoint": "https://good.test/authorize",
                "token_endpoint": "https://good.test/token",
                "jwks_uri": "https://good.test/jwks",
            })
        )
        resp = client.put("/api/auth/oidc/config", json={
            "enabled": True, "provider_name": "Good", "issuer": "https://good.test",
            "client_id": "cid", "client_secret": "s3cret", "default_role": "normal",
            "scopes": ["openid", "profile", "email"],
        })
    assert resp.status_code == 200
    assert resp.json()["client_secret"] == "••••••••"


def test_put_oidc_config_enabled_rejects_unreachable_issuer(client):
    with respx.mock:
        respx.get("https://bad.test/.well-known/openid-configuration").mock(
            return_value=httpx.Response(500)
        )
        resp = client.put("/api/auth/oidc/config", json={
            "enabled": True, "provider_name": "Bad", "issuer": "https://bad.test",
            "client_id": "cid", "client_secret": "s3cret", "default_role": "normal",
            "scopes": ["openid", "profile", "email"],
        })
    assert resp.status_code == 422


def test_put_oidc_config_keeps_existing_secret_when_omitted(client):
    client.put("/api/auth/oidc/config", json={
        "enabled": False, "provider_name": "Keycloak", "issuer": "https://x.test",
        "client_id": "cid", "client_secret": "s3cret", "default_role": "normal",
        "scopes": ["openid", "profile", "email"],
    })
    resp = client.put("/api/auth/oidc/config", json={
        "enabled": False, "provider_name": "Keycloak Renamed", "issuer": "https://x.test",
        "client_id": "cid", "default_role": "normal", "scopes": ["openid", "profile", "email"],
    })
    assert resp.status_code == 200
    from myhome.persistence_auth import load_oidc_config
    assert load_oidc_config().client_secret == "s3cret"
    assert load_oidc_config().provider_name == "Keycloak Renamed"
```

Add an autouse fixture at the top of `test_auth_oidc.py` to clear the discovery cache between tests (mirrors the one in `test_oidc.py`):

```python
from myhome import oidc as oidc_module


@pytest.fixture(autouse=True)
def _clear_discovery_cache():
    oidc_module.clear_discovery_cache()
    yield
    oidc_module.clear_discovery_cache()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd packages/backend && pytest tests/test_auth_oidc.py -v`
Expected: FAIL — none of the config endpoints exist yet (404s).

- [ ] **Step 3: Add the endpoints to `routes/auth.py`**

Add these imports to the top of `packages/backend/src/myhome/routes/auth.py`:

```python
from .. import oidc
from ..models_auth import OidcConfig
from ..persistence_auth import load_oidc_config, save_oidc_config
```

(`ApiToken, TokenDocument, User, UserDocument` are already imported from `..models_auth` — add `OidcConfig` to that existing import line rather than duplicating it.)

Add these models near the other request/response models:

```python
class OidcStatusResponse(BaseModel):
    enabled: bool
    provider_name: str


class OidcConfigResponse(BaseModel):
    enabled: bool
    provider_name: str
    issuer: str
    client_id: str
    client_secret: str  # masked
    default_role: str
    scopes: list[str]


class OidcConfigUpdateRequest(BaseModel):
    enabled: bool
    provider_name: str
    issuer: str
    client_id: str
    client_secret: str | None = None  # omit/None keeps the existing secret
    default_role: str
    scopes: list[str] = ["openid", "profile", "email"]
```

Add these routes (a good spot is right after the `# ── API token management ──` section, before the `# ── Helper ──` section):

```python
# ── OIDC ────────────────────────────────────────────────────────────────────

def _oidc_config_response(config: OidcConfig) -> OidcConfigResponse:
    return OidcConfigResponse(
        enabled=config.enabled, provider_name=config.provider_name, issuer=config.issuer,
        client_id=config.client_id,
        client_secret="••••••••" if config.client_secret else "",
        default_role=config.default_role, scopes=config.scopes,
    )


@router.get("/api/auth/oidc/status")
def oidc_status() -> OidcStatusResponse:
    config = load_oidc_config()
    return OidcStatusResponse(enabled=config.enabled, provider_name=config.provider_name)


@router.get("/api/auth/oidc/config")
def get_oidc_config(current_user: tuple[str, str] = require_auth("admin")) -> OidcConfigResponse:
    return _oidc_config_response(load_oidc_config())


@router.put("/api/auth/oidc/config")
async def put_oidc_config(
    body: OidcConfigUpdateRequest,
    current_user: tuple[str, str] = require_auth("admin"),
) -> OidcConfigResponse:
    if body.default_role not in ROLE_ORDER:
        raise HTTPException(422, "Invalid role")
    existing = load_oidc_config()
    secret = body.client_secret if body.client_secret else existing.client_secret
    if body.enabled:
        await oidc.validate_issuer_reachable(body.issuer)
    config = OidcConfig(
        enabled=body.enabled, provider_name=body.provider_name, issuer=body.issuer,
        client_id=body.client_id, client_secret=secret,
        default_role=body.default_role, scopes=body.scopes,
    )
    save_oidc_config(config)
    return _oidc_config_response(config)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd packages/backend && pytest tests/test_auth_oidc.py -v`
Expected: PASS (all tests in the file)

- [ ] **Step 5: Run the full backend test suite to check for regressions**

Run: `cd packages/backend && pytest -v`
Expected: All PASS

- [ ] **Step 6: Commit**

```bash
git add packages/backend/src/myhome/routes/auth.py packages/backend/tests/test_auth_oidc.py
git commit -m "feat(auth): add OIDC config CRUD and status endpoints"
```

---

### Task 8: OIDC login and callback endpoints

**Files:**
- Modify: `packages/backend/src/myhome/routes/auth.py`
- Modify: `packages/backend/tests/test_auth_oidc.py`

- [ ] **Step 1: Write the failing tests**

Add to `packages/backend/tests/test_auth_oidc.py`:

```python
import json
import time
from urllib.parse import parse_qs, urlparse

from authlib.jose import JsonWebKey
from authlib.jose import jwt as authlib_jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from myhome.persistence_auth import load_users

DISCOVERY = {
    "authorization_endpoint": "https://idp.example.test/authorize",
    "token_endpoint": "https://idp.example.test/token",
    "jwks_uri": "https://idp.example.test/jwks",
}


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
    return authlib_jwt.encode(header, claims, private_pem).decode("utf-8")


def test_oidc_login_redirects_to_authorization_endpoint(fresh):
    save_oidc_config(OidcConfig(
        enabled=True, provider_name="TestIdP", issuer="https://idp.example.test",
        client_id="cid", client_secret="csecret", default_role="normal",
        scopes=["openid", "profile", "email"],
    ))
    with respx.mock:
        respx.get("https://idp.example.test/.well-known/openid-configuration").mock(
            return_value=httpx.Response(200, json=DISCOVERY)
        )
        resp = fresh.get("/api/auth/oidc/login", follow_redirects=False)
    assert resp.status_code == 307
    location = resp.headers["location"]
    assert location.startswith("https://idp.example.test/authorize")
    assert "code_challenge=" in location
    assert "oidc_flow" in resp.cookies


def test_oidc_login_404s_when_disabled(fresh):
    resp = fresh.get("/api/auth/oidc/login", follow_redirects=False)
    assert resp.status_code == 404


def test_oidc_callback_creates_new_user_and_sets_session(fresh):
    private_pem, public_pem = _generate_rsa_keypair()
    kid = "test-key-1"
    save_oidc_config(OidcConfig(
        enabled=True, provider_name="TestIdP", issuer="https://idp.example.test",
        client_id="cid", client_secret="csecret", default_role="normal",
        scopes=["openid", "profile", "email"],
    ))
    with respx.mock:
        respx.get("https://idp.example.test/.well-known/openid-configuration").mock(
            return_value=httpx.Response(200, json=DISCOVERY)
        )
        login_resp = fresh.get("/api/auth/oidc/login", follow_redirects=False)
        qs = parse_qs(urlparse(login_resp.headers["location"]).query)
        state, nonce = qs["state"][0], qs["nonce"][0]

        claims_in = {
            "iss": "https://idp.example.test", "aud": "cid", "sub": "sub-123",
            "exp": int(time.time()) + 3600, "nonce": nonce,
            "preferred_username": "newoidcuser", "email": "newoidcuser@example.test",
        }
        id_token = _make_id_token(private_pem, kid, claims_in)
        respx.get("https://idp.example.test/jwks").mock(
            return_value=httpx.Response(200, json=_make_jwks(public_pem, kid))
        )
        respx.post("https://idp.example.test/token").mock(
            return_value=httpx.Response(200, json={
                "access_token": "at-1", "id_token": id_token, "token_type": "Bearer",
            })
        )
        callback_resp = fresh.get(
            "/api/auth/oidc/callback", params={"code": "authcode123", "state": state},
            follow_redirects=False,
        )
    assert callback_resp.status_code == 307
    assert callback_resp.headers["location"] == "/"
    assert "myhome_access" in callback_resp.cookies

    users = load_users().users
    created = next(u for u in users if u.username == "newoidcuser")
    assert created.role == "normal"
    assert created.auth_provider == "oidc"
    assert created.password_hash is None


def test_oidc_callback_links_existing_username(fresh, tmp_path, monkeypatch):
    from datetime import datetime, timezone
    from myhome.models_auth import User, UserDocument
    save_users(UserDocument(users=[
        User(id="existing-1", username="alice", role="admin",
             created_at=datetime.now(timezone.utc).isoformat(), auth_provider="local"),
    ]))
    private_pem, public_pem = _generate_rsa_keypair()
    kid = "test-key-1"
    save_oidc_config(OidcConfig(
        enabled=True, provider_name="TestIdP", issuer="https://idp.example.test",
        client_id="cid", client_secret="csecret", default_role="ro",
        scopes=["openid", "profile", "email"],
    ))
    with respx.mock:
        respx.get("https://idp.example.test/.well-known/openid-configuration").mock(
            return_value=httpx.Response(200, json=DISCOVERY)
        )
        login_resp = fresh.get("/api/auth/oidc/login", follow_redirects=False)
        qs = parse_qs(urlparse(login_resp.headers["location"]).query)
        state, nonce = qs["state"][0], qs["nonce"][0]

        claims_in = {
            "iss": "https://idp.example.test", "aud": "cid", "sub": "sub-999",
            "exp": int(time.time()) + 3600, "nonce": nonce, "preferred_username": "Alice",
        }
        id_token = _make_id_token(private_pem, kid, claims_in)
        respx.get("https://idp.example.test/jwks").mock(
            return_value=httpx.Response(200, json=_make_jwks(public_pem, kid))
        )
        respx.post("https://idp.example.test/token").mock(
            return_value=httpx.Response(200, json={
                "access_token": "at-1", "id_token": id_token, "token_type": "Bearer",
            })
        )
        callback_resp = fresh.get(
            "/api/auth/oidc/callback", params={"code": "authcode123", "state": state},
            follow_redirects=False,
        )
    assert "myhome_access" in callback_resp.cookies
    users = load_users().users
    assert len(users) == 1  # linked, not duplicated
    assert users[0].id == "existing-1"
    assert users[0].role == "admin"  # kept existing role, not overwritten by default_role


def test_oidc_callback_rejects_mismatched_state(fresh):
    save_oidc_config(OidcConfig(
        enabled=True, provider_name="TestIdP", issuer="https://idp.example.test",
        client_id="cid", client_secret="csecret", default_role="normal",
    ))
    with respx.mock:
        respx.get("https://idp.example.test/.well-known/openid-configuration").mock(
            return_value=httpx.Response(200, json=DISCOVERY)
        )
        fresh.get("/api/auth/oidc/login", follow_redirects=False)
        resp = fresh.get(
            "/api/auth/oidc/callback", params={"code": "x", "state": "wrong-state"},
            follow_redirects=False,
        )
    assert resp.status_code == 307
    assert resp.headers["location"] == "/?error=oidc_failed"


def test_oidc_callback_rejects_missing_flow_cookie(fresh):
    resp = fresh.get(
        "/api/auth/oidc/callback", params={"code": "x", "state": "some-state"},
        follow_redirects=False,
    )
    assert resp.status_code == 307
    assert resp.headers["location"] == "/?error=oidc_failed"


def test_oidc_callback_passes_through_idp_error_param(fresh):
    resp = fresh.get(
        "/api/auth/oidc/callback", params={"error": "access_denied"},
        follow_redirects=False,
    )
    assert resp.status_code == 307
    assert resp.headers["location"] == "/?error=oidc_failed"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd packages/backend && pytest tests/test_auth_oidc.py -v -k "login or callback"`
Expected: FAIL — `/api/auth/oidc/login` and `/api/auth/oidc/callback` don't exist yet (404s).

- [ ] **Step 3: Add the endpoints to `routes/auth.py`**

Add these imports to the top of `packages/backend/src/myhome/routes/auth.py`:

```python
import json

import httpx
from authlib.jose.errors import JoseError
from fastapi import Cookie, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
```

(`Cookie, HTTPException, Response` are already imported from `fastapi` — merge `Request` into that existing import line rather than duplicating it. `import secrets` and `from datetime import datetime, timezone` are already present at the top of the file.)

Add near the OIDC config routes from Task 7:

```python
_OIDC_FLOW_COOKIE = "oidc_flow"
_OIDC_FLOW_MAX_AGE = 600


def _redirect_uri(request: Request) -> str:
    return str(request.base_url).rstrip("/") + "/api/auth/oidc/callback"


@router.get("/api/auth/oidc/login")
async def oidc_login(request: Request) -> RedirectResponse:
    config = load_oidc_config()
    if not config.enabled:
        raise HTTPException(404, "OIDC is not enabled")
    url, state, code_verifier, nonce = await oidc.build_authorization_url(
        config, _redirect_uri(request),
    )
    response = RedirectResponse(url)
    flow_payload = json.dumps({"state": state, "code_verifier": code_verifier, "nonce": nonce})
    response.set_cookie(
        _OIDC_FLOW_COOKIE, flow_payload, httponly=True, samesite="lax",
        max_age=_OIDC_FLOW_MAX_AGE,
    )
    return response


@router.get("/api/auth/oidc/callback")
async def oidc_callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    oidc_flow: str | None = Cookie(default=None),
) -> RedirectResponse:
    if error or not code or not state or not oidc_flow:
        return RedirectResponse("/?error=oidc_failed")
    try:
        flow = json.loads(oidc_flow)
        expected_state, code_verifier, nonce = flow["state"], flow["code_verifier"], flow["nonce"]
    except (json.JSONDecodeError, KeyError):
        return RedirectResponse("/?error=oidc_failed")
    if state != expected_state:
        return RedirectResponse("/?error=oidc_failed")

    config = load_oidc_config()
    if not config.enabled:
        return RedirectResponse("/?error=oidc_failed")

    try:
        claims = await oidc.exchange_code_for_claims(
            config, _redirect_uri(request), code, code_verifier, nonce,
        )
        username = oidc.extract_username(claims)
    except (HTTPException, httpx.HTTPError, JoseError):
        return RedirectResponse("/?error=oidc_failed")

    doc = load_users()
    user = next((u for u in doc.users if u.username.lower() == username.lower()), None)
    if user is None:
        user = User(
            id=secrets.token_hex(8), username=username, password_hash=None,
            role=config.default_role, created_at=datetime.now(timezone.utc).isoformat(),
            auth_provider="oidc",
        )
        doc.users.append(user)
        save_users(doc)

    response = RedirectResponse("/")
    _set_auth_cookies(response, user.id, user.role)
    response.delete_cookie(_OIDC_FLOW_COOKIE)
    return response
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd packages/backend && pytest tests/test_auth_oidc.py -v`
Expected: PASS (all tests in the file)

- [ ] **Step 5: Run the full backend test suite to check for regressions**

Run: `cd packages/backend && pytest -v`
Expected: All PASS

- [ ] **Step 6: Commit**

```bash
git add packages/backend/src/myhome/routes/auth.py packages/backend/tests/test_auth_oidc.py
git commit -m "feat(auth): add OIDC login and callback endpoints with JIT user provisioning"
```

---

### Task 9: Handle `password_hash: None` in login and change-password

**Files:**
- Modify: `packages/backend/src/myhome/routes/auth.py`
- Modify: `packages/backend/tests/test_auth.py`

- [ ] **Step 1: Write the failing tests**

Add to `packages/backend/tests/test_auth.py`. `User` is already imported at the top of this file (`from myhome.models_auth import User, UserDocument`) — add these two more imports alongside it:

```python
from datetime import datetime, timezone
from myhome.persistence_auth import load_users
```

Then add the test functions:

```python
def test_login_against_oidc_only_user_returns_401(fresh):
    doc = load_users()
    doc.users.append(User(
        id="u-oidc", username="oidcuser", password_hash=None, role="normal",
        created_at=datetime.now(timezone.utc).isoformat(), auth_provider="oidc",
    ))
    save_users(doc)
    resp = fresh.post("/api/auth/login", json={"username": "oidcuser", "password": "anything"})
    assert resp.status_code == 401


def test_change_password_sets_password_when_none_exists(fresh):
    doc = load_users()
    doc.users.append(User(
        id="u-oidc2", username="oidcuser2", password_hash=None, role="normal",
        created_at=datetime.now(timezone.utc).isoformat(), auth_provider="oidc",
    ))
    save_users(doc)
    from myhome.deps import create_access_token
    fresh.cookies.set("myhome_access", create_access_token("u-oidc2", "normal"))
    resp = fresh.put("/api/auth/me/password", json={
        "current_password": "",
        "new_password": "newpassword99",
    })
    assert resp.status_code == 204
    reloaded = next(u for u in load_users().users if u.id == "u-oidc2")
    from myhome.deps import pwd_ctx
    assert pwd_ctx.verify("newpassword99", reloaded.password_hash)
```

(Directly setting the `myhome_access` cookie via `create_access_token` is the simplest way to authenticate as a specific user in a test without going through a full login flow — it's the same helper the real login/callback endpoints use.)

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd packages/backend && pytest tests/test_auth.py -v -k "oidc_only_user or sets_password_when_none"`
Expected: FAIL — both tests raise a `TypeError` out of `pwd_ctx.verify(secret, None)` (the `fresh` fixture uses `raise_server_exceptions=True`, so the crash inside the route propagates as a test error rather than a clean 401/400 response).

- [ ] **Step 3: Update `login` and `change_password` in `routes/auth.py`**

Change:

```python
@router.post("/api/auth/login")
def login(body: LoginRequest, response: Response) -> UserInfo:
    doc = load_users()
    user = next((u for u in doc.users if u.username.lower() == body.username.lower()), None)
    if user is None or not pwd_ctx.verify(body.password, user.password_hash):
        raise HTTPException(401, "Invalid username or password")
```

to:

```python
@router.post("/api/auth/login")
def login(body: LoginRequest, response: Response) -> UserInfo:
    doc = load_users()
    user = next((u for u in doc.users if u.username.lower() == body.username.lower()), None)
    if user is None or user.password_hash is None or not pwd_ctx.verify(body.password, user.password_hash):
        raise HTTPException(401, "Invalid username or password")
```

Change:

```python
    if not pwd_ctx.verify(body.current_password, user.password_hash):
        raise HTTPException(400, "Current password incorrect")
    if len(body.new_password) < 8:
        raise HTTPException(422, "Password must be at least 8 characters")
    user.password_hash = pwd_ctx.hash(body.new_password)
    save_users(doc)
```

to:

```python
    if user.password_hash is not None and not pwd_ctx.verify(body.current_password, user.password_hash):
        raise HTTPException(400, "Current password incorrect")
    if len(body.new_password) < 8:
        raise HTTPException(422, "Password must be at least 8 characters")
    user.password_hash = pwd_ctx.hash(body.new_password)
    save_users(doc)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd packages/backend && pytest tests/test_auth.py -v`
Expected: PASS (all tests in the file)

- [ ] **Step 5: Run the full backend test suite**

Run: `cd packages/backend && pytest -v`
Expected: All PASS

- [ ] **Step 6: Commit**

```bash
git add packages/backend/src/myhome/routes/auth.py packages/backend/tests/test_auth.py
git commit -m "fix(auth): handle null password_hash in login and change-password for OIDC-only accounts"
```

---

### Task 10: Frontend — LoginPage SSO button and error banner

**Files:**
- Modify: `packages/editor/src/lib/components/LoginPage.svelte`
- Modify: `packages/editor/test/LoginPage.test.ts`

- [ ] **Step 1: Write the failing tests**

Add to `packages/editor/test/LoginPage.test.ts` (add `beforeEach`/`afterEach` fetch mocking alongside the existing ones):

```typescript
describe("LoginPage — OIDC", () => {
  let target: HTMLDivElement;
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    target = document.createElement("div");
    document.body.appendChild(target);
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    target.remove();
    window.history.replaceState({}, "", "/");
  });

  it("shows SSO button when OIDC is enabled", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true, json: async () => ({ enabled: true, provider_name: "Keycloak" }),
    });
    const app = mount(LoginPage, { target, props: { onlogin: vi.fn(), login: vi.fn() } });
    await new Promise((r) => setTimeout(r, 0));
    flushSync();
    expect(target.textContent).toContain("Sign in with Keycloak");
    unmount(app);
  });

  it("does not show SSO button when OIDC is disabled", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true, json: async () => ({ enabled: false, provider_name: "" }),
    });
    const app = mount(LoginPage, { target, props: { onlogin: vi.fn(), login: vi.fn() } });
    await new Promise((r) => setTimeout(r, 0));
    flushSync();
    expect(target.textContent).not.toContain("Sign in with");
    unmount(app);
  });

  it("shows a sign-in-failed banner when the URL has ?error=oidc_failed", async () => {
    window.history.replaceState({}, "", "/?error=oidc_failed");
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true, json: async () => ({ enabled: false, provider_name: "" }),
    });
    const app = mount(LoginPage, { target, props: { onlogin: vi.fn(), login: vi.fn() } });
    await new Promise((r) => setTimeout(r, 0));
    flushSync();
    expect(target.textContent).toContain("Sign-in failed");
    unmount(app);
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd packages/editor && npx vitest run test/LoginPage.test.ts`
Expected: FAIL — 3 new tests fail (no SSO button/banner exist yet).

- [ ] **Step 3: Update `LoginPage.svelte`**

```svelte
<!-- packages/editor/src/lib/components/LoginPage.svelte -->
<script lang="ts">
  interface Props {
    onlogin: () => void;
    login: (username: string, password: string) => Promise<unknown>;
  }
  let { onlogin, login }: Props = $props();

  let username = $state("");
  let password = $state("");
  let error = $state<string | null>(null);
  let loading = $state(false);

  let oidcEnabled = $state(false);
  let oidcProviderName = $state("");

  async function loadOidcStatus(): Promise<void> {
    try {
      const resp = await fetch("/api/auth/oidc/status");
      if (!resp.ok) return;
      const data = await resp.json();
      oidcEnabled = data.enabled;
      oidcProviderName = data.provider_name;
    } catch {
      oidcEnabled = false;
    }
  }

  function checkOidcError(): void {
    const params = new URLSearchParams(window.location.search);
    if (params.get("error") === "oidc_failed") {
      error = "Sign-in failed, please try again";
      params.delete("error");
      const query = params.toString();
      window.history.replaceState({}, "", window.location.pathname + (query ? `?${query}` : ""));
    }
  }

  loadOidcStatus();
  checkOidcError();

  function signInWithOidc(): void {
    window.location.href = "/api/auth/oidc/login";
  }

  async function handleSubmit(e: SubmitEvent): Promise<void> {
    e.preventDefault();
    error = null;
    loading = true;
    try {
      await login(username, password);
      onlogin();
    } catch {
      error = "Invalid username or password";
    } finally {
      loading = false;
    }
  }
</script>

<div class="login-page">
  <div class="login-card">
    <div class="login-header">
      <span class="login-logo">🏠</span>
      <h1 class="login-title">My Home</h1>
      <p class="login-subtitle">Sign in to continue</p>
    </div>

    {#if error}
      <div class="login-error">{error}</div>
    {/if}

    {#if oidcEnabled}
      <button type="button" class="oidc-btn" onclick={signInWithOidc}>
        Sign in with {oidcProviderName}
      </button>
      <div class="oidc-divider"><span>or</span></div>
    {/if}

    <form class="login-form" onsubmit={handleSubmit}>
      <div class="form-field">
        <label for="login-username">Username</label>
        <input
          id="login-username"
          type="text"
          bind:value={username}
          autocomplete="username"
          required
        />
      </div>
      <div class="form-field">
        <label for="login-password">Password</label>
        <input
          id="login-password"
          type="password"
          bind:value={password}
          autocomplete="current-password"
          required
        />
      </div>

      <button type="submit" class="login-btn" disabled={loading}>
        {loading ? "Signing in…" : "Sign in"}
      </button>
    </form>

    <p class="login-footer">Contact your admin to create an account</p>
  </div>
</div>

<style>
  .login-page {
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--bg);
  }

  .login-card {
    width: 400px;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 40px;
    display: flex;
    flex-direction: column;
    gap: 24px;
  }

  .login-header {
    text-align: center;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 8px;
  }

  .login-logo { font-size: 2rem; }

  .login-title {
    margin: 0;
    font-size: 1.5rem;
    color: var(--text);
    font-family: var(--font-sans);
  }

  .login-subtitle {
    margin: 0;
    font-size: 0.875rem;
    color: var(--text-muted);
  }

  .oidc-btn {
    background: var(--surface-alt);
    color: var(--text);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 12px;
    font-size: 0.9rem;
    font-weight: 600;
    cursor: pointer;
    font-family: var(--font-sans);
  }

  .oidc-btn:hover { background: var(--surface-hover); }

  .oidc-divider {
    display: flex;
    align-items: center;
    text-align: center;
    color: var(--text-faint);
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }

  .oidc-divider::before,
  .oidc-divider::after {
    content: "";
    flex: 1;
    border-bottom: 1px solid var(--border);
  }

  .oidc-divider span { padding: 0 12px; }

  .login-form { display: flex; flex-direction: column; gap: 16px; }

  .form-field { display: flex; flex-direction: column; gap: 6px; }

  .form-field label {
    font-size: 0.75rem;
    font-weight: 600;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.06em;
    font-family: var(--font-sans);
  }

  .form-field input {
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 10px 14px;
    font-size: 0.9rem;
    color: var(--text);
    font-family: var(--font-sans);
  }

  .form-field input:focus {
    outline: none;
    border-color: var(--accent);
  }

  .login-error {
    background: color-mix(in srgb, red 10%, transparent);
    border: 1px solid color-mix(in srgb, red 30%, transparent);
    border-radius: 6px;
    padding: 10px 14px;
    font-size: 0.85rem;
    color: var(--text);
  }

  .login-btn {
    background: var(--accent);
    color: #fff;
    border: none;
    border-radius: 6px;
    padding: 12px;
    font-size: 0.9rem;
    font-weight: 600;
    cursor: pointer;
    font-family: var(--font-sans);
  }

  .login-btn:disabled { opacity: 0.6; cursor: not-allowed; }

  .login-footer {
    margin: 0;
    text-align: center;
    font-size: 0.78rem;
    color: var(--text-faint);
  }
</style>
```

(This moves the `{#if error}` block above the form, since a `?error=oidc_failed` banner needs to be visible whether or not the SSO button is shown — functionally equivalent for the local-login-error case since `error` is still set by `handleSubmit` the same way.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd packages/editor && npx vitest run test/LoginPage.test.ts`
Expected: PASS (all tests in the file, including the pre-existing ones)

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/lib/components/LoginPage.svelte packages/editor/test/LoginPage.test.ts
git commit -m "feat(auth): add OIDC sign-in button and error banner to LoginPage"
```

---

### Task 11: Frontend — SettingsPage Single Sign-On card

**Files:**
- Modify: `packages/editor/src/lib/components/SettingsPage.svelte`
- Modify: `packages/editor/test/SettingsPage.test.ts`

- [ ] **Step 1: Write the failing tests**

Add a new `describe` block to `packages/editor/test/SettingsPage.test.ts`:

```typescript
describe("SettingsPage — Single Sign-On", () => {
  let target: HTMLDivElement;
  let fetchMock: ReturnType<typeof vi.fn>;
  const originalFetch = globalThis.fetch;

  function defaultOidcConfig() {
    return {
      enabled: false, provider_name: "", issuer: "", client_id: "",
      client_secret: "", default_role: "normal", scopes: ["openid", "profile", "email"],
    };
  }

  beforeEach(() => {
    target = document.createElement("div");
    document.body.appendChild(target);
    fetchMock = vi.fn().mockImplementation((url: string) => {
      if (url === "/api/auth/tokens") return Promise.resolve({ ok: true, json: async () => [] });
      if (url === "/api/auth/users") return Promise.resolve({ ok: true, json: async () => [] });
      if (url === "/api/mcp/config") return Promise.resolve({ ok: true, json: async () => ({ enabled: false }) });
      if (url === "/api/auth/oidc/config") return Promise.resolve({ ok: true, json: async () => defaultOidcConfig() });
      return Promise.resolve(new Response(null, { status: 200 }));
    });
    globalThis.fetch = fetchMock;
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    target.remove();
  });

  it("renders the Single Sign-On card for an admin", async () => {
    const app = mount(SettingsPage, { target, props: { store: makeStore(), authStore: makeAuthStore("admin") } });
    await new Promise((r) => setTimeout(r, 0));
    flushSync();
    expect(target.textContent).toContain("Single Sign-On");
    unmount(app);
  });

  it("does not render the Single Sign-On card for a non-admin", async () => {
    const app = mount(SettingsPage, { target, props: { store: makeStore(), authStore: makeAuthStore("normal") } });
    await new Promise((r) => setTimeout(r, 0));
    flushSync();
    expect(target.textContent).not.toContain("Single Sign-On");
    unmount(app);
  });

  it("saves config via PUT /api/auth/oidc/config", async () => {
    fetchMock.mockImplementation((url: string, opts?: RequestInit) => {
      if (url === "/api/auth/tokens") return Promise.resolve({ ok: true, json: async () => [] });
      if (url === "/api/auth/users") return Promise.resolve({ ok: true, json: async () => [] });
      if (url === "/api/mcp/config") return Promise.resolve({ ok: true, json: async () => ({ enabled: false }) });
      if (url === "/api/auth/oidc/config" && (!opts || opts.method === undefined)) {
        return Promise.resolve({ ok: true, json: async () => defaultOidcConfig() });
      }
      if (url === "/api/auth/oidc/config" && opts?.method === "PUT") {
        return Promise.resolve({ ok: true, json: async () => ({ ...defaultOidcConfig(), enabled: true, provider_name: "Keycloak" }) });
      }
      return Promise.resolve(new Response(null, { status: 200 }));
    });
    const app = mount(SettingsPage, { target, props: { store: makeStore(), authStore: makeAuthStore("admin") } });
    await new Promise((r) => setTimeout(r, 0));
    flushSync();

    const saveButtons = Array.from(target.querySelectorAll("button")).filter(b => b.textContent?.trim() === "Save");
    expect(saveButtons.length).toBeGreaterThan(0);
    saveButtons[saveButtons.length - 1].click();
    await new Promise((r) => setTimeout(r, 0));
    flushSync();

    const putCall = fetchMock.mock.calls.find(
      (c: unknown[]) => c[0] === "/api/auth/oidc/config" && (c[1] as RequestInit)?.method === "PUT",
    );
    expect(putCall).toBeTruthy();
    unmount(app);
  });

  it("shows an error message when save fails", async () => {
    fetchMock.mockImplementation((url: string, opts?: RequestInit) => {
      if (url === "/api/auth/tokens") return Promise.resolve({ ok: true, json: async () => [] });
      if (url === "/api/auth/users") return Promise.resolve({ ok: true, json: async () => [] });
      if (url === "/api/mcp/config") return Promise.resolve({ ok: true, json: async () => ({ enabled: false }) });
      if (url === "/api/auth/oidc/config" && opts?.method === "PUT") {
        return Promise.resolve({ ok: false, status: 422, json: async () => ({ detail: "Could not reach issuer" }) });
      }
      if (url === "/api/auth/oidc/config") return Promise.resolve({ ok: true, json: async () => defaultOidcConfig() });
      return Promise.resolve(new Response(null, { status: 200 }));
    });
    const app = mount(SettingsPage, { target, props: { store: makeStore(), authStore: makeAuthStore("admin") } });
    await new Promise((r) => setTimeout(r, 0));
    flushSync();

    const saveButtons = Array.from(target.querySelectorAll("button")).filter(b => b.textContent?.trim() === "Save");
    saveButtons[saveButtons.length - 1].click();
    await new Promise((r) => setTimeout(r, 0));
    flushSync();

    expect(target.textContent).toContain("Could not reach issuer");
    unmount(app);
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd packages/editor && npx vitest run test/SettingsPage.test.ts`
Expected: FAIL — 4 new tests fail (no Single Sign-On card exists yet).

- [ ] **Step 3: Add the OIDC section to `SettingsPage.svelte`**

Add this block to the `<script>` section, after the "MCP Server" block (after the `loadMcpConfig();` call, before the "Backup & Restore" comment):

```typescript
  // --- Single Sign-On / OIDC (admin only) ---
  interface OidcConfigInfo {
    enabled: boolean;
    provider_name: string;
    issuer: string;
    client_id: string;
    client_secret: string;
    default_role: string;
    scopes: string[];
  }

  let oidcConfig = $state<OidcConfigInfo>({
    enabled: false, provider_name: "", issuer: "", client_id: "",
    client_secret: "", default_role: "normal", scopes: ["openid", "profile", "email"],
  });
  let oidcConfigLoaded = $state(false);
  let oidcClientSecretDraft = $state("");
  let oidcError = $state<string | null>(null);
  let oidcSaving = $state(false);

  async function loadOidcConfig(): Promise<void> {
    if (authStore.user?.role !== "admin") return;
    try {
      const resp = await fetch("/api/auth/oidc/config");
      if (!resp.ok) return;
      oidcConfig = await resp.json();
    } finally {
      oidcConfigLoaded = true;
    }
  }

  async function saveOidcConfig(): Promise<void> {
    oidcError = null;
    oidcSaving = true;
    try {
      const body: Record<string, unknown> = {
        enabled: oidcConfig.enabled,
        provider_name: oidcConfig.provider_name,
        issuer: oidcConfig.issuer,
        client_id: oidcConfig.client_id,
        default_role: oidcConfig.default_role,
        scopes: oidcConfig.scopes,
      };
      if (oidcClientSecretDraft.trim()) body.client_secret = oidcClientSecretDraft.trim();
      const resp = await fetch("/api/auth/oidc/config", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!resp.ok) {
        const d = await resp.json().catch(() => ({}));
        oidcError = (d as { detail?: string }).detail ?? `Error ${resp.status}`;
        return;
      }
      oidcConfig = await resp.json();
      oidcClientSecretDraft = "";
    } finally {
      oidcSaving = false;
    }
  }

  loadOidcConfig();
```

Add this Card to the template, after the `<!-- MCP Server (admin only) -->` card's closing `{/if}` and before `<!-- Backup & Restore -->`:

```svelte
    <!-- Single Sign-On (admin only) -->
    {#if authStore.user?.role === "admin"}
      <Card>
        <div class="section-header">
          <h2>Single Sign-On</h2>
        </div>
        <p class="section-desc">
          Let users sign in via an external OIDC provider (Keycloak, Authentik, Google
          Workspace, etc.) alongside local username/password login.
        </p>
        {#if oidcConfigLoaded}
          <label class="module-row">
            <input type="checkbox" bind:checked={oidcConfig.enabled} />
            <span class="mod-label">Enable Single Sign-On</span>
          </label>
          <div class="modal-form" style="margin-top: var(--space-3)">
            <div class="modal-field">
              <span class="modal-label">Provider name</span>
              <Input bind:value={oidcConfig.provider_name} placeholder="e.g. Keycloak" />
            </div>
            <div class="modal-field">
              <span class="modal-label">Issuer URL</span>
              <Input bind:value={oidcConfig.issuer} placeholder="https://auth.example.com/realms/home" />
            </div>
            <div class="modal-field">
              <span class="modal-label">Client ID</span>
              <Input bind:value={oidcConfig.client_id} />
            </div>
            <div class="modal-field">
              <span class="modal-label">Client secret</span>
              <Input type="password" bind:value={oidcClientSecretDraft} placeholder={oidcConfig.client_secret || "Not set"} />
            </div>
            <div class="modal-field">
              <span class="modal-label">Default role for new sign-ins</span>
              <select bind:value={oidcConfig.default_role} class="modal-select">
                {#each ["ro", "normal", "admin"] as r}
                  <option value={r}>{r}</option>
                {/each}
              </select>
            </div>
            <div class="modal-field">
              <span class="modal-label">Redirect URI</span>
              <p class="empty-hint">{window.location.origin}/api/auth/oidc/callback</p>
            </div>
            {#if oidcError}<div class="error">{oidcError}</div>{/if}
            <div class="modal-actions">
              <Button onclick={saveOidcConfig} disabled={oidcSaving}>{oidcSaving ? "Saving…" : "Save"}</Button>
            </div>
          </div>
        {/if}
      </Card>
    {/if}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd packages/editor && npx vitest run test/SettingsPage.test.ts`
Expected: PASS (all tests in the file, including pre-existing ones)

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/lib/components/SettingsPage.svelte packages/editor/test/SettingsPage.test.ts
git commit -m "feat(auth): add Single Sign-On configuration card to Settings"
```

---

### Task 12: Full test suite + typecheck

**Files:** none (verification only)

- [ ] **Step 1: Run the full backend test suite**

Run: `cd packages/backend && pytest -v`
Expected: All tests PASS (no regressions across the whole auth/OIDC surface)

- [ ] **Step 2: Run the full frontend test suite**

Run: `cd packages/editor && npx vitest run`
Expected: All tests PASS

- [ ] **Step 3: Typecheck the frontend**

Run: `cd packages/editor && npx svelte-check --tsconfig ./tsconfig.json` (or the project's existing typecheck script if `package.json` defines one — check with `cat packages/editor/package.json | grep -A2 '"scripts"'` first and use that instead if it differs)
Expected: No new type errors introduced by `LoginPage.svelte` or `SettingsPage.svelte` changes

- [ ] **Step 4: Manual smoke test (optional but recommended)**

Start the backend and frontend dev servers, open Settings as an admin user, verify the "Single Sign-On" card renders and the enable toggle/fields are interactive. Verify the login page loads without errors when OIDC is disabled (default state) — this is the common case and must not regress.

- [ ] **Step 5: Commit any leftover changes**

```bash
git status
```

If there's nothing to commit, this task is done. If a typecheck fix was needed, commit it:

```bash
git add -A
git commit -m "fix: typecheck fixes for OIDC integration"
```
