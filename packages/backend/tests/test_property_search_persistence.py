from myhome.models_property_search import (
    PropertySearch,
    PropertySearchConfig,
    PropertySearchRun,
    PropertySuggestion,
)
from myhome import persistence_property_search as ps


def _search(id="s1", name="Plots"):
    return PropertySearch(id=id, name=name, prompt="land near Novo Mesto", createdAt="2026-11-01T08:00:00+00:00")


def _suggestion(id="g1", search_id="s1", url="https://a.si/1"):
    return PropertySuggestion(
        id=id, searchId=search_id, runId="r1", title="Plot", listingUrl=url,
        createdAt="2026-11-02T08:00:00+00:00", price=150000, landSize=800, type="land",
    )


def _second_home(client) -> str:
    return client.post("/api/homes", json={"name": "Other", "type": "existing"}).json()["id"]


def test_search_roundtrip(client, home_id):
    s = _search()
    ps.insert_search(home_id, s)
    assert ps.get_search(home_id, "s1") == s
    s.name = "Renamed"
    ps.update_search(home_id, s)
    assert ps.get_search(home_id, "s1").name == "Renamed"


def test_searches_scoped_by_home(client, home_id):
    other = _second_home(client)
    ps.insert_search(home_id, _search("s1"))
    ps.insert_search(other, _search("s2"))
    assert [s.id for s in ps.list_searches(home_id)] == ["s1"]
    assert [s.id for s in ps.list_searches(other)] == ["s2"]
    assert ps.get_search(other, "s1") is None


def test_delete_search_keeps_seen(client, home_id):
    ps.insert_search(home_id, _search())
    ps.insert_suggestions(home_id, [_suggestion()])
    ps.add_seen(home_id, [("https://a.si/1", "fp1")])
    assert ps.delete_search(home_id, "s1") is True
    assert ps.list_suggestions(home_id) == []
    urls, fps = ps.seen_keys(home_id)
    assert "https://a.si/1" in urls and "fp1" in fps


def test_add_seen_ignores_existing_key(client, home_id):
    ps.add_seen(home_id, [("u1", None)])
    ps.add_seen(home_id, [("u1", "fp")])
    urls, _ = ps.seen_keys(home_id)
    assert urls == {"u1"}


def test_config_defaults(client, home_id):
    assert ps.load_config(home_id) == PropertySearchConfig()
    cfg = PropertySearchConfig(brevoApiKey="k", recipients=["a@b.c"], retentionDays=10)
    ps.save_config(home_id, cfg)
    assert ps.load_config(home_id) == cfg


def test_suggestion_status_update(client, home_id):
    ps.insert_search(home_id, _search())
    ps.insert_suggestions(home_id, [_suggestion()])
    assert ps.set_suggestion_status(home_id, "g1", "accepted", accepted_property_id="p1") is True
    g = ps.get_suggestion(home_id, "g1")
    assert g.status == "accepted" and g.acceptedPropertyId == "p1"
    assert [x.id for x in ps.list_suggestions(home_id, ["new", "pinned"])] == []
    assert ps.set_suggestion_status(home_id, "missing", "rejected") is False


def test_run_roundtrip_and_find(client, home_id):
    ps.insert_search(home_id, _search())
    run = PropertySearchRun(id="r1", searchId="s1", slot="x", startedAt="2026-11-02T08:00:00+00:00", status="running")
    ps.insert_run(home_id, run)
    run.status = "succeeded"
    run.sites = ["https://a.si"]
    ps.update_run(home_id, run)
    found = ps.find_run("r1")
    assert found is not None and found[0] == home_id and found[1].status == "succeeded"
    assert ps.list_runs(home_id, "s1")[0].sites == ["https://a.si"]


def test_recent_seen(client, home_id):
    ps.insert_search(home_id, _search())
    ps.insert_suggestions(home_id, [_suggestion("g1", url="https://a.si/1"), _suggestion("g2", url="https://a.si/2")])
    assert {r["url"] for r in ps.recent_seen(home_id)} == {"https://a.si/1", "https://a.si/2"}


def test_reset_clears_everything(client, home_id):
    ps.insert_search(home_id, _search())
    ps.insert_suggestions(home_id, [_suggestion()])
    ps.add_seen(home_id, [("u", None)])
    ps.save_config(home_id, PropertySearchConfig(retentionDays=5))
    ps.reset_property_search(home_id)
    assert ps.list_searches(home_id) == []
    assert ps.list_suggestions(home_id) == []
    assert ps.seen_keys(home_id) == (set(), set())
    assert ps.load_config(home_id) == PropertySearchConfig()
