import pytest
from myhome.models_costs import CostEntry, CostsDocument
from myhome.persistence_costs import save_costs


def make_doc() -> CostsDocument:
    return CostsDocument(
        entries=[
            CostEntry(
                id="e1",
                categoryId="cat-fuel",
                date="2025-10-14",
                totalAmount=1650.0,
                quantity=1500.0,
                unitPrice=1.10,
                contactId="sup-butagaz",
            )
        ]
    )


def test_get_costs_empty_when_no_file(client, home_id):
    resp = client.get(f"/api/homes/{home_id}/costs")
    assert resp.status_code == 200
    assert resp.json()["entries"] == []


def test_get_costs_returns_saved_data(client, tmp_path, home_id):
    save_costs(home_id, make_doc())
    resp = client.get(f"/api/homes/{home_id}/costs")
    assert resp.status_code == 200
    assert resp.json()["entries"][0]["id"] == "e1"


def test_create_entry(client, home_id):
    payload = {
        "categoryId": "cat-fuel",
        "date": "2025-10-14",
        "totalAmount": 1650.0,
        "quantity": 1500.0,
        "unitPrice": 1.10,
        "contactId": "sup-butagaz",
    }
    resp = client.post(f"/api/homes/{home_id}/costs/entries", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["categoryId"] == "cat-fuel"
    assert data["totalAmount"] == 1650.0
    assert data["quantity"] == 1500.0
    assert data["contactId"] == "sup-butagaz"
    assert "id" in data


def test_create_lump_sum_entry(client, home_id):
    resp = client.post(f"/api/homes/{home_id}/costs/entries", json={
        "categoryId": "cat-tax",
        "date": "2025-03-01",
        "totalAmount": 1648.0,
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["quantity"] is None
    assert data["unitPrice"] is None
    assert data["contactId"] is None


def test_update_entry_partial(client, tmp_path, home_id):
    save_costs(home_id, make_doc())
    resp = client.put(f"/api/homes/{home_id}/costs/entries/e1", json={"totalAmount": 1800.0, "contactId": "sup-total"})
    assert resp.status_code == 204
    entry = client.get(f"/api/homes/{home_id}/costs").json()["entries"][0]
    assert entry["totalAmount"] == 1800.0
    assert entry["contactId"] == "sup-total"
    assert entry["quantity"] == 1500.0    # unchanged
    assert entry["unitPrice"] == 1.10     # unchanged


def test_update_entry_404(client, home_id):
    resp = client.put(f"/api/homes/{home_id}/costs/entries/nonexistent", json={"totalAmount": 100.0})
    assert resp.status_code == 404


def test_delete_entry(client, tmp_path, home_id):
    save_costs(home_id, make_doc())
    resp = client.delete(f"/api/homes/{home_id}/costs/entries/e1")
    assert resp.status_code == 204
    assert client.get(f"/api/homes/{home_id}/costs").json()["entries"] == []


def test_delete_entry_404(client, home_id):
    resp = client.delete(f"/api/homes/{home_id}/costs/entries/nonexistent")
    assert resp.status_code == 404


def _make_valid_pdf() -> bytes:
    import fitz
    doc = fitz.open()
    doc.new_page(width=200, height=200)
    return doc.write()


def _entry_id(client, home_id) -> str:
    resp = client.post(f"/api/homes/{home_id}/costs/entries", json={
        "categoryId": "cat1", "date": "2026-01-01", "totalAmount": 100.0,
    })
    return resp.json()["id"]


def test_costs_attachments_empty_by_default(client, home_id):
    eid = _entry_id(client, home_id)
    entry = next(e for e in client.get(f"/api/homes/{home_id}/costs").json()["entries"] if e["id"] == eid)
    assert entry["attachments"] == []


def test_costs_upload_jpeg_accepted(client, home_id):
    eid = _entry_id(client, home_id)
    resp = client.post(
        f"/api/homes/{home_id}/attachments/costs/{eid}",
        files={"file": ("receipt.jpg", b"\xff\xd8\xff" + b"\x00" * 50, "image/jpeg")},
    )
    assert resp.status_code == 201
    assert resp.json()["filename"] == "receipt.jpg"
    entry = next(e for e in client.get(f"/api/homes/{home_id}/costs").json()["entries"] if e["id"] == eid)
    assert "receipt.jpg" in entry["attachments"]


def test_costs_upload_unsupported_rejected(client, home_id):
    eid = _entry_id(client, home_id)
    resp = client.post(
        f"/api/homes/{home_id}/attachments/costs/{eid}",
        files={"file": ("x.exe", b"\x4d\x5a", "application/octet-stream")},
    )
    assert resp.status_code == 400


def test_costs_upload_pdf_creates_thumbnail(client, tmp_path, home_id):
    eid = _entry_id(client, home_id)
    resp = client.post(
        f"/api/homes/{home_id}/attachments/costs/{eid}",
        files={"file": ("invoice.pdf", _make_valid_pdf(), "application/pdf")},
    )
    assert resp.status_code == 201
    thumb = tmp_path / "homes" / home_id / "costs-attachments" / eid / "invoice.pdf.thumb.jpg"
    assert thumb.exists()


def test_costs_delete_attachment_removes_thumb(client, tmp_path, home_id):
    eid = _entry_id(client, home_id)
    client.post(f"/api/homes/{home_id}/attachments/costs/{eid}",
        files={"file": ("invoice.pdf", _make_valid_pdf(), "application/pdf")})
    thumb = tmp_path / "homes" / home_id / "costs-attachments" / eid / "invoice.pdf.thumb.jpg"
    assert thumb.exists()
    client.delete(f"/api/homes/{home_id}/attachments/costs/{eid}/invoice.pdf")
    assert not thumb.exists()


def test_costs_get_jpeg_returns_image_content_type(client, home_id):
    eid = _entry_id(client, home_id)
    client.post(f"/api/homes/{home_id}/attachments/costs/{eid}",
        files={"file": ("receipt.jpg", b"\xff\xd8\xff" + b"\x00" * 50, "image/jpeg")})
    resp = client.get(f"/api/homes/{home_id}/attachments/costs/{eid}/receipt.jpg")
    assert resp.status_code == 200
    assert "image/jpeg" in resp.headers["content-type"]


def test_update_synced_cost_entry_rejected(client, home_id):
    resp = client.post(f"/api/homes/{home_id}/insurance", json={
        "name": "Home Insurance", "categoryId": "icat-home", "premiumAmount": 45.0,
        "premiumFrequency": "monthly", "includeInCosts": True,
    })
    entry_id = resp.json()["linkedCostEntryId"]
    resp2 = client.put(f"/api/homes/{home_id}/costs/entries/{entry_id}", json={"totalAmount": 999.0})
    assert resp2.status_code == 400


def test_delete_synced_cost_entry_rejected(client, home_id):
    resp = client.post(f"/api/homes/{home_id}/insurance", json={
        "name": "Home Insurance", "categoryId": "icat-home", "premiumAmount": 45.0,
        "premiumFrequency": "monthly", "includeInCosts": True,
    })
    entry_id = resp.json()["linkedCostEntryId"]
    resp2 = client.delete(f"/api/homes/{home_id}/costs/entries/{entry_id}")
    assert resp2.status_code == 400


def _create_consumable(client, home_id, quantity=10.0) -> str:
    resp = client.post(f"/api/homes/{home_id}/consumables", json={
        "name": "Heating Oil", "emoji": "🛢️", "unit": "L", "quantity": quantity, "minQuantity": 100.0,
    })
    return resp.json()["id"]


def test_create_entry_with_linked_consumable_applies_stock_increase(client, home_id):
    con_id = _create_consumable(client, home_id, quantity=200.0)
    resp = client.post(f"/api/homes/{home_id}/costs/entries", json={
        "categoryId": "cat-fuel", "date": "2026-01-01", "totalAmount": 900.0,
        "quantity": 1000.0, "unitPrice": 0.9, "linkedConsumableId": con_id,
    })
    assert resp.status_code == 201
    entry_id = resp.json()["id"]

    con = client.get(f"/api/homes/{home_id}/consumables").json()
    item = next(c for c in con["consumables"] if c["id"] == con_id)
    assert item["quantity"] == 1200.0
    tx = next(t for t in con["transactions"] if t["consumableId"] == con_id)
    assert tx["delta"] == 1000.0
    assert tx["costEntryId"] == entry_id
    # Backdated to the cost entry's own date, not the moment it was saved.
    assert tx["timestamp"].startswith("2026-01-01")


def test_update_entry_linked_quantity_reconciles_stock(client, home_id):
    con_id = _create_consumable(client, home_id, quantity=200.0)
    entry_id = client.post(f"/api/homes/{home_id}/costs/entries", json={
        "categoryId": "cat-fuel", "date": "2026-01-01", "totalAmount": 900.0,
        "quantity": 1000.0, "linkedConsumableId": con_id,
    }).json()["id"]

    resp = client.put(f"/api/homes/{home_id}/costs/entries/{entry_id}", json={"quantity": 1500.0})
    assert resp.status_code == 204

    con = client.get(f"/api/homes/{home_id}/consumables").json()
    item = next(c for c in con["consumables"] if c["id"] == con_id)
    assert item["quantity"] == 1700.0
    txs = [t for t in con["transactions"] if t["costEntryId"] == entry_id]
    assert len(txs) == 1
    assert txs[0]["delta"] == 1500.0


def test_update_entry_removing_link_reverses_stock(client, home_id):
    con_id = _create_consumable(client, home_id, quantity=200.0)
    entry_id = client.post(f"/api/homes/{home_id}/costs/entries", json={
        "categoryId": "cat-fuel", "date": "2026-01-01", "totalAmount": 900.0,
        "quantity": 1000.0, "linkedConsumableId": con_id,
    }).json()["id"]

    resp = client.put(f"/api/homes/{home_id}/costs/entries/{entry_id}", json={"linkedConsumableId": None})
    assert resp.status_code == 204

    con = client.get(f"/api/homes/{home_id}/consumables").json()
    item = next(c for c in con["consumables"] if c["id"] == con_id)
    assert item["quantity"] == 200.0
    assert [t for t in con["transactions"] if t["costEntryId"] == entry_id] == []


def test_delete_entry_reverses_linked_stock(client, home_id):
    con_id = _create_consumable(client, home_id, quantity=200.0)
    entry_id = client.post(f"/api/homes/{home_id}/costs/entries", json={
        "categoryId": "cat-fuel", "date": "2026-01-01", "totalAmount": 900.0,
        "quantity": 1000.0, "linkedConsumableId": con_id,
    }).json()["id"]

    resp = client.delete(f"/api/homes/{home_id}/costs/entries/{entry_id}")
    assert resp.status_code == 204

    con = client.get(f"/api/homes/{home_id}/consumables").json()
    item = next(c for c in con["consumables"] if c["id"] == con_id)
    assert item["quantity"] == 200.0
    assert con["transactions"] == []


def test_linked_entries_created_out_of_date_order_recompute_chronologically(client, home_id):
    # Reproduces the real bug: a linked cost entry's date can be backdated,
    # so creation order no longer matches chronological order. Create the
    # later-dated entry FIRST, then an earlier-dated one -- both
    # transactions' running totals must reflect true date order, not
    # creation order.
    con_id = _create_consumable(client, home_id, quantity=0.0)
    client.post(f"/api/homes/{home_id}/costs/entries", json={
        "categoryId": "cat-fuel", "date": "2026-03-01", "totalAmount": 450.0,
        "quantity": 500.0, "linkedConsumableId": con_id,
    })
    client.post(f"/api/homes/{home_id}/costs/entries", json={
        "categoryId": "cat-fuel", "date": "2026-01-01", "totalAmount": 900.0,
        "quantity": 1000.0, "linkedConsumableId": con_id,
    })

    con = client.get(f"/api/homes/{home_id}/consumables").json()
    item = next(c for c in con["consumables"] if c["id"] == con_id)
    txs = sorted(
        (t for t in con["transactions"] if t["consumableId"] == con_id),
        key=lambda t: t["timestamp"],
    )
    assert [t["quantityAfter"] for t in txs] == [1000.0, 1500.0]
    assert item["quantity"] == 1500.0


def test_delete_linked_consumable_clears_cost_entry_link(client, home_id):
    con_id = _create_consumable(client, home_id, quantity=200.0)
    entry_id = client.post(f"/api/homes/{home_id}/costs/entries", json={
        "categoryId": "cat-fuel", "date": "2026-01-01", "totalAmount": 900.0,
        "quantity": 1000.0, "linkedConsumableId": con_id,
    }).json()["id"]

    resp = client.delete(f"/api/homes/{home_id}/consumables/{con_id}")
    assert resp.status_code == 204

    entry = next(e for e in client.get(f"/api/homes/{home_id}/costs").json()["entries"] if e["id"] == entry_id)
    assert entry["linkedConsumableId"] is None


def test_reset_costs_clears_data(client, home_id):
    client.post(f"/api/homes/{home_id}/costs", json={
        "categoryId": "cat-fuel", "date": "2026-01-01", "totalAmount": 100.0,
    })
    from myhome.persistence_costs import reset_costs
    reset_costs(home_id)
    assert client.get(f"/api/homes/{home_id}/costs").json()["entries"] == []
