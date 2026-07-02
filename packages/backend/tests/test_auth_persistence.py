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
