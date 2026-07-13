# OIDC Account-Linking Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the privilege-escalation gap where an OIDC login can silently take over an existing local-only account (including admin) just by username collision, and stop trusting mutable/unverified claims for identity matching.

**Architecture:** Add a persisted `oidc_sub` (the IdP's stable, cryptographically-asserted subject identifier) to `User`. On callback, match returning OIDC users by `oidc_sub` first. Only fall back to username matching to link a *pre-existing OIDC-provisioned* account that predates this change (backfilling its `oidc_sub`); never auto-link to a `local`-provider account or to an oidc account already bound to a different `sub`. Also require the `sub` claim to be present (make it essential in ID-token validation) and stop trusting an `email`-derived username unless the IdP marked it `email_verified`.

**Tech Stack:** FastAPI, Pydantic, Authlib (`authlib.jose`), pytest + respx (existing patterns in `test_oidc.py` / `test_auth_oidc.py`).

---

### Task 1: Persist a stable `oidc_sub` on `User`

**Files:**
- Modify: `packages/backend/src/myhome/models_auth.py:6-12`
- Test: `packages/backend/tests/test_auth_persistence.py`

- [ ] **Step 1: Write the failing test**

Add to `packages/backend/tests/test_auth_persistence.py`:

```python
def test_save_and_load_users_roundtrip_preserves_oidc_sub(data_dir):
    doc = UserDocument(users=[
        User(id="u1", username="alice", password_hash=None, role="admin",
             created_at="2026-01-01T00:00:00+00:00", auth_provider="oidc", oidc_sub="idp-sub-123")
    ])
    save_users(doc)
    loaded = load_users()
    assert loaded.users[0].oidc_sub == "idp-sub-123"


def test_user_oidc_sub_defaults_to_none():
    user = User(id="u1", username="alice", role="normal", created_at="2026-01-01T00:00:00+00:00")
    assert user.oidc_sub is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/backend && python -m pytest tests/test_auth_persistence.py -v -k oidc_sub`
Expected: FAIL with `TypeError` / `AttributeError` — `oidc_sub` is not a recognized field yet (Pydantic will actually error because `User(..., oidc_sub=...)` passes an unknown kwarg — with default `model_config` this raises `ValidationError` for extra field, or the attribute access fails on the load side). Either way, both new tests fail.

- [ ] **Step 3: Add the field**

In `packages/backend/src/myhome/models_auth.py`, change:

```python
class User(BaseModel):
    id: str
    username: str
    password_hash: str | None = None
    role: str  # "admin" | "normal" | "ro"
    created_at: str  # ISO-8601
    auth_provider: str = "local"  # "local" | "oidc"
```

to:

```python
class User(BaseModel):
    id: str
    username: str
    password_hash: str | None = None
    role: str  # "admin" | "normal" | "ro"
    created_at: str  # ISO-8601
    auth_provider: str = "local"  # "local" | "oidc"
    oidc_sub: str | None = None  # IdP's stable subject identifier, set only for auth_provider="oidc"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd packages/backend && python -m pytest tests/test_auth_persistence.py -v -k oidc_sub`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add packages/backend/src/myhome/models_auth.py packages/backend/tests/test_auth_persistence.py
git commit -m "feat: persist stable oidc_sub on User"
```

---

### Task 2: Require `sub` claim and gate email-fallback on `email_verified`

**Files:**
- Modify: `packages/backend/src/myhome/oidc.py:81-107`
- Test: `packages/backend/tests/test_oidc.py`

- [ ] **Step 1: Write the failing tests**

In `packages/backend/tests/test_oidc.py`, replace the existing `test_extract_username_falls_back_to_email_local_part` test with:

```python
def test_extract_username_falls_back_to_verified_email_local_part():
    claims = {"email": "carol@example.test", "email_verified": True}
    assert oidc.extract_username(claims) == "carol"


def test_extract_username_rejects_unverified_email():
    claims = {"email": "carol@example.test", "email_verified": False}
    with pytest.raises(HTTPException):
        oidc.extract_username(claims)


def test_extract_username_rejects_email_without_verified_flag():
    claims = {"email": "carol@example.test"}
    with pytest.raises(HTTPException):
        oidc.extract_username(claims)
```

Add a new test near `test_exchange_code_for_claims_happy_path`:

```python
async def test_exchange_code_for_claims_rejects_missing_sub():
    private_pem, public_pem = _generate_rsa_keypair()
    kid = "test-key-1"
    config = OidcConfig(
        enabled=True, provider_name="TestIdP", issuer="https://idp.example.test",
        client_id="cid", client_secret="csecret", default_role="normal",
        scopes=["openid", "profile", "email"],
    )
    claims_in = {
        "iss": "https://idp.example.test", "aud": "cid",
        "exp": int(time.time()) + 3600, "nonce": "test-nonce-abc",
        "preferred_username": "alice",
    }  # no "sub" claim
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
                code="authcode123", code_verifier="verifier123", nonce="test-nonce-abc",
            )
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd packages/backend && python -m pytest tests/test_oidc.py -v`
Expected: the three `extract_username` tests fail (email fallback currently ignores `email_verified`), and `test_exchange_code_for_claims_rejects_missing_sub` fails because a missing `sub` is currently accepted.

- [ ] **Step 3: Implement**

In `packages/backend/src/myhome/oidc.py`, change the `claims_options` in `exchange_code_for_claims`:

```python
        claims = authlib_jwt.decode(
            id_token, jwks,
            claims_options={
                "iss": {"essential": True, "value": config.issuer},
                "aud": {"essential": True, "value": config.client_id},
                "exp": {"essential": True},
                "sub": {"essential": True},
            },
        )
```

And replace `extract_username`:

```python
def extract_username(claims: dict) -> str:
    username = claims.get("preferred_username")
    if username:
        return username
    if claims.get("email") and claims.get("email_verified"):
        return claims["email"].split("@")[0]
    raise HTTPException(400, "ID token has neither preferred_username nor a verified email claim")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd packages/backend && python -m pytest tests/test_oidc.py -v`
Expected: PASS. Also run `python -m pytest tests/test_auth_oidc.py -v` — `test_oidc_callback_creates_new_user_and_sets_session` includes both `preferred_username` and `email` in its claims so it's unaffected; confirm it still passes.

- [ ] **Step 5: Commit**

```bash
git add packages/backend/src/myhome/oidc.py packages/backend/tests/test_oidc.py
git commit -m "fix: require sub claim and verified email for OIDC identity extraction"
```

---

### Task 3: Match OIDC logins by stable `sub`, never auto-link to local accounts

**Files:**
- Modify: `packages/backend/src/myhome/routes/auth.py:402-411`
- Test: `packages/backend/tests/test_auth_oidc.py`

- [ ] **Step 1: Write the failing tests**

In `packages/backend/tests/test_auth_oidc.py`, replace `test_oidc_callback_links_existing_username` (it currently asserts the vulnerable auto-link-by-username-to-a-local-account behavior) with:

```python
def test_oidc_callback_rejects_conflicting_local_username(fresh):
    from datetime import datetime, timezone
    from myhome.models_auth import User, UserDocument
    save_users(UserDocument(users=[
        User(id="existing-1", username="alice", password_hash="somehash", role="admin",
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
    assert callback_resp.status_code == 307
    assert callback_resp.headers["location"] == "/?error=oidc_account_conflict"
    assert "myhome_access" not in callback_resp.cookies
    users = load_users().users
    assert len(users) == 1
    assert users[0].auth_provider == "local"  # untouched


def test_oidc_callback_relogin_matches_by_sub_even_if_username_changed(fresh):
    private_pem, public_pem = _generate_rsa_keypair()
    kid = "test-key-1"
    save_oidc_config(OidcConfig(
        enabled=True, provider_name="TestIdP", issuer="https://idp.example.test",
        client_id="cid", client_secret="csecret", default_role="normal",
        scopes=["openid", "profile", "email"],
    ))

    def _do_login(username: str, sub: str):
        with respx.mock:
            respx.get("https://idp.example.test/.well-known/openid-configuration").mock(
                return_value=httpx.Response(200, json=DISCOVERY)
            )
            login_resp = fresh.get("/api/auth/oidc/login", follow_redirects=False)
            qs = parse_qs(urlparse(login_resp.headers["location"]).query)
            state, nonce = qs["state"][0], qs["nonce"][0]
            claims_in = {
                "iss": "https://idp.example.test", "aud": "cid", "sub": sub,
                "exp": int(time.time()) + 3600, "nonce": nonce, "preferred_username": username,
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
            return fresh.get(
                "/api/auth/oidc/callback", params={"code": "authcode123", "state": state},
                follow_redirects=False,
            )

    first = _do_login("dave", "sub-abc")
    assert "myhome_access" in first.cookies
    second = _do_login("dave-renamed", "sub-abc")  # same sub, IdP-side username changed
    assert "myhome_access" in second.cookies

    users = load_users().users
    assert len(users) == 1  # re-login matched by sub, no duplicate created
    assert users[0].oidc_sub == "sub-abc"


def test_oidc_callback_backfills_legacy_oidc_user_missing_sub(fresh):
    from datetime import datetime, timezone
    from myhome.models_auth import User, UserDocument
    save_users(UserDocument(users=[
        User(id="legacy-1", username="erin", password_hash=None, role="normal",
             created_at=datetime.now(timezone.utc).isoformat(), auth_provider="oidc", oidc_sub=None),
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
            "iss": "https://idp.example.test", "aud": "cid", "sub": "sub-erin-1",
            "exp": int(time.time()) + 3600, "nonce": nonce, "preferred_username": "erin",
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
    assert len(users) == 1
    assert users[0].id == "legacy-1"
    assert users[0].oidc_sub == "sub-erin-1"  # backfilled
```

Also update `test_oidc_callback_creates_new_user_and_sets_session`'s final assertions to add:

```python
    assert created.oidc_sub == "sub-123"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd packages/backend && python -m pytest tests/test_auth_oidc.py -v`
Expected: the new/modified tests fail — current code links to any username match regardless of `auth_provider`, never sets `oidc_sub`, and doesn't recognize `oidc_account_conflict`.

- [ ] **Step 3: Implement**

In `packages/backend/src/myhome/routes/auth.py`, replace the matching block in `oidc_callback` (currently lines ~402-411):

```python
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
```

with:

```python
    sub = claims["sub"]
    doc = load_users()
    user = next((u for u in doc.users if u.auth_provider == "oidc" and u.oidc_sub == sub), None)
    if user is None:
        existing = next((u for u in doc.users if u.username.lower() == username.lower()), None)
        if existing is not None:
            if existing.auth_provider != "oidc" or existing.oidc_sub is not None:
                # Never silently take over a local account or one already bound to a
                # different subject; require explicit admin intervention to resolve.
                return RedirectResponse("/?error=oidc_account_conflict")
            existing.oidc_sub = sub  # legacy OIDC account predating oidc_sub tracking
            user = existing
        else:
            user = User(
                id=secrets.token_hex(8), username=username, password_hash=None,
                role=config.default_role, created_at=datetime.now(timezone.utc).isoformat(),
                auth_provider="oidc", oidc_sub=sub,
            )
            doc.users.append(user)
        save_users(doc)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd packages/backend && python -m pytest tests/test_auth_oidc.py -v`
Expected: PASS. Then run the full backend suite: `cd packages/backend && python -m pytest -q`
Expected: all tests pass (baseline was 400 passed before this plan; expect 400 + new tests, minus the 1 replaced test, net positive).

- [ ] **Step 5: Commit**

```bash
git add packages/backend/src/myhome/routes/auth.py packages/backend/tests/test_auth_oidc.py
git commit -m "fix: match OIDC logins by stable sub, never auto-link to local accounts"
```

---

### Task 4: Surface the account-conflict error distinctly in the login UI

**Files:**
- Modify: `packages/editor/src/lib/components/LoginPage.svelte:28-36`
- Test: `packages/editor/test/LoginPage.test.ts`

- [ ] **Step 1: Write the failing test**

In `packages/editor/test/LoginPage.test.ts`, inside the existing `describe("LoginPage — OIDC", ...)` block, add a sibling test right after `"shows a sign-in-failed banner when the URL has ?error=oidc_failed"`:

```typescript
  it("shows an account-conflict message for ?error=oidc_account_conflict", async () => {
    window.history.replaceState({}, "", "/?error=oidc_account_conflict");
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true, json: async () => ({ enabled: false, provider_name: "" }),
    });
    const app = mount(LoginPage, { target, props: { onlogin: vi.fn(), login: vi.fn() } });
    await new Promise((r) => setTimeout(r, 0));
    flushSync();
    expect(target.textContent).toContain("already exists");
    expect(window.location.search).toBe("");
    unmount(app);
  });
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/editor && npx vitest run test/LoginPage.test.ts`
Expected: FAIL — current `checkOidcError` only recognizes `oidc_failed` and ignores `oidc_account_conflict`, so no matching message is rendered and the query string isn't cleared.

- [ ] **Step 3: Implement**

In `packages/editor/src/lib/components/LoginPage.svelte`, replace `checkOidcError`:

```svelte
  function checkOidcError(): void {
    const params = new URLSearchParams(window.location.search);
    const errParam = params.get("error");
    if (errParam === "oidc_failed") {
      error = "Sign-in failed, please try again";
    } else if (errParam === "oidc_account_conflict") {
      error = "An account with this username already exists. Contact your administrator to link accounts.";
    } else {
      return;
    }
    params.delete("error");
    const query = params.toString();
    window.history.replaceState({}, "", window.location.pathname + (query ? `?${query}` : ""));
  }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd packages/editor && npx vitest run test/LoginPage.test.ts`
Expected: PASS. Then run the full frontend suite: `cd packages/editor && npx vitest run`
Expected: all tests pass (baseline was 462 passed before this plan).

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/lib/components/LoginPage.svelte packages/editor/test/LoginPage.test.ts
git commit -m "feat: distinct login message for OIDC account-linking conflicts"
```

---

### Task 5: Full-suite verification

- [ ] **Step 1:** Run `cd packages/backend && python -m pytest -q` — expect all green.
- [ ] **Step 2:** Run `cd packages/editor && npx vitest run` — expect all green.
- [ ] **Step 3:** Run `cd packages/editor && npx svelte-check` (or the project's existing typecheck command) and confirm no *new* errors versus the pre-existing baseline (there is a known pre-existing, unrelated typecheck debt in `SettingsPage.test.ts` — don't fix it here, just confirm nothing new was introduced in the files this plan touches).

---

## Out of scope (explicitly, per user discussion)

- The MEDIUM finding "OIDC-only users can set their first local password without extra verification" (`change_password` skipping the current-password check when `password_hash is None`) is **not** being changed: `change_password` already requires an authenticated session for that exact `user_id` via `require_auth`, so there is no cross-user path — a user setting their own first local password is expected, intended behavior, not a privilege escalation.
- No self-service "link my account" UI flow, no multi-provider support, no claim/role mapping — unchanged from the original OIDC design spec's stated out-of-scope list.
