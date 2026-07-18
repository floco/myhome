import pytest
from myhome.models_locations import Location, LocationCriterion, LocationRating, LocationsDocument
from myhome.persistence_locations import DEFAULT_CRITERIA, load_locations, save_locations, seed_default_criteria


def make_doc() -> LocationsDocument:
    return LocationsDocument(
        criteria=[LocationCriterion(id="crit1", name="Cost of Living", description="How expensive", weight="high")],
        locations=[Location(id="loc1", name="Ljubljana", emoji="🇸🇮")],
        ratings=[LocationRating(locationId="loc1", criterionId="crit1", score=4, note="Cheap enough")],
    )


def test_load_locations_empty(client, home_id):
    doc = load_locations(home_id)
    assert doc.criteria == []
    assert doc.locations == []
    assert doc.ratings == []


def test_save_and_load_round_trip(client, home_id):
    save_locations(home_id, make_doc())
    doc = load_locations(home_id)
    assert doc.criteria[0].name == "Cost of Living"
    assert doc.criteria[0].weight == "high"
    assert doc.locations[0].name == "Ljubljana"
    assert doc.locations[0].emoji == "🇸🇮"
    assert doc.ratings[0].score == 4
    assert doc.ratings[0].note == "Cheap enough"


def test_save_removes_criterion_and_its_ratings_together(client, home_id):
    # save_locations persists exactly what it's given -- callers (routes/MCP
    # tools) are responsible for dropping ratings that reference a removed
    # criterion/location before calling save, same as consumables/transactions.
    save_locations(home_id, make_doc())
    doc = load_locations(home_id)
    doc.criteria = []
    doc.ratings = [r for r in doc.ratings if r.criterionId != "crit1"]
    save_locations(home_id, doc)
    reloaded = load_locations(home_id)
    assert reloaded.criteria == []
    assert reloaded.ratings == []


def test_save_removes_location_and_its_ratings_together(client, home_id):
    save_locations(home_id, make_doc())
    doc = load_locations(home_id)
    doc.locations = []
    doc.ratings = [r for r in doc.ratings if r.locationId != "loc1"]
    save_locations(home_id, doc)
    reloaded = load_locations(home_id)
    assert reloaded.locations == []
    assert reloaded.ratings == []


def test_seed_default_criteria(client, home_id):
    seed_default_criteria(home_id)
    doc = load_locations(home_id)
    assert len(doc.criteria) == len(DEFAULT_CRITERIA) == 11
    assert doc.locations == []
    names = [c.name for c in doc.criteria]
    assert "Cost of Living" in names
    assert "Healthcare" in names
    assert all(c.weight == "medium" for c in doc.criteria)
    assert all(c.description != "" for c in doc.criteria)
