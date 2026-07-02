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
