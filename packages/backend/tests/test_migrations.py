from sqlalchemy import create_engine, text

from myhome.migrations import CURRENT_VERSION, run_migrations


def test_run_migrations_adds_ha_user_id_to_pre_existing_users_table(tmp_path):
    # Simulate a DB created before this migration existed: build the users
    # table via raw SQL without the ha_user_id column, seed one row, and
    # stamp schema_version at 2 (the version immediately before this one).
    db_path = tmp_path / "legacy.db"
    engine = create_engine(f"sqlite:///{db_path}")
    with engine.begin() as conn:
        conn.execute(text(
            "CREATE TABLE users ("
            "id VARCHAR PRIMARY KEY, username VARCHAR NOT NULL, password_hash VARCHAR, "
            "role VARCHAR NOT NULL, created_at VARCHAR NOT NULL, auth_provider VARCHAR NOT NULL, "
            "oidc_sub VARCHAR, order_index INTEGER NOT NULL)"
        ))
        conn.execute(text(
            "INSERT INTO users (id, username, password_hash, role, created_at, auth_provider, oidc_sub, order_index) "
            "VALUES ('u1', 'alice', 'hash', 'admin', '2026-01-01T00:00:00+00:00', 'local', NULL, 0)"
        ))
        conn.execute(text("CREATE TABLE schema_version (version INTEGER NOT NULL)"))
        conn.execute(text("INSERT INTO schema_version (version) VALUES (2)"))

    run_migrations(engine)

    with engine.connect() as conn:
        version = conn.execute(text("SELECT version FROM schema_version")).scalar()
        row = conn.execute(text("SELECT id, username, ha_user_id FROM users WHERE id = 'u1'")).mappings().first()

    assert version == CURRENT_VERSION
    assert row["username"] == "alice"
    assert row["ha_user_id"] is None
