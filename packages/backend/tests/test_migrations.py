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
        # A real pre-v4 database already has these tables (they predate the
        # ha_user_id migration) -- create them empty so migration 4's
        # rename/recreate dance has something realistic to operate on.
        _create_legacy_category_tables(conn)

    run_migrations(engine)

    with engine.connect() as conn:
        version = conn.execute(text("SELECT version FROM schema_version")).scalar()
        row = conn.execute(text("SELECT id, username, ha_user_id FROM users WHERE id = 'u1'")).mappings().first()

    assert version == CURRENT_VERSION
    assert row["username"] == "alice"
    assert row["ha_user_id"] is None


def _create_legacy_category_tables(conn) -> None:
    conn.execute(text(
        "CREATE TABLE cost_categories ("
        "id VARCHAR PRIMARY KEY, home_id VARCHAR NOT NULL, order_index INTEGER NOT NULL, "
        "name VARCHAR NOT NULL, emoji VARCHAR NOT NULL, unit VARCHAR, color VARCHAR NOT NULL, "
        "placement_floor_id VARCHAR, placement_x FLOAT, placement_y FLOAT)"
    ))
    for other_table, cols in [
        ("inventory_categories", "id VARCHAR PRIMARY KEY, home_id VARCHAR NOT NULL, order_index INTEGER NOT NULL, name VARCHAR NOT NULL"),
        ("work_categories", "id VARCHAR PRIMARY KEY, home_id VARCHAR NOT NULL, order_index INTEGER NOT NULL, name VARCHAR NOT NULL, emoji VARCHAR NOT NULL"),
        ("suppliers", "id VARCHAR PRIMARY KEY, home_id VARCHAR NOT NULL, order_index INTEGER NOT NULL, name VARCHAR NOT NULL"),
        ("consumable_categories", "id VARCHAR PRIMARY KEY, home_id VARCHAR NOT NULL, order_index INTEGER NOT NULL, name VARCHAR NOT NULL, emoji VARCHAR NOT NULL"),
    ]:
        conn.execute(text(f"CREATE TABLE {other_table} ({cols})"))


def test_run_migrations_scopes_cost_categories_by_home(tmp_path):
    # Simulate a DB created before this migration: cost_categories with a
    # bare `id` primary key (the original, buggy shape), seeded with the
    # same fixed category id for two different homes -- which the old
    # schema could never have actually allowed to coexist, since the first
    # INSERT of the second home's row would have violated the old
    # single-column UNIQUE/PRIMARY KEY constraint. We seed only one row
    # here (as the old schema forces), then confirm the migrated table
    # accepts a second home's row with the same id afterward.
    db_path = tmp_path / "legacy.db"
    engine = create_engine(f"sqlite:///{db_path}")
    with engine.begin() as conn:
        conn.execute(text(
            "CREATE TABLE homes (id VARCHAR PRIMARY KEY, name VARCHAR, type VARCHAR, created_at VARCHAR)"
        ))
        conn.execute(text("INSERT INTO homes (id, name, type, created_at) VALUES ('h1', 'Home 1', 'existing', '2026-01-01')"))
        conn.execute(text("INSERT INTO homes (id, name, type, created_at) VALUES ('h2', 'Home 2', 'existing', '2026-01-01')"))
        _create_legacy_category_tables(conn)
        conn.execute(text(
            "INSERT INTO cost_categories (id, home_id, order_index, name, emoji, color) "
            "VALUES ('cat-fuel', 'h1', 0, 'Fuel', '🛢', '#4466cc')"
        ))
        conn.execute(text("CREATE TABLE schema_version (version INTEGER NOT NULL)"))
        conn.execute(text("INSERT INTO schema_version (version) VALUES (3)"))

    run_migrations(engine)

    # After migration, the same fixed id can now be inserted for a second home.
    with engine.begin() as conn:
        conn.execute(text(
            "INSERT INTO cost_categories (id, home_id, order_index, name, emoji, color) "
            "VALUES ('cat-fuel', 'h2', 0, 'Fuel', '🛢', '#4466cc')"
        ))

    with engine.connect() as conn:
        version = conn.execute(text("SELECT version FROM schema_version")).scalar()
        rows = conn.execute(text("SELECT id, home_id, name FROM cost_categories ORDER BY home_id")).mappings().all()

    assert version == CURRENT_VERSION
    assert [dict(r) for r in rows] == [
        {"id": "cat-fuel", "home_id": "h1", "name": "Fuel"},
        {"id": "cat-fuel", "home_id": "h2", "name": "Fuel"},
    ]
