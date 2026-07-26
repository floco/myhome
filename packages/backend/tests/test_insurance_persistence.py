from myhome.models_insurance import InsurancePolicy, InsuranceDocument
from myhome.persistence_insurance import (
    delete_attachment,
    get_attachment_path,
    load_insurance,
    save_attachment,
    save_insurance,
)

HOME_ID = "test-home"


def _setup(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    (tmp_path / "homes" / HOME_ID).mkdir(parents=True)
    from myhome.db import get_engine
    from myhome.schema import homes as homes_table
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(homes_table.insert().values(
            id=HOME_ID, name="Test Home", type="existing", created_at="2026-01-01T00:00:00+00:00",
        ))


def make_doc() -> InsuranceDocument:
    return InsuranceDocument(policies=[
        InsurancePolicy(
            id="ins1", name="Home Insurance — AXA", categoryId="icat-home",
            premiumAmount=45.0, premiumFrequency="monthly", includeInCosts=True,
            startDate="2026-01-01", endDate="2027-01-01",
        )
    ])


def test_load_returns_empty_when_missing(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    doc = load_insurance(HOME_ID)
    assert doc.policies == []


def test_round_trip(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    save_insurance(HOME_ID, make_doc())
    loaded = load_insurance(HOME_ID)
    p = loaded.policies[0]
    assert p.id == "ins1"
    assert p.name == "Home Insurance — AXA"
    assert p.categoryId == "icat-home"
    assert p.premiumAmount == 45.0
    assert p.premiumFrequency == "monthly"
    assert p.includeInCosts is True
    assert p.attachments == []
    assert p.linkedCostEntryId is None


def test_round_trip_preserves_order(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    doc = InsuranceDocument(policies=[
        InsurancePolicy(id="ins1", name="A", categoryId="icat-home", premiumFrequency="annual", includeInCosts=False),
        InsurancePolicy(id="ins2", name="B", categoryId="icat-travel", premiumFrequency="annual", includeInCosts=False),
    ])
    save_insurance(HOME_ID, doc)
    loaded = load_insurance(HOME_ID)
    assert [p.id for p in loaded.policies] == ["ins1", "ins2"]


def test_attachment_save_and_delete(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    save_attachment(HOME_ID, "ins1", "policy.pdf", b"%PDF test")
    path = get_attachment_path(HOME_ID, "ins1", "policy.pdf")
    assert path.exists()
    assert path.read_bytes() == b"%PDF test"
    assert delete_attachment(HOME_ID, "ins1", "policy.pdf") is True
    assert not path.exists()


def test_delete_attachment_missing_returns_false(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    assert delete_attachment(HOME_ID, "ins1", "nope.pdf") is False
