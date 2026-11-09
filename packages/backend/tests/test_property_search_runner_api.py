from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from myhome import persistence_property_search as ps
from myhome.main import app
from myhome.models_property_search import PropertySearchRun

CLAIM = "/api/property-search/runner/claim"


def _search(client, home_id, **kw):
    body = {"name": "Plots", "prompt": "land near Novo Mesto", "maxResultsPerRun": 10, "maxListingAgeDays": 7, **kw}
    s = client.post(f"/api/homes/{home_id}/property-searches", json=body).json()
    client.post(f"/api/homes/{home_id}/property-searches/{s['id']}/run-now")
    return s


def _listing(n, **kw):
    return {"title": f"Plot {n}", "listingUrl": f"https://a.si/oglas/{n}", "reason": "fits", "type": "land",
            "price": 100000 + n * 10000, "landSize": 800 + n * 100, "location": "Novo Mesto",
            "sourceSite": "a.si", **kw}


def _complete(client, run_id, listings, **kw):
    return client.post(f"/api/property-search/runner/runs/{run_id}/complete",
                       json={"listings": listings, "sitesQueried": ["https://a.si/search"], **kw})


def _rerun(client, home_id, search_id):
    client.post(f"/api/homes/{home_id}/property-searches/{search_id}/run-now")
    return client.post(CLAIM).json()


def test_claim_returns_due_search_and_204_when_none(client, home_id):
    assert client.post(CLAIM).status_code == 204
    s = _search(client, home_id)
    resp = client.post(CLAIM)
    assert resp.status_code == 200
    c = resp.json()
    assert c["searchId"] == s["id"] and c["homeId"] == home_id and c["prompt"] == "land near Novo Mesto"
    assert c["maxResultsPerRun"] == 10 and c["maxListingAgeDays"] == 7 and c["today"] and c["seen"] == []
    # claim consumed the run-now request
    assert ps.get_search(home_id, s["id"]).runRequestedAt is None


def test_claim_twice_returns_204_second_time(client, home_id):
    _search(client, home_id)
    assert client.post(CLAIM).status_code == 200
    assert client.post(CLAIM).status_code == 204


def test_stale_running_run_is_reclaimed(client, home_id):
    s = _search(client, home_id)
    run_id = client.post(CLAIM).json()["runId"]
    run = ps.get_run(home_id, run_id)
    run.startedAt = (datetime.now(timezone.utc) - timedelta(hours=3)).isoformat()
    ps.update_run(home_id, run)
    # Manual slot is consumed; a stale run marks failed and the user re-requests.
    client.post(f"/api/homes/{home_id}/property-searches/{s['id']}/run-now")
    assert client.post(CLAIM).status_code == 200
    assert ps.get_run(home_id, run_id).status == "failed"


def test_complete_stores_new_and_counts_duplicates(client, home_id):
    s = _search(client, home_id)
    c = client.post(CLAIM).json()
    r = _complete(client, c["runId"], [_listing(1), _listing(2)])
    assert r.status_code == 200 and r.json() == {"received": 2, "new": 2, "duplicates": 0}
    c2 = _rerun(client, home_id, s["id"])
    assert {x["url"] for x in c2["seen"]} == {"https://a.si/oglas/1", "https://a.si/oglas/2"}
    r2 = _complete(client, c2["runId"], [_listing(1), _listing(2, listingUrl="https://www.a.si/oglas/2/?utm_x=1"), _listing(3)])
    assert r2.json() == {"received": 3, "new": 1, "duplicates": 2}
    run = ps.get_run(home_id, c2["runId"])
    assert run.status == "succeeded" and run.newCount == 1 and run.sites == ["https://a.si/search"]
    assert ps.get_search(home_id, s["id"]).lastRunStatus == "succeeded"
    assert len(client.get(f"/api/homes/{home_id}/property-suggestions").json()) == 3


def test_complete_dedups_within_batch(client, home_id):
    _search(client, home_id)
    c = client.post(CLAIM).json()
    assert _complete(client, c["runId"], [_listing(1), _listing(1)]).json() == {"received": 2, "new": 1, "duplicates": 1}


def test_complete_skips_malformed_listings(client, home_id):
    _search(client, home_id)
    c = client.post(CLAIM).json()
    bad = [{"title": "x"}, {"title": "ok", "listingUrl": "https://a.si/9", "price": "abc"}, "nonsense",
           {"title": "t", "listingUrl": "ftp://a.si/1"}]
    r = _complete(client, c["runId"], bad + [_listing(1)])
    assert r.status_code == 200 and r.json()["new"] == 1 and r.json()["received"] == 5


def test_complete_drops_too_old_listings(client, home_id):
    _search(client, home_id, maxListingAgeDays=7)
    c = client.post(CLAIM).json()
    today = datetime.fromisoformat(c["today"])
    old = (today - timedelta(days=10)).date().isoformat()
    fresh = (today - timedelta(days=2)).date().isoformat()
    r = _complete(client, c["runId"], [_listing(1, publishedAt=old), _listing(2, publishedAt=fresh), _listing(3, publishedAt="soon")])
    assert r.json()["new"] == 2


def test_complete_respects_max_results(client, home_id):
    _search(client, home_id, maxResultsPerRun=2)
    c = client.post(CLAIM).json()
    _complete(client, c["runId"], [_listing(i) for i in range(5)])
    titles = [g["title"] for g in client.get(f"/api/homes/{home_id}/property-suggestions").json()]
    assert sorted(titles) == ["Plot 0", "Plot 1"]


def test_complete_skips_existing_property_by_fingerprint(client, home_id):
    client.post(f"/api/homes/{home_id}/properties", json={
        "name": "Known", "type": "land", "price": 110000, "landSize": 900, "address": "Novo mesto, Slovenia"})
    _search(client, home_id)
    c = client.post(CLAIM).json()
    r = _complete(client, c["runId"], [_listing(1, listingUrl="https://other.si/x"), _listing(5)])
    assert r.json() == {"received": 2, "new": 1, "duplicates": 1}


def test_complete_unknown_or_finished_run(client, home_id):
    assert _complete(client, "nope", []).status_code == 404
    _search(client, home_id)
    c = client.post(CLAIM).json()
    _complete(client, c["runId"], [])
    assert _complete(client, c["runId"], []).status_code == 409


def test_complete_stores_usage(client, home_id):
    _search(client, home_id)
    c = client.post(CLAIM).json()
    usage = {"provider": "claude-code", "tokensByModel": {"m": 1200}, "totalTokens": 1200,
             "quotas": [{"label": "Weekly", "usedPct": 34}]}
    _complete(client, c["runId"], [], usage=usage, searchQueries=["q1"])
    run = ps.get_run(home_id, c["runId"])
    assert run.usage.totalTokens == 1200 and run.usage.quotas[0].usedPct == 34 and run.searchQueries == ["q1"]


def test_fail_usage_limit_leaves_search_due(client, home_id):
    s = client.post(f"/api/homes/{home_id}/property-searches", json={"name": "n", "prompt": "p"}).json()
    # Make a scheduled slot exist: created long ago, daily at 00:00.
    search = ps.get_search(home_id, s["id"])
    search.createdAt = "2026-01-01T00:00:00+00:00"
    search.time = "00:00"
    ps.update_search(home_id, search)
    c = client.post(CLAIM).json()
    r = client.post(f"/api/property-search/runner/runs/{c['runId']}/fail", json={"reason": "usage_limit", "message": "limit"})
    assert r.status_code == 204
    assert ps.get_run(home_id, c["runId"]).status == "usage_limited"
    assert client.post(CLAIM).status_code == 204  # backoff: not retried on the next tick
    run = ps.get_run(home_id, c["runId"])
    run.finishedAt = (datetime.now(timezone.utc) - timedelta(minutes=61)).isoformat()
    ps.update_run(home_id, run)
    assert client.post(CLAIM).status_code == 200  # retried after an hour


def test_fail_error_marks_failed(client, home_id):
    s = _search(client, home_id)
    c = client.post(CLAIM).json()
    client.post(f"/api/property-search/runner/runs/{c['runId']}/fail", json={"reason": "error", "message": "boom"})
    got = ps.get_search(home_id, s["id"])
    assert got.lastRunStatus == "failed" and got.lastRunError == "boom"


def test_ro_token_cannot_claim(client, home_id):
    token = client.post("/api/auth/tokens", json={"name": "runner", "role": "ro"}).json()["token"]
    tc = TestClient(app)
    assert tc.post(CLAIM, headers={"Authorization": f"Bearer {token}"}).status_code == 403


def test_normal_token_can_claim(client, home_id):
    token = client.post("/api/auth/tokens", json={"name": "runner", "role": "normal"}).json()["token"]
    tc = TestClient(app)
    assert tc.post(CLAIM, headers={"Authorization": f"Bearer {token}"}).status_code == 204


def test_complete_skips_nan_and_infinite_numbers(client, home_id):
    _search(client, home_id)
    c = client.post(CLAIM).json()
    body = ('{"listings": [{"title": "a", "listingUrl": "https://a.si/n", "price": NaN, "landSize": 800},'
            ' {"title": "b", "listingUrl": "https://a.si/i", "price": 1e400, "landSize": 800},'
            ' {"title": "c", "listingUrl": "https://a.si/s", "price": "NaN", "landSize": 800},'
            ' {"title": "ok", "listingUrl": "https://a.si/ok"}]}')
    r = client.post(f"/api/property-search/runner/runs/{c['runId']}/complete", content=body,
                    headers={"Content-Type": "application/json"})
    assert r.status_code == 200 and r.json()["new"] == 1


def test_complete_records_counts_on_search(client, home_id):
    s = _search(client, home_id)
    c = client.post(CLAIM).json()
    _complete(client, c["runId"], [_listing(1), _listing(1)])
    got = ps.get_search(home_id, s["id"])
    assert got.lastRunNew == 1 and got.lastRunDuplicates == 1 and got.lastRunEmailError is None


def test_complete_stores_country_and_city(client, home_id):
    _search(client, home_id)
    c = client.post(CLAIM).json()
    _complete(client, c["runId"], [_listing(1, country="Slovenia", region="Dolenjska", city="Novo mesto"), _listing(2)])
    by_url = {g["listingUrl"]: g for g in client.get(f"/api/homes/{home_id}/property-suggestions").json()}
    assert by_url["https://a.si/oglas/1"]["country"] == "Slovenia"
    assert by_url["https://a.si/oglas/1"]["city"] == "Novo mesto"
    assert by_url["https://a.si/oglas/1"]["region"] == "Dolenjska"
    assert by_url["https://a.si/oglas/2"]["country"] is None and by_url["https://a.si/oglas/2"]["city"] is None
    assert by_url["https://a.si/oglas/2"]["region"] is None
