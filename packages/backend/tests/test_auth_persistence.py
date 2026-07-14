import pytest
from myhome.models_auth import ApiToken, OidcConfig, OidcConfigDocument, TokenDocument, User, UserDocument
from myhome.persistence_auth import load_oidc_config, load_tokens, load_users, save_oidc_config, save_tokens, save_users


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


def test_save_and_load_users_preserves_order(data_dir):
    doc = UserDocument(users=[
        User(id="u1", username="alice", role="admin", created_at="2026-01-01T00:00:00+00:00"),
        User(id="u2", username="bob", role="normal", created_at="2026-01-02T00:00:00+00:00"),
    ])
    save_users(doc)
    loaded = load_users()
    assert [u.username for u in loaded.users] == ["alice", "bob"]


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


