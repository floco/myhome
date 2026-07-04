def test_get_mcp_config_defaults_disabled(client):
    resp = client.get("/api/mcp/config")
    assert resp.status_code == 200
    assert resp.json() == {"enabled": False}


def test_put_mcp_config_enables(client):
    resp = client.put("/api/mcp/config", json={"enabled": True})
    assert resp.status_code == 200
    assert resp.json() == {"enabled": True}
    assert client.get("/api/mcp/config").json() == {"enabled": True}


def test_mcp_config_forbidden_for_non_admin(ro_client):
    resp = ro_client.get("/api/mcp/config")
    assert resp.status_code == 403
    resp2 = ro_client.put("/api/mcp/config", json={"enabled": True})
    assert resp2.status_code == 403
