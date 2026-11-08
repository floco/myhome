from datetime import datetime, timedelta, timezone

from myhome import persistence_property_search as ps
from myhome.models_property_search import PropertySearch, PropertySearchConfig, PropertySearchRun, PropertySuggestion
from myhome.persistence_properties import reset_properties
from myhome.property_search_cleanup import cleanup_home

NOW = datetime(2026, 11, 8, 3, 0, tzinfo=timezone.utc)


def _seed(home_id):
    ps.insert_search(home_id, PropertySearch(id="s1", name="n", prompt="p", createdAt="2026-01-01T00:00:00+00:00"))
    old = (NOW - timedelta(days=40)).isoformat()
    recent = (NOW - timedelta(days=5)).isoformat()
    items = []
    for id, status, created in [("old-new", "new", old), ("old-rej", "rejected", old), ("old-pin", "pinned", old),
                                ("old-acc", "accepted", old), ("recent", "new", recent)]:
        items.append(PropertySuggestion(id=id, searchId="s1", runId="r", title=id, listingUrl=f"https://a.si/{id}",
                                        status=status, createdAt=created))
    ps.insert_suggestions(home_id, items)
    ps.add_seen(home_id, [(f"https://a.si/{i.id}", None) for i in items])


def test_cleanup_deletes_old_new_and_rejected(client, home_id):
    _seed(home_id)
    assert cleanup_home(home_id, NOW) == 2
    remaining = {g.id for g in ps.list_suggestions(home_id)}
    assert remaining == {"old-pin", "old-acc", "recent"}


def test_cleanup_respects_retention_setting(client, home_id):
    _seed(home_id)
    ps.save_config(home_id, PropertySearchConfig(retentionDays=3))
    assert cleanup_home(home_id, NOW) == 3


def test_cleanup_keeps_pinned_and_accepted(client, home_id):
    _seed(home_id)
    cleanup_home(home_id, NOW)
    assert ps.get_suggestion(home_id, "old-pin") is not None and ps.get_suggestion(home_id, "old-acc") is not None


def test_cleanup_prunes_old_runs(client, home_id):
    _seed(home_id)
    ps.insert_run(home_id, PropertySearchRun(id="r-old", searchId="s1", slot="a", status="succeeded",
                                             startedAt=(NOW - timedelta(days=100)).isoformat()))
    ps.insert_run(home_id, PropertySearchRun(id="r-new", searchId="s1", slot="b", status="succeeded",
                                             startedAt=(NOW - timedelta(days=10)).isoformat()))
    cleanup_home(home_id, NOW)
    assert [r.id for r in ps.list_runs(home_id, "s1")] == ["r-new"]


def test_cleanup_keeps_seen_so_no_resuggest(client, home_id):
    _seed(home_id)
    cleanup_home(home_id, NOW)
    s = client.post(f"/api/homes/{home_id}/property-searches", json={"name": "n2", "prompt": "p"}).json()
    client.post(f"/api/homes/{home_id}/property-searches/{s['id']}/run-now")
    run_id = client.post("/api/property-search/runner/claim").json()["runId"]
    r = client.post(f"/api/property-search/runner/runs/{run_id}/complete",
                    json={"listings": [{"title": "again", "listingUrl": "https://a.si/old-new"}]})
    assert r.json() == {"received": 1, "new": 0, "duplicates": 1}


def test_reset_properties_clears_suggestions(client, home_id):
    _seed(home_id)
    reset_properties(home_id)
    assert ps.list_suggestions(home_id) == [] and ps.list_searches(home_id) == []
    assert ps.seen_keys(home_id) == (set(), set())
