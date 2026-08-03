from myhome.models_insurance import InsurancePolicy, InsuranceDocument
from myhome.persistence_costs import load_costs
from myhome.persistence_insurance import save_insurance


def make_doc() -> InsuranceDocument:
    return InsuranceDocument(policies=[
        InsurancePolicy(
            id="ins1", name="Home Insurance — AXA", categoryId="icat-home",
            premiumAmount=45.0, premiumFrequency="monthly", includeInCosts=False,
        )
    ])


def test_get_insurance_empty_when_no_data(client, home_id):
    resp = client.get(f"/api/homes/{home_id}/insurance")
    assert resp.status_code == 200
    assert resp.json()["policies"] == []


def test_get_insurance_returns_saved_data(client, home_id):
    save_insurance(home_id, make_doc())
    resp = client.get(f"/api/homes/{home_id}/insurance")
    assert resp.status_code == 200
    assert resp.json()["policies"][0]["id"] == "ins1"


def test_create_policy(client, home_id):
    payload = {"name": "Travel Insurance", "categoryId": "icat-travel", "premiumFrequency": "annual"}
    resp = client.post(f"/api/homes/{home_id}/insurance", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Travel Insurance"
    assert data["includeInCosts"] is False
    assert data["attachments"] == []
    assert data["linkedCostEntryId"] is None
    assert "id" in data
    assert len(client.get(f"/api/homes/{home_id}/insurance").json()["policies"]) == 1


def test_create_policy_full_fields(client, home_id):
    payload = {
        "name": "Home Insurance — AXA", "categoryId": "icat-home", "contactId": "con-1",
        "policyNumber": "POL-123", "coverageSummary": "Fire, theft, water damage",
        "conditionsUrl": "https://example.com/policy.pdf", "startDate": "2026-01-01",
        "endDate": "2027-01-01", "premiumAmount": 45.0, "premiumFrequency": "monthly",
        "includeInCosts": True, "alternatives": "Quoted Allianz at 50€/mo", "notes": "Renews automatically",
    }
    resp = client.post(f"/api/homes/{home_id}/insurance", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["premiumAmount"] == 45.0
    assert data["contactId"] == "con-1"
    assert data["includeInCosts"] is True


def test_update_policy_partial(client, home_id):
    save_insurance(home_id, make_doc())
    resp = client.put(f"/api/homes/{home_id}/insurance/ins1", json={"premiumAmount": 50.0})
    assert resp.status_code == 204
    policy = client.get(f"/api/homes/{home_id}/insurance").json()["policies"][0]
    assert policy["premiumAmount"] == 50.0
    assert policy["name"] == "Home Insurance — AXA"  # unchanged


def test_update_policy_404(client, home_id):
    resp = client.put(f"/api/homes/{home_id}/insurance/nope", json={"premiumAmount": 1.0})
    assert resp.status_code == 404


def test_delete_policy(client, home_id):
    save_insurance(home_id, make_doc())
    resp = client.delete(f"/api/homes/{home_id}/insurance/ins1")
    assert resp.status_code == 204
    assert client.get(f"/api/homes/{home_id}/insurance").json()["policies"] == []


def test_delete_policy_404(client, home_id):
    resp = client.delete(f"/api/homes/{home_id}/insurance/nope")
    assert resp.status_code == 404


def test_upload_attachment(client, home_id):
    save_insurance(home_id, make_doc())
    resp = client.post(
        f"/api/homes/{home_id}/attachments/insurance/ins1",
        files={"file": ("policy.pdf", b"%PDF-1.4 test", "application/pdf")},
    )
    assert resp.status_code == 201
    assert resp.json()["filename"] == "policy.pdf"
    policy = client.get(f"/api/homes/{home_id}/insurance").json()["policies"][0]
    assert "policy.pdf" in policy["attachments"]


def test_upload_unsupported_type_rejected(client, home_id):
    save_insurance(home_id, make_doc())
    resp = client.post(
        f"/api/homes/{home_id}/attachments/insurance/ins1",
        files={"file": ("notes.txt", b"hello", "text/plain")},
    )
    assert resp.status_code == 400


def test_get_attachment(client, home_id):
    save_insurance(home_id, make_doc())
    client.post(
        f"/api/homes/{home_id}/attachments/insurance/ins1",
        files={"file": ("policy.pdf", b"%PDF-1.4 test content", "application/pdf")},
    )
    resp = client.get(f"/api/homes/{home_id}/attachments/insurance/ins1/policy.pdf")
    assert resp.status_code == 200
    assert "pdf" in resp.headers["content-type"]


def test_delete_attachment(client, home_id):
    save_insurance(home_id, make_doc())
    client.post(
        f"/api/homes/{home_id}/attachments/insurance/ins1",
        files={"file": ("policy.pdf", b"%PDF test", "application/pdf")},
    )
    resp = client.delete(f"/api/homes/{home_id}/attachments/insurance/ins1/policy.pdf")
    assert resp.status_code == 204
    policy = client.get(f"/api/homes/{home_id}/insurance").json()["policies"][0]
    assert "policy.pdf" not in policy["attachments"]


def test_delete_policy_removes_attachments(client, tmp_path, home_id):
    save_insurance(home_id, make_doc())
    client.post(
        f"/api/homes/{home_id}/attachments/insurance/ins1",
        files={"file": ("policy.pdf", b"%PDF test", "application/pdf")},
    )
    client.delete(f"/api/homes/{home_id}/insurance/ins1")
    attach_dir = tmp_path / "homes" / home_id / "insurance-attachments" / "ins1"
    assert not attach_dir.exists()


def test_activity_log_records_insurance_actions(client, home_id):
    resp = client.post(
        f"/api/homes/{home_id}/insurance",
        json={"name": "Travel Insurance", "categoryId": "icat-travel", "premiumFrequency": "annual"},
    )
    policy_id = resp.json()["id"]
    log = client.get(f"/api/homes/{home_id}/activity").json()
    entry = next(e for e in log["entries"] if e["module"] == "insurance" and e["action"] == "create")
    assert entry["entityLabel"] == "Travel Insurance"
    assert entry["refId"] == policy_id


def test_create_policy_with_include_in_costs_syncs_cost_entry(client, home_id):
    payload = {
        "name": "Home Insurance — AXA", "categoryId": "icat-home", "premiumAmount": 45.0,
        "premiumFrequency": "monthly", "includeInCosts": True, "startDate": "2026-01-01",
    }
    resp = client.post(f"/api/homes/{home_id}/insurance", json=payload)
    policy = resp.json()
    assert policy["linkedCostEntryId"] is not None

    costs = load_costs(home_id)
    assert len(costs.entries) == 1
    entry = costs.entries[0]
    assert entry.id == policy["linkedCostEntryId"]
    assert entry.categoryId == "cat-insurance"
    assert entry.totalAmount == 540.0  # 45 * 12
    assert entry.sourceModule == "insurance"
    assert entry.sourceId == policy["id"]
    assert entry.date == "2026-01-01"


def test_create_policy_without_include_in_costs_does_not_sync(client, home_id):
    payload = {
        "name": "Travel Insurance", "categoryId": "icat-travel", "premiumAmount": 120.0,
        "premiumFrequency": "annual", "includeInCosts": False,
    }
    resp = client.post(f"/api/homes/{home_id}/insurance", json=payload)
    assert resp.json()["linkedCostEntryId"] is None
    assert load_costs(home_id).entries == []


def test_toggling_include_in_costs_on_creates_synced_entry(client, home_id):
    resp = client.post(f"/api/homes/{home_id}/insurance", json={
        "name": "Life Insurance", "categoryId": "icat-life", "premiumAmount": 30.0,
        "premiumFrequency": "monthly", "includeInCosts": False,
    })
    policy_id = resp.json()["id"]
    assert load_costs(home_id).entries == []

    client.put(f"/api/homes/{home_id}/insurance/{policy_id}", json={"includeInCosts": True})
    costs = load_costs(home_id)
    assert len(costs.entries) == 1
    assert costs.entries[0].sourceId == policy_id


def test_toggling_include_in_costs_off_removes_synced_entry(client, home_id):
    resp = client.post(f"/api/homes/{home_id}/insurance", json={
        "name": "Home Insurance", "categoryId": "icat-home", "premiumAmount": 45.0,
        "premiumFrequency": "monthly", "includeInCosts": True,
    })
    policy_id = resp.json()["id"]
    assert len(load_costs(home_id).entries) == 1

    client.put(f"/api/homes/{home_id}/insurance/{policy_id}", json={"includeInCosts": False})
    assert load_costs(home_id).entries == []


def test_updating_premium_updates_synced_cost_entry_amount(client, home_id):
    resp = client.post(f"/api/homes/{home_id}/insurance", json={
        "name": "Home Insurance", "categoryId": "icat-home", "premiumAmount": 45.0,
        "premiumFrequency": "monthly", "includeInCosts": True,
    })
    policy_id = resp.json()["id"]
    client.put(f"/api/homes/{home_id}/insurance/{policy_id}", json={"premiumAmount": 50.0})
    costs = load_costs(home_id)
    assert len(costs.entries) == 1
    assert costs.entries[0].totalAmount == 600.0  # 50 * 12


def test_deleting_synced_policy_removes_cost_entry(client, home_id):
    resp = client.post(f"/api/homes/{home_id}/insurance", json={
        "name": "Home Insurance", "categoryId": "icat-home", "premiumAmount": 45.0,
        "premiumFrequency": "monthly", "includeInCosts": True,
    })
    policy_id = resp.json()["id"]
    assert len(load_costs(home_id).entries) == 1
    client.delete(f"/api/homes/{home_id}/insurance/{policy_id}")
    assert load_costs(home_id).entries == []


def test_reset_insurance_clears_data(client, home_id):
    client.post(f"/api/homes/{home_id}/insurance", json={
        "name": "Travel Insurance", "categoryId": "icat-travel", "premiumFrequency": "annual",
    })
    from myhome.persistence_insurance import reset_insurance
    reset_insurance(home_id)
    assert client.get(f"/api/homes/{home_id}/insurance").json()["policies"] == []
