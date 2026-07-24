# packages/backend/tests/test_contacts.py
def test_get_contacts_empty_when_none(client, home_id):
    resp = client.get(f"/api/homes/{home_id}/contacts")
    assert resp.status_code == 200
    assert resp.json()["contacts"] == []


def test_create_contact(client, home_id):
    payload = {"name": "Metro Plumbing", "typeId": "ctype-supplier"}
    resp = client.post(f"/api/homes/{home_id}/contacts", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Metro Plumbing"
    assert data["typeId"] == "ctype-supplier"
    assert data["companyName"] is None
    assert "id" in data
    assert len(client.get(f"/api/homes/{home_id}/contacts").json()["contacts"]) == 1


def test_create_contact_full_fields(client, home_id):
    payload = {
        "name": "Jane Doe", "companyName": "Acme Roofing", "typeId": "ctype-contractor",
        "phone": "+1 555-1234", "email": "jane@acme.example", "address": "123 Main St",
        "website": "https://acme.example", "notes": "Prefers morning calls",
    }
    resp = client.post(f"/api/homes/{home_id}/contacts", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["companyName"] == "Acme Roofing"
    assert data["email"] == "jane@acme.example"


def test_update_contact_partial(client, home_id):
    created = client.post(f"/api/homes/{home_id}/contacts", json={"name": "Jane", "typeId": "ctype-contractor"}).json()
    resp = client.put(f"/api/homes/{home_id}/contacts/{created['id']}", json={"phone": "555-0000"})
    assert resp.status_code == 204
    contact = client.get(f"/api/homes/{home_id}/contacts").json()["contacts"][0]
    assert contact["phone"] == "555-0000"
    assert contact["name"] == "Jane"  # unchanged


def test_update_contact_404(client, home_id):
    resp = client.put(f"/api/homes/{home_id}/contacts/nope", json={"name": "X"})
    assert resp.status_code == 404


def test_delete_contact(client, home_id):
    created = client.post(f"/api/homes/{home_id}/contacts", json={"name": "Jane", "typeId": "ctype-contractor"}).json()
    resp = client.delete(f"/api/homes/{home_id}/contacts/{created['id']}")
    assert resp.status_code == 204
    assert client.get(f"/api/homes/{home_id}/contacts").json()["contacts"] == []


def test_delete_contact_404(client, home_id):
    resp = client.delete(f"/api/homes/{home_id}/contacts/nope")
    assert resp.status_code == 404


def test_get_contact_usage_empty(client, home_id):
    created = client.post(f"/api/homes/{home_id}/contacts", json={"name": "Jane", "typeId": "ctype-contractor"}).json()
    resp = client.get(f"/api/homes/{home_id}/contacts/{created['id']}/usage")
    assert resp.status_code == 200
    assert resp.json()["references"] == []


def test_delete_contact_blocked_when_used_by_work(client, home_id):
    contact = client.post(f"/api/homes/{home_id}/contacts", json={"name": "Metro Plumbing", "typeId": "ctype-supplier"}).json()
    client.post(f"/api/homes/{home_id}/works", json={"title": "Fix sink", "status": "done", "date": "2026-01-01", "contactId": contact["id"]})
    resp = client.delete(f"/api/homes/{home_id}/contacts/{contact['id']}")
    assert resp.status_code == 409
    assert resp.json()["detail"]["references"][0]["module"] == "works"
    # contact must still exist
    assert len(client.get(f"/api/homes/{home_id}/contacts").json()["contacts"]) == 1


def test_delete_contact_blocked_when_used_by_cost_entry(client, home_id):
    contact = client.post(f"/api/homes/{home_id}/contacts", json={"name": "Metro Plumbing", "typeId": "ctype-supplier"}).json()
    client.post(f"/api/homes/{home_id}/costs/entries", json={"categoryId": "cat-fuel", "date": "2026-01-01", "totalAmount": 50.0, "contactId": contact["id"]})
    resp = client.delete(f"/api/homes/{home_id}/contacts/{contact['id']}")
    assert resp.status_code == 409
    assert resp.json()["detail"]["references"][0]["module"] == "costs"


def test_get_contact_usage_reflects_work_reference(client, home_id):
    contact = client.post(f"/api/homes/{home_id}/contacts", json={"name": "Metro Plumbing", "typeId": "ctype-supplier"}).json()
    client.post(f"/api/homes/{home_id}/works", json={"title": "Fix sink", "status": "done", "date": "2026-01-01", "contactId": contact["id"]})
    resp = client.get(f"/api/homes/{home_id}/contacts/{contact['id']}/usage")
    refs = resp.json()["references"]
    assert len(refs) == 1
    assert refs[0]["label"] == "Fix sink"


def test_delete_contact_unblocked_after_reference_removed(client, home_id):
    contact = client.post(f"/api/homes/{home_id}/contacts", json={"name": "Metro Plumbing", "typeId": "ctype-supplier"}).json()
    work = client.post(f"/api/homes/{home_id}/works", json={"title": "Fix sink", "status": "done", "date": "2026-01-01", "contactId": contact["id"]}).json()
    client.put(f"/api/homes/{home_id}/works/{work['id']}", json={"contactId": None})
    resp = client.delete(f"/api/homes/{home_id}/contacts/{contact['id']}")
    assert resp.status_code == 204
