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
    # insurance_categories is also a brand-new table (added alongside migration
    # 6) -- like contact_types, give it the composite (id, home_id) PK from
    # schema.py directly rather than the bare-id shape the pre-migration-4
    # tables above use, since it never existed in that older, buggy shape.
    conn.execute(text(
        "CREATE TABLE insurance_categories (id VARCHAR NOT NULL, home_id VARCHAR NOT NULL, "
        "order_index INTEGER NOT NULL, name VARCHAR NOT NULL, emoji VARCHAR NOT NULL, PRIMARY KEY (id, home_id))"
    ))
    # inventory_items pre-dates migration 7 (which adds category_id/owner_id/
    # store_id and backfills category_id from this legacy `category` column),
    # so every migration test's snapshot needs it in this old shape too.
    conn.execute(text(
        "CREATE TABLE inventory_items (id VARCHAR PRIMARY KEY, home_id VARCHAR NOT NULL, "
        "order_index INTEGER NOT NULL, name VARCHAR NOT NULL, emoji VARCHAR NOT NULL, "
        "category VARCHAR NOT NULL, brand VARCHAR, model VARCHAR, serial_number VARCHAR, "
        "purchase_date VARCHAR, purchase_price FLOAT, warranty_expiry_date VARCHAR, "
        "notes VARCHAR NOT NULL, attachments TEXT NOT NULL, placement_floor_id VARCHAR, "
        "placement_room_id VARCHAR, placement_x FLOAT, placement_y FLOAT)"
    ))
    # chore_assignments pre-dates migration 8 (which adds the label column),
    # so every migration test's snapshot needs it in this old shape too.
    conn.execute(text(
        "CREATE TABLE chore_assignments (id VARCHAR PRIMARY KEY, home_id VARCHAR NOT NULL, "
        "order_index INTEGER NOT NULL, chore_id VARCHAR NOT NULL, room_id VARCHAR, "
        "position_x FLOAT, position_y FLOAT, next_due_date VARCHAR NOT NULL)"
    ))
    # locations pre-dates migration 10 (which adds notes/attachments), so
    # every migration test's snapshot needs it in this old shape too.
    conn.execute(text(
        "CREATE TABLE locations (id VARCHAR PRIMARY KEY, home_id VARCHAR NOT NULL, "
        "order_index INTEGER NOT NULL, name VARCHAR NOT NULL, emoji VARCHAR NOT NULL)"
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
        # Scoped to 'cat-fuel' -- migration 6 also backfills an unrelated
        # 'cat-insurance' row per home, which is exercised separately by
        # test_run_migrations_adds_insurance_support.
        rows = conn.execute(
            text("SELECT id, home_id, name FROM cost_categories WHERE id = 'cat-fuel' ORDER BY home_id")
        ).mappings().all()

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
        # This test stamps schema_version=4, i.e. migration 4 (which gives
        # cost_categories a composite (id, home_id) PK) is assumed already
        # applied -- but _create_legacy_category_tables always builds the
        # pre-migration-4 bare-id shape. Recreate it in the post-migration-4
        # shape so migration 6's later per-home cost_categories backfill
        # (unrelated to this test's supplier-absorption focus) doesn't
        # collide across homes on a uniqueness constraint that would never
        # exist in a real database already at version 4.
        conn.execute(text("DROP TABLE cost_categories"))
        conn.execute(text(
            "CREATE TABLE cost_categories (id VARCHAR NOT NULL, home_id VARCHAR NOT NULL, "
            "order_index INTEGER NOT NULL, name VARCHAR NOT NULL, emoji VARCHAR NOT NULL, "
            "unit VARCHAR, color VARCHAR NOT NULL, placement_floor_id VARCHAR, placement_x FLOAT, "
            "placement_y FLOAT, PRIMARY KEY (id, home_id))"
        ))
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


def test_run_migrations_adds_insurance_support(tmp_path):
    db_path = tmp_path / "legacy.db"
    engine = create_engine(f"sqlite:///{db_path}")
    with engine.begin() as conn:
        conn.execute(text(
            "CREATE TABLE homes (id VARCHAR PRIMARY KEY, name VARCHAR, type VARCHAR, created_at VARCHAR)"
        ))
        conn.execute(text("INSERT INTO homes (id, name, type, created_at) VALUES ('h1', 'Home 1', 'existing', '2026-01-01')"))
        conn.execute(text("INSERT INTO homes (id, name, type, created_at) VALUES ('h2', 'Home 2', 'existing', '2026-01-01')"))
        # Build a post-migration-5 snapshot directly (composite-PK cost_categories,
        # contact_id already renamed on cost_entries) rather than reusing
        # _create_legacy_category_tables, which builds a pre-migration-4 snapshot.
        conn.execute(text(
            "CREATE TABLE cost_categories (id VARCHAR NOT NULL, home_id VARCHAR NOT NULL, "
            "order_index INTEGER NOT NULL, name VARCHAR NOT NULL, emoji VARCHAR NOT NULL, "
            "unit VARCHAR, color VARCHAR NOT NULL, placement_floor_id VARCHAR, placement_x FLOAT, "
            "placement_y FLOAT, PRIMARY KEY (id, home_id))"
        ))
        conn.execute(text(
            "CREATE TABLE insurance_categories (id VARCHAR NOT NULL, home_id VARCHAR NOT NULL, "
            "order_index INTEGER NOT NULL, name VARCHAR NOT NULL, emoji VARCHAR NOT NULL, PRIMARY KEY (id, home_id))"
        ))
        # inventory_categories/inventory_items are needed too since this
        # snapshot now also runs migration 7 (_add_inventory_owner_store_and_category_id)
        # on its way to CURRENT_VERSION.
        conn.execute(text(
            "CREATE TABLE inventory_categories (id VARCHAR NOT NULL, home_id VARCHAR NOT NULL, "
            "order_index INTEGER NOT NULL, name VARCHAR NOT NULL, PRIMARY KEY (id, home_id))"
        ))
        conn.execute(text(
            "CREATE TABLE inventory_items (id VARCHAR PRIMARY KEY, home_id VARCHAR NOT NULL, "
            "order_index INTEGER NOT NULL, name VARCHAR NOT NULL, emoji VARCHAR NOT NULL, "
            "category VARCHAR NOT NULL, brand VARCHAR, model VARCHAR, serial_number VARCHAR, "
            "purchase_date VARCHAR, purchase_price FLOAT, warranty_expiry_date VARCHAR, "
            "notes VARCHAR NOT NULL, attachments TEXT NOT NULL, placement_floor_id VARCHAR, "
            "placement_room_id VARCHAR, placement_x FLOAT, placement_y FLOAT)"
        ))
        # cost_entries already has contact_id (post-migration-5 shape) but not
        # the new source_module/source_id columns yet.
        conn.execute(text(
            "CREATE TABLE cost_entries (id VARCHAR PRIMARY KEY, home_id VARCHAR NOT NULL, "
            "order_index INTEGER NOT NULL, category_id VARCHAR NOT NULL, date VARCHAR NOT NULL, "
            "total_amount FLOAT NOT NULL, quantity FLOAT, unit_price FLOAT, contact_id VARCHAR, "
            "notes VARCHAR NOT NULL, room_id VARCHAR, attachments TEXT NOT NULL)"
        ))
        conn.execute(text(
            "INSERT INTO cost_entries (id, home_id, order_index, category_id, date, total_amount, notes, attachments) "
            "VALUES ('c1', 'h1', 0, 'cat-fuel', '2026-01-01', 100.0, '', '[]')"
        ))
        # chore_assignments is needed too since this snapshot now also runs
        # migration 8 (_add_assignment_label_column) on its way to CURRENT_VERSION.
        conn.execute(text(
            "CREATE TABLE chore_assignments (id VARCHAR PRIMARY KEY, home_id VARCHAR NOT NULL, "
            "order_index INTEGER NOT NULL, chore_id VARCHAR NOT NULL, room_id VARCHAR, "
            "position_x FLOAT, position_y FLOAT, next_due_date VARCHAR NOT NULL)"
        ))
        # locations is needed too since this snapshot now also runs
        # migration 10 (_add_locations_notes_and_attachments) on its way to
        # CURRENT_VERSION.
        conn.execute(text(
            "CREATE TABLE locations (id VARCHAR PRIMARY KEY, home_id VARCHAR NOT NULL, "
            "order_index INTEGER NOT NULL, name VARCHAR NOT NULL, emoji VARCHAR NOT NULL)"
        ))
        conn.execute(text(
            "INSERT INTO cost_categories (id, home_id, order_index, name, emoji, color) "
            "VALUES ('cat-fuel', 'h1', 0, 'Fuel', '🛢', '#4466cc')"
        ))
        conn.execute(text("CREATE TABLE schema_version (version INTEGER NOT NULL)"))
        conn.execute(text("INSERT INTO schema_version (version) VALUES (5)"))

    run_migrations(engine)

    with engine.connect() as conn:
        version = conn.execute(text("SELECT version FROM schema_version")).scalar()
        cost_row = conn.execute(text("SELECT source_module, source_id FROM cost_entries WHERE id = 'c1'")).mappings().first()
        h1_insurance_cats = conn.execute(
            text("SELECT id, name, emoji FROM insurance_categories WHERE home_id = 'h1' ORDER BY order_index")
        ).mappings().all()
        h2_insurance_cats = conn.execute(
            text("SELECT id FROM insurance_categories WHERE home_id = 'h2'")
        ).mappings().all()
        h1_cost_cats = conn.execute(
            text("SELECT id, name FROM cost_categories WHERE home_id = 'h1' ORDER BY order_index")
        ).mappings().all()

    assert version == CURRENT_VERSION
    assert cost_row["source_module"] is None
    assert cost_row["source_id"] is None
    assert [c["id"] for c in h1_insurance_cats] == [
        "icat-home", "icat-auto", "icat-health", "icat-life", "icat-travel", "icat-liability",
    ]
    assert h1_insurance_cats[0]["name"] == "Home"
    assert h1_insurance_cats[0]["emoji"] == "🏠"
    assert len(h2_insurance_cats) == 6
    assert [c["id"] for c in h1_cost_cats] == ["cat-fuel", "cat-insurance"]


def test_run_migrations_backfills_inventory_category_id(tmp_path):
    db_path = tmp_path / "legacy.db"
    engine = create_engine(f"sqlite:///{db_path}")
    with engine.begin() as conn:
        conn.execute(text(
            "CREATE TABLE homes (id VARCHAR PRIMARY KEY, name VARCHAR, type VARCHAR, created_at VARCHAR)"
        ))
        conn.execute(text("INSERT INTO homes (id, name, type, created_at) VALUES ('h1', 'Home 1', 'existing', '2026-01-01')"))
        conn.execute(text(
            "CREATE TABLE inventory_categories (id VARCHAR NOT NULL, home_id VARCHAR NOT NULL, "
            "order_index INTEGER NOT NULL, name VARCHAR NOT NULL, PRIMARY KEY (id, home_id))"
        ))
        conn.execute(text(
            "INSERT INTO inventory_categories (id, home_id, order_index, name) VALUES ('inv-electronics', 'h1', 0, 'Electronics')"
        ))
        conn.execute(text(
            "CREATE TABLE inventory_items (id VARCHAR PRIMARY KEY, home_id VARCHAR NOT NULL, "
            "order_index INTEGER NOT NULL, name VARCHAR NOT NULL, emoji VARCHAR NOT NULL, "
            "category VARCHAR NOT NULL, brand VARCHAR, model VARCHAR, serial_number VARCHAR, "
            "purchase_date VARCHAR, purchase_price FLOAT, warranty_expiry_date VARCHAR, "
            "notes VARCHAR NOT NULL, attachments TEXT NOT NULL, placement_floor_id VARCHAR, "
            "placement_room_id VARCHAR, placement_x FLOAT, placement_y FLOAT)"
        ))
        conn.execute(text(
            "INSERT INTO inventory_items (id, home_id, order_index, name, emoji, category, notes, attachments) "
            "VALUES ('i1', 'h1', 0, 'TV', '📺', 'Electronics', '', '[]')"
        ))
        conn.execute(text(
            "INSERT INTO inventory_items (id, home_id, order_index, name, emoji, category, notes, attachments) "
            "VALUES ('i2', 'h1', 1, 'Drill', '🔩', 'Tools', '', '[]')"
        ))
        conn.execute(text(
            "INSERT INTO inventory_items (id, home_id, order_index, name, emoji, category, notes, attachments) "
            "VALUES ('i3', 'h1', 2, 'Misc', '📦', '', '', '[]')"
        ))
        # chore_assignments is needed too since this snapshot now also runs
        # migration 8 (_add_assignment_label_column) on its way to CURRENT_VERSION.
        conn.execute(text(
            "CREATE TABLE chore_assignments (id VARCHAR PRIMARY KEY, home_id VARCHAR NOT NULL, "
            "order_index INTEGER NOT NULL, chore_id VARCHAR NOT NULL, room_id VARCHAR, "
            "position_x FLOAT, position_y FLOAT, next_due_date VARCHAR NOT NULL)"
        ))
        # locations is needed too since this snapshot now also runs
        # migration 10 (_add_locations_notes_and_attachments) on its way to
        # CURRENT_VERSION.
        conn.execute(text(
            "CREATE TABLE locations (id VARCHAR PRIMARY KEY, home_id VARCHAR NOT NULL, "
            "order_index INTEGER NOT NULL, name VARCHAR NOT NULL, emoji VARCHAR NOT NULL)"
        ))
        conn.execute(text("CREATE TABLE schema_version (version INTEGER NOT NULL)"))
        conn.execute(text("INSERT INTO schema_version (version) VALUES (6)"))

    run_migrations(engine)

    with engine.connect() as conn:
        version = conn.execute(text("SELECT version FROM schema_version")).scalar()
        cats = conn.execute(
            text("SELECT id, name FROM inventory_categories WHERE home_id = 'h1' ORDER BY order_index")
        ).mappings().all()
        items = conn.execute(
            text("SELECT id, category_id, owner_id, store_id FROM inventory_items WHERE home_id = 'h1' ORDER BY order_index")
        ).mappings().all()

    assert version == CURRENT_VERSION
    assert [c["name"] for c in cats] == ["Electronics", "Tools"]
    tools_id = next(c["id"] for c in cats if c["name"] == "Tools")
    assert items[0]["category_id"] == "inv-electronics"
    assert items[1]["category_id"] == tools_id
    assert items[2]["category_id"] is None
    assert items[0]["owner_id"] is None
    assert items[0]["store_id"] is None


def test_run_migrations_adds_label_to_pre_existing_chore_assignments_table(tmp_path):
    db_path = tmp_path / "legacy.db"
    engine = create_engine(f"sqlite:///{db_path}")
    with engine.begin() as conn:
        conn.execute(text(
            "CREATE TABLE chore_assignments ("
            "id VARCHAR PRIMARY KEY, home_id VARCHAR NOT NULL, order_index INTEGER NOT NULL, "
            "chore_id VARCHAR NOT NULL, room_id VARCHAR, position_x FLOAT, position_y FLOAT, "
            "next_due_date VARCHAR NOT NULL)"
        ))
        conn.execute(text(
            "INSERT INTO chore_assignments (id, home_id, order_index, chore_id, room_id, position_x, position_y, next_due_date) "
            "VALUES ('a1', 'h1', 0, 'c1', 'r1', NULL, NULL, '2027-01-01T00:00:00Z')"
        ))
        # inventory_items is needed too since this snapshot (schema_version 7)
        # now also runs migration 9 (_drop_inventory_legacy_category_column)
        # on its way to CURRENT_VERSION -- already in the post-migration-7
        # shape (category_id/owner_id/store_id present, legacy `category`
        # column still lingering) since migration 7 is behind this snapshot.
        conn.execute(text(
            "CREATE TABLE inventory_items (id VARCHAR PRIMARY KEY, home_id VARCHAR NOT NULL, "
            "order_index INTEGER NOT NULL, name VARCHAR NOT NULL, emoji VARCHAR NOT NULL, "
            "category VARCHAR NOT NULL, category_id VARCHAR, owner_id VARCHAR, store_id VARCHAR, "
            "brand VARCHAR, model VARCHAR, serial_number VARCHAR, "
            "purchase_date VARCHAR, purchase_price FLOAT, warranty_expiry_date VARCHAR, "
            "notes VARCHAR NOT NULL, attachments TEXT NOT NULL, placement_floor_id VARCHAR, "
            "placement_room_id VARCHAR, placement_x FLOAT, placement_y FLOAT)"
        ))
        # locations is needed too since this snapshot now also runs
        # migration 10 (_add_locations_notes_and_attachments) on its way to
        # CURRENT_VERSION.
        conn.execute(text(
            "CREATE TABLE locations (id VARCHAR PRIMARY KEY, home_id VARCHAR NOT NULL, "
            "order_index INTEGER NOT NULL, name VARCHAR NOT NULL, emoji VARCHAR NOT NULL)"
        ))
        conn.execute(text("CREATE TABLE schema_version (version INTEGER NOT NULL)"))
        conn.execute(text("INSERT INTO schema_version (version) VALUES (7)"))

    run_migrations(engine)

    with engine.connect() as conn:
        version = conn.execute(text("SELECT version FROM schema_version")).scalar()
        row = conn.execute(text("SELECT id, label FROM chore_assignments WHERE id = 'a1'")).mappings().first()

    assert version == CURRENT_VERSION
    assert row["label"] is None


def test_run_migrations_drops_inventory_legacy_category_column(tmp_path):
    # Reproduces the production bug: a database that already ran migration 7
    # (has category_id/owner_id/store_id, but still carries the old NOT NULL
    # `category` column migration 7 backfilled from and never dropped) fails
    # every subsequent inventory save, because save_inventory()'s INSERT --
    # built from schema.py's Table, which has no `category` column -- never
    # supplies a value for that still-NOT-NULL column.
    db_path = tmp_path / "legacy.db"
    engine = create_engine(f"sqlite:///{db_path}")
    with engine.begin() as conn:
        conn.execute(text(
            "CREATE TABLE inventory_items (id VARCHAR PRIMARY KEY, home_id VARCHAR NOT NULL, "
            "order_index INTEGER NOT NULL, name VARCHAR NOT NULL, emoji VARCHAR NOT NULL, "
            "category VARCHAR NOT NULL, category_id VARCHAR, owner_id VARCHAR, store_id VARCHAR, "
            "brand VARCHAR, model VARCHAR, serial_number VARCHAR, "
            "purchase_date VARCHAR, purchase_price FLOAT, warranty_expiry_date VARCHAR, "
            "notes VARCHAR NOT NULL, attachments TEXT NOT NULL, placement_floor_id VARCHAR, "
            "placement_room_id VARCHAR, placement_x FLOAT, placement_y FLOAT)"
        ))
        conn.execute(text(
            "INSERT INTO inventory_items "
            "(id, home_id, order_index, name, emoji, category, category_id, notes, attachments) "
            "VALUES ('i1', 'h1', 0, 'TV', '📺', 'Electronics', 'inv-electronics', '', '[]')"
        ))
        # locations is needed too since this snapshot now also runs
        # migration 10 (_add_locations_notes_and_attachments) on its way to
        # CURRENT_VERSION.
        conn.execute(text(
            "CREATE TABLE locations (id VARCHAR PRIMARY KEY, home_id VARCHAR NOT NULL, "
            "order_index INTEGER NOT NULL, name VARCHAR NOT NULL, emoji VARCHAR NOT NULL)"
        ))
        conn.execute(text("CREATE TABLE schema_version (version INTEGER NOT NULL)"))
        conn.execute(text("INSERT INTO schema_version (version) VALUES (8)"))

    run_migrations(engine)

    with engine.begin() as conn:
        version = conn.execute(text("SELECT version FROM schema_version")).scalar()
        row = conn.execute(text("SELECT id, category_id FROM inventory_items WHERE id = 'i1'")).mappings().first()
        columns = {c[1] for c in conn.execute(text("PRAGMA table_info(inventory_items)")).all()}
        # The exact statement shape save_inventory() issues on every save --
        # this raised sqlite3.IntegrityError before the fix.
        conn.execute(text(
            "INSERT INTO inventory_items "
            "(id, home_id, order_index, name, emoji, category_id, owner_id, store_id, "
            "brand, model, serial_number, purchase_date, purchase_price, warranty_expiry_date, "
            "notes, attachments, placement_floor_id, placement_room_id, placement_x, placement_y) "
            "VALUES ('i2', 'h1', 1, 'Drill', '🔩', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, "
            "'', '[]', NULL, NULL, NULL, NULL)"
        ))

    assert version == CURRENT_VERSION
    assert row["id"] == "i1"
    assert row["category_id"] == "inv-electronics"
    assert "category" not in columns


def test_run_migrations_adds_notes_and_attachments_to_pre_existing_locations_table(tmp_path):
    db_path = tmp_path / "legacy.db"
    engine = create_engine(f"sqlite:///{db_path}")
    with engine.begin() as conn:
        conn.execute(text(
            "CREATE TABLE locations (id VARCHAR PRIMARY KEY, home_id VARCHAR NOT NULL, "
            "order_index INTEGER NOT NULL, name VARCHAR NOT NULL, emoji VARCHAR NOT NULL)"
        ))
        conn.execute(text(
            "INSERT INTO locations (id, home_id, order_index, name, emoji) "
            "VALUES ('loc1', 'h1', 0, 'Ljubljana', '🇸🇮')"
        ))
        conn.execute(text("CREATE TABLE schema_version (version INTEGER NOT NULL)"))
        conn.execute(text("INSERT INTO schema_version (version) VALUES (9)"))

    run_migrations(engine)

    with engine.connect() as conn:
        version = conn.execute(text("SELECT version FROM schema_version")).scalar()
        row = conn.execute(text("SELECT notes, attachments FROM locations WHERE id = 'loc1'")).mappings().first()

    assert version == CURRENT_VERSION
    assert row["notes"] == ""
    assert row["attachments"] == "[]"
