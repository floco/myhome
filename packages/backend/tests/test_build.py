def test_get_build_empty_when_no_project(client, home_id):
    resp = client.get(f"/api/homes/{home_id}/build")
    assert resp.status_code == 200
    assert resp.json()["project"] is None


def test_start_build_seeds_template(client, home_id):
    resp = client.post(f"/api/homes/{home_id}/build/start", json={})
    assert resp.status_code == 201
    data = resp.json()
    assert data["project"]["status"] == "planning"
    assert len(data["phases"]) == 22
    assert len(data["tasks"]) == 58
    assert len(data["dependencies"]) > 0


def test_start_build_conflict_when_already_started(client, home_id):
    client.post(f"/api/homes/{home_id}/build/start", json={})
    resp = client.post(f"/api/homes/{home_id}/build/start", json={})
    assert resp.status_code == 409


def test_update_project(client, home_id):
    client.post(f"/api/homes/{home_id}/build/start", json={})
    resp = client.put(f"/api/homes/{home_id}/build/project", json={"status": "in_progress", "plannedBudget": 300000.0})
    assert resp.status_code == 204
    data = client.get(f"/api/homes/{home_id}/build").json()
    assert data["project"]["status"] == "in_progress"
    assert data["project"]["plannedBudget"] == 300000.0


def test_update_project_404_when_no_project(client, home_id):
    resp = client.put(f"/api/homes/{home_id}/build/project", json={"status": "in_progress"})
    assert resp.status_code == 404


def test_delete_project(client, home_id):
    client.post(f"/api/homes/{home_id}/build/start", json={})
    resp = client.delete(f"/api/homes/{home_id}/build/project")
    assert resp.status_code == 204
    assert client.get(f"/api/homes/{home_id}/build").json()["project"] is None


def test_update_phase(client, home_id):
    data = client.post(f"/api/homes/{home_id}/build/start", json={}).json()
    phase_id = data["phases"][0]["id"]
    resp = client.put(f"/api/homes/{home_id}/build/phases/{phase_id}", json={"status": "in_progress"})
    assert resp.status_code == 204
    updated = client.get(f"/api/homes/{home_id}/build").json()
    assert updated["phases"][0]["status"] == "in_progress"


def test_update_phase_name_override(client, home_id):
    data = client.post(f"/api/homes/{home_id}/build/start", json={}).json()
    phase_id = data["phases"][0]["id"]
    client.put(f"/api/homes/{home_id}/build/phases/{phase_id}", json={"nameOverride": "Custom Planning"})
    updated = client.get(f"/api/homes/{home_id}/build").json()
    assert updated["phases"][0]["nameOverride"] == "Custom Planning"


def test_update_phase_404(client, home_id):
    client.post(f"/api/homes/{home_id}/build/start", json={})
    resp = client.put(f"/api/homes/{home_id}/build/phases/nope", json={"status": "in_progress"})
    assert resp.status_code == 404


def test_create_custom_task(client, home_id):
    data = client.post(f"/api/homes/{home_id}/build/start", json={}).json()
    phase_id = data["phases"][0]["id"]
    resp = client.post(f"/api/homes/{home_id}/build/tasks", json={"phaseId": phase_id, "titleOverride": "Extra permit visit"})
    assert resp.status_code == 201
    task = resp.json()
    assert task["titleOverride"] == "Extra permit visit"
    assert task["titleKey"] is None


def test_update_task(client, home_id):
    data = client.post(f"/api/homes/{home_id}/build/start", json={}).json()
    task_id = data["tasks"][0]["id"]
    resp = client.put(f"/api/homes/{home_id}/build/tasks/{task_id}", json={
        "status": "in_progress", "actualCost": 550.0, "contractorId": "Acme Surveying",
    })
    assert resp.status_code == 204
    updated = client.get(f"/api/homes/{home_id}/build").json()
    task = next(t for t in updated["tasks"] if t["id"] == task_id)
    assert task["status"] == "in_progress"
    assert task["actualCost"] == 550.0
    assert task["contractorId"] == "Acme Surveying"


def test_update_task_404(client, home_id):
    client.post(f"/api/homes/{home_id}/build/start", json={})
    resp = client.put(f"/api/homes/{home_id}/build/tasks/nope", json={"status": "completed"})
    assert resp.status_code == 404


def test_delete_task_cascades_dependencies(client, home_id):
    data = client.post(f"/api/homes/{home_id}/build/start", json={}).json()
    task_id = data["tasks"][0]["id"]
    resp = client.delete(f"/api/homes/{home_id}/build/tasks/{task_id}")
    assert resp.status_code == 204
    updated = client.get(f"/api/homes/{home_id}/build").json()
    assert all(t["id"] != task_id for t in updated["tasks"])
    assert all(d["predecessorTaskId"] != task_id and d["successorTaskId"] != task_id for d in updated["dependencies"])


def test_delete_task_404(client, home_id):
    client.post(f"/api/homes/{home_id}/build/start", json={})
    resp = client.delete(f"/api/homes/{home_id}/build/tasks/nope")
    assert resp.status_code == 404


def test_create_dependency(client, home_id):
    data = client.post(f"/api/homes/{home_id}/build/start", json={}).json()
    t1, t2 = data["tasks"][0]["id"], data["tasks"][-1]["id"]
    resp = client.post(f"/api/homes/{home_id}/build/dependencies", json={"predecessorTaskId": t1, "successorTaskId": t2})
    assert resp.status_code == 201
    updated = client.get(f"/api/homes/{home_id}/build").json()
    assert any(d["predecessorTaskId"] == t1 and d["successorTaskId"] == t2 for d in updated["dependencies"])


def test_delete_dependency(client, home_id):
    data = client.post(f"/api/homes/{home_id}/build/start", json={}).json()
    dep_id = data["dependencies"][0]["id"]
    resp = client.delete(f"/api/homes/{home_id}/build/dependencies/{dep_id}")
    assert resp.status_code == 204
    updated = client.get(f"/api/homes/{home_id}/build").json()
    assert all(d["id"] != dep_id for d in updated["dependencies"])


def test_delete_dependency_404(client, home_id):
    client.post(f"/api/homes/{home_id}/build/start", json={})
    resp = client.delete(f"/api/homes/{home_id}/build/dependencies/nope")
    assert resp.status_code == 404


def test_upload_and_get_task_attachment(client, home_id):
    data = client.post(f"/api/homes/{home_id}/build/start", json={}).json()
    task_id = data["tasks"][0]["id"]
    resp = client.post(
        f"/api/homes/{home_id}/build/tasks/{task_id}/attachments",
        files={"file": ("photo.jpg", b"\xff\xd8\xff\xe0" + b"\x00" * 100, "image/jpeg")},
    )
    assert resp.status_code == 201
    assert resp.json()["filename"] == "photo.jpg"
    updated = client.get(f"/api/homes/{home_id}/build").json()
    task = next(t for t in updated["tasks"] if t["id"] == task_id)
    assert "photo.jpg" in task["attachments"]

    get_resp = client.get(f"/api/homes/{home_id}/build/tasks/{task_id}/attachments/photo.jpg")
    assert get_resp.status_code == 200


def test_upload_attachment_unsupported_type_rejected(client, home_id):
    data = client.post(f"/api/homes/{home_id}/build/start", json={}).json()
    task_id = data["tasks"][0]["id"]
    resp = client.post(
        f"/api/homes/{home_id}/build/tasks/{task_id}/attachments",
        files={"file": ("notes.txt", b"hello", "text/plain")},
    )
    assert resp.status_code == 400


def test_delete_task_attachment(client, home_id):
    data = client.post(f"/api/homes/{home_id}/build/start", json={}).json()
    task_id = data["tasks"][0]["id"]
    client.post(
        f"/api/homes/{home_id}/build/tasks/{task_id}/attachments",
        files={"file": ("photo.jpg", b"\xff\xd8\xff\xe0" + b"\x00" * 100, "image/jpeg")},
    )
    resp = client.delete(f"/api/homes/{home_id}/build/tasks/{task_id}/attachments/photo.jpg")
    assert resp.status_code == 204
    updated = client.get(f"/api/homes/{home_id}/build").json()
    task = next(t for t in updated["tasks"] if t["id"] == task_id)
    assert "photo.jpg" not in task["attachments"]


def test_delete_task_removes_attachments_dir(client, tmp_path, home_id):
    data = client.post(f"/api/homes/{home_id}/build/start", json={}).json()
    task_id = data["tasks"][0]["id"]
    client.post(
        f"/api/homes/{home_id}/build/tasks/{task_id}/attachments",
        files={"file": ("photo.jpg", b"\xff\xd8\xff\xe0" + b"\x00" * 100, "image/jpeg")},
    )
    client.delete(f"/api/homes/{home_id}/build/tasks/{task_id}")
    attach_dir = tmp_path / "homes" / home_id / "build-attachments" / task_id
    assert not attach_dir.exists()
