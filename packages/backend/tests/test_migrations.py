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
    # In real use, metadata.create_all() runs before run_migrations() on
    # every startup (see db.py), so by the time ANY migration runs against
    # a real database, every table currently in schema.py already exists
    # (empty, if it's new since that database was last upgraded). This
    # helper is shared by every migration test to keep that guarantee true
    # here too -- a table added for a later migration (e.g. contact_types,
    # added for migration 5) must still exist for a DB whose schema_version
    # sits at an earlier migration, or that later migration blows up
    # against these hand-built "legacy" snapshots even though it would
    # never see a missing table in production.
    conn.execute(text(
        "CREATE TABLE IF NOT EXISTS homes ("
        "id VARCHAR PRIMARY KEY, name VARCHAR, type VARCHAR, created_at VARCHAR)"
    ))
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
    conn.execute(text(
        "CREATE TABLE cost_entries (id VARCHAR PRIMARY KEY, home_id VARCHAR NOT NULL, "
        "order_index INTEGER NOT NULL, category_id VARCHAR NOT NULL, date VARCHAR NOT NULL, "
        "total_amount FLOAT NOT NULL, quantity FLOAT, unit_price FLOAT, supplier_id VARCHAR, "
        "notes VARCHAR NOT NULL, room_id VARCHAR, attachments TEXT NOT NULL)"
    ))
    conn.execute(text(
        "CREATE TABLE works (id VARCHAR PRIMARY KEY, home_id VARCHAR NOT NULL, "
        "order_index INTEGER NOT NULL, title VARCHAR NOT NULL, description VARCHAR NOT NULL, "
        "status VARCHAR NOT NULL, category_id VARCHAR, date VARCHAR NOT NULL, total_cost FLOAT, "
        "supplier_id VARCHAR, notes VARCHAR NOT NULL, attachments TEXT NOT NULL, "
        "placement_floor_id VARCHAR, placement_x FLOAT, placement_y FLOAT)"
    ))
    conn.execute(text(
        "CREATE TABLE contact_types (id VARCHAR NOT NULL, home_id VARCHAR NOT NULL, "
        "order_index INTEGER NOT NULL, name VARCHAR NOT NULL, PRIMARY KEY (id, home_id))"
    ))


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


def test_run_migrations_absorbs_suppliers_into_contacts(tmp_path):
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
            "INSERT INTO cost_entries (id, home_id, order_index, category_id, date, total_amount, "
            "supplier_id, notes, attachments) VALUES "
            "('c1', 'h1', 0, 'cat-fuel', '2026-01-01', 100.0, 'sup-1', '', '[]')"
        ))
        conn.execute(text(
            "INSERT INTO works (id, home_id, order_index, title, description, status, date, "
            "supplier_id, notes, attachments) VALUES "
            "('w1', 'h1', 0, 'Roof repair', '', 'done', '2026-01-01', 'sup-1', '', '[]')"
        ))
        conn.execute(text("CREATE TABLE schema_version (version INTEGER NOT NULL)"))
        conn.execute(text("INSERT INTO schema_version (version) VALUES (4)"))

    run_migrations(engine)

    with engine.connect() as conn:
        version = conn.execute(text("SELECT version FROM schema_version")).scalar()
        cost_row = conn.execute(text("SELECT contact_id FROM cost_entries WHERE id = 'c1'")).mappings().first()
        work_row = conn.execute(text("SELECT contact_id FROM works WHERE id = 'w1'")).mappings().first()
        supplier_table_exists = conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name='suppliers'")
        ).first()
        h1_types = conn.execute(
            text("SELECT id, name FROM contact_types WHERE home_id = 'h1' ORDER BY order_index")
        ).mappings().all()
        h2_types = conn.execute(
            text("SELECT id, name FROM contact_types WHERE home_id = 'h2' ORDER BY order_index")
        ).mappings().all()

    assert version == CURRENT_VERSION
    assert cost_row["contact_id"] == "sup-1"
    assert work_row["contact_id"] == "sup-1"
    assert supplier_table_exists is None
    assert [t["id"] for t in h1_types] == [
        "ctype-contractor", "ctype-supplier", "ctype-service", "ctype-agent", "ctype-notary", "ctype-other",
    ]
    assert h1_types[0]["name"] == "Contractor"
    assert len(h2_types) == 6
