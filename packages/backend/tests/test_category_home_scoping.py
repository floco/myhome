def test_creating_two_demo_homes_does_not_collide_on_category_ids(client):
    resp1 = client.post("/api/homes", json={"name": "Demo 1", "type": "demo"})
    assert resp1.status_code == 201

    resp2 = client.post("/api/homes", json={"name": "Demo 2", "type": "demo"})
    assert resp2.status_code == 201, resp2.text

    home1_id = resp1.json()["id"]
    home2_id = resp2.json()["id"]

    settings1 = client.get(f"/api/homes/{home1_id}/settings").json()
    settings2 = client.get(f"/api/homes/{home2_id}/settings").json()
    assert len(settings1["costCategories"]) > 0
    assert len(settings2["costCategories"]) > 0
    assert {c["id"] for c in settings1["costCategories"]} == {c["id"] for c in settings2["costCategories"]}
