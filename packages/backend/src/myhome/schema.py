# packages/backend/src/myhome/schema.py
"""SQLAlchemy Core table definitions for the SQLite persistence layer.

Every persistence_x.py module's tables live here, added incrementally as
each module is converted. See the Global Constraints in
docs/superpowers/plans/2026-07-13-sqlite-persistence.md for the rules on
when a home_id/parent-id column gets a hard ForeignKey vs. stays a plain
column, and for the order_index convention.
"""
from __future__ import annotations

from sqlalchemy import Boolean, Column, Float, ForeignKey, Index, Integer, MetaData, String, Table, Text

metadata = MetaData()

homes = Table(
    "homes", metadata,
    Column("id", String, primary_key=True),
    Column("name", String, nullable=False),
    Column("type", String, nullable=False),
    Column("created_at", String, nullable=False),
)

home_modules = Table(
    "home_modules", metadata,
    Column("home_id", String, ForeignKey("homes.id", ondelete="CASCADE"), primary_key=True),
    Column("module_id", String, primary_key=True),
    Column("order_index", Integer, nullable=False),
)

users = Table(
    "users", metadata,
    Column("id", String, primary_key=True),
    Column("username", String, nullable=False, unique=True),
    Column("password_hash", String),
    Column("role", String, nullable=False),
    Column("created_at", String, nullable=False),
    Column("auth_provider", String, nullable=False),
    Column("oidc_sub", String),
    Column("ha_user_id", String),
    Column("order_index", Integer, nullable=False),
)

# api_tokens.owner_id intentionally has no ForeignKey: users and tokens are
# saved by different, independently-timed save_x() calls (see the hard-FK
# rule in the plan's Global Constraints), so this stays a plain matched-in-
# Python string column exactly like today.
api_tokens = Table(
    "api_tokens", metadata,
    Column("id", String, primary_key=True),
    Column("name", String, nullable=False),
    Column("token_hash", String, nullable=False),
    Column("role", String, nullable=False),
    Column("owner_id", String, nullable=False),
    Column("created_at", String, nullable=False),
    Column("last_used_at", String),
    Column("order_index", Integer, nullable=False),
)

oidc_config = Table(
    "oidc_config", metadata,
    Column("id", Integer, primary_key=True),
    Column("enabled", Boolean, nullable=False),
    Column("provider_name", String, nullable=False),
    Column("issuer", String, nullable=False),
    Column("client_id", String, nullable=False),
    Column("client_secret", String, nullable=False),
    Column("default_role", String, nullable=False),
    Column("scopes", Text, nullable=False),
)

mcp_config = Table(
    "mcp_config", metadata,
    Column("id", Integer, primary_key=True),
    Column("enabled", Boolean, nullable=False),
)

backup_config = Table(
    "backup_config", metadata,
    Column("id", Integer, primary_key=True),
    Column("enabled", Boolean, nullable=False),
    Column("frequency", String, nullable=False),
    Column("time", String, nullable=False),
    Column("day_of_week", Integer, nullable=False),
    Column("day_of_month", Integer, nullable=False),
    Column("retention_count", Integer, nullable=False),
)

backup_state = Table(
    "backup_state", metadata,
    Column("id", Integer, primary_key=True),
    Column("last_run_date", String),
)

# These five tables' ids are meaningful fixed strings (e.g. "cat-fuel",
# "inv-electronics") shared verbatim across every home's default/demo seed
# data -- they were only ever unique *within* a home under the pre-SQLite
# per-home-JSON-file format. The primary key must be (home_id, id), not a
# bare `id`, or seeding a second home's defaults collides with the first.
cost_categories = Table(
    "cost_categories", metadata,
    Column("id", String, primary_key=True),
    Column("home_id", String, ForeignKey("homes.id", ondelete="CASCADE"), primary_key=True),
    Column("order_index", Integer, nullable=False),
    Column("name", String, nullable=False),
    Column("emoji", String, nullable=False),
    Column("unit", String),
    Column("color", String, nullable=False),
    Column("placement_floor_id", String),
    Column("placement_x", Float),
    Column("placement_y", Float),
)

inventory_categories = Table(
    "inventory_categories", metadata,
    Column("id", String, primary_key=True),
    Column("home_id", String, ForeignKey("homes.id", ondelete="CASCADE"), primary_key=True),
    Column("order_index", Integer, nullable=False),
    Column("name", String, nullable=False),
)

work_categories = Table(
    "work_categories", metadata,
    Column("id", String, primary_key=True),
    Column("home_id", String, ForeignKey("homes.id", ondelete="CASCADE"), primary_key=True),
    Column("order_index", Integer, nullable=False),
    Column("name", String, nullable=False),
    Column("emoji", String, nullable=False),
)

suppliers = Table(
    "suppliers", metadata,
    Column("id", String, primary_key=True),
    Column("home_id", String, ForeignKey("homes.id", ondelete="CASCADE"), primary_key=True),
    Column("order_index", Integer, nullable=False),
    Column("name", String, nullable=False),
)

consumable_categories = Table(
    "consumable_categories", metadata,
    Column("id", String, primary_key=True),
    Column("home_id", String, ForeignKey("homes.id", ondelete="CASCADE"), primary_key=True),
    Column("order_index", Integer, nullable=False),
    Column("name", String, nullable=False),
    Column("emoji", String, nullable=False),
)

settings = Table(
    "settings", metadata,
    Column("home_id", String, ForeignKey("homes.id", ondelete="CASCADE"), primary_key=True),
    Column("consumable_units", Text, nullable=False),
    Column("notif_enabled", Boolean, nullable=False),
    Column("notif_chores_due_soon_threshold", Float, nullable=False),
    Column("notif_warranty_days_threshold", Integer, nullable=False),
    Column("notif_ha_push_enabled", Boolean, nullable=False),
    Column("notif_ha_notify_service", String),
    Column("notif_ha_push_time", String, nullable=False),
)

chores = Table(
    "chores", metadata,
    Column("id", String, primary_key=True),
    Column("home_id", String, ForeignKey("homes.id", ondelete="CASCADE"), nullable=False),
    Column("order_index", Integer, nullable=False),
    Column("donetick_id", Integer),
    Column("name", String, nullable=False),
    Column("emoji", String, nullable=False),
    Column("period_days", Float, nullable=False),
    Column("frequency_type", String, nullable=False),
    Column("frequency", Integer, nullable=False),
    Column("frequency_metadata", Text, nullable=False),
    Column("schedule_from_due", Boolean, nullable=False),
    Column("next_due_date", String, nullable=False),
    Column("description", String, nullable=False),
    Column("attachments", Text, nullable=False),
)

chore_assignments = Table(
    "chore_assignments", metadata,
    Column("id", String, primary_key=True),
    Column("home_id", String, ForeignKey("homes.id", ondelete="CASCADE"), nullable=False),
    Column("order_index", Integer, nullable=False),
    Column("chore_id", String, ForeignKey("chores.id", ondelete="CASCADE"), nullable=False),
    Column("room_id", String),
    Column("position_x", Float),
    Column("position_y", Float),
    Column("next_due_date", String, nullable=False),
)

chore_completions = Table(
    "chore_completions", metadata,
    Column("id", String, primary_key=True),
    Column("home_id", String, ForeignKey("homes.id", ondelete="CASCADE"), nullable=False),
    Column("order_index", Integer, nullable=False),
    Column("chore_id", String, ForeignKey("chores.id", ondelete="CASCADE"), nullable=False),
    Column("assignment_id", String),
    Column("completed_at", String, nullable=False),
    Column("scheduled_due", String, nullable=False),
    Column("notes", String, nullable=False),
)

# category_id/supplier_id are plain columns, no ForeignKey -- see the
# hard-FK rule in this plan's Global Constraints (settings' category
# tables are cleared/reinserted by a different save_x() call).
cost_entries = Table(
    "cost_entries", metadata,
    Column("id", String, primary_key=True),
    Column("home_id", String, ForeignKey("homes.id", ondelete="CASCADE"), nullable=False),
    Column("order_index", Integer, nullable=False),
    Column("category_id", String, nullable=False),
    Column("date", String, nullable=False),
    Column("total_amount", Float, nullable=False),
    Column("quantity", Float),
    Column("unit_price", Float),
    Column("supplier_id", String),
    Column("notes", String, nullable=False),
    Column("room_id", String),
    Column("attachments", Text, nullable=False),
)

inventory_items = Table(
    "inventory_items", metadata,
    Column("id", String, primary_key=True),
    Column("home_id", String, ForeignKey("homes.id", ondelete="CASCADE"), nullable=False),
    Column("order_index", Integer, nullable=False),
    Column("name", String, nullable=False),
    Column("emoji", String, nullable=False),
    Column("category", String, nullable=False),
    Column("brand", String),
    Column("model", String),
    Column("serial_number", String),
    Column("purchase_date", String),
    Column("purchase_price", Float),
    Column("warranty_expiry_date", String),
    Column("notes", String, nullable=False),
    Column("attachments", Text, nullable=False),
    Column("placement_floor_id", String),
    Column("placement_room_id", String),
    Column("placement_x", Float),
    Column("placement_y", Float),
)

works = Table(
    "works", metadata,
    Column("id", String, primary_key=True),
    Column("home_id", String, ForeignKey("homes.id", ondelete="CASCADE"), nullable=False),
    Column("order_index", Integer, nullable=False),
    Column("title", String, nullable=False),
    Column("description", String, nullable=False),
    Column("status", String, nullable=False),
    Column("category_id", String),
    Column("date", String, nullable=False),
    Column("total_cost", Float),
    Column("supplier_id", String),
    Column("notes", String, nullable=False),
    Column("attachments", Text, nullable=False),
    Column("placement_floor_id", String),
    Column("placement_x", Float),
    Column("placement_y", Float),
)

consumables = Table(
    "consumables", metadata,
    Column("id", String, primary_key=True),
    Column("home_id", String, ForeignKey("homes.id", ondelete="CASCADE"), nullable=False),
    Column("order_index", Integer, nullable=False),
    Column("name", String, nullable=False),
    Column("emoji", String, nullable=False),
    Column("unit", String, nullable=False),
    Column("quantity", Float, nullable=False),
    Column("min_quantity", Float, nullable=False),
    Column("category_id", String),
    Column("description", String, nullable=False),
    Column("placement_floor_id", String),
    Column("placement_room_id", String),
    Column("placement_x", Float),
    Column("placement_y", Float),
)

consumable_transactions = Table(
    "consumable_transactions", metadata,
    Column("id", String, primary_key=True),
    Column("home_id", String, ForeignKey("homes.id", ondelete="CASCADE"), nullable=False),
    Column("order_index", Integer, nullable=False),
    Column("consumable_id", String, ForeignKey("consumables.id", ondelete="CASCADE"), nullable=False),
    Column("delta", Float, nullable=False),
    Column("quantity_after", Float, nullable=False),
    Column("note", String, nullable=False),
    Column("timestamp", String, nullable=False),
)

activity_log_entries = Table(
    "activity_log_entries", metadata,
    Column("id", String, primary_key=True),
    Column("home_id", String, ForeignKey("homes.id", ondelete="CASCADE"), nullable=False),
    Column("timestamp", String, nullable=False),
    Column("user_id", String, nullable=False),
    Column("username", String, nullable=False),
    Column("module", String, nullable=False),
    Column("action", String, nullable=False),
    Column("entity_label", String, nullable=False),
    Column("ref_id", String),
    Index("ix_activity_log_home_timestamp", "home_id", "timestamp"),
)

notification_state = Table(
    "notification_state", metadata,
    Column("home_id", String, ForeignKey("homes.id", ondelete="CASCADE"), primary_key=True),
    Column("warranty_notified", Text, nullable=False),
    Column("build_phases_notified", Text, nullable=False, server_default="[]"),
    Column("last_push_digest_date", String),
)

house_documents = Table(
    "house_documents", metadata,
    Column("home_id", String, ForeignKey("homes.id", ondelete="CASCADE"), primary_key=True),
    Column("doc", Text, nullable=False),
)

location_criteria = Table(
    "location_criteria", metadata,
    Column("id", String, primary_key=True),
    Column("home_id", String, ForeignKey("homes.id", ondelete="CASCADE"), nullable=False),
    Column("order_index", Integer, nullable=False),
    Column("name", String, nullable=False),
    Column("description", String, nullable=False),
    Column("weight", String, nullable=False),
)

locations = Table(
    "locations", metadata,
    Column("id", String, primary_key=True),
    Column("home_id", String, ForeignKey("homes.id", ondelete="CASCADE"), nullable=False),
    Column("order_index", Integer, nullable=False),
    Column("name", String, nullable=False),
    Column("emoji", String, nullable=False),
)

location_ratings = Table(
    "location_ratings", metadata,
    Column("location_id", String, ForeignKey("locations.id", ondelete="CASCADE"), primary_key=True),
    Column("criterion_id", String, ForeignKey("location_criteria.id", ondelete="CASCADE"), primary_key=True),
    Column("home_id", String, ForeignKey("homes.id", ondelete="CASCADE"), nullable=False),
    Column("score", Integer),
    Column("note", String, nullable=False),
)

properties = Table(
    "properties", metadata,
    Column("id", String, primary_key=True),
    Column("home_id", String, ForeignKey("homes.id", ondelete="CASCADE"), nullable=False),
    Column("order_index", Integer, nullable=False),
    Column("name", String, nullable=False),
    Column("emoji", String, nullable=False),
    Column("type", String, nullable=False),
    Column("status", String, nullable=False),
    Column("location_id", String),
    Column("address", String, nullable=False),
    Column("price", Float),
    Column("land_size", Float),
    Column("built_size", Float),
    Column("bedrooms", Integer),
    Column("bathrooms", Integer),
    Column("listing_url", String),
    Column("contact", String, nullable=False),
    Column("pros", Text, nullable=False),
    Column("cons", Text, nullable=False),
    Column("notes", String, nullable=False),
    Column("attachments", Text, nullable=False),
)

build_projects = Table(
    "build_projects", metadata,
    Column("id", String, primary_key=True),
    Column("home_id", String, ForeignKey("homes.id", ondelete="CASCADE"), nullable=False, unique=True),
    Column("status", String, nullable=False),
    Column("planned_start_date", String),
    Column("planned_completion_date", String),
    Column("actual_completion_date", String),
    Column("planned_budget", Float),
    Column("notes", String, nullable=False),
    Column("created_at", String, nullable=False),
    Column("updated_at", String, nullable=False),
)

build_phases = Table(
    "build_phases", metadata,
    Column("id", String, primary_key=True),
    Column("build_project_id", String, ForeignKey("build_projects.id", ondelete="CASCADE"), nullable=False),
    Column("display_order", Integer, nullable=False),
    Column("name_key", String),
    Column("name_override", String),
    Column("description_key", String),
    Column("description_override", String),
    Column("status", String, nullable=False),
    Column("planned_start_date", String),
    Column("planned_end_date", String),
    Column("actual_start_date", String),
    Column("actual_end_date", String),
)

build_tasks = Table(
    "build_tasks", metadata,
    Column("id", String, primary_key=True),
    Column("phase_id", String, ForeignKey("build_phases.id", ondelete="CASCADE"), nullable=False),
    Column("parent_task_id", String),
    Column("display_order", Integer, nullable=False),
    Column("title_key", String),
    Column("title_override", String),
    Column("description_key", String),
    Column("description_override", String),
    Column("status", String, nullable=False),
    Column("planned_start_date", String),
    Column("planned_due_date", String),
    Column("actual_completion_date", String),
    Column("planned_cost", Float),
    Column("actual_cost", Float),
    Column("contractor_id", String),
    Column("validation_required", Boolean, nullable=False),
    Column("validation_status", String, nullable=False),
    Column("notes", String, nullable=False),
    Column("attachments", Text, nullable=False),
)

build_task_dependencies = Table(
    "build_task_dependencies", metadata,
    Column("id", String, primary_key=True),
    Column("predecessor_task_id", String, ForeignKey("build_tasks.id", ondelete="CASCADE"), nullable=False),
    Column("successor_task_id", String, ForeignKey("build_tasks.id", ondelete="CASCADE"), nullable=False),
)
