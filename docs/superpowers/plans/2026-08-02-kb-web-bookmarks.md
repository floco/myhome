# KB Web Bookmarks Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let a user (via the KB page editor) or an MCP client paste/provide a URL and get a Notion-style "Web Bookmark" card — title, description, thumbnail image, favicon+domain, auto-fetched from the target page — embedded inline in a KB page.

**Architecture:** A new shared backend module `link_preview.py` does the security-sensitive work (SSRF-guarded fetch of a URL, HTML meta-tag parsing, HTML card rendering) and is used by both a new REST endpoint (`POST /api/homes/{home_id}/kb/link-preview`) and a new MCP tool (`add_kb_bookmark`). On the frontend, `MarkdownEditor.svelte` gets a new toolbar button that delegates URL collection to its parent via a callback prop (same pattern as the existing `onSlashPage`), and `KBPage.svelte` implements that callback with a small modal.

**Tech Stack:** Python 3.12, FastAPI, `httpx` (already a dependency), stdlib `html.parser`/`ipaddress`/`socket`, Svelte 5, `marked` + `DOMPurify`, `respx` (already a dev dependency) for mocking `httpx` in tests.

Design doc: `docs/superpowers/specs/2026-08-02-kb-web-bookmarks-design.md`.

## Global Constraints

- `fetch_link_preview(url)` **never raises for network/fetch/parse failure** — timeout, connection error, non-2xx, blocked private address, unresolvable host, non-HTML content-type, or no metadata found all fall back to `title=<hostname>, description="", image=None, favicon=None`. It raises `ValueError` **only** when `url` isn't an absolute `http`/`https` URL. Every caller (REST endpoint, MCP tool) relies on this: only the malformed-URL case needs its own error branch.
- SSRF guard: before fetching a URL (including every redirect hop), resolve its hostname via `socket.getaddrinfo` and reject (via `ValueError`, caught internally per the point above) if any resolved address is private/loopback/link-local/reserved/multicast (stdlib `ipaddress` predicates). Redirects are followed manually (`httpx.Client(follow_redirects=False)`, max 3 hops) specifically so each hop gets re-validated — plain `follow_redirects=True` would skip this and reopen a DNS-rebinding-style hole.
- **Tests must never depend on real DNS/network.** Every test that exercises `fetch_link_preview` (directly, via the REST endpoint, or via the MCP tool) must `monkeypatch.setattr(socket, "getaddrinfo", ...)` to a fake resolver returning a fixed public IP (`93.184.216.34`), and use `respx.mock` to intercept the `httpx` calls. Verified empirically during design that this sandbox's real DNS happens to work, but tests must not rely on that being true everywhere (CI, offline dev environments, etc).
- No new runtime dependency. HTML parsing uses stdlib `html.parser.HTMLParser`; no favicon service, no HTML-parsing library.
- Follow the existing `_xxx_impl(...)` / `@mcp.tool() async def xxx(ctx, ...)` split in `mcp_tools_kb.py`: the plain function does the work and raises `ValueError` on error; the tool wrapper does the role check then delegates.

---

## File Structure

- **Create** `packages/backend/src/myhome/link_preview.py` — `LinkPreview` dataclass, `fetch_link_preview`, `render_bookmark_html`, and the SSRF-guarded fetch/parse internals.
- **Create** `packages/backend/tests/test_link_preview.py`
- **Modify** `packages/backend/src/myhome/models_kb.py` — add `KBLinkPreviewRequest`.
- **Modify** `packages/backend/src/myhome/routes/kb.py` — add the `POST .../kb/link-preview` endpoint.
- **Modify** `packages/backend/tests/test_kb.py` — add endpoint tests.
- **Modify** `packages/backend/src/myhome/mcp_tools_kb.py` — add `_add_kb_bookmark_impl` + `add_kb_bookmark` tool.
- **Modify** `packages/backend/tests/test_mcp_tools_kb.py` — add tool tests.
- **Modify** `packages/editor/src/lib/components/ui/MarkdownEditor.svelte` — DOMPurify `target` fix, `onInsertBookmark` prop, 🔖 toolbar button, bookmark card CSS.
- **Modify** `packages/editor/test/MarkdownEditor.test.ts` — add tests.
- **Modify** `packages/editor/src/lib/kbStore.svelte.ts` — add `fetchLinkPreview`.
- **Modify** `packages/editor/test/kbStore.test.ts` — add tests.
- **Modify** `packages/editor/src/lib/components/KBPage.svelte` — bookmark URL modal, wires `onInsertBookmark`.
- **Modify** `packages/editor/test/KBPage.test.ts` — add tests (and a `link-preview` branch in the shared fake backend).
- **Modify** `packages/editor/src/lib/locales/en.json` and `fr.json` — new strings.

---

## Task 1: `link_preview.py` — SSRF-guarded fetch, parse, and render

**Files:**
- Create: `packages/backend/src/myhome/link_preview.py`
- Test: `packages/backend/tests/test_link_preview.py`

**Interfaces:**
- Produces: `LinkPreview` (dataclass: `url: str, title: str, description: str, image: str | None, favicon: str | None`), `fetch_link_preview(url: str) -> LinkPreview`, `render_bookmark_html(preview: LinkPreview) -> str` — both consumed by Task 2 (REST) and Task 3 (MCP tool).

- [ ] **Step 1: Write the failing tests**

Create `packages/backend/tests/test_link_preview.py`:

```python
import socket

import httpx
import pytest
import respx
from httpx import Response

from myhome.link_preview import LinkPreview, fetch_link_preview, render_bookmark_html


def _fake_getaddrinfo_public(*args, **kwargs):
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 0))]


def _fake_getaddrinfo_private(*args, **kwargs):
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.0.0.5", 0))]


def _fake_getaddrinfo_unresolvable(*args, **kwargs):
    raise socket.gaierror("Name or service not known")


@pytest.fixture(autouse=True)
def _public_dns(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", _fake_getaddrinfo_public)


def test_fetch_link_preview_extracts_og_tags():
    with respx.mock:
        respx.get("http://example.com/page").mock(
            return_value=Response(
                200,
                headers={"content-type": "text/html; charset=utf-8"},
                html='<html><head><title>Fallback</title>'
                     '<meta property="og:title" content="OG Title">'
                     '<meta property="og:description" content="OG Desc">'
                     '<meta property="og:image" content="/img/og.png">'
                     '<link rel="icon" href="/favicon.ico">'
                     '</head></html>',
            )
        )
        preview = fetch_link_preview("http://example.com/page")
    assert preview.title == "OG Title"
    assert preview.description == "OG Desc"
    assert preview.image == "http://example.com/img/og.png"
    assert preview.favicon == "http://example.com/favicon.ico"


def test_fetch_link_preview_falls_back_to_title_tag_and_meta_description():
    with respx.mock:
        respx.get("http://example.com/page").mock(
            return_value=Response(
                200,
                headers={"content-type": "text/html"},
                html='<html><head><title>Page Title</title>'
                     '<meta name="description" content="Meta Desc"></head></html>',
            )
        )
        preview = fetch_link_preview("http://example.com/page")
    assert preview.title == "Page Title"
    assert preview.description == "Meta Desc"
    assert preview.image is None


def test_fetch_link_preview_falls_back_to_hostname_when_nothing_found():
    with respx.mock:
        respx.get("http://example.com/page").mock(
            return_value=Response(200, headers={"content-type": "text/html"}, html="<html></html>")
        )
        preview = fetch_link_preview("http://example.com/page")
    assert preview.title == "example.com"
    assert preview.description == ""


def test_fetch_link_preview_follows_redirect_and_revalidates_host():
    with respx.mock:
        respx.get("http://example.com/page").mock(
            return_value=Response(301, headers={"location": "http://example.com/final"})
        )
        respx.get("http://example.com/final").mock(
            return_value=Response(
                200,
                headers={"content-type": "text/html"},
                html='<meta property="og:title" content="Final Page">',
            )
        )
        preview = fetch_link_preview("http://example.com/page")
    assert preview.title == "Final Page"


def test_fetch_link_preview_rejects_private_address(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", _fake_getaddrinfo_private)
    with respx.mock:
        preview = fetch_link_preview("http://internal.example/page")
    assert preview.title == "internal.example"
    assert preview.description == ""


def test_fetch_link_preview_falls_back_when_host_unresolvable(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", _fake_getaddrinfo_unresolvable)
    with respx.mock:
        preview = fetch_link_preview("http://nowhere.example/page")
    assert preview.title == "nowhere.example"


def test_fetch_link_preview_falls_back_on_non_html_content_type():
    with respx.mock:
        respx.get("http://example.com/file.pdf").mock(
            return_value=Response(200, headers={"content-type": "application/pdf"}, content=b"%PDF-1.4")
        )
        preview = fetch_link_preview("http://example.com/file.pdf")
    assert preview.title == "example.com"


def test_fetch_link_preview_falls_back_on_connection_error():
    with respx.mock:
        respx.get("http://example.com/page").mock(side_effect=httpx.ConnectError("boom"))
        preview = fetch_link_preview("http://example.com/page")
    assert preview.title == "example.com"


def test_fetch_link_preview_rejects_non_http_scheme():
    with pytest.raises(ValueError, match="must be an absolute http"):
        fetch_link_preview("ftp://example.com/x")


def test_render_bookmark_html_escapes_title_and_description():
    preview = LinkPreview(
        url="https://example.com", title="<script>alert(1)</script>", description="a & b",
        image=None, favicon=None,
    )
    result = render_bookmark_html(preview)
    assert "<script>" not in result
    assert "&lt;script&gt;" in result
    assert "a &amp; b" in result


def test_render_bookmark_html_omits_image_and_favicon_when_absent():
    preview = LinkPreview(url="https://example.com", title="Title", description="", image=None, favicon=None)
    result = render_bookmark_html(preview)
    assert "kb-bookmark-image" not in result
    assert "kb-bookmark-favicon" not in result


def test_render_bookmark_html_includes_target_blank_and_rel():
    preview = LinkPreview(url="https://example.com", title="Title", description="", image=None, favicon=None)
    result = render_bookmark_html(preview)
    assert 'target="_blank"' in result
    assert 'rel="noopener noreferrer"' in result
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest packages/backend/tests/test_link_preview.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'myhome.link_preview'`

- [ ] **Step 3: Write the implementation**

Create `packages/backend/src/myhome/link_preview.py`:

```python
"""SSRF-guarded fetch of a URL's Open Graph / HTML metadata, and rendering of the
resulting Notion-style bookmark card. Shared by the KB link-preview REST endpoint
(routes/kb.py) and the add_kb_bookmark MCP tool (mcp_tools_kb.py) -- this is the one
place that fetches an arbitrary user-supplied URL server-side, so both callers go
through the same guard rather than duplicating it."""
from __future__ import annotations

import html
import ipaddress
import socket
from dataclasses import dataclass
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

import httpx

_TIMEOUT = 5.0
_MAX_REDIRECTS = 3
_MAX_BYTES = 1_000_000


@dataclass
class LinkPreview:
    url: str
    title: str
    description: str
    image: str | None
    favicon: str | None


def _check_host_allowed(hostname: str) -> None:
    try:
        infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror as exc:
        raise ValueError(f"Cannot resolve host {hostname!r}") from exc
    for _family, _type, _proto, _canonname, sockaddr in infos:
        ip = ipaddress.ip_address(sockaddr[0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
            raise ValueError(f"Refusing to fetch private/internal address {ip}")


def _fetch_html(url: str) -> tuple[str, str]:
    current = url
    with httpx.Client(follow_redirects=False, timeout=_TIMEOUT) as client:
        for _ in range(_MAX_REDIRECTS + 1):
            hostname = urlparse(current).hostname
            if not hostname:
                raise ValueError(f"Invalid URL {current!r}")
            _check_host_allowed(hostname)
            with client.stream("GET", current) as resp:
                if resp.is_redirect:
                    location = resp.headers.get("location")
                    if not location:
                        raise ValueError("Redirect with no Location header")
                    current = urljoin(current, location)
                    continue
                resp.raise_for_status()
                content_type = resp.headers.get("content-type", "")
                if "text/html" not in content_type:
                    raise ValueError(f"Unsupported content-type {content_type!r}")
                chunks = []
                total = 0
                for chunk in resp.iter_bytes():
                    chunks.append(chunk)
                    total += len(chunk)
                    if total >= _MAX_BYTES:
                        break
                body = b"".join(chunks)
                return body.decode(resp.encoding or "utf-8", errors="replace"), current
    raise ValueError("Too many redirects")


class _MetaParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.title = ""
        self._in_title = False
        self.og_title: str | None = None
        self.og_description: str | None = None
        self.og_image: str | None = None
        self.meta_description: str | None = None
        self.icon: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        d = dict(attrs)
        if tag == "title":
            self._in_title = True
        elif tag == "meta":
            prop = (d.get("property") or "").lower()
            name = (d.get("name") or "").lower()
            content = d.get("content")
            if prop == "og:title" and content:
                self.og_title = content
            elif prop == "og:description" and content:
                self.og_description = content
            elif prop == "og:image" and content:
                self.og_image = content
            elif name == "description" and content:
                self.meta_description = content
        elif tag == "link":
            rel = (d.get("rel") or "").lower()
            href = d.get("href")
            if rel in ("icon", "shortcut icon") and href and not self.icon:
                self.icon = href

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title += data

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False


def _resolve_absolute(value: str | None, base_url: str) -> str | None:
    if not value:
        return None
    absolute = urljoin(base_url, value)
    if urlparse(absolute).scheme not in ("http", "https"):
        return None
    return absolute


def fetch_link_preview(url: str) -> LinkPreview:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise ValueError(f"Invalid URL {url!r}: must be an absolute http(s) URL")
    fallback_title = parsed.hostname
    try:
        body, final_url = _fetch_html(url)
        parser = _MetaParser()
        parser.feed(body)
        title = parser.og_title or parser.title.strip() or fallback_title
        description = parser.og_description or parser.meta_description or ""
        image = _resolve_absolute(parser.og_image, final_url)
        favicon = _resolve_absolute(parser.icon, final_url)
        return LinkPreview(url=url, title=title, description=description, image=image, favicon=favicon)
    except Exception:
        return LinkPreview(url=url, title=fallback_title, description="", image=None, favicon=None)


def render_bookmark_html(preview: LinkPreview) -> str:
    hostname = urlparse(preview.url).hostname or preview.url
    title_html = html.escape(preview.title or hostname)
    description_html = (
        f'<span class="kb-bookmark-desc">{html.escape(preview.description)}</span>' if preview.description else ""
    )
    favicon_html = (
        f'<img class="kb-bookmark-favicon" src="{html.escape(preview.favicon)}">' if preview.favicon else ""
    )
    image_html = (
        f'<img class="kb-bookmark-image" src="{html.escape(preview.image)}" alt="">' if preview.image else ""
    )
    return (
        f'<a class="kb-bookmark" href="{html.escape(preview.url)}" target="_blank" rel="noopener noreferrer">'
        f'<span class="kb-bookmark-text">'
        f'<span class="kb-bookmark-title">{title_html}</span>'
        f"{description_html}"
        f'<span class="kb-bookmark-domain">{favicon_html}{html.escape(hostname)}</span>'
        "</span>"
        f"{image_html}"
        "</a>"
    )
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest packages/backend/tests/test_link_preview.py -v`
Expected: PASS (12 tests)

- [ ] **Step 5: Run the full backend suite to check nothing else broke**

Run: `pytest packages/backend`
Expected: PASS (all tests, including the pre-existing suite)

- [ ] **Step 6: Commit**

```bash
git add packages/backend/src/myhome/link_preview.py packages/backend/tests/test_link_preview.py
git commit -m "feat(backend): add SSRF-guarded link-preview fetch/parse/render module"
```

---

## Task 2: REST endpoint `POST /api/homes/{home_id}/kb/link-preview`

**Files:**
- Modify: `packages/backend/src/myhome/models_kb.py`
- Modify: `packages/backend/src/myhome/routes/kb.py`
- Test: `packages/backend/tests/test_kb.py`

**Interfaces:**
- Consumes: `fetch_link_preview`, `render_bookmark_html` from `myhome.link_preview` (Task 1).
- Produces: nothing consumed by later tasks — this is a leaf endpoint used only by the frontend (Task 5).

- [ ] **Step 1: Write the failing tests**

Add to the top of `packages/backend/tests/test_kb.py` (alongside the existing `import pytest` etc.):

```python
import socket

import respx
from httpx import Response
```

Then append these tests to the end of the file:

```python
def _fake_getaddrinfo(*args, **kwargs):
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 0))]


def test_kb_link_preview_returns_html_and_fields(client, home_id, monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", _fake_getaddrinfo)
    with respx.mock:
        respx.get("http://example.com/page").mock(
            return_value=Response(
                200,
                headers={"content-type": "text/html"},
                html='<meta property="og:title" content="OG Title">',
            )
        )
        resp = client.post(f"/api/homes/{home_id}/kb/link-preview", json={"url": "http://example.com/page"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "OG Title"
    assert 'class="kb-bookmark"' in data["html"]


def test_kb_link_preview_rejects_malformed_url(client, home_id):
    resp = client.post(f"/api/homes/{home_id}/kb/link-preview", json={"url": "not-a-url"})
    assert resp.status_code == 400
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest packages/backend/tests/test_kb.py -v -k link_preview`
Expected: FAIL — `404` (no such route yet)

- [ ] **Step 3: Write the implementation**

In `packages/backend/src/myhome/models_kb.py`, add at the end of the file:

```python
class KBLinkPreviewRequest(BaseModel):
    url: str
```

In `packages/backend/src/myhome/routes/kb.py`, update the imports:

```python
from ..link_preview import fetch_link_preview, render_bookmark_html
from ..models_kb import (
    KBCreate, KBDocument, KBEntry, KBLinkPreviewRequest, KBReorder, KBTrashDocument, KBUpdate,
)
```

Add the endpoint at the end of the file:

```python
@router.post("/api/homes/{home_id}/kb/link-preview")
def get_kb_link_preview(home_id: str, body: KBLinkPreviewRequest) -> dict:
    # home_id is unused -- kept for URL-namespace consistency with the rest of this
    # router; this endpoint isn't entry- or home-scoped, it's a stateless URL lookup.
    try:
        preview = fetch_link_preview(body.url)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {
        "html": render_bookmark_html(preview),
        "title": preview.title,
        "description": preview.description,
        "image": preview.image,
    }
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest packages/backend/tests/test_kb.py -v -k link_preview`
Expected: PASS (2 tests)

- [ ] **Step 5: Run the full backend suite**

Run: `pytest packages/backend`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add packages/backend/src/myhome/models_kb.py packages/backend/src/myhome/routes/kb.py packages/backend/tests/test_kb.py
git commit -m "feat(backend): add KB link-preview REST endpoint"
```

---

## Task 3: MCP tool `add_kb_bookmark`

**Files:**
- Modify: `packages/backend/src/myhome/mcp_tools_kb.py`
- Test: `packages/backend/tests/test_mcp_tools_kb.py`

**Interfaces:**
- Consumes: `fetch_link_preview`, `render_bookmark_html` from `myhome.link_preview` (Task 1); `_live_entry`, `_now`, `save_entry` already in `mcp_tools_kb.py`.
- Produces: `_add_kb_bookmark_impl(home_id, entry_id, url, title=None, description=None) -> dict` — no other task depends on it.

- [ ] **Step 1: Write the failing tests**

Append to `packages/backend/tests/test_mcp_tools_kb.py`:

```python
def test_add_kb_bookmark_appends_card_and_bumps_updated_at(home_id, monkeypatch):
    import socket

    import respx
    from httpx import Response
    from myhome.mcp_tools_kb import _add_kb_bookmark_impl, _create_kb_entry_impl

    monkeypatch.setattr(
        socket, "getaddrinfo",
        lambda *a, **k: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 0))],
    )
    entry = _create_kb_entry_impl(home_id, "Notes", content="Existing content")
    with respx.mock:
        respx.get("http://example.com/page").mock(
            return_value=Response(
                200, headers={"content-type": "text/html"},
                html='<meta property="og:title" content="OG Title">',
            )
        )
        result = _add_kb_bookmark_impl(home_id, entry["id"], "http://example.com/page")
    assert "Existing content" in result["content"]
    assert 'class="kb-bookmark"' in result["content"]
    assert "OG Title" in result["content"]
    assert result["updatedAt"] != entry["updatedAt"]


def test_add_kb_bookmark_title_and_description_override_fetched_values(home_id, monkeypatch):
    import socket

    import respx
    from httpx import Response
    from myhome.mcp_tools_kb import _add_kb_bookmark_impl, _create_kb_entry_impl

    monkeypatch.setattr(
        socket, "getaddrinfo",
        lambda *a, **k: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 0))],
    )
    entry = _create_kb_entry_impl(home_id, "Notes")
    with respx.mock:
        respx.get("http://example.com/page").mock(
            return_value=Response(
                200, headers={"content-type": "text/html"},
                html='<meta property="og:title" content="Fetched Title">',
            )
        )
        result = _add_kb_bookmark_impl(
            home_id, entry["id"], "http://example.com/page",
            title="Custom Title", description="Custom Desc",
        )
    assert "Custom Title" in result["content"]
    assert "Custom Desc" in result["content"]
    assert "Fetched Title" not in result["content"]


def test_add_kb_bookmark_unknown_entry_id_raises(home_id):
    from myhome.mcp_tools_kb import _add_kb_bookmark_impl
    with pytest.raises(ValueError):
        _add_kb_bookmark_impl(home_id, "nonexistent", "http://example.com")
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest packages/backend/tests/test_mcp_tools_kb.py -v -k add_kb_bookmark`
Expected: FAIL — `ImportError: cannot import name '_add_kb_bookmark_impl'`

- [ ] **Step 3: Write the implementation**

In `packages/backend/src/myhome/mcp_tools_kb.py`, add to the imports:

```python
from .link_preview import fetch_link_preview, render_bookmark_html
```

Add the impl function (grouped with the other `_xxx_impl` functions, e.g. after `_delete_kb_entry_impl`):

```python
def _add_kb_bookmark_impl(
    home_id: str | None, entry_id: str, url: str,
    title: str | None = None, description: str | None = None,
) -> dict:
    resolved = _resolve_home_id(home_id)
    entry = _live_entry(resolved, entry_id)
    if entry is None:
        raise ValueError(f"Unknown entry_id {entry_id!r}")
    preview = fetch_link_preview(url)
    if title is not None:
        preview.title = title
    if description is not None:
        preview.description = description
    card_html = render_bookmark_html(preview)
    entry.content = f"{entry.content}\n\n{card_html}\n"
    entry.updatedAt = _now()
    save_entry(resolved, entry)
    return entry.model_dump()
```

Add the tool wrapper at the end of the file:

```python
@mcp.tool()
async def add_kb_bookmark(
    ctx: Context, entry_id: str, url: str,
    title: str | None = None, description: str | None = None, home_id: str | None = None,
) -> dict:
    """Add a web-bookmark card to a knowledge base page, appended to the end of its
    content. Automatically fetches the target page's title/description/image;
    title/description override the fetched values if given."""
    await _require_role(ctx.request_context.request, "normal")
    return _add_kb_bookmark_impl(home_id, entry_id, url, title, description)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest packages/backend/tests/test_mcp_tools_kb.py -v -k add_kb_bookmark`
Expected: PASS (3 tests)

- [ ] **Step 5: Run the full backend suite**

Run: `pytest packages/backend`
Expected: PASS

- [ ] **Step 6: Manually verify the MCP server still boots**

Run: `cd packages/backend && python -c "from myhome.mcp_app import mcp_asgi_app; print('OK')"`
Expected: prints `OK` with no traceback.

- [ ] **Step 7: Commit**

```bash
git add packages/backend/src/myhome/mcp_tools_kb.py packages/backend/tests/test_mcp_tools_kb.py
git commit -m "feat(backend): add add_kb_bookmark MCP tool"
```

---

## Task 4: `MarkdownEditor.svelte` bookmark button + `kbStore.fetchLinkPreview`

**Files:**
- Modify: `packages/editor/src/lib/components/ui/MarkdownEditor.svelte`
- Modify: `packages/editor/src/lib/kbStore.svelte.ts`
- Modify: `packages/editor/src/lib/locales/en.json` and `fr.json`
- Test: `packages/editor/test/MarkdownEditor.test.ts`
- Test: `packages/editor/test/kbStore.test.ts`

**Interfaces:**
- Produces: `MarkdownEditor` prop `onInsertBookmark?: () => Promise<string | null>`; `kbStore.fetchLinkPreview(url: string) -> Promise<{html, title, description, image}>` — both consumed by Task 5 (`KBPage.svelte`).

- [ ] **Step 1: Write the failing frontend tests**

Append to `packages/editor/test/MarkdownEditor.test.ts`:

```typescript
describe("MarkdownEditor — bookmark insert", () => {
  it("does not show 🔖 button when onInsertBookmark is omitted", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const app = mount(MarkdownEditor, { target, props: { value: "", editing: true } });
    flushSync();
    expect(target.querySelector('[title="Insert bookmark"]')).toBeNull();
    unmount(app);
    target.remove();
  });

  it("shows 🔖 button when onInsertBookmark is provided", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const onInsertBookmark = async () => null;
    const app = mount(MarkdownEditor, { target, props: { value: "", editing: true, onInsertBookmark } });
    flushSync();
    expect(target.querySelector('[title="Insert bookmark"]')).not.toBeNull();
    unmount(app);
    target.remove();
  });

  it("clicking 🔖 button inserts the resolved HTML at the cursor", async () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const onInsertBookmark = async () => '<a class="kb-bookmark" href="https://example.com">Example</a>';
    const app = mount(MarkdownEditor, { target, props: { value: "", editing: true, onInsertBookmark } });
    flushSync();
    (target.querySelector('[title="Insert bookmark"]') as HTMLButtonElement).click();
    await new Promise((r) => setTimeout(r, 0));
    flushSync();
    const textarea = target.querySelector("textarea.md-editor") as HTMLTextAreaElement;
    expect(textarea.value).toBe('<a class="kb-bookmark" href="https://example.com">Example</a>');
    unmount(app);
    target.remove();
  });

  it("clicking 🔖 button does nothing when onInsertBookmark resolves to null", async () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const onInsertBookmark = async () => null;
    const app = mount(MarkdownEditor, { target, props: { value: "", editing: true, onInsertBookmark } });
    flushSync();
    (target.querySelector('[title="Insert bookmark"]') as HTMLButtonElement).click();
    await new Promise((r) => setTimeout(r, 0));
    flushSync();
    const textarea = target.querySelector("textarea.md-editor") as HTMLTextAreaElement;
    expect(textarea.value).toBe("");
    unmount(app);
    target.remove();
  });
});

describe("MarkdownEditor — DOMPurify target attribute", () => {
  it('preserves target="_blank" on rendered links (needed for bookmark cards to open in a new tab)', () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const app = mount(MarkdownEditor, {
      target,
      props: {
        value: '<a class="kb-bookmark" href="https://example.com" target="_blank" rel="noopener noreferrer">Example</a>',
        editing: false,
      },
    });
    flushSync();
    const link = target.querySelector("a.kb-bookmark");
    expect(link?.getAttribute("target")).toBe("_blank");
    unmount(app);
    target.remove();
  });
});
```

Append to `packages/editor/test/kbStore.test.ts` (after the existing `describe` blocks):

```typescript
describe("kbStore — fetchLinkPreview", () => {
  it("posts the url and returns the response body", async () => {
    const fetchFn = stubRoutedFetch([
      {
        match: methodAt("POST", "/kb/link-preview"),
        respond: () => ok(200, { html: '<a class="kb-bookmark">Example</a>', title: "Example", description: "", image: null }),
      },
    ]);
    const store = createKBStore(getHomeId);
    const result = await store.fetchLinkPreview("https://example.com");
    expect(result.html).toBe('<a class="kb-bookmark">Example</a>');
    expect(fetchFn).toHaveBeenCalledWith(
      `/api/homes/${HOME}/kb/link-preview`,
      expect.objectContaining({ method: "POST", body: JSON.stringify({ url: "https://example.com" }) }),
    );
  });

  it("throws on a non-ok response", async () => {
    stubRoutedFetch([
      { match: methodAt("POST", "/kb/link-preview"), respond: () => fail(400) },
    ]);
    const store = createKBStore(getHomeId);
    await expect(store.fetchLinkPreview("not-a-url")).rejects.toThrow("HTTP 400");
  });
});
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `npm --prefix packages/editor test -- MarkdownEditor kbStore`
Expected: FAIL — the bookmark/DOMPurify tests fail (button/prop don't exist yet); `fetchLinkPreview` tests fail with `store.fetchLinkPreview is not a function`.

- [ ] **Step 3: Implement the `MarkdownEditor.svelte` changes**

Update the `Props` interface and destructuring:

```typescript
  interface Props {
    value: string;
    editing: boolean;
    placeholder?: string;
    minHeight?: string;
    mediaItems?: MediaItem[];
    clickToEdit?: boolean;
    resolveKbLink?: (id: string) => { title: string; icon: string } | null;
    onSlashPage?: () => Promise<{ id: string; title: string } | null>;
    onInsertBookmark?: () => Promise<string | null>;
  }

  let {
    value = $bindable(),
    editing = $bindable(),
    placeholder,
    minHeight = "200px",
    mediaItems = [],
    clickToEdit = true,
    resolveKbLink,
    onSlashPage,
    onInsertBookmark,
  }: Props = $props();
```

Update the DOMPurify sanitize call to preserve `target`:

```typescript
  // marked() is sync here (no async extensions); cast to string is safe.
  // ADD_ATTR: DOMPurify strips target="_blank" by default -- needed so bookmark
  // cards (and any other link) open in a new tab instead of navigating the SPA away.
  const renderedHtml = $derived(
    value.trim()
      ? resolveKbLinksInHtml(DOMPurify.sanitize(marked(value) as string, { ADD_ATTR: ["target"] }))
      : "",
  );
```

Add the handler (near `insertMedia`):

```typescript
  async function handleInsertBookmark(): Promise<void> {
    if (!onInsertBookmark) return;
    const bookmarkHtml = await onInsertBookmark();
    if (bookmarkHtml) insert(bookmarkHtml);
  }
```

Add the toolbar button, after the media-picker `{#if mediaItems.length > 0}` block and before the closing `</div>` of `.md-toolbar`:

```svelte
    {#if onInsertBookmark}
      <span class="tb-sep" aria-hidden="true"></span>
      <button
        class="tb-btn"
        type="button"
        title={$_('markdownEditor.insertBookmark')}
        onclick={handleInsertBookmark}
      >🔖</button>
    {/if}
```

Add CSS at the end of the `<style>` block (alongside the other `.md-preview :global(...)` rules):

```css
  .md-preview :global(a.kb-bookmark) {
    display: flex; align-items: stretch;
    border: 1px solid var(--border); border-radius: var(--radius-md);
    overflow: hidden; text-decoration: none; margin: 0.5em 0;
    background: var(--surface-alt);
  }
  .md-preview :global(a.kb-bookmark:hover) { border-color: var(--accent); }
  .md-preview :global(.kb-bookmark-text) {
    flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 4px;
    padding: 10px 12px; justify-content: center;
  }
  .md-preview :global(.kb-bookmark-title) { color: var(--text); font-weight: 600; font-size: 13px; }
  .md-preview :global(.kb-bookmark-desc) {
    color: var(--text-muted); font-size: 12px;
    overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
  }
  .md-preview :global(.kb-bookmark-domain) {
    color: var(--text-faint); font-size: 11px;
    display: flex; align-items: center; gap: 4px;
  }
  .md-preview :global(.kb-bookmark-favicon) { width: 14px; height: 14px; border-radius: 2px; }
  .md-preview :global(.kb-bookmark-image) { width: 120px; flex-shrink: 0; object-fit: cover; }
```

- [ ] **Step 4: Implement the `kbStore.svelte.ts` change**

Add the method (alongside `uploadAttachment`/`deleteAttachment`):

```typescript
  async function fetchLinkPreview(
    url: string,
  ): Promise<{ html: string; title: string; description: string; image: string | null }> {
    const homeId = getHomeId();
    if (!homeId) throw new Error("No active home");
    const resp = await fetch(`/api/homes/${homeId}/kb/link-preview`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url }),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    return resp.json();
  }
```

Add `fetchLinkPreview,` to the returned object (alongside `uploadAttachment,`/`deleteAttachment,`).

- [ ] **Step 5: Add the i18n strings**

In `packages/editor/src/lib/locales/en.json`, add to the `"markdownEditor"` object (after `"insertMediaAttachment"`):

```json
    "insertBookmark": "Insert bookmark",
```

In `packages/editor/src/lib/locales/fr.json`, add to the same object:

```json
    "insertBookmark": "Insérer un favori",
```

- [ ] **Step 6: Run the tests to verify they pass**

Run: `npm --prefix packages/editor test -- MarkdownEditor kbStore`
Expected: PASS (4 new `MarkdownEditor` bookmark tests + 1 DOMPurify test + 2 new `kbStore` tests, all pre-existing tests in both files still pass)

- [ ] **Step 7: Run the full frontend suite**

Run: `npm --prefix packages/editor test`
Expected: PASS (all tests, including the pre-existing suite)

- [ ] **Step 8: Commit**

```bash
git add packages/editor/src/lib/components/ui/MarkdownEditor.svelte packages/editor/src/lib/kbStore.svelte.ts packages/editor/src/lib/locales/en.json packages/editor/src/lib/locales/fr.json packages/editor/test/MarkdownEditor.test.ts packages/editor/test/kbStore.test.ts
git commit -m "feat(frontend): MarkdownEditor bookmark insert button + kbStore.fetchLinkPreview"
```

---

## Task 5: `KBPage.svelte` bookmark URL modal

**Files:**
- Modify: `packages/editor/src/lib/components/KBPage.svelte`
- Modify: `packages/editor/src/lib/locales/en.json` and `fr.json`
- Test: `packages/editor/test/KBPage.test.ts`

**Interfaces:**
- Consumes: `onInsertBookmark` prop and `kbStore.fetchLinkPreview` from Task 4.
- Produces: nothing consumed by other tasks — this is the final wiring.

- [ ] **Step 1: Write the failing tests**

In `packages/editor/test/KBPage.test.ts`, add a branch to `createFakeKbBackend`'s `handle()` function, right after the existing `if (url.endsWith("/kb/trash") && method === "GET") { ... }` block:

```typescript
    if (url.endsWith("/kb/link-preview") && method === "POST") {
      return {
        ok: true, status: 200,
        json: async () => ({
          html: `<a class="kb-bookmark" href="${body.url}">${body.url}</a>`,
          title: body.url, description: "", image: null,
        }),
      };
    }
```

Then append these tests at the end of the file:

```typescript
describe("KBPage — insert bookmark", () => {
  it("fetches a link preview and inserts the returned HTML at the cursor", async () => {
    const entries = [makeEntry({ content: "" })];
    const { target, comp } = await setup(entries, { selectedItemId: "e1" });
    const editBtn = Array.from(target.querySelectorAll("button")).find((b) => b.textContent === "Edit") as HTMLElement;
    editBtn.click();
    flushSync();
    (target.querySelector('[title="Insert bookmark"]') as HTMLButtonElement).click();
    flushSync();
    const modal = target.querySelector(".ui-modal") as HTMLElement;
    expect(modal).not.toBeNull();
    const urlInput = modal.querySelector(".ui-input") as HTMLInputElement;
    urlInput.value = "https://example.com";
    urlInput.dispatchEvent(new Event("input", { bubbles: true }));
    flushSync();
    const insertBtn = Array.from(modal.querySelectorAll("button")).find((b) => b.textContent?.includes("Insert")) as HTMLElement;
    insertBtn.click();
    await tick(); flushSync(); await tick(); flushSync();
    expect(target.querySelector(".ui-modal")).toBeNull();
    const textarea = target.querySelector("textarea.md-editor") as HTMLTextAreaElement;
    expect(textarea.value).toContain("kb-bookmark");
    expect(textarea.value).toContain("https://example.com");
    unmount(comp); target.remove();
  });

  it("Cancel closes the modal without inserting anything", async () => {
    const entries = [makeEntry({ content: "" })];
    const { target, comp } = await setup(entries, { selectedItemId: "e1" });
    const editBtn = Array.from(target.querySelectorAll("button")).find((b) => b.textContent === "Edit") as HTMLElement;
    editBtn.click();
    flushSync();
    (target.querySelector('[title="Insert bookmark"]') as HTMLButtonElement).click();
    flushSync();
    const modal = target.querySelector(".ui-modal") as HTMLElement;
    const cancelBtn = Array.from(modal.querySelectorAll("button")).find((b) => b.textContent === "Cancel") as HTMLElement;
    cancelBtn.click();
    flushSync();
    expect(target.querySelector(".ui-modal")).toBeNull();
    const textarea = target.querySelector("textarea.md-editor") as HTMLTextAreaElement;
    expect(textarea.value).toBe("");
    unmount(comp); target.remove();
  });
});
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `npm --prefix packages/editor test -- KBPage`
Expected: FAIL — `[title="Insert bookmark"]` is null (KBPage doesn't pass `onInsertBookmark` to `MarkdownEditor` yet)

- [ ] **Step 3: Write the implementation**

Add state, alongside the other `let ... = $state(...)` declarations in `KBPage.svelte`:

```typescript
  let bookmarkModalOpen = $state(false);
  let bookmarkUrl = $state("");
  let bookmarkFetching = $state(false);
  let bookmarkError = $state<string | null>(null);
  let bookmarkResolve: ((html: string | null) => void) | null = null;
```

Add the handlers, alongside `handleSlashPage`:

```typescript
  function handleInsertBookmark(): Promise<string | null> {
    bookmarkUrl = "";
    bookmarkError = null;
    bookmarkModalOpen = true;
    return new Promise((resolve) => { bookmarkResolve = resolve; });
  }

  function closeBookmarkModal(result: string | null): void {
    bookmarkModalOpen = false;
    bookmarkResolve?.(result);
    bookmarkResolve = null;
  }

  async function handleConfirmBookmark(): Promise<void> {
    const url = bookmarkUrl.trim();
    if (!url) { bookmarkError = $_('kb.page.bookmarkUrlRequired'); return; }
    bookmarkFetching = true;
    bookmarkError = null;
    try {
      const { html } = await store.fetchLinkPreview(url);
      closeBookmarkModal(html);
    } catch (e) {
      bookmarkError = e instanceof Error ? e.message : $_('kb.page.bookmarkFetchFailed');
    } finally {
      bookmarkFetching = false;
    }
  }
```

Wire the prop into `<MarkdownEditor>`:

```svelte
          <MarkdownEditor
            bind:value={draftContent}
            bind:editing
            mediaItems={contentTab === "content" ? mediaItems : []}
            clickToEdit={false}
            placeholder={$_('kb.page.startWritingPlaceholder')}
            {resolveKbLink}
            onSlashPage={handleSlashPage}
            onInsertBookmark={handleInsertBookmark}
          />
```

Add the modal markup, after the existing delete-confirmation `<Modal>` block:

```svelte
<Modal open={bookmarkModalOpen} title={$_('kb.page.bookmarkModalTitle')} onclose={() => closeBookmarkModal(null)} width="420px">
  <Input placeholder={$_('kb.page.bookmarkUrlPlaceholder')} bind:value={bookmarkUrl} />
  {#if bookmarkError}
    <p class="bookmark-error">{bookmarkError}</p>
  {/if}
  {#snippet footer()}
    <Button variant="ghost" onclick={() => closeBookmarkModal(null)}>{$_('common.cancel')}</Button>
    <Button variant="primary" disabled={bookmarkFetching} onclick={handleConfirmBookmark}>
      {bookmarkFetching ? $_('kb.page.bookmarkFetching') : $_('kb.page.bookmarkInsert')}
    </Button>
  {/snippet}
</Modal>
```

Add CSS at the end of the `<style>` block:

```css
  .bookmark-error { color: var(--danger); font-size: 12px; margin: 6px 0 0; }
```

- [ ] **Step 4: Add the i18n strings**

In `packages/editor/src/lib/locales/en.json`, add to the `"kb"."page"` object (after `"restoreItNote"`):

```json
      "bookmarkModalTitle": "Insert bookmark",
      "bookmarkUrlPlaceholder": "https://example.com",
      "bookmarkUrlRequired": "A URL is required",
      "bookmarkFetchFailed": "Failed to fetch preview",
      "bookmarkFetching": "Fetching…",
      "bookmarkInsert": "Insert"
```

In `packages/editor/src/lib/locales/fr.json`, add to the same object (after `"restoreItNote"`):

```json
      "bookmarkModalTitle": "Insérer un favori",
      "bookmarkUrlPlaceholder": "https://example.com",
      "bookmarkUrlRequired": "Une URL est requise",
      "bookmarkFetchFailed": "Échec de la récupération de l'aperçu",
      "bookmarkFetching": "Récupération…",
      "bookmarkInsert": "Insérer"
```

(Remember to add a trailing comma after `"restoreItNote": "..."` in both files, since it's no longer the last key in the object.)

- [ ] **Step 5: Run the tests to verify they pass**

Run: `npm --prefix packages/editor test -- KBPage`
Expected: PASS (2 new tests, all pre-existing `KBPage` tests still pass)

- [ ] **Step 6: Run the full frontend suite**

Run: `npm --prefix packages/editor test`
Expected: PASS (all tests, including the pre-existing suite)

- [ ] **Step 7: Commit**

```bash
git add packages/editor/src/lib/components/KBPage.svelte packages/editor/src/lib/locales/en.json packages/editor/src/lib/locales/fr.json packages/editor/test/KBPage.test.ts
git commit -m "feat(frontend): wire KB bookmark-insert modal into KBPage"
```

---

## Self-Review Notes

- **Spec coverage:** SSRF guard + always-succeeds fetch (Task 1), REST endpoint (Task 2), MCP tool with title/description override (Task 3), MarkdownEditor button + DOMPurify `target` fix + kbStore method (Task 4), KBPage modal wiring (Task 5) — every design-doc section maps to a task.
- **Type consistency:** `LinkPreview`/`fetch_link_preview`/`render_bookmark_html` signatures are identical everywhere they're used (Tasks 2 and 3 both import them unchanged from Task 1). `onInsertBookmark: () => Promise<string | null>` matches between its definition in `MarkdownEditor.svelte` (Task 4) and its implementation in `KBPage.svelte` (Task 5). `fetchLinkPreview(url) -> Promise<{html, title, description, image}>` matches between `kbStore.svelte.ts` (Task 4) and its usage in `KBPage.svelte` (Task 5).
- **No placeholders:** every step has complete, runnable code, verified by hand-running the Task 1 fetch/parse/render logic (redirect-following, SSRF fallback, HTML parsing, escaping) and the DOMPurify `target`-attribute fix against this exact codebase's `marked`/`DOMPurify` versions before writing this plan.
