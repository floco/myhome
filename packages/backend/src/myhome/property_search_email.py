# packages/backend/src/myhome/property_search_email.py
"""Brevo transactional emails for the AI property search (digest + failure)."""
from __future__ import annotations

import logging
from html import escape
from urllib.parse import urlsplit

import httpx

from . import persistence_property_search as ps
from .models_property_search import PropertySearch, PropertySearchConfig, PropertySearchRun, PropertySuggestion

log = logging.getLogger(__name__)

BREVO_URL = "https://api.brevo.com/v3/smtp/email"
TIMEOUT_S = 20


class EmailError(Exception):
    pass


def _hosts(sites: list[str]) -> list[str]:
    hosts = set()
    for s in sites:
        host = (urlsplit(s).netloc or s).lower().strip()
        if host.startswith("www."):
            host = host[4:]
        if host:
            hosts.add(host)
    return sorted(hosts)


def _money(price: float | None, currency: str | None) -> str:
    if price is None:
        return ""
    return f"{price:,.0f} {currency or ''}".strip()


def _facts(item: PropertySuggestion) -> list[str]:
    facts = [_money(item.price, item.currency)]
    if item.landSize is not None:
        facts.append(f"land {item.landSize:,.0f} m²")
    if item.builtSize is not None:
        facts.append(f"built {item.builtSize:,.0f} m²")
    facts += [item.location, item.sourceSite]
    return [f for f in facts if f]


def _usage_lines(run: PropertySearchRun) -> list[str]:
    u = run.usage
    if u is None:
        return ["n/a"]
    lines = [f"Total tokens: {u.totalTokens:,}"]
    lines += [f"  {model}: {n:,}" for model, n in sorted(u.tokensByModel.items())]
    lines += [f"{q.label}: {q.usedPct}% used" if q.usedPct is not None else f"{q.label}: n/a" for q in u.quotas]
    return lines


def _footer(run: PropertySearchRun) -> tuple[str, str]:
    hosts = _hosts(run.sites)
    usage = _usage_lines(run)
    text = "\nSites queried:\n" + ("\n".join(f"- {h}" for h in hosts) or "- (none reported)")
    text += "\n\nUsage:\n" + "\n".join(usage) + "\n"
    html = ("<h3>Sites queried</h3><ul>" + ("".join(f"<li>{escape(h)}</li>" for h in hosts) or "<li>(none reported)</li>")
            + "</ul><h3>Usage</h3><ul>" + "".join(f"<li>{escape(line.strip())}</li>" for line in usage) + "</ul>")
    return html, text


def render_digest(search: PropertySearch, run: PropertySearchRun, items: list[PropertySuggestion],
                  app_base_url: str) -> tuple[str, str, str]:
    n = len(items)
    subject = f"{n} new propert{'y' if n == 1 else 'ies'} — {search.name}"
    html_parts = [f"<h2>{escape(subject)}</h2>"]
    text_parts = [subject, ""]
    for item in items:
        facts = " · ".join(_facts(item))
        html_parts.append(
            f'<div style="margin-bottom:16px"><a href="{escape(item.listingUrl, quote=True)}"><strong>'
            f"{escape(item.title)}</strong></a><br>{escape(facts)}<br><em>{escape(item.reason)}</em></div>"
        )
        text_parts += [f"* {item.title}", f"  {facts}", f"  {item.reason}", f"  {item.listingUrl}", ""]
    if app_base_url:
        link = f"{app_base_url.rstrip('/')}/#/properties"
        html_parts.append(f'<p><a href="{escape(link, quote=True)}">Open the suggestions in My Home</a></p>')
        text_parts.append(f"Open the suggestions in My Home: {link}")
    fhtml, ftext = _footer(run)
    return subject, "".join(html_parts) + fhtml, "\n".join(text_parts) + ftext


def render_failure(search: PropertySearch, run: PropertySearchRun) -> tuple[str, str, str]:
    subject = f"Property search failed — {search.name}"
    reason = run.error or run.status
    fhtml, ftext = _footer(run)
    return (subject, f"<h2>{escape(subject)}</h2><p>{escape(reason)}</p>" + fhtml,
            f"{subject}\n\n{reason}\n" + ftext)


def send_brevo(cfg: PropertySearchConfig, subject: str, html: str, text: str) -> None:
    if not cfg.brevoApiKey or not cfg.senderEmail or not cfg.recipients:
        raise EmailError("Brevo API key, sender email and at least one recipient are required")
    payload = {
        "sender": {"email": cfg.senderEmail, "name": cfg.senderName or "My Home"},
        "to": [{"email": r} for r in cfg.recipients],
        "subject": subject, "htmlContent": html, "textContent": text,
    }
    try:
        resp = httpx.post(BREVO_URL, json=payload, timeout=TIMEOUT_S,
                          headers={"api-key": cfg.brevoApiKey, "accept": "application/json"})
    except httpx.HTTPError as e:
        raise EmailError(f"Brevo unreachable: {e}") from e
    if resp.status_code >= 300:
        try:
            detail = resp.json().get("message") or resp.text
        except ValueError:
            detail = resp.text
        raise EmailError(f"Brevo error {resp.status_code}: {detail}")


def _config_complete(cfg: PropertySearchConfig) -> bool:
    return bool(cfg.brevoApiKey and cfg.senderEmail and cfg.recipients)


def _send_and_record(home_id: str, run: PropertySearchRun, rendered: tuple[str, str, str]) -> None:
    cfg = ps.load_config(home_id)
    if not _config_complete(cfg):
        return
    try:
        send_brevo(cfg, *rendered)
    except EmailError as e:
        log.warning("Property search email failed for home %s: %s", home_id, e)
        run.emailError = str(e)[:1000]
        ps.update_run(home_id, run)


def send_digest_if_any(home_id: str, search: PropertySearch, run: PropertySearchRun,
                       items: list[PropertySuggestion]) -> None:
    if not items:
        return
    cfg = ps.load_config(home_id)
    _send_and_record(home_id, run, render_digest(search, run, items, cfg.appBaseUrl))


def send_failure(home_id: str, search: PropertySearch, run: PropertySearchRun) -> None:
    _send_and_record(home_id, run, render_failure(search, run))


def send_test(home_id: str) -> None:
    cfg = ps.load_config(home_id)
    search = PropertySearch(id="test", name="Test search", prompt="-", createdAt="")
    run = PropertySearchRun(id="test", searchId="test", slot="test", startedAt="", status="succeeded",
                            sites=["https://example.com"])
    item = PropertySuggestion(id="test", searchId="test", runId="test", title="Example listing",
                              listingUrl="https://example.com/listing", price=150000, currency="EUR",
                              landSize=800, location="Novo Mesto", sourceSite="example.com",
                              reason="This is a test email from My Home.", createdAt="")
    send_brevo(cfg, *render_digest(search, run, [item], cfg.appBaseUrl))
