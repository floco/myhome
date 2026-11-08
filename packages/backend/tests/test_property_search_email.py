import httpx
import pytest
import respx

from myhome import persistence_property_search as ps
from myhome.models_property_search import (
    PropertySearch,
    PropertySearchConfig,
    PropertySearchRun,
    PropertySuggestion,
    QuotaUsage,
    SearchUsage,
)
from myhome.property_search_email import EmailError, render_digest, render_failure, send_brevo

BREVO = "https://api.brevo.com/v3/smtp/email"
CLAIM = "/api/property-search/runner/claim"


def _search():
    return PropertySearch(id="s1", name="Plots Novo Mesto", prompt="p", createdAt="2026-11-01T00:00:00+00:00")


def _run():
    return PropertySearchRun(
        id="r1", searchId="s1", slot="x", startedAt="2026-11-08T08:00:00+00:00", status="succeeded",
        sites=["https://www.nepremicnine.net/oglasi?x=1", "https://bolha.com/a", "https://nepremicnine.net/b"],
        usage=SearchUsage(provider="claude-code", tokensByModel={"claude-x": 1500}, totalTokens=1500,
                          quotas=[QuotaUsage(label="Weekly", usedPct=34), QuotaUsage(label="5-hour", usedPct=None)]),
    )


def _item(title="Nice plot"):
    return PropertySuggestion(id="g1", searchId="s1", runId="r1", title=title, listingUrl="https://a.si/1",
                              price=150000, currency="EUR", landSize=820, location="Novo Mesto",
                              sourceSite="nepremicnine.net", reason="fits", createdAt="2026-11-08T08:00:00+00:00")


CFG = PropertySearchConfig(brevoApiKey="xkeysib-1", senderEmail="home@x.si", senderName="My Home",
                           recipients=["a@x.si", "b@x.si"], appBaseUrl="http://ha.local:8000/")


def test_digest_subject_and_link():
    subject, html, text = render_digest(_search(), _run(), [_item()], CFG.appBaseUrl)
    assert subject == "1 new property — Plots Novo Mesto"
    assert "http://ha.local:8000/#/properties" in html and "https://a.si/1" in html
    assert "150,000 EUR" in text and "820 m²" in text


def test_digest_contains_sites_and_usage():
    _, html, text = render_digest(_search(), _run(), [_item(), _item("Other")], "")
    for body in (html, text):
        assert "bolha.com" in body and "nepremicnine.net" in body
        assert "Weekly: 34% used" in body and "5-hour: n/a" in body and "1,500" in body
    assert text.count("nepremicnine.net") >= 1 and "www.nepremicnine.net" not in text
    assert "#/properties" not in html


def test_digest_escapes_html():
    _, html, _ = render_digest(_search(), _run(), [_item("<script>x</script>")], "")
    assert "<script>" not in html and "&lt;script&gt;" in html


def test_failure_subject():
    run = _run()
    run.error = "boom"
    subject, html, text = render_failure(_search(), run)
    assert subject == "Property search failed — Plots Novo Mesto" and "boom" in text


@respx.mock
def test_send_brevo_posts_expected_payload():
    route = respx.post(BREVO).mock(return_value=httpx.Response(201, json={"messageId": "m"}))
    send_brevo(CFG, "S", "<p>h</p>", "t")
    req = route.calls.last.request
    assert req.headers["api-key"] == "xkeysib-1"
    import json
    body = json.loads(req.content)
    assert body["to"] == [{"email": "a@x.si"}, {"email": "b@x.si"}]
    assert body["sender"] == {"email": "home@x.si", "name": "My Home"}
    assert body["subject"] == "S" and body["htmlContent"] == "<p>h</p>" and body["textContent"] == "t"


@respx.mock
def test_send_brevo_raises_on_401():
    respx.post(BREVO).mock(return_value=httpx.Response(401, json={"message": "Key not found"}))
    with pytest.raises(EmailError, match="Key not found"):
        send_brevo(CFG, "S", "h", "t")


def test_send_brevo_raises_when_incomplete():
    with pytest.raises(EmailError):
        send_brevo(PropertySearchConfig(), "S", "h", "t")


def _setup_run(client, home_id):
    ps.save_config(home_id, CFG)
    s = client.post(f"/api/homes/{home_id}/property-searches", json={"name": "Plots", "prompt": "p"}).json()
    client.post(f"/api/homes/{home_id}/property-searches/{s['id']}/run-now")
    return client.post(CLAIM).json()["runId"]


LISTING = {"title": "Plot", "listingUrl": "https://a.si/1", "reason": "fits"}


@respx.mock
def test_complete_sends_digest(client, home_id):
    route = respx.post(BREVO).mock(return_value=httpx.Response(201, json={}))
    run_id = _setup_run(client, home_id)
    client.post(f"/api/property-search/runner/runs/{run_id}/complete", json={"listings": [LISTING]})
    assert route.call_count == 1


@respx.mock
def test_complete_survives_brevo_failure(client, home_id):
    respx.post(BREVO).mock(return_value=httpx.Response(500, json={"message": "down"}))
    run_id = _setup_run(client, home_id)
    resp = client.post(f"/api/property-search/runner/runs/{run_id}/complete", json={"listings": [LISTING]})
    assert resp.status_code == 200
    run = ps.get_run(home_id, run_id)
    assert run.status == "succeeded" and run.emailError and "down" in run.emailError


@respx.mock
def test_no_email_when_zero_new(client, home_id):
    route = respx.post(BREVO).mock(return_value=httpx.Response(201, json={}))
    run_id = _setup_run(client, home_id)
    client.post(f"/api/property-search/runner/runs/{run_id}/complete", json={"listings": []})
    assert route.call_count == 0


@respx.mock
def test_fail_error_sends_failure_email(client, home_id):
    route = respx.post(BREVO).mock(return_value=httpx.Response(201, json={}))
    run_id = _setup_run(client, home_id)
    client.post(f"/api/property-search/runner/runs/{run_id}/fail", json={"reason": "error", "message": "boom"})
    assert route.call_count == 1


@respx.mock
def test_test_email_endpoint_502_on_brevo_error(client, home_id):
    ps.save_config(home_id, CFG)
    respx.post(BREVO).mock(return_value=httpx.Response(400, json={"message": "bad sender"}))
    resp = client.post(f"/api/homes/{home_id}/property-search-config/test-email")
    assert resp.status_code == 502 and "bad sender" in resp.json()["detail"]


@respx.mock
def test_test_email_endpoint_ok(client, home_id):
    ps.save_config(home_id, CFG)
    respx.post(BREVO).mock(return_value=httpx.Response(201, json={}))
    assert client.post(f"/api/homes/{home_id}/property-search-config/test-email").status_code == 204
