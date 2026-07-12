from myhome.demo_content import (
    CHORES,
    CONSUMABLES,
    INVENTORY_ITEMS,
    KB_TITLES,
    WORKS,
    generate_demo_settings,
)


def test_generate_demo_settings_has_expected_category_counts():
    settings = generate_demo_settings()
    assert len(settings.costCategories) == 9
    assert len(settings.workCategories) == 7
    assert len(settings.inventoryCategories) == 8
    assert len(settings.consumableCategories) == 6
    assert len(settings.suppliers) == 9
    assert len(settings.consumableUnits) > 0


def test_generate_demo_settings_ids_are_unique():
    settings = generate_demo_settings()
    assert len({c.id for c in settings.costCategories}) == 9
    assert len({c.id for c in settings.workCategories}) == 7
    assert len({c.id for c in settings.inventoryCategories}) == 8
    assert len({c.id for c in settings.consumableCategories}) == 6
    assert len({s.id for s in settings.suppliers}) == 9


def test_curated_content_lists_have_at_least_32_entries():
    assert len(CHORES) >= 32
    assert len(INVENTORY_ITEMS) >= 32
    assert len(WORKS) >= 32
    assert len(KB_TITLES) >= 32
    assert len(CONSUMABLES) >= 32


def test_curated_entries_reference_valid_category_ids():
    settings = generate_demo_settings()
    inventory_cat_ids = {c.id for c in settings.inventoryCategories}
    work_cat_ids = {c.id for c in settings.workCategories}
    consumable_cat_ids = {c.id for c in settings.consumableCategories}
    for _name, _emoji, category_id, _price_range in INVENTORY_ITEMS:
        assert category_id in inventory_cat_ids
    for _title, category_id, _cost_range in WORKS:
        assert category_id in work_cat_ids
    for _name, _emoji, category_id, _unit in CONSUMABLES:
        assert category_id in consumable_cat_ids
