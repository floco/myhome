# Auth & API Tokens Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add multi-user login (username + password), three roles (Admin/Normal/RO), JWT browser sessions, opaque API tokens, user management UI, and API token management UI to MyHome.

**Architecture:** JWT-based browser sessions via `httpOnly` cookies (`myhome_access` 1h, `myhome_refresh` 7d); opaque bearer tokens for automation/MCP/mobile stored hashed in `tokens.json`. A FastAPI middleware in `main.py` enforces auth on all routes except `/api/auth/login` and `/api/auth/refresh`; role minimums for writes (≥ normal) are enforced there. Auth routes use a `require_auth(min_role)` dependency for fine-grained admin/normal control. The frontend checks `/api/auth/me` on load and shows `LoginPage.svelte` when unauthenticated.

**Tech Stack:** FastAPI, python-jose[cryptography], passlib[bcrypt], Svelte 5 runes ($state/$derived/$props), Vitest, pytest + httpx TestClient.

**Spec:** `docs/superpowers/specs/2026-07-02-auth-api-tokens-design.md`

---

## File Map

**Backend — new files**
- `packages/backend/src/myhome/models_auth.py` — `User`, `ApiToken`, `UserDocument`, `TokenDocument` Pydantic models
- `packages/backend/src/myhome/persistence_auth.py` — load/save `users.json` and `tokens.json`
- `packages/backend/src/myhome/deps.py` — secret management, JWT helpers, `require_auth(min_role)`, `get_user_from_request`
- `packages/backend/src/myhome/routes/auth.py` — all auth endpoints
- `packages/backend/tests/test_auth.py` — core auth tests
- `packages/backend/tests/test_auth_users.py` — user management tests
- `packages/backend/tests/test_auth_tokens.py` — API token tests
- `packages/backend/tests/test_auth_roles.py` — role enforcement tests

**Backend — modified files**
- `packages/backend/pyproject.toml` — add `python-jose[cryptography]`, `passlib[bcrypt]`
- `packages/backend/src/myhome/main.py` — first-boot logic, auth middleware, include `auth.router`
- `packages/backend/tests/conftest.py` — add `client` (admin-authed) and `ro_client` fixtures

**Frontend — new files**
- `packages/editor/src/lib/authStore.svelte.ts` — auth state + login/logout/changePassword
- `packages/editor/src/lib/components/LoginPage.svelte` — login form
- `packages/editor/test/authStore.test.ts`
- `packages/editor/test/LoginPage.test.ts`

**Frontend — modified files**
- `packages/editor/src/App.svelte` — import authStore, show LoginPage when unauthenticated, add user menu to topbar
- `packages/editor/src/lib/components/SettingsPage.svelte` — add `authStore` prop, API Tokens section, Users section (admin)
- `packages/editor/test/App.test.ts` — mock `/api/auth/me` in `stubFetch`
- `packages/editor/test/SettingsPage.test.ts` — extend `makeStore` with auth-related mocks

---

## Task 1: Backend auth models

**Files:**
- Create: `packages/backend/src/myhome/models_auth.py`

- [ ] **Step 1: Create the models file**

```python
# packages/backend/src/myhome/models_auth.py
from __future__ import annotations
from pydantic import BaseModel


class User(BaseModel):
    id: str
    username: str
    password_hash: str
    role: str  # "admin" | "normal" | "ro"
    created_at: str  # ISO-8601


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
```

- [ ] **Step 2: Commit**

```bash
git add packages/backend/src/myhome/models_auth.py
git commit -m "feat(auth): add User and ApiToken Pydantic models"
```

---

## Task 2: Auth persistence

**Files:**
- Create: `packages/backend/src/myhome/persistence_auth.py`

- [ ] **Step 1: Create persistence module**

```python
# packages/backend/src/myhome/persistence_auth.py
import json
import os
from pathlib import Path

from .models_auth import TokenDocument, UserDocument


def _users_file() -> Path:
    return Path(os.environ.get("DATA_DIR", "/data")) / "users.json"


def _tokens_file() -> Path:
    return Path(os.environ.get("DATA_DIR", "/data")) / "tokens.json"


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
```

- [ ] **Step 2: Write the failing test**

```python
# packages/backend/tests/test_auth_persistence.py
import pytest
from myhome.models_auth import ApiToken, TokenDocument, User, UserDocument
from myhome.persistence_auth import load_tokens, load_users, save_tokens, save_users


@pytest.fixture()
def data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    return tmp_path


def test_load_users_returns_empty_when_no_file(data_dir):
    doc = load_users()
    assert doc.users == []
    assert doc.version == 1


def test_save_and_load_users_roundtrip(data_dir):
    doc = UserDocument(users=[
        User(id="u1", username="alice", password_hash="hash", role="admin", created_at="2026-01-01T00:00:00+00:00")
    ])
    save_users(doc)
    loaded = load_users()
    assert len(loaded.users) == 1
    assert loaded.users[0].username == "alice"
    assert loaded.users[0].role == "admin"


def test_save_users_atomic_write(data_dir):
    doc = UserDocument(users=[
        User(id="u1", username="bob", password_hash="h", role="normal", created_at="2026-01-01T00:00:00+00:00")
    ])
    save_users(doc)
    assert (data_dir / "users.json").exists()
    assert not (data_dir / "users.tmp").exists()


def test_load_tokens_returns_empty_when_no_file(data_dir):
    doc = load_tokens()
    assert doc.tokens == []


def test_save_and_load_tokens_roundtrip(data_dir):
    doc = TokenDocument(tokens=[
        ApiToken(id="t1", name="MCP", token_hash="abc123", role="ro",
                 owner_id="u1", created_at="2026-01-01T00:00:00+00:00")
    ])
    save_tokens(doc)
    loaded = load_tokens()
    assert len(loaded.tokens) == 1
    assert loaded.tokens[0].name == "MCP"
    assert loaded.tokens[0].last_used_at is None
```

- [ ] **Step 3: Run test to verify it fails**

```bash
cd packages/backend && python -m pytest tests/test_auth_persistence.py -v
```
Expected: FAIL — `ModuleNotFoundError: No module named 'myhome.persistence_auth'`

- [ ] **Step 4: Run test to verify it passes (persistence_auth.py now exists)**

```bash
cd packages/backend && python -m pytest tests/test_auth_persistence.py -v
```
Expected: all 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add packages/backend/src/myhome/persistence_auth.py packages/backend/tests/test_auth_persistence.py
git commit -m "feat(auth): add auth persistence for users.json and tokens.json"
```

---

## Task 3: Install new dependencies + JWT utilities (deps.py)

**Files:**
- Modify: `packages/backend/pyproject.toml`
- Create: `packages/backend/src/myhome/deps.py`

- [ ] **Step 1: Add dependencies to pyproject.toml**

In `packages/backend/pyproject.toml`, update the `dependencies` list:

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
]
```

- [ ] **Step 2: Install the new dependencies**

```bash
cd packages/backend && pip install "python-jose[cryptography]>=3.3" "passlib[bcrypt]>=1.7"
```
Expected: Successfully installed python-jose, cryptography, passlib, bcrypt

- [ ] **Step 3: Create deps.py**

```python
# packages/backend/src/myhome/deps.py
from __future__ import annotations

import hashlib
import os
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import Cookie, Depends, Header, HTTPException, Request
from jose import JWTError, jwt
from passlib.context import CryptContext

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
REFRESH_TOKEN_EXPIRE_DAYS = 7
ROLE_ORDER: dict[str, int] = {"ro": 0, "normal": 1, "admin": 2}

pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _get_or_create_secret() -> str:
    env_val = os.environ.get("SECRET_KEY", "")
    if env_val:
        return env_val
    key_file = Path(os.environ.get("DATA_DIR", "/data")) / "secret_key"
    if key_file.exists():
        return key_file.read_text().strip()
    key = secrets.token_hex(32)
    key_file.parent.mkdir(parents=True, exist_ok=True)
    key_file.write_text(key)
    return key


def create_access_token(user_id: str, role: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": user_id, "role": role, "exp": expire, "iss": "myhome", "type": "access"}
    return jwt.encode(payload, _get_or_create_secret(), algorithm=ALGORITHM)


def create_refresh_token(user_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {"sub": user_id, "exp": expire, "iss": "myhome", "type": "refresh"}
    return jwt.encode(payload, _get_or_create_secret(), algorithm=ALGORITHM)


def _decode_access(token: str) -> dict | None:
    try:
        payload = jwt.decode(token, _get_or_create_secret(), algorithms=[ALGORITHM])
        return payload if payload.get("type") == "access" else None
    except JWTError:
        return None


def _decode_refresh(token: str) -> dict | None:
    try:
        payload = jwt.decode(token, _get_or_create_secret(), algorithms=[ALGORITHM])
        return payload if payload.get("type") == "refresh" else None
    except JWTError:
        return None


def _bearer_lookup(raw_token: str) -> tuple[str, str] | None:
    """Check opaque bearer token. Returns (user_id, role) or None."""
    from .persistence_auth import load_tokens, save_tokens

    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    doc = load_tokens()
    api_token = next((t for t in doc.tokens if t.token_hash == token_hash), None)
    if api_token is None:
        return None
    api_token.last_used_at = datetime.now(timezone.utc).isoformat()
    save_tokens(doc)
    return (api_token.owner_id, api_token.role)


async def _resolve_user(
    myhome_access: str | None = Cookie(default=None),
    authorization: str | None = Header(default=None),
) -> tuple[str, str] | None:
    """Return (user_id, role) from cookie JWT or Bearer token, or None."""
    if myhome_access:
        payload = _decode_access(myhome_access)
        if payload:
            return (payload["sub"], payload["role"])
    if authorization and authorization.startswith("Bearer "):
        return _bearer_lookup(authorization[7:])
    return None


async def get_user_from_request(request: Request) -> tuple[str, str] | None:
    """Extract (user_id, role) from a raw Request for use in middleware."""
    access_token = request.cookies.get("myhome_access")
    if access_token:
        payload = _decode_access(access_token)
        if payload:
            return (payload["sub"], payload["role"])
    auth_header = request.headers.get("authorization", "")
    if auth_header.startswith("Bearer "):
        return _bearer_lookup(auth_header[7:])
    return None


def require_auth(min_role: str = "ro"):
    """Return a FastAPI Depends that validates auth and enforces min_role."""
    async def _dep(
        user: tuple[str, str] | None = Depends(_resolve_user),
    ) -> tuple[str, str]:
        if user is None:
            raise HTTPException(401, "Authentication required")
        _, role = user
        if ROLE_ORDER.get(role, -1) < ROLE_ORDER.get(min_role, 0):
            raise HTTPException(403, "Insufficient permissions")
        return user

    return Depends(_dep)
```

- [ ] **Step 4: Write failing tests for JWT utilities**

```python
# packages/backend/tests/test_deps.py
import os
import pytest
from myhome.deps import (
    ROLE_ORDER,
    _decode_access,
    _decode_refresh,
    create_access_token,
    create_refresh_token,
    pwd_ctx,
)


@pytest.fixture(autouse=True)
def set_secret(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "test-secret-for-deps-tests")


def test_role_order_ro_less_than_normal():
    assert ROLE_ORDER["ro"] < ROLE_ORDER["normal"] < ROLE_ORDER["admin"]


def test_create_and_decode_access_token():
    token = create_access_token("user-1", "admin")
    payload = _decode_access(token)
    assert payload is not None
    assert payload["sub"] == "user-1"
    assert payload["role"] == "admin"
    assert payload["type"] == "access"


def test_decode_access_token_rejects_refresh_token():
    token = create_refresh_token("user-1")
    assert _decode_access(token) is None


def test_create_and_decode_refresh_token():
    token = create_refresh_token("user-1")
    payload = _decode_refresh(token)
    assert payload is not None
    assert payload["sub"] == "user-1"
    assert payload["type"] == "refresh"


def test_decode_refresh_token_rejects_access_token():
    token = create_access_token("user-1", "ro")
    assert _decode_refresh(token) is None


def test_decode_access_rejects_garbage():
    assert _decode_access("not-a-token") is None


def test_pwd_ctx_verify():
    hashed = pwd_ctx.hash("mypassword")
    assert pwd_ctx.verify("mypassword", hashed)
    assert not pwd_ctx.verify("wrongpassword", hashed)
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
cd packages/backend && python -m pytest tests/test_deps.py -v
```
Expected: all 7 tests PASS

- [ ] **Step 6: Commit**

```bash
git add packages/backend/pyproject.toml packages/backend/src/myhome/deps.py packages/backend/tests/test_deps.py
git commit -m "feat(auth): JWT utilities and require_auth dependency"
```

---

## Task 4: Core auth routes + first-boot + middleware

**Files:**
- Create: `packages/backend/src/myhome/routes/auth.py`
- Modify: `packages/backend/src/myhome/main.py`
- Create: `packages/backend/tests/test_auth.py`

- [ ] **Step 1: Create routes/auth.py**

```python
# packages/backend/src/myhome/routes/auth.py
from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timezone

from fastapi import APIRouter, Cookie, HTTPException, Response
from pydantic import BaseModel

from ..deps import (
    ROLE_ORDER,
    _decode_refresh,
    create_access_token,
    create_refresh_token,
    pwd_ctx,
    require_auth,
)
from ..models_auth import ApiToken, TokenDocument, User, UserDocument
from ..persistence_auth import load_tokens, load_users, save_tokens, save_users

router = APIRouter()


# ── Request / Response models ──────────────────────────────────────────────

class LoginRequest(BaseModel):
    username: str
    password: str


class UserInfo(BaseModel):
    id: str
    username: str
    role: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class CreateUserRequest(BaseModel):
    username: str
    password: str
    role: str


class UpdateUserRequest(BaseModel):
    role: str | None = None
    password: str | None = None


class CreateTokenRequest(BaseModel):
    name: str
    role: str


class TokenInfo(BaseModel):
    id: str
    name: str
    role: str
    owner_id: str
    created_at: str
    last_used_at: str | None = None


class CreatedTokenResponse(BaseModel):
    token: str
    info: TokenInfo


# ── Core auth ─────────────────────────────────────────────────────────────

@router.post("/api/auth/login")
def login(body: LoginRequest, response: Response) -> UserInfo:
    doc = load_users()
    user = next((u for u in doc.users if u.username.lower() == body.username.lower()), None)
    if user is None or not pwd_ctx.verify(body.password, user.password_hash):
        raise HTTPException(401, "Invalid username or password")
    _set_auth_cookies(response, user.id, user.role)
    return UserInfo(id=user.id, username=user.username, role=user.role)


@router.post("/api/auth/refresh", status_code=204)
def refresh(response: Response, myhome_refresh: str | None = Cookie(default=None)) -> None:
    if myhome_refresh is None:
        raise HTTPException(401, "No refresh token")
    payload = _decode_refresh(myhome_refresh)
    if payload is None:
        raise HTTPException(401, "Invalid or expired refresh token")
    doc = load_users()
    user = next((u for u in doc.users if u.id == payload["sub"]), None)
    if user is None:
        raise HTTPException(401, "User not found")
    response.set_cookie("myhome_access", create_access_token(user.id, user.role), httponly=True, samesite="lax")


@router.post("/api/auth/logout", status_code=204)
def logout(response: Response) -> None:
    response.delete_cookie("myhome_access")
    response.delete_cookie("myhome_refresh")


@router.get("/api/auth/me")
def get_me(current_user: tuple[str, str] = require_auth("ro")) -> UserInfo:
    user_id, _ = current_user
    doc = load_users()
    user = next((u for u in doc.users if u.id == user_id), None)
    if user is None:
        raise HTTPException(404, "User not found")
    return UserInfo(id=user.id, username=user.username, role=user.role)


@router.put("/api/auth/me/password", status_code=204)
def change_password(
    body: ChangePasswordRequest,
    current_user: tuple[str, str] = require_auth("ro"),
) -> None:
    user_id, _ = current_user
    doc = load_users()
    user = next((u for u in doc.users if u.id == user_id), None)
    if user is None:
        raise HTTPException(404)
    if not pwd_ctx.verify(body.current_password, user.password_hash):
        raise HTTPException(400, "Current password incorrect")
    if len(body.new_password) < 8:
        raise HTTPException(422, "Password must be at least 8 characters")
    user.password_hash = pwd_ctx.hash(body.new_password)
    save_users(doc)


# ── User management (admin only) ───────────────────────────────────────────

@router.get("/api/auth/users")
def list_users(current_user: tuple[str, str] = require_auth("admin")) -> list[UserInfo]:
    doc = load_users()
    return [UserInfo(id=u.id, username=u.username, role=u.role) for u in doc.users]


@router.post("/api/auth/users", status_code=201)
def create_user(
    body: CreateUserRequest,
    current_user: tuple[str, str] = require_auth("admin"),
) -> UserInfo:
    if body.role not in ROLE_ORDER:
        raise HTTPException(422, "Invalid role")
    if len(body.password) < 8:
        raise HTTPException(422, "Password must be at least 8 characters")
    doc = load_users()
    if any(u.username.lower() == body.username.lower() for u in doc.users):
        raise HTTPException(409, "Username already exists")
    user = User(
        id=secrets.token_hex(8),
        username=body.username,
        password_hash=pwd_ctx.hash(body.password),
        role=body.role,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    doc.users.append(user)
    save_users(doc)
    return UserInfo(id=user.id, username=user.username, role=user.role)


@router.put("/api/auth/users/{uid}", status_code=204)
def update_user(
    uid: str,
    body: UpdateUserRequest,
    current_user: tuple[str, str] = require_auth("admin"),
) -> None:
    doc = load_users()
    user = next((u for u in doc.users if u.id == uid), None)
    if user is None:
        raise HTTPException(404)
    if body.role is not None:
        if body.role not in ROLE_ORDER:
            raise HTTPException(422, "Invalid role")
        user.role = body.role
    if body.password is not None:
        if len(body.password) < 8:
            raise HTTPException(422, "Password must be at least 8 characters")
        user.password_hash = pwd_ctx.hash(body.password)
    save_users(doc)


@router.delete("/api/auth/users/{uid}", status_code=204)
def delete_user(
    uid: str,
    current_user: tuple[str, str] = require_auth("admin"),
) -> None:
    caller_id, _ = current_user
    if uid == caller_id:
        raise HTTPException(400, "Cannot delete your own account")
    doc = load_users()
    user = next((u for u in doc.users if u.id == uid), None)
    if user is None:
        raise HTTPException(404)
    doc.users = [u for u in doc.users if u.id != uid]
    save_users(doc)
    tdoc = load_tokens()
    tdoc.tokens = [t for t in tdoc.tokens if t.owner_id != uid]
    save_tokens(tdoc)


# ── API token management ───────────────────────────────────────────────────

@router.get("/api/auth/tokens")
def list_tokens(current_user: tuple[str, str] = require_auth("ro")) -> list[TokenInfo]:
    user_id, _ = current_user
    doc = load_tokens()
    return [
        TokenInfo(
            id=t.id, name=t.name, role=t.role, owner_id=t.owner_id,
            created_at=t.created_at, last_used_at=t.last_used_at,
        )
        for t in doc.tokens
        if t.owner_id == user_id
    ]


@router.post("/api/auth/tokens", status_code=201)
def create_token(
    body: CreateTokenRequest,
    current_user: tuple[str, str] = require_auth("ro"),
) -> CreatedTokenResponse:
    user_id, caller_role = current_user
    if body.role not in ROLE_ORDER:
        raise HTTPException(422, "Invalid role")
    if ROLE_ORDER[body.role] > ROLE_ORDER[caller_role]:
        raise HTTPException(422, "Token role cannot exceed your own role")
    raw_token = secrets.token_hex(32)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    api_token = ApiToken(
        id=secrets.token_hex(8),
        name=body.name,
        token_hash=token_hash,
        role=body.role,
        owner_id=user_id,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    doc = load_tokens()
    doc.tokens.append(api_token)
    save_tokens(doc)
    info = TokenInfo(
        id=api_token.id, name=api_token.name, role=api_token.role,
        owner_id=api_token.owner_id, created_at=api_token.created_at,
    )
    return CreatedTokenResponse(token=raw_token, info=info)


@router.delete("/api/auth/tokens/{tid}", status_code=204)
def delete_token(
    tid: str,
    current_user: tuple[str, str] = require_auth("ro"),
) -> None:
    user_id, role = current_user
    doc = load_tokens()
    token = next((t for t in doc.tokens if t.id == tid), None)
    if token is None:
        raise HTTPException(404)
    if token.owner_id != user_id and role != "admin":
        raise HTTPException(403, "Cannot delete another user's token")
    doc.tokens = [t for t in doc.tokens if t.id != tid]
    save_tokens(doc)


# ── Helper ─────────────────────────────────────────────────────────────────

def _set_auth_cookies(response: Response, user_id: str, role: str) -> None:
    response.set_cookie("myhome_access", create_access_token(user_id, role), httponly=True, samesite="lax")
    response.set_cookie("myhome_refresh", create_refresh_token(user_id), httponly=True, samesite="lax")
```

- [ ] **Step 2: Update main.py**

Replace `packages/backend/src/myhome/main.py` with:

```python
# packages/backend/src/myhome/main.py
import os
import secrets
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from .deps import ROLE_ORDER, get_user_from_request
from .routes import auth, backup, chores, consumables, costs, ha, house, inventory, kb, settings, svg, works

app = FastAPI(title="MyHome Backend", version="0.1.0")


# ── First boot ────────────────────────────────────────────────────────────

def _first_boot() -> None:
    data_dir = Path(os.environ.get("DATA_DIR", "/data"))
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
```

- [ ] **Step 3: Update conftest.py to provide auth-ready fixtures**

Replace `packages/backend/tests/conftest.py` with:

```python
# packages/backend/tests/conftest.py
import sys
from pathlib import Path

src_dir = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_dir))

import pytest
from fastapi.testclient import TestClient
from myhome.main import app
from myhome.models_auth import User, UserDocument
from myhome.persistence_auth import save_users


def _make_users(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("SECRET_KEY", "test-secret-key-for-tests-only")
    from passlib.context import CryptContext

    pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
    save_users(UserDocument(users=[
        User(
            id="u-admin", username="admin",
            password_hash=pwd_ctx.hash("admin123"),
            role="admin", created_at="2026-01-01T00:00:00+00:00",
        ),
        User(
            id="u-normal", username="normaluser",
            password_hash=pwd_ctx.hash("normal123"),
            role="normal", created_at="2026-01-01T00:00:00+00:00",
        ),
        User(
            id="u-ro", username="rouser",
            password_hash=pwd_ctx.hash("ro123456"),
            role="ro", created_at="2026-01-01T00:00:00+00:00",
        ),
    ]))


@pytest.fixture()
def client(tmp_path, monkeypatch):
    _make_users(tmp_path, monkeypatch)
    tc = TestClient(app)
    resp = tc.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    assert resp.status_code == 200
    return tc


@pytest.fixture()
def ro_client(tmp_path, monkeypatch):
    _make_users(tmp_path, monkeypatch)
    tc = TestClient(app)
    resp = tc.post("/api/auth/login", json={"username": "rouser", "password": "ro123456"})
    assert resp.status_code == 200
    return tc
```

- [ ] **Step 4: Remove local `client` fixture from every existing test file that defines one**

Run this to find them:
```bash
grep -l "def client" packages/backend/tests/
```

For each file listed, delete the lines:
```python
@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    return TestClient(app)
```

Also delete the now-unused `from fastapi.testclient import TestClient` and `from myhome.main import app` imports from any file that no longer needs them directly (the conftest provides `client`).

Also update any test function that creates a TestClient inline, like:
```python
# Before (in test_settings.py):
def test_get_settings_returns_saved_data(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    save_settings(SettingsDocument(...))
    resp = TestClient(app).get("/api/settings")

# After:
def test_get_settings_returns_saved_data(client):
    save_settings(SettingsDocument(...))  # DATA_DIR already set by client fixture
    resp = client.get("/api/settings")
```

- [ ] **Step 5: Write core auth tests**

```python
# packages/backend/tests/test_auth.py
import pytest
from fastapi.testclient import TestClient
from myhome.main import app
from myhome.models_auth import User, UserDocument
from myhome.persistence_auth import save_users


@pytest.fixture()
def fresh(tmp_path, monkeypatch):
    """Unauthenticated client with admin user already seeded."""
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("SECRET_KEY", "test-secret-key-for-tests-only")
    from passlib.context import CryptContext
    pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
    save_users(UserDocument(users=[
        User(id="u1", username="admin", password_hash=pwd_ctx.hash("admin123"),
             role="admin", created_at="2026-01-01T00:00:00+00:00")
    ]))
    return TestClient(app, raise_server_exceptions=True)


def test_unauthenticated_request_returns_401(fresh):
    resp = fresh.get("/api/settings")
    assert resp.status_code == 401


def test_login_happy_path(fresh):
    resp = fresh.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["username"] == "admin"
    assert data["role"] == "admin"
    assert "myhome_access" in resp.cookies
    assert "myhome_refresh" in resp.cookies


def test_login_wrong_password_returns_401(fresh):
    resp = fresh.post("/api/auth/login", json={"username": "admin", "password": "wrongpass"})
    assert resp.status_code == 401


def test_login_unknown_user_returns_401(fresh):
    resp = fresh.post("/api/auth/login", json={"username": "nobody", "password": "admin123"})
    assert resp.status_code == 401


def test_me_returns_current_user(client):
    resp = client.get("/api/auth/me")
    assert resp.status_code == 200
    data = resp.json()
    assert data["username"] == "admin"
    assert data["role"] == "admin"


def test_me_returns_401_when_not_logged_in(fresh):
    resp = fresh.get("/api/auth/me")
    assert resp.status_code == 401


def test_logout_clears_cookies(client):
    resp = client.post("/api/auth/logout")
    assert resp.status_code == 204
    assert resp.cookies.get("myhome_access") is None or resp.cookies.get("myhome_access") == ""


def test_refresh_issues_new_access_token(fresh):
    login_resp = fresh.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    assert login_resp.status_code == 200
    # TestClient preserves cookies; refresh uses the myhome_refresh cookie
    resp = fresh.post("/api/auth/refresh")
    assert resp.status_code == 204
    assert "myhome_access" in resp.cookies


def test_refresh_fails_without_cookie(fresh):
    resp = fresh.post("/api/auth/refresh")
    assert resp.status_code == 401


def test_change_password_succeeds(client):
    resp = client.put("/api/auth/me/password", json={
        "current_password": "admin123",
        "new_password": "newpassword99",
    })
    assert resp.status_code == 204


def test_change_password_wrong_current_returns_400(client):
    resp = client.put("/api/auth/me/password", json={
        "current_password": "wrongpass",
        "new_password": "newpassword99",
    })
    assert resp.status_code == 400


def test_change_password_too_short_returns_422(client):
    resp = client.put("/api/auth/me/password", json={
        "current_password": "admin123",
        "new_password": "short",
    })
    assert resp.status_code == 422
```

- [ ] **Step 6: Run all auth tests**

```bash
cd packages/backend && python -m pytest tests/test_auth.py -v
```
Expected: all 12 tests PASS

- [ ] **Step 7: Run existing test suite to confirm no regressions**

```bash
cd packages/backend && python -m pytest tests/ -v --ignore=tests/test_auth_users.py --ignore=tests/test_auth_tokens.py --ignore=tests/test_auth_roles.py -v
```
Expected: all existing tests PASS (they now use the new auth-aware `client` fixture)

- [ ] **Step 8: Commit**

```bash
git add packages/backend/src/myhome/routes/auth.py \
        packages/backend/src/myhome/main.py \
        packages/backend/tests/conftest.py \
        packages/backend/tests/test_auth.py \
        packages/backend/tests/
git commit -m "feat(auth): login/logout/me/refresh/change-password routes + auth middleware"
```

---

## Task 5: User management route tests

**Files:**
- Create: `packages/backend/tests/test_auth_users.py`

The user management endpoints already exist in `routes/auth.py` from Task 4. This task covers their tests.

- [ ] **Step 1: Write user management tests**

```python
# packages/backend/tests/test_auth_users.py
import pytest


def test_list_users_as_admin(client):
    resp = client.get("/api/auth/users")
    assert resp.status_code == 200
    users = resp.json()
    assert any(u["username"] == "admin" for u in users)


def test_list_users_blocked_for_normal(ro_client):
    # ro_client is logged in as "rouser" (role=ro)
    resp = ro_client.get("/api/auth/users")
    assert resp.status_code == 403


def test_create_user_as_admin(client):
    resp = client.post("/api/auth/users", json={
        "username": "newbie",
        "password": "newbiepw99",
        "role": "normal",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["username"] == "newbie"
    assert data["role"] == "normal"
    assert "id" in data


def test_create_user_duplicate_username_returns_409(client):
    client.post("/api/auth/users", json={"username": "dup", "password": "dup12345", "role": "normal"})
    resp = client.post("/api/auth/users", json={"username": "DUP", "password": "dup12345", "role": "normal"})
    assert resp.status_code == 409


def test_create_user_short_password_returns_422(client):
    resp = client.post("/api/auth/users", json={"username": "x", "password": "short", "role": "normal"})
    assert resp.status_code == 422


def test_create_user_invalid_role_returns_422(client):
    resp = client.post("/api/auth/users", json={"username": "x", "password": "valid123", "role": "superuser"})
    assert resp.status_code == 422


def test_update_user_role_as_admin(client):
    create_resp = client.post("/api/auth/users", json={
        "username": "target", "password": "targetpw1", "role": "normal"
    })
    uid = create_resp.json()["id"]
    resp = client.put(f"/api/auth/users/{uid}", json={"role": "ro"})
    assert resp.status_code == 204
    users = client.get("/api/auth/users").json()
    target = next(u for u in users if u["id"] == uid)
    assert target["role"] == "ro"


def test_update_user_password_as_admin(client):
    create_resp = client.post("/api/auth/users", json={
        "username": "pwchange", "password": "oldpw1234", "role": "normal"
    })
    uid = create_resp.json()["id"]
    resp = client.put(f"/api/auth/users/{uid}", json={"password": "newpw9876"})
    assert resp.status_code == 204


def test_delete_user_as_admin(client):
    create_resp = client.post("/api/auth/users", json={
        "username": "todelete", "password": "todelete1", "role": "normal"
    })
    uid = create_resp.json()["id"]
    resp = client.delete(f"/api/auth/users/{uid}")
    assert resp.status_code == 204
    users = client.get("/api/auth/users").json()
    assert not any(u["id"] == uid for u in users)


def test_delete_self_returns_400(client):
    me = client.get("/api/auth/me").json()
    resp = client.delete(f"/api/auth/users/{me['id']}")
    assert resp.status_code == 400


def test_delete_user_cascades_tokens(client):
    from myhome.persistence_auth import load_tokens
    create_resp = client.post("/api/auth/users", json={
        "username": "tokenowner", "password": "tokenown1", "role": "normal"
    })
    uid = create_resp.json()["id"]
    # Create a token for this user (would need to log in as them — skip direct persistence approach)
    # Instead verify via /api/auth/tokens after delete shows 0 (only meaningful if we had the token)
    client.delete(f"/api/auth/users/{uid}")
    # Verify user gone
    users = client.get("/api/auth/users").json()
    assert not any(u["id"] == uid for u in users)
```

- [ ] **Step 2: Run tests**

```bash
cd packages/backend && python -m pytest tests/test_auth_users.py -v
```
Expected: all 11 tests PASS

- [ ] **Step 3: Commit**

```bash
git add packages/backend/tests/test_auth_users.py
git commit -m "test(auth): user management endpoint tests"
```

---

## Task 6: API token management tests + role enforcement

**Files:**
- Create: `packages/backend/tests/test_auth_tokens.py`
- Create: `packages/backend/tests/test_auth_roles.py`

- [ ] **Step 1: Write token management tests**

```python
# packages/backend/tests/test_auth_tokens.py
import pytest


def test_list_tokens_initially_empty(client):
    resp = client.get("/api/auth/tokens")
    assert resp.status_code == 200
    assert resp.json() == []


def test_create_token(client):
    resp = client.post("/api/auth/tokens", json={"name": "My Script", "role": "ro"})
    assert resp.status_code == 201
    data = resp.json()
    assert "token" in data
    assert len(data["token"]) == 64  # 32 bytes hex
    assert data["info"]["name"] == "My Script"
    assert data["info"]["role"] == "ro"


def test_created_token_appears_in_list(client):
    client.post("/api/auth/tokens", json={"name": "Listed", "role": "ro"})
    resp = client.get("/api/auth/tokens")
    tokens = resp.json()
    assert any(t["name"] == "Listed" for t in tokens)


def test_token_list_does_not_expose_raw_token(client):
    client.post("/api/auth/tokens", json={"name": "Secret", "role": "ro"})
    tokens = client.get("/api/auth/tokens").json()
    for t in tokens:
        assert "token_hash" not in t
        assert len(t.get("id", "")) < 32  # id is short, not the raw 64-char token


def test_create_token_scope_ceiling_enforced(ro_client):
    # ro user cannot create an admin-scoped token
    resp = ro_client.post("/api/auth/tokens", json={"name": "Escalation", "role": "admin"})
    assert resp.status_code == 422


def test_create_token_invalid_role_returns_422(client):
    resp = client.post("/api/auth/tokens", json={"name": "Bad", "role": "superuser"})
    assert resp.status_code == 422


def test_revoke_token(client):
    create_resp = client.post("/api/auth/tokens", json={"name": "ToRevoke", "role": "ro"})
    tid = create_resp.json()["info"]["id"]
    resp = client.delete(f"/api/auth/tokens/{tid}")
    assert resp.status_code == 204
    tokens = client.get("/api/auth/tokens").json()
    assert not any(t["id"] == tid for t in tokens)


def test_revoke_nonexistent_token_returns_404(client):
    resp = client.delete("/api/auth/tokens/nonexistent")
    assert resp.status_code == 404


def test_bearer_token_authenticates_request(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("SECRET_KEY", "test-secret-key-for-tests-only")
    from passlib.context import CryptContext
    from myhome.models_auth import User, UserDocument
    from myhome.persistence_auth import save_users
    from fastapi.testclient import TestClient
    from myhome.main import app
    pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
    save_users(UserDocument(users=[
        User(id="u1", username="admin", password_hash=pwd_ctx.hash("admin123"),
             role="admin", created_at="2026-01-01T00:00:00+00:00")
    ]))
    tc = TestClient(app)
    # Login to get a session, then create a token
    tc.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    create_resp = tc.post("/api/auth/tokens", json={"name": "Automation", "role": "normal"})
    raw_token = create_resp.json()["token"]
    # Now use the raw token as a Bearer token on a fresh (cookieless) client
    bare = TestClient(app)
    resp = bare.get("/api/settings", headers={"Authorization": f"Bearer {raw_token}"})
    assert resp.status_code == 200


def test_bearer_token_updates_last_used_at(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("SECRET_KEY", "test-secret-key-for-tests-only")
    from passlib.context import CryptContext
    from myhome.models_auth import User, UserDocument
    from myhome.persistence_auth import load_tokens, save_users
    from fastapi.testclient import TestClient
    from myhome.main import app
    pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
    save_users(UserDocument(users=[
        User(id="u1", username="admin", password_hash=pwd_ctx.hash("admin123"),
             role="admin", created_at="2026-01-01T00:00:00+00:00")
    ]))
    tc = TestClient(app)
    tc.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    create_resp = tc.post("/api/auth/tokens", json={"name": "Tracker", "role": "ro"})
    raw_token = create_resp.json()["token"]
    bare = TestClient(app)
    bare.get("/api/settings", headers={"Authorization": f"Bearer {raw_token}"})
    doc = load_tokens()
    used = next(t for t in doc.tokens if t.name == "Tracker")
    assert used.last_used_at is not None
```

- [ ] **Step 2: Write role enforcement tests**

```python
# packages/backend/tests/test_auth_roles.py
import pytest


def test_ro_user_can_read_settings(ro_client):
    resp = ro_client.get("/api/settings")
    assert resp.status_code == 200


def test_ro_user_blocked_from_writing_settings(ro_client):
    resp = ro_client.put("/api/settings/suppliers", json=[{"id": "s1", "name": "Acme"}])
    assert resp.status_code == 403


def test_ro_user_blocked_from_creating_chore(ro_client):
    resp = ro_client.post("/api/chores", json={
        "name": "Clean", "emoji": "🧹", "frequencyDays": 7,
        "nextDueDate": "2026-07-10", "categoryId": None,
    })
    assert resp.status_code == 403


def test_normal_user_can_write_data(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("SECRET_KEY", "test-secret-key-for-tests-only")
    from passlib.context import CryptContext
    from myhome.models_auth import User, UserDocument
    from myhome.persistence_auth import save_users
    from fastapi.testclient import TestClient
    from myhome.main import app
    pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
    save_users(UserDocument(users=[
        User(id="u1", username="normal", password_hash=pwd_ctx.hash("normal123"),
             role="normal", created_at="2026-01-01T00:00:00+00:00")
    ]))
    tc = TestClient(app)
    tc.post("/api/auth/login", json={"username": "normal", "password": "normal123"})
    resp = tc.put("/api/settings/suppliers", json=[{"id": "s1", "name": "Plumbers"}])
    assert resp.status_code == 204


def test_normal_user_blocked_from_user_management(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("SECRET_KEY", "test-secret-key-for-tests-only")
    from passlib.context import CryptContext
    from myhome.models_auth import User, UserDocument
    from myhome.persistence_auth import save_users
    from fastapi.testclient import TestClient
    from myhome.main import app
    pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
    save_users(UserDocument(users=[
        User(id="u1", username="normal", password_hash=pwd_ctx.hash("normal123"),
             role="normal", created_at="2026-01-01T00:00:00+00:00")
    ]))
    tc = TestClient(app)
    tc.post("/api/auth/login", json={"username": "normal", "password": "normal123"})
    resp = tc.get("/api/auth/users")
    assert resp.status_code == 403


def test_ro_bearer_token_blocked_on_write(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("SECRET_KEY", "test-secret-key-for-tests-only")
    from passlib.context import CryptContext
    from myhome.models_auth import User, UserDocument
    from myhome.persistence_auth import save_users
    from fastapi.testclient import TestClient
    from myhome.main import app
    pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
    save_users(UserDocument(users=[
        User(id="u1", username="admin", password_hash=pwd_ctx.hash("admin123"),
             role="admin", created_at="2026-01-01T00:00:00+00:00")
    ]))
    tc = TestClient(app)
    tc.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    create_resp = tc.post("/api/auth/tokens", json={"name": "ReadOnly", "role": "ro"})
    raw_token = create_resp.json()["token"]
    bare = TestClient(app)
    resp = bare.put("/api/settings/suppliers",
                    json=[{"id": "s1", "name": "X"}],
                    headers={"Authorization": f"Bearer {raw_token}"})
    assert resp.status_code == 403
```

- [ ] **Step 3: Run all new tests**

```bash
cd packages/backend && python -m pytest tests/test_auth_tokens.py tests/test_auth_roles.py -v
```
Expected: all tests PASS

- [ ] **Step 4: Run full backend test suite**

```bash
cd packages/backend && python -m pytest tests/ -v
```
Expected: all tests PASS

- [ ] **Step 5: Commit**

```bash
git add packages/backend/tests/test_auth_tokens.py packages/backend/tests/test_auth_roles.py
git commit -m "test(auth): API token management and role enforcement tests"
```

---

## Task 7: Frontend authStore

**Files:**
- Create: `packages/editor/src/lib/authStore.svelte.ts`
- Create: `packages/editor/test/authStore.test.ts`

- [ ] **Step 1: Create authStore.svelte.ts**

```typescript
// packages/editor/src/lib/authStore.svelte.ts

export interface AuthUser {
  id: string;
  username: string;
  role: "admin" | "normal" | "ro";
}

export function createAuthStore() {
  let user = $state<AuthUser | null>(null);
  let checking = $state(true);

  async function init(): Promise<void> {
    try {
      const resp = await fetch("/api/auth/me");
      user = resp.ok ? await resp.json() : null;
    } catch {
      user = null;
    } finally {
      checking = false;
    }
  }

  async function login(username: string, password: string): Promise<AuthUser> {
    const resp = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });
    if (!resp.ok) throw new Error("Invalid credentials");
    const u: AuthUser = await resp.json();
    user = u;
    return u;
  }

  async function logout(): Promise<void> {
    await fetch("/api/auth/logout", { method: "POST" });
    user = null;
  }

  async function changePassword(currentPassword: string, newPassword: string): Promise<void> {
    const resp = await fetch("/api/auth/me/password", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
    });
    if (!resp.ok) {
      const data: { detail?: string } = await resp.json().catch(() => ({}));
      throw new Error(data.detail ?? `HTTP ${resp.status}`);
    }
  }

  init();

  return {
    get user() { return user; },
    get checking() { return checking; },
    login,
    logout,
    changePassword,
  };
}
```

- [ ] **Step 2: Write the failing test**

```typescript
// packages/editor/test/authStore.test.ts
import { describe, it, expect, vi, beforeEach } from "vitest";
import { flushSync } from "svelte";
import { createAuthStore } from "../src/lib/authStore.svelte";

describe("authStore", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });

  it("starts with checking=true and user=null", () => {
    vi.mocked(fetch).mockResolvedValue({ ok: false, status: 401 } as Response);
    const store = createAuthStore();
    expect(store.checking).toBe(true);
    expect(store.user).toBeNull();
  });

  it("sets user when /me returns 200", async () => {
    const mockUser = { id: "u1", username: "admin", role: "admin" };
    vi.mocked(fetch).mockResolvedValue({ ok: true, json: async () => mockUser } as Response);
    const store = createAuthStore();
    await new Promise((r) => setTimeout(r, 0));
    flushSync();
    expect(store.user).toEqual(mockUser);
    expect(store.checking).toBe(false);
  });

  it("sets user=null and checking=false when /me returns 401", async () => {
    vi.mocked(fetch).mockResolvedValue({ ok: false, status: 401 } as Response);
    const store = createAuthStore();
    await new Promise((r) => setTimeout(r, 0));
    flushSync();
    expect(store.user).toBeNull();
    expect(store.checking).toBe(false);
  });

  it("login() calls /api/auth/login and sets user", async () => {
    const mockUser = { id: "u1", username: "alice", role: "normal" };
    vi.mocked(fetch)
      .mockResolvedValueOnce({ ok: false, status: 401 } as Response)  // init /me
      .mockResolvedValueOnce({ ok: true, json: async () => mockUser } as Response);
    const store = createAuthStore();
    await new Promise((r) => setTimeout(r, 0));
    flushSync();
    const result = await store.login("alice", "alicepass");
    flushSync();
    expect(store.user).toEqual(mockUser);
    expect(result).toEqual(mockUser);
  });

  it("login() throws on 401 and does not set user", async () => {
    vi.mocked(fetch)
      .mockResolvedValueOnce({ ok: false, status: 401 } as Response)  // init
      .mockResolvedValueOnce({ ok: false, status: 401 } as Response);  // login
    const store = createAuthStore();
    await new Promise((r) => setTimeout(r, 0));
    flushSync();
    await expect(store.login("x", "y")).rejects.toThrow("Invalid credentials");
    expect(store.user).toBeNull();
  });

  it("logout() calls /api/auth/logout and clears user", async () => {
    const mockUser = { id: "u1", username: "admin", role: "admin" };
    vi.mocked(fetch)
      .mockResolvedValueOnce({ ok: true, json: async () => mockUser } as Response)
      .mockResolvedValueOnce({ ok: true } as Response);
    const store = createAuthStore();
    await new Promise((r) => setTimeout(r, 0));
    flushSync();
    await store.logout();
    flushSync();
    expect(store.user).toBeNull();
    const logoutCall = vi.mocked(fetch).mock.calls.find((c) => c[0] === "/api/auth/logout");
    expect(logoutCall).toBeTruthy();
  });
});
```

- [ ] **Step 3: Run test to verify it fails**

```bash
cd packages/editor && npx vitest run test/authStore.test.ts
```
Expected: FAIL — module not found

- [ ] **Step 4: Run test to verify it passes**

```bash
cd packages/editor && npx vitest run test/authStore.test.ts
```
Expected: all 6 tests PASS

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/lib/authStore.svelte.ts packages/editor/test/authStore.test.ts
git commit -m "feat(auth): authStore — login/logout/changePassword with /me check"
```

---

## Task 8: LoginPage component

**Files:**
- Create: `packages/editor/src/lib/components/LoginPage.svelte`
- Create: `packages/editor/test/LoginPage.test.ts`

- [ ] **Step 1: Write the failing test first**

```typescript
// packages/editor/test/LoginPage.test.ts
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { mount, unmount, flushSync } from "svelte";
import LoginPage from "../src/lib/components/LoginPage.svelte";

describe("LoginPage", () => {
  let target: HTMLDivElement;

  beforeEach(() => {
    target = document.createElement("div");
    document.body.appendChild(target);
  });

  afterEach(() => {
    target.remove();
  });

  it("renders username field, password field, and Sign in button", () => {
    const app = mount(LoginPage, {
      target,
      props: { onlogin: vi.fn(), login: vi.fn() },
    });
    flushSync();
    expect(target.querySelector('input[type="text"]')).not.toBeNull();
    expect(target.querySelector('input[type="password"]')).not.toBeNull();
    expect(target.textContent).toContain("Sign in");
    unmount(app);
  });

  it("shows contact-admin footer and no self-registration prompt", () => {
    const app = mount(LoginPage, {
      target,
      props: { onlogin: vi.fn(), login: vi.fn() },
    });
    flushSync();
    expect(target.textContent).toContain("Contact your admin");
    unmount(app);
  });

  it("calls login() and onlogin() on successful submit", async () => {
    const mockUser = { id: "u1", username: "admin", role: "admin" };
    const mockLogin = vi.fn().mockResolvedValue(mockUser);
    const mockOnlogin = vi.fn();
    const app = mount(LoginPage, {
      target,
      props: { onlogin: mockOnlogin, login: mockLogin },
    });
    flushSync();
    const usernameInput = target.querySelector('input[type="text"]') as HTMLInputElement;
    const passwordInput = target.querySelector('input[type="password"]') as HTMLInputElement;
    usernameInput.value = "admin";
    usernameInput.dispatchEvent(new Event("input"));
    passwordInput.value = "admin123";
    passwordInput.dispatchEvent(new Event("input"));
    flushSync();
    target.querySelector("form")!.dispatchEvent(
      new Event("submit", { bubbles: true, cancelable: true }),
    );
    await new Promise((r) => setTimeout(r, 0));
    flushSync();
    expect(mockLogin).toHaveBeenCalledWith("admin", "admin123");
    expect(mockOnlogin).toHaveBeenCalled();
    unmount(app);
  });

  it("shows error message when login() throws", async () => {
    const mockLogin = vi.fn().mockRejectedValue(new Error("bad creds"));
    const app = mount(LoginPage, {
      target,
      props: { onlogin: vi.fn(), login: mockLogin },
    });
    flushSync();
    target.querySelector("form")!.dispatchEvent(
      new Event("submit", { bubbles: true, cancelable: true }),
    );
    await new Promise((r) => setTimeout(r, 0));
    flushSync();
    expect(target.textContent).toContain("Invalid username or password");
    unmount(app);
  });

  it("does not show error before any submit attempt", () => {
    const app = mount(LoginPage, {
      target,
      props: { onlogin: vi.fn(), login: vi.fn() },
    });
    flushSync();
    expect(target.textContent).not.toContain("Invalid username or password");
    unmount(app);
  });
});
```

- [ ] **Step 2: Run to verify it fails**

```bash
cd packages/editor && npx vitest run test/LoginPage.test.ts
```
Expected: FAIL — module not found

- [ ] **Step 3: Create LoginPage.svelte**

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
      <h1 class="login-title">MyHome</h1>
      <p class="login-subtitle">Sign in to continue</p>
    </div>

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

      {#if error}
        <div class="login-error">{error}</div>
      {/if}

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

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd packages/editor && npx vitest run test/LoginPage.test.ts
```
Expected: all 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/lib/components/LoginPage.svelte packages/editor/test/LoginPage.test.ts
git commit -m "feat(auth): LoginPage component"
```

---

## Task 9: App.svelte — auth gate and user menu

**Files:**
- Modify: `packages/editor/src/App.svelte`
- Modify: `packages/editor/test/App.test.ts`

- [ ] **Step 1: Update App.test.ts to mock /api/auth/me**

In `packages/editor/test/App.test.ts`, update the `stubFetch` function to include `/api/auth/me`:

```typescript
function stubFetch(handlers: Record<string, unknown> = {}) {
  vi.stubGlobal("fetch", vi.fn().mockImplementation((url: string) => {
    const defaultHandlers: Record<string, unknown> = {
      "/api/auth/me": { id: "u1", username: "admin", role: "admin" },
      ...handlers,
    };
    if (url in defaultHandlers) {
      return Promise.resolve({
        ok: true,
        status: 200,
        statusText: "OK",
        json: async () => defaultHandlers[url],
      });
    }
    return Promise.resolve({
      ok: false,
      status: 404,
      statusText: "Not Found",
      json: async () => undefined,
    });
  }));
}
```

Also update `mountAndLoad` to tick an extra time for the auth store to resolve:
```typescript
async function mountAndLoad(target: HTMLElement, route = "#/plan"): Promise<ReturnType<typeof mount>> {
  window.location.hash = route;
  const app = mount(App, { target });
  await tick();
  await tick();
  await tick();  // extra tick for authStore init
  flushSync();
  return app;
}
```

- [ ] **Step 2: Run existing App tests to confirm they still pass before modifying App.svelte**

```bash
cd packages/editor && npx vitest run test/App.test.ts
```
Expected: PASS (with the updated stubFetch)

- [ ] **Step 3: Update App.svelte — add imports**

At the top of the `<script>` block in `packages/editor/src/App.svelte`, add after the existing imports:

```typescript
  import { createAuthStore } from "./lib/authStore.svelte";
  import LoginPage from "./lib/components/LoginPage.svelte";
```

And after the existing store instantiations (after `const consumableStore = createConsumableStore();`), add:

```typescript
  const authStore = createAuthStore();
```

- [ ] **Step 4: Update App.svelte — add user menu state**

After the `let navExpanded = $state(false);` line, add:

```typescript
  let userMenuOpen = $state(false);
  let showChangePassword = $state(false);
  let cpCurrent = $state("");
  let cpNew = $state("");
  let cpError = $state<string | null>(null);
  let cpLoading = $state(false);

  async function handleChangePassword(): Promise<void> {
    cpError = null;
    cpLoading = true;
    try {
      await authStore.changePassword(cpCurrent, cpNew);
      showChangePassword = false;
      cpCurrent = "";
      cpNew = "";
    } catch (e) {
      cpError = e instanceof Error ? e.message : "Failed";
    } finally {
      cpLoading = false;
    }
  }

  async function handleSignOut(): Promise<void> {
    await authStore.logout();
    userMenuOpen = false;
  }
```

- [ ] **Step 5: Update App.svelte — auth gate in template**

The root template in App.svelte starts with `<svelte:window .../>` and `<div class="app">`. Wrap the existing content so that if auth is not ready or user is null, we show the appropriate screen.

Replace the existing `<div class="app">` opening and everything inside with a conditional:

At the very top of the HTML template (before `<svelte:window>`), add:

```svelte
{#if authStore.checking}
  <div class="auth-loading">Loading…</div>
{:else if !authStore.user}
  <LoginPage onlogin={() => {}} login={authStore.login} />
{:else}
```

And at the very end of the template (after the closing `</div>` for `.app`), close the `{:else}` block:

```svelte
{/if}
```

- [ ] **Step 6: Update App.svelte — add user menu to topbar**

In the topbar `<header class="topbar">`, after the theme toggle button, add:

```svelte
    <div class="user-menu-wrap">
      <button
        class="icon-btn user-chip"
        onclick={() => { userMenuOpen = !userMenuOpen; }}
        title="User menu"
      >
        {authStore.user?.username.slice(0, 2).toUpperCase()}
      </button>
      {#if userMenuOpen}
        <div class="user-dropdown">
          <div class="user-dropdown-header">
            <span class="user-dropdown-name">{authStore.user?.username}</span>
            <span class="user-role-badge">{authStore.user?.role}</span>
          </div>
          <hr class="user-dropdown-sep" />
          <button class="user-dropdown-item" onclick={() => { showChangePassword = true; userMenuOpen = false; }}>
            Change password
          </button>
          <button class="user-dropdown-item signout" onclick={handleSignOut}>
            Sign out
          </button>
        </div>
      {/if}
    </div>
```

- [ ] **Step 7: Add change password modal to App.svelte template (before closing `{/if}`)**

After the NavMenu and content `</div>` closes, add:

```svelte
  {#if showChangePassword}
    <Modal title="Change Password" onclose={() => { showChangePassword = false; cpError = null; }}>
      <div style="display:flex;flex-direction:column;gap:12px;padding:4px 0">
        <Input label="Current password" type="password" bind:value={cpCurrent} />
        <Input label="New password (min 8 chars)" type="password" bind:value={cpNew} />
        {#if cpError}<div style="color:var(--danger);font-size:0.85rem">{cpError}</div>{/if}
        <div style="display:flex;gap:8px;justify-content:flex-end;margin-top:8px">
          <Button variant="secondary" onclick={() => { showChangePassword = false; cpError = null; }}>Cancel</Button>
          <Button onclick={handleChangePassword} disabled={cpLoading}>
            {cpLoading ? "Saving…" : "Change password"}
          </Button>
        </div>
      </div>
    </Modal>
  {/if}
```

Add the Modal, Input, and Button imports at the top of the script if not already present:
```typescript
  import Modal from "./lib/components/ui/Modal.svelte";
  import Input from "./lib/components/ui/Input.svelte";
  import Button from "./lib/components/ui/Button.svelte";
```

- [ ] **Step 8: Add CSS for user menu to App.svelte `<style>` block**

```css
  .auth-loading {
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--text-muted);
    font-size: 0.9rem;
  }

  .user-menu-wrap { position: relative; }

  .user-chip {
    width: 32px;
    height: 32px;
    border-radius: 50%;
    background: var(--accent);
    color: #fff;
    font-size: 0.7rem;
    font-weight: 700;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .user-dropdown {
    position: absolute;
    top: calc(100% + 6px);
    right: 0;
    min-width: 180px;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 8px 0;
    box-shadow: 0 4px 16px rgba(0,0,0,0.3);
    z-index: 200;
  }

  .user-dropdown-header {
    padding: 8px 14px 6px;
    display: flex;
    flex-direction: column;
    gap: 2px;
  }

  .user-dropdown-name { font-size: 0.9rem; color: var(--text); font-weight: 600; }

  .user-role-badge {
    font-size: 0.7rem;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }

  .user-dropdown-sep { margin: 4px 0; border: none; border-top: 1px solid var(--border); }

  .user-dropdown-item {
    display: block;
    width: 100%;
    text-align: left;
    background: none;
    border: none;
    padding: 8px 14px;
    font-size: 0.875rem;
    color: var(--text);
    cursor: pointer;
    font-family: var(--font-sans);
  }

  .user-dropdown-item:hover { background: var(--surface-hover, var(--border)); }
  .user-dropdown-item.signout { color: var(--danger, #e05); }
```

- [ ] **Step 9: Run App tests**

```bash
cd packages/editor && npx vitest run test/App.test.ts
```
Expected: PASS

- [ ] **Step 10: Commit**

```bash
git add packages/editor/src/App.svelte packages/editor/test/App.test.ts
git commit -m "feat(auth): App.svelte auth gate and user menu"
```

---

## Task 10: Settings — API Tokens tab

**Files:**
- Modify: `packages/editor/src/lib/components/SettingsPage.svelte`
- Modify: `packages/editor/test/SettingsPage.test.ts`

- [ ] **Step 1: Add authStore prop and token management to SettingsPage.svelte**

At the top of the `<script>` in `SettingsPage.svelte`, add after the existing imports:

```typescript
  import type { createAuthStore, AuthUser } from "../authStore.svelte";
  type AuthStore = ReturnType<typeof createAuthStore>;
```

Add `authStore` to the Props interface:

```typescript
  interface Props {
    store: SettingsStore;
    authStore: AuthStore;
  }
  let { store, authStore }: Props = $props();
```

Add token state and methods after the existing state declarations:

```typescript
  // --- API Tokens ---
  interface TokenInfo {
    id: string;
    name: string;
    role: string;
    owner_id: string;
    created_at: string;
    last_used_at: string | null;
  }

  let apiTokens = $state<TokenInfo[]>([]);
  let tokensLoaded = $state(false);
  let showNewTokenModal = $state(false);
  let newTokenName = $state("");
  let newTokenRole = $state<string>("ro");
  let createdTokenSecret = $state<string | null>(null);
  let confirmRevokeTokenId = $state<string | null>(null);
  let tokenError = $state<string | null>(null);

  const _allRoles = ["ro", "normal", "admin"];
  const roleOptions = $derived(
    _allRoles.slice(0, _allRoles.indexOf(authStore.user?.role ?? "ro") + 1)
  );

  async function loadTokens(): Promise<void> {
    try {
      const resp = await fetch("/api/auth/tokens");
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      apiTokens = await resp.json();
    } finally {
      tokensLoaded = true;
    }
  }

  async function createApiToken(): Promise<void> {
    if (!newTokenName.trim()) { tokenError = "Name required"; return; }
    tokenError = null;
    const resp = await fetch("/api/auth/tokens", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: newTokenName.trim(), role: newTokenRole }),
    });
    if (!resp.ok) { tokenError = `Error ${resp.status}`; return; }
    const data = await resp.json();
    createdTokenSecret = data.token;
    newTokenName = "";
    newTokenRole = "ro";
    showNewTokenModal = false;
    await loadTokens();
  }

  async function revokeToken(id: string): Promise<void> {
    await fetch(`/api/auth/tokens/${id}`, { method: "DELETE" });
    confirmRevokeTokenId = null;
    await loadTokens();
  }

  loadTokens();
```

- [ ] **Step 2: Add API Tokens section to template**

In the SettingsPage template, add a new card section after the existing content (before the closing `</div>` of the page):

```svelte
  <!-- API Tokens -->
  <Card title="API Tokens">
    <div class="section-content">
      <p class="section-desc">Tokens for automation, MCP, and API access. A token's scope cannot exceed your own role.</p>
      <Button onclick={() => { showNewTokenModal = true; tokenError = null; }}>New token</Button>
      {#if tokensLoaded}
        {#if apiTokens.length === 0}
          <p class="empty-hint">No tokens yet.</p>
        {:else}
          <table class="token-table">
            <thead>
              <tr><th>Name</th><th>Scope</th><th>Created</th><th>Last used</th><th></th></tr>
            </thead>
            <tbody>
              {#each apiTokens as t (t.id)}
                <tr>
                  <td>{t.name}</td>
                  <td><span class="role-badge">{t.role}</span></td>
                  <td>{t.created_at.slice(0, 10)}</td>
                  <td>{t.last_used_at ? t.last_used_at.slice(0, 10) : "—"}</td>
                  <td>
                    {#if confirmRevokeTokenId === t.id}
                      <Button variant="danger" onclick={() => revokeToken(t.id)}>Confirm revoke</Button>
                      <Button variant="secondary" onclick={() => { confirmRevokeTokenId = null; }}>Cancel</Button>
                    {:else}
                      <Button variant="secondary" onclick={() => { confirmRevokeTokenId = t.id; }}>Revoke</Button>
                    {/if}
                  </td>
                </tr>
              {/each}
            </tbody>
          </table>
        {/if}
      {/if}
    </div>
  </Card>

  {#if showNewTokenModal}
    <Modal title="New API Token" onclose={() => { showNewTokenModal = false; tokenError = null; }}>
      <div style="display:flex;flex-direction:column;gap:12px;padding:4px 0">
        <Input label="Token name" bind:value={newTokenName} placeholder="e.g. Home Assistant MCP" />
        <div style="display:flex;flex-direction:column;gap:6px">
          <label style="font-size:0.8rem;font-weight:600;color:var(--text-muted);text-transform:uppercase;letter-spacing:0.06em">Scope</label>
          <select bind:value={newTokenRole} style="background:var(--bg);border:1px solid var(--border);border-radius:6px;padding:8px 10px;color:var(--text);font-size:0.9rem">
            {#each roleOptions as r}
              <option value={r}>{r}</option>
            {/each}
          </select>
        </div>
        {#if tokenError}<div style="color:var(--danger);font-size:0.85rem">{tokenError}</div>{/if}
        <div style="display:flex;gap:8px;justify-content:flex-end;margin-top:8px">
          <Button variant="secondary" onclick={() => { showNewTokenModal = false; tokenError = null; }}>Cancel</Button>
          <Button onclick={createApiToken}>Create</Button>
        </div>
      </div>
    </Modal>
  {/if}

  {#if createdTokenSecret}
    <Modal title="Token Created" onclose={() => { createdTokenSecret = null; }}>
      <div style="display:flex;flex-direction:column;gap:12px;padding:4px 0">
        <p style="font-size:0.875rem;color:var(--text)">Copy this token now. It will not be shown again.</p>
        <div style="background:var(--bg);border:1px solid var(--border);border-radius:6px;padding:12px;font-family:var(--font-mono,monospace);font-size:0.8rem;word-break:break-all;color:var(--text)">{createdTokenSecret}</div>
        <Button onclick={() => navigator.clipboard.writeText(createdTokenSecret!)}>Copy to clipboard</Button>
        <Button variant="secondary" onclick={() => { createdTokenSecret = null; }}>Done</Button>
      </div>
    </Modal>
  {/if}
```

- [ ] **Step 3: Add token table styles to SettingsPage.svelte `<style>` block**

```css
  .token-table { width: 100%; border-collapse: collapse; margin-top: var(--space-2); font-size: 0.875rem; }
  .token-table th { text-align: left; padding: 6px 8px; color: var(--text-muted); font-weight: 600; font-size: 0.75rem; text-transform: uppercase; border-bottom: 1px solid var(--border); }
  .token-table td { padding: 8px 8px; border-bottom: 1px solid var(--border); color: var(--text); }
  .role-badge { background: var(--surface); border: 1px solid var(--border); border-radius: 4px; padding: 2px 6px; font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase; }
  .section-desc { font-size: 0.875rem; color: var(--text-muted); margin: 0 0 var(--space-2); }
  .empty-hint { font-size: 0.875rem; color: var(--text-faint); margin: var(--space-2) 0 0; }
```

- [ ] **Step 4: Update App.svelte to pass authStore to SettingsPage**

In App.svelte, find where SettingsPage is used and add the `authStore` prop:
```svelte
<SettingsPage store={settingsStore} {authStore} />
```

- [ ] **Step 5: Update test/SettingsPage.test.ts to include authStore in makeStore**

In `makeStore()`, add a mock authStore:

```typescript
function makeStore() {
  return {
    // ... existing fields ...
    consumableUnits: [],
    consumableCategories: [],
    updateConsumableUnits: vi.fn(),
    updateConsumableCategories: vi.fn(),
  };
}

function makeAuthStore(role: "admin" | "normal" | "ro" = "admin") {
  return {
    user: { id: "u1", username: "admin", role },
    checking: false,
    login: vi.fn(),
    logout: vi.fn(),
    changePassword: vi.fn(),
  };
}
```

Update the `mount(SettingsPage, ...)` calls to include `authStore: makeAuthStore()`:

```typescript
const app = mount(SettingsPage, {
  target,
  props: { store: makeStore(), authStore: makeAuthStore() },
});
```

- [ ] **Step 6: Add API Tokens tab tests to SettingsPage.test.ts**

```typescript
describe("SettingsPage — API Tokens", () => {
  let target: HTMLDivElement;
  let fetchMock: ReturnType<typeof vi.fn>;
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    target = document.createElement("div");
    document.body.appendChild(target);
    fetchMock = vi.fn().mockImplementation((url: string) => {
      if (url === "/api/auth/tokens") {
        return Promise.resolve({
          ok: true,
          json: async () => [
            { id: "t1", name: "MCP Server", role: "ro", owner_id: "u1",
              created_at: "2026-07-02T10:00:00+00:00", last_used_at: null },
          ],
        });
      }
      return Promise.resolve(new Response(null, { status: 200 }));
    });
    globalThis.fetch = fetchMock;
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    target.remove();
  });

  it("renders the API Tokens section", () => {
    const app = mount(SettingsPage, { target, props: { store: makeStore(), authStore: makeAuthStore() } });
    flushSync();
    expect(target.textContent).toContain("API Tokens");
    unmount(app);
  });

  it("shows token list after load", async () => {
    const app = mount(SettingsPage, { target, props: { store: makeStore(), authStore: makeAuthStore() } });
    flushSync();
    await new Promise((r) => setTimeout(r, 0));
    flushSync();
    expect(target.textContent).toContain("MCP Server");
    unmount(app);
  });

  it("opens New Token modal when button clicked", () => {
    const app = mount(SettingsPage, { target, props: { store: makeStore(), authStore: makeAuthStore() } });
    flushSync();
    const btn = [...target.querySelectorAll("button")].find((b) => b.textContent?.includes("New token"))!;
    btn.click();
    flushSync();
    expect(target.querySelector(".ui-modal")).not.toBeNull();
    expect(target.textContent).toContain("Token name");
    unmount(app);
  });

  it("calls POST /api/auth/tokens when Create is clicked", async () => {
    fetchMock = vi.fn().mockImplementation((url: string, opts?: RequestInit) => {
      if (url === "/api/auth/tokens" && opts?.method === "POST") {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            token: "abc123def456",
            info: { id: "t2", name: "Test", role: "ro", owner_id: "u1",
                    created_at: "2026-07-02T11:00:00+00:00", last_used_at: null },
          }),
        });
      }
      if (url === "/api/auth/tokens") {
        return Promise.resolve({ ok: true, json: async () => [] });
      }
      return Promise.resolve(new Response(null, { status: 200 }));
    });
    globalThis.fetch = fetchMock;
    const app = mount(SettingsPage, { target, props: { store: makeStore(), authStore: makeAuthStore() } });
    flushSync();
    const newBtn = [...target.querySelectorAll("button")].find((b) => b.textContent?.includes("New token"))!;
    newBtn.click();
    flushSync();
    const nameInput = target.querySelector("input") as HTMLInputElement;
    nameInput.value = "Test";
    nameInput.dispatchEvent(new Event("input"));
    flushSync();
    const createBtn = [...target.querySelectorAll("button")].find((b) => b.textContent?.trim() === "Create")!;
    createBtn.click();
    await new Promise((r) => setTimeout(r, 0));
    flushSync();
    const calls = fetchMock.mock.calls.filter(([url, opts]) => url === "/api/auth/tokens" && opts?.method === "POST");
    expect(calls.length).toBe(1);
    unmount(app);
  });
});
```

- [ ] **Step 7: Run tests**

```bash
cd packages/editor && npx vitest run test/SettingsPage.test.ts
```
Expected: all tests PASS

- [ ] **Step 8: Commit**

```bash
git add packages/editor/src/lib/components/SettingsPage.svelte \
        packages/editor/src/App.svelte \
        packages/editor/test/SettingsPage.test.ts
git commit -m "feat(auth): Settings API Tokens tab — create, list, revoke"
```

---

## Task 11: Settings — Users tab (admin only)

**Files:**
- Modify: `packages/editor/src/lib/components/SettingsPage.svelte`
- Modify: `packages/editor/test/SettingsPage.test.ts`

- [ ] **Step 1: Add user management state to SettingsPage.svelte script**

Add after the token state declarations:

```typescript
  // --- User management (admin only) ---
  interface UserInfo {
    id: string;
    username: string;
    role: string;
    created_at: string;
  }

  let users = $state<UserInfo[]>([]);
  let usersLoaded = $state(false);
  let showNewUserModal = $state(false);
  let newUserName = $state("");
  let newUserPassword = $state("");
  let newUserRole = $state<string>("normal");
  let userError = $state<string | null>(null);
  let editingUserId = $state<string | null>(null);
  let editUserRole = $state<string>("normal");
  let resetPasswordUserId = $state<string | null>(null);
  let resetPasswordValue = $state("");
  let confirmDeleteUserId = $state<string | null>(null);

  async function loadUsers(): Promise<void> {
    if (authStore.user?.role !== "admin") return;
    try {
      const resp = await fetch("/api/auth/users");
      if (!resp.ok) return;
      users = await resp.json();
    } finally {
      usersLoaded = true;
    }
  }

  async function createUser(): Promise<void> {
    if (!newUserName.trim()) { userError = "Username required"; return; }
    if (newUserPassword.length < 8) { userError = "Password must be at least 8 characters"; return; }
    userError = null;
    const resp = await fetch("/api/auth/users", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username: newUserName.trim(), password: newUserPassword, role: newUserRole }),
    });
    if (!resp.ok) {
      const d = await resp.json().catch(() => ({}));
      userError = d.detail ?? `Error ${resp.status}`;
      return;
    }
    showNewUserModal = false;
    newUserName = "";
    newUserPassword = "";
    newUserRole = "normal";
    await loadUsers();
  }

  async function updateUserRole(uid: string, role: string): Promise<void> {
    await fetch(`/api/auth/users/${uid}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ role }),
    });
    editingUserId = null;
    await loadUsers();
  }

  async function resetUserPassword(uid: string): Promise<void> {
    if (resetPasswordValue.length < 8) return;
    await fetch(`/api/auth/users/${uid}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ password: resetPasswordValue }),
    });
    resetPasswordUserId = null;
    resetPasswordValue = "";
  }

  async function deleteUser(uid: string): Promise<void> {
    await fetch(`/api/auth/users/${uid}`, { method: "DELETE" });
    confirmDeleteUserId = null;
    await loadUsers();
  }

  if (authStore.user?.role === "admin") loadUsers();
```

- [ ] **Step 2: Add Users section to template (after the API Tokens section)**

```svelte
  <!-- Users (admin only) -->
  {#if authStore.user?.role === "admin"}
    <Card title="Users">
      <div class="section-content">
        <Button onclick={() => { showNewUserModal = true; userError = null; }}>New user</Button>
        {#if usersLoaded}
          <table class="token-table" style="margin-top:var(--space-2)">
            <thead>
              <tr><th>Username</th><th>Role</th><th>Created</th><th>Actions</th></tr>
            </thead>
            <tbody>
              {#each users as u (u.id)}
                <tr>
                  <td>{u.username}</td>
                  <td>
                    {#if editingUserId === u.id}
                      <select
                        bind:value={editUserRole}
                        style="background:var(--bg);border:1px solid var(--border);border-radius:4px;padding:4px 8px;font-size:0.85rem;color:var(--text)"
                      >
                        {#each ["ro", "normal", "admin"] as r}
                          <option value={r}>{r}</option>
                        {/each}
                      </select>
                      <Button onclick={() => updateUserRole(u.id, editUserRole)}>Save</Button>
                      <Button variant="secondary" onclick={() => { editingUserId = null; }}>Cancel</Button>
                    {:else}
                      <span class="role-badge">{u.role}</span>
                    {/if}
                  </td>
                  <td>{u.created_at.slice(0, 10)}</td>
                  <td style="display:flex;gap:4px;flex-wrap:wrap">
                    {#if editingUserId !== u.id}
                      <Button variant="secondary" onclick={() => { editingUserId = u.id; editUserRole = u.role; }}>Edit role</Button>
                    {/if}
                    {#if resetPasswordUserId === u.id}
                      <input
                        type="password"
                        bind:value={resetPasswordValue}
                        placeholder="New password (min 8)"
                        style="background:var(--bg);border:1px solid var(--border);border-radius:4px;padding:4px 8px;font-size:0.85rem;color:var(--text)"
                      />
                      <Button onclick={() => resetUserPassword(u.id)}>Set</Button>
                      <Button variant="secondary" onclick={() => { resetPasswordUserId = null; resetPasswordValue = ""; }}>Cancel</Button>
                    {:else}
                      <Button variant="secondary" onclick={() => { resetPasswordUserId = u.id; }}>Reset pw</Button>
                    {/if}
                    {#if u.id !== authStore.user?.id}
                      {#if confirmDeleteUserId === u.id}
                        <Button variant="danger" onclick={() => deleteUser(u.id)}>Confirm delete</Button>
                        <Button variant="secondary" onclick={() => { confirmDeleteUserId = null; }}>Cancel</Button>
                      {:else}
                        <Button variant="secondary" onclick={() => { confirmDeleteUserId = u.id; }}>Delete</Button>
                      {/if}
                    {/if}
                  </td>
                </tr>
              {/each}
            </tbody>
          </table>
        {/if}
      </div>
    </Card>

    {#if showNewUserModal}
      <Modal title="New User" onclose={() => { showNewUserModal = false; userError = null; }}>
        <div style="display:flex;flex-direction:column;gap:12px;padding:4px 0">
          <Input label="Username" bind:value={newUserName} placeholder="username" />
          <Input label="Password (min 8 chars)" type="password" bind:value={newUserPassword} />
          <div style="display:flex;flex-direction:column;gap:6px">
            <label style="font-size:0.8rem;font-weight:600;color:var(--text-muted);text-transform:uppercase;letter-spacing:0.06em">Role</label>
            <select bind:value={newUserRole} style="background:var(--bg);border:1px solid var(--border);border-radius:6px;padding:8px 10px;color:var(--text);font-size:0.9rem">
              {#each ["ro", "normal", "admin"] as r}
                <option value={r}>{r}</option>
              {/each}
            </select>
          </div>
          {#if userError}<div style="color:var(--danger);font-size:0.85rem">{userError}</div>{/if}
          <div style="display:flex;gap:8px;justify-content:flex-end;margin-top:8px">
            <Button variant="secondary" onclick={() => { showNewUserModal = false; userError = null; }}>Cancel</Button>
            <Button onclick={createUser}>Create user</Button>
          </div>
        </div>
      </Modal>
    {/if}
  {/if}
```

- [ ] **Step 3: Add Users tab tests to SettingsPage.test.ts**

```typescript
describe("SettingsPage — Users tab (admin only)", () => {
  let target: HTMLDivElement;
  let fetchMock: ReturnType<typeof vi.fn>;
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    target = document.createElement("div");
    document.body.appendChild(target);
    fetchMock = vi.fn().mockImplementation((url: string) => {
      if (url === "/api/auth/tokens") return Promise.resolve({ ok: true, json: async () => [] });
      if (url === "/api/auth/users") {
        return Promise.resolve({
          ok: true,
          json: async () => [
            { id: "u1", username: "admin", role: "admin", created_at: "2026-01-01T00:00:00+00:00" },
            { id: "u2", username: "alice", role: "normal", created_at: "2026-01-02T00:00:00+00:00" },
          ],
        });
      }
      return Promise.resolve(new Response(null, { status: 200 }));
    });
    globalThis.fetch = fetchMock;
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    target.remove();
  });

  it("shows Users section for admin", async () => {
    const app = mount(SettingsPage, {
      target,
      props: { store: makeStore(), authStore: makeAuthStore("admin") },
    });
    flushSync();
    await new Promise((r) => setTimeout(r, 0));
    flushSync();
    expect(target.textContent).toContain("Users");
    expect(target.textContent).toContain("alice");
    unmount(app);
  });

  it("hides Users section for non-admin", () => {
    const app = mount(SettingsPage, {
      target,
      props: { store: makeStore(), authStore: makeAuthStore("normal") },
    });
    flushSync();
    // Users section title should not be visible in the card list for normal users
    const cards = [...target.querySelectorAll(".ui-card")].map((c) => c.textContent);
    expect(cards.some((t) => t?.includes("New user"))).toBe(false);
    unmount(app);
  });

  it("opens New User modal when button clicked", async () => {
    const app = mount(SettingsPage, {
      target,
      props: { store: makeStore(), authStore: makeAuthStore("admin") },
    });
    flushSync();
    await new Promise((r) => setTimeout(r, 0));
    flushSync();
    const btn = [...target.querySelectorAll("button")].find((b) => b.textContent?.includes("New user"))!;
    btn.click();
    flushSync();
    expect(target.querySelector(".ui-modal")).not.toBeNull();
    expect(target.textContent).toContain("Username");
    unmount(app);
  });

  it("calls POST /api/auth/users when Create user is clicked", async () => {
    fetchMock = vi.fn().mockImplementation((url: string, opts?: RequestInit) => {
      if (url === "/api/auth/tokens") return Promise.resolve({ ok: true, json: async () => [] });
      if (url === "/api/auth/users" && opts?.method === "POST") {
        return Promise.resolve({
          ok: true,
          json: async () => ({ id: "u3", username: "bob", role: "normal", created_at: "2026-07-02T00:00:00+00:00" }),
        });
      }
      if (url === "/api/auth/users") return Promise.resolve({ ok: true, json: async () => [] });
      return Promise.resolve(new Response(null, { status: 200 }));
    });
    globalThis.fetch = fetchMock;
    const app = mount(SettingsPage, {
      target,
      props: { store: makeStore(), authStore: makeAuthStore("admin") },
    });
    flushSync();
    const btn = [...target.querySelectorAll("button")].find((b) => b.textContent?.includes("New user"))!;
    btn.click();
    flushSync();
    const inputs = target.querySelectorAll(".ui-modal input");
    (inputs[0] as HTMLInputElement).value = "bob";
    inputs[0].dispatchEvent(new Event("input"));
    (inputs[1] as HTMLInputElement).value = "bobpassword1";
    inputs[1].dispatchEvent(new Event("input"));
    flushSync();
    const createBtn = [...target.querySelectorAll(".ui-modal button")].find(
      (b) => b.textContent?.includes("Create user"),
    )!;
    createBtn.click();
    await new Promise((r) => setTimeout(r, 0));
    flushSync();
    const postCalls = fetchMock.mock.calls.filter(([url, opts]) => url === "/api/auth/users" && opts?.method === "POST");
    expect(postCalls.length).toBe(1);
    unmount(app);
  });
});
```

- [ ] **Step 4: Run all SettingsPage tests**

```bash
cd packages/editor && npx vitest run test/SettingsPage.test.ts
```
Expected: all tests PASS

- [ ] **Step 5: Run full frontend test suite**

```bash
cd packages/editor && npx vitest run
```
Expected: all tests PASS

- [ ] **Step 6: Run full backend test suite**

```bash
cd packages/backend && python -m pytest tests/ -v
```
Expected: all tests PASS

- [ ] **Step 7: Commit**

```bash
git add packages/editor/src/lib/components/SettingsPage.svelte \
        packages/editor/test/SettingsPage.test.ts
git commit -m "feat(auth): Settings Users tab — create, edit role, reset password, delete"
```

---

## Final Verification

- [ ] **Run both full test suites**

```bash
cd packages/backend && python -m pytest tests/ -v
cd packages/editor && npx vitest run
```

Expected: all backend tests PASS, all frontend tests PASS.

- [ ] **Verify first-boot works**

```bash
cd packages/backend && DATA_DIR=/tmp/myhome-test-boot python -c "
from myhome.main import _first_boot
import os; os.environ['DATA_DIR']='/tmp/myhome-test-boot'
_first_boot()
"
```
Expected: prints `[myhome] First boot — admin password: <password>` and `/tmp/myhome-test-boot/users.json` exists.

- [ ] **Final commit if anything uncommitted**

```bash
git status
```
