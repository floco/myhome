from datetime import timedelta

import pytest

from myhome.attachment_tokens import (
    InvalidTokenError,
    consume_token,
    mint_download_token,
    mint_upload_token,
)


def test_mint_upload_token_is_consumable_once():
    token, expires_at = mint_upload_token("home1", "kb", "entry1", "photo.jpg")
    scope = consume_token(token, "upload")
    assert scope.home_id == "home1"
    assert scope.module == "kb"
    assert scope.item_id == "entry1"
    assert scope.filename == "photo.jpg"
    assert scope.expires_at == expires_at

    with pytest.raises(InvalidTokenError):
        consume_token(token, "upload")


def test_mint_download_token_is_consumable_once():
    token, _expires_at = mint_download_token("home1", "inventory", "item1", "manual.pdf")
    scope = consume_token(token, "download")
    assert scope.filename == "manual.pdf"

    with pytest.raises(InvalidTokenError):
        consume_token(token, "download")


def test_consume_wrong_kind_raises():
    token, _ = mint_upload_token("home1", "kb", "entry1", "photo.jpg")
    with pytest.raises(InvalidTokenError):
        consume_token(token, "download")


def test_consume_unknown_token_raises():
    with pytest.raises(InvalidTokenError):
        consume_token("not-a-real-token", "upload")


def test_consume_expired_token_raises(monkeypatch):
    import myhome.attachment_tokens as tokens_module

    monkeypatch.setattr(tokens_module, "TOKEN_TTL", timedelta(seconds=-1))
    token, _ = mint_upload_token("home1", "kb", "entry1", "photo.jpg")
    with pytest.raises(InvalidTokenError, match="expired"):
        consume_token(token, "upload")
