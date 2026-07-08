from myhome.persistence_activity import load_activity_log


def test_creating_chore_logs_activity(client, home_id):
    client.post(f"/api/homes/{home_id}/chores", json={
        "name": "Sweep kitchen", "emoji": "🧹", "periodDays": 7,
        "nextDueDate": "2026-01-01T00:00:00Z",
    })
    entries = load_activity_log(home_id).entries
    assert any(e.module == "chores" and e.action == "create" and e.entityLabel == "Sweep kitchen" for e in entries)


def test_updating_chore_logs_activity(client, home_id):
    chore = client.post(f"/api/homes/{home_id}/chores", json={
        "name": "Sweep kitchen", "emoji": "🧹", "periodDays": 7,
        "nextDueDate": "2026-01-01T00:00:00Z",
    }).json()
    client.put(f"/api/homes/{home_id}/chores/{chore['id']}", json={"description": "Updated"})
    entries = load_activity_log(home_id).entries
    assert any(e.module == "chores" and e.action == "update" and e.entityLabel == "Sweep kitchen" for e in entries)


def test_deleting_chore_logs_activity(client, home_id):
    chore = client.post(f"/api/homes/{home_id}/chores", json={
        "name": "Sweep kitchen", "emoji": "🧹", "periodDays": 7,
        "nextDueDate": "2026-01-01T00:00:00Z",
    }).json()
    client.delete(f"/api/homes/{home_id}/chores/{chore['id']}")
    entries = load_activity_log(home_id).entries
    assert any(e.module == "chores" and e.action == "delete" and e.entityLabel == "Sweep kitchen" for e in entries)


def test_completing_chore_logs_activity(client, home_id):
    chore = client.post(f"/api/homes/{home_id}/chores", json={
        "name": "Sweep kitchen", "emoji": "🧹", "periodDays": 7,
        "nextDueDate": "2026-01-01T00:00:00Z",
    }).json()
    client.post(f"/api/homes/{home_id}/chores/{chore['id']}/complete", json={"notes": ""})
    entries = load_activity_log(home_id).entries
    assert any(e.module == "chores" and e.action == "complete" and e.entityLabel == "Sweep kitchen" for e in entries)


def test_completing_assignment_logs_activity(client, home_id):
    chore = client.post(f"/api/homes/{home_id}/chores", json={
        "name": "Sweep kitchen", "emoji": "🧹", "periodDays": 7,
        "nextDueDate": "2026-01-01T00:00:00Z",
    }).json()
    assignment = client.post(f"/api/homes/{home_id}/assignments", json={
        "choreId": chore["id"], "roomId": None, "position": None, "nextDueDate": "2026-01-01T00:00:00Z",
    }).json()
    client.post(f"/api/homes/{home_id}/assignments/{assignment['id']}/complete", json={"notes": ""})
    entries = load_activity_log(home_id).entries
    assert any(e.module == "chores" and e.action == "complete" and e.entityLabel == "Sweep kitchen" for e in entries)


def test_creating_work_logs_activity(client, home_id):
    client.post(f"/api/homes/{home_id}/works", json={"title": "Fix boiler", "date": "2026-01-01"})
    entries = load_activity_log(home_id).entries
    assert any(e.module == "works" and e.action == "create" and e.entityLabel == "Fix boiler" for e in entries)


def test_updating_work_logs_activity(client, home_id):
    work = client.post(f"/api/homes/{home_id}/works", json={"title": "Fix boiler", "date": "2026-01-01"}).json()
    client.put(f"/api/homes/{home_id}/works/{work['id']}", json={"status": "in_progress"})
    entries = load_activity_log(home_id).entries
    assert any(e.module == "works" and e.action == "update" and e.entityLabel == "Fix boiler" for e in entries)


def test_deleting_work_logs_activity(client, home_id):
    work = client.post(f"/api/homes/{home_id}/works", json={"title": "Fix boiler", "date": "2026-01-01"}).json()
    client.delete(f"/api/homes/{home_id}/works/{work['id']}")
    entries = load_activity_log(home_id).entries
    assert any(e.module == "works" and e.action == "delete" and e.entityLabel == "Fix boiler" for e in entries)


def test_creating_cost_entry_logs_activity(client, home_id):
    client.post(f"/api/homes/{home_id}/costs/entries", json={
        "categoryId": "cat-1", "date": "2026-01-01", "totalAmount": 45.0, "notes": "Electricity",
    })
    entries = load_activity_log(home_id).entries
    assert any(e.module == "costs" and e.action == "create" and e.entityLabel == "Electricity" for e in entries)


def test_creating_cost_entry_without_notes_uses_amount_as_label(client, home_id):
    client.post(f"/api/homes/{home_id}/costs/entries", json={
        "categoryId": "cat-1", "date": "2026-01-01", "totalAmount": 45.5,
    })
    entries = load_activity_log(home_id).entries
    assert any(e.module == "costs" and e.action == "create" and e.entityLabel == "45.5" for e in entries)


def test_updating_cost_entry_logs_activity(client, home_id):
    entry = client.post(f"/api/homes/{home_id}/costs/entries", json={
        "categoryId": "cat-1", "date": "2026-01-01", "totalAmount": 45.0, "notes": "Electricity",
    }).json()
    client.put(f"/api/homes/{home_id}/costs/entries/{entry['id']}", json={"totalAmount": 50.0})
    entries = load_activity_log(home_id).entries
    assert any(e.module == "costs" and e.action == "update" and e.entityLabel == "Electricity" for e in entries)


def test_deleting_cost_entry_logs_activity(client, home_id):
    entry = client.post(f"/api/homes/{home_id}/costs/entries", json={
        "categoryId": "cat-1", "date": "2026-01-01", "totalAmount": 45.0, "notes": "Electricity",
    }).json()
    client.delete(f"/api/homes/{home_id}/costs/entries/{entry['id']}")
    entries = load_activity_log(home_id).entries
    assert any(e.module == "costs" and e.action == "delete" and e.entityLabel == "Electricity" for e in entries)


def test_creating_inventory_item_logs_activity(client, home_id):
    client.post(f"/api/homes/{home_id}/inventory/items", json={"name": "TV"})
    entries = load_activity_log(home_id).entries
    assert any(e.module == "inventory" and e.action == "create" and e.entityLabel == "TV" for e in entries)


def test_updating_inventory_item_logs_activity(client, home_id):
    item = client.post(f"/api/homes/{home_id}/inventory/items", json={"name": "TV"}).json()
    client.put(f"/api/homes/{home_id}/inventory/items/{item['id']}", json={"brand": "Samsung"})
    entries = load_activity_log(home_id).entries
    assert any(e.module == "inventory" and e.action == "update" and e.entityLabel == "TV" for e in entries)


def test_deleting_inventory_item_logs_activity(client, home_id):
    item = client.post(f"/api/homes/{home_id}/inventory/items", json={"name": "TV"}).json()
    client.delete(f"/api/homes/{home_id}/inventory/items/{item['id']}")
    entries = load_activity_log(home_id).entries
    assert any(e.module == "inventory" and e.action == "delete" and e.entityLabel == "TV" for e in entries)


def test_creating_consumable_logs_activity(client, home_id):
    client.post(f"/api/homes/{home_id}/consumables", json={"name": "Salt", "quantity": 5, "minQuantity": 1})
    entries = load_activity_log(home_id).entries
    assert any(e.module == "consumables" and e.action == "create" and e.entityLabel == "Salt" for e in entries)


def test_adjusting_consumable_stock_logs_activity(client, home_id):
    item = client.post(f"/api/homes/{home_id}/consumables", json={"name": "Salt", "quantity": 5, "minQuantity": 1}).json()
    client.post(f"/api/homes/{home_id}/consumables/{item['id']}/stock", json={"quantity": 2, "note": ""})
    entries = load_activity_log(home_id).entries
    assert any(e.module == "consumables" and e.action == "update" and e.entityLabel == "Salt" for e in entries)


def test_deleting_consumable_logs_activity(client, home_id):
    item = client.post(f"/api/homes/{home_id}/consumables", json={"name": "Salt", "quantity": 5, "minQuantity": 1}).json()
    client.delete(f"/api/homes/{home_id}/consumables/{item['id']}")
    entries = load_activity_log(home_id).entries
    assert any(e.module == "consumables" and e.action == "delete" and e.entityLabel == "Salt" for e in entries)


def test_creating_kb_entry_logs_activity(client, home_id):
    client.post(f"/api/homes/{home_id}/kb", json={"title": "How to reset router", "content": "..."})
    entries = load_activity_log(home_id).entries
    assert any(e.module == "kb" and e.action == "create" and e.entityLabel == "How to reset router" for e in entries)


def test_updating_kb_entry_logs_activity(client, home_id):
    entry = client.post(f"/api/homes/{home_id}/kb", json={"title": "How to reset router", "content": "..."}).json()
    client.put(f"/api/homes/{home_id}/kb/{entry['id']}", json={"content": "Updated steps"})
    entries = load_activity_log(home_id).entries
    assert any(e.module == "kb" and e.action == "update" and e.entityLabel == "How to reset router" for e in entries)


def test_deleting_kb_entry_logs_activity(client, home_id):
    entry = client.post(f"/api/homes/{home_id}/kb", json={"title": "How to reset router", "content": "..."}).json()
    client.delete(f"/api/homes/{home_id}/kb/{entry['id']}")
    entries = load_activity_log(home_id).entries
    assert any(e.module == "kb" and e.action == "delete" and e.entityLabel == "How to reset router" for e in entries)
