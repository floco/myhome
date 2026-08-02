# KB web bookmarks — design

## Problem

The user wants to embed Notion-style "Web Bookmark" cards inside a KB page — paste
a URL, get a rich preview card (title, description, thumbnail image, favicon+domain)
embedded inline in the page content — and wants the same capability exposed over
MCP so an assistant can add a bookmark to a KB page directly.

## Goals

- A toolbar action in the KB Markdown editor that, given a URL, fetches that page's
  Open Graph metadata (falling back to `<title>`/meta description/hostname) and
  inserts a rendered bookmark card at the cursor position.
- An MCP tool that does the same against a specific KB entry, appending the card to
  the end of its content.
- Both paths share one backend module for the fetch+parse logic, since it's the
  security-sensitive part (arbitrary user-supplied URL, server-side fetch).

## Non-goals

- No "refresh preview" action — the card is a snapshot captured at insertion time,
  matching how inserted media/links already work in this editor.
- No downloading/storing the preview image locally — hotlinked directly from the
  source site, matching common link-preview conventions (Slack/GitHub unfurls) and
  avoiding extra backend storage/attachment-gallery-visibility questions.
- No manual-entry fallback UI for when a fetch "fails" — the fetch is designed to
  always produce *something* (see Fetch behavior below), so there's no separate
  failure state to design for in the UI.
- No new third-party dependency (e.g. an HTML parsing library, a favicon service) —
  parsing uses stdlib `html.parser.HTMLParser`; favicon comes from the same page
  fetch, not a third-party favicon API.

## Design

### Shared module: `link_preview.py`

Two pure functions, used by both the REST endpoint and the MCP tool:

```python
@dataclass
class LinkPreview:
    url: str
    title: str
    description: str
    image: str | None
    favicon: str | None

def fetch_link_preview(url: str) -> LinkPreview: ...
def render_bookmark_html(preview: LinkPreview) -> str: ...
```

**`fetch_link_preview`:**

- Rejects non-`http(s)` URLs immediately (`ValueError`) — this is the one case that
  surfaces as a hard error to the caller.
- SSRF guard: resolves the hostname via `socket.getaddrinfo` and rejects if *any*
  resolved address is private/loopback/link-local (stdlib `ipaddress`:
  `.is_private`/`.is_loopback`/`.is_link_local`, covering `10.0.0.0/8`,
  `172.16.0.0/12`, `192.168.0.0/16`, `127.0.0.0/8`, `169.254.0.0/16`, `::1`,
  `fc00::/7`, etc). This matters because this runs as a Home Assistant addon on a
  LAN — an unguarded fetch could be used to probe internal devices or the HA
  supervisor API, the same class of concern the MCP server's own DNS-rebinding
  comment (`mcp_server.py`) already flags.
- No automatic redirect-following: `httpx.get(url, follow_redirects=False,
  timeout=5.0)`, then manually follow up to 3 `3xx` redirects, **re-running the
  DNS/private-range check on each redirect target**. Plain
  `follow_redirects=True` would skip this and reopen the DNS-rebinding hole (pass
  the check on the initial URL, redirect to something internal).
- Response caps: stream and stop after ~1&nbsp;MB; require `Content-Type:
  text/html*` before parsing (skip parsing non-HTML responses).
- Parsing via a small `HTMLParser` subclass: pulls `<meta property="og:title">`,
  `<meta property="og:description">`, `<meta property="og:image">`, `<title>`,
  `<meta name="description">`, and `<link rel="icon">`/`<link rel="shortcut
  icon">`. Relative `image`/`favicon` URLs are resolved against the final
  (post-redirect) URL via `urllib.parse.urljoin`.
- Fallback chain: title = `og:title` → `<title>` text → URL hostname. description =
  `og:description` → `meta[name=description]` → `""`. image/favicon: `None` if not
  found or not resolvable to an absolute `http(s)` URL.
- **Always returns a `LinkPreview`, never raises for fetch/parse failure** —
  timeout, connection error, non-2xx status, blocked private address, or no
  metadata found all fall back to `title=hostname, description="", image=None,
  favicon=None`. Only a malformed `url` argument raises. This means the REST
  endpoint and MCP tool never need a distinct "preview fetch failed" branch.

**`render_bookmark_html`:** builds the card markup, HTML-escaping `title`/
`description` via `html.escape()`:

```html
<a class="kb-bookmark" href="{url}" target="_blank" rel="noopener noreferrer">
  <span class="kb-bookmark-text">
    <span class="kb-bookmark-title">{title}</span>
    <span class="kb-bookmark-desc">{description}</span>
    <span class="kb-bookmark-domain"><img class="kb-bookmark-favicon" src="{favicon}">{hostname}</span>
  </span>
  <img class="kb-bookmark-image" src="{image}" alt="">
</a>
```

(favicon `<img>` and outer image `<img>` omitted from the markup when absent.)

### REST endpoint

`POST /api/homes/{home_id}/kb/link-preview`, body `{"url": str}`, returns
`{"html": str, "title": str, "description": str, "image": str | None}`.

Not entry-specific — insertion position (cursor) is a client-side concern, same as
the existing media-insert flow in `MarkdownEditor.svelte` (`insertMedia` builds an
HTML string client-side and splices it into `value` directly; this endpoint is the
server-side equivalent for a fetched-preview HTML string). Raises `400` for a
malformed `url`; otherwise always `200` per the fetch behavior above.

### MCP tool

In `mcp_tools_kb.py`, alongside the existing KB tools:

```python
@mcp.tool()
async def add_kb_bookmark(
    ctx: Context, entry_id: str, url: str,
    title: str | None = None, description: str | None = None, home_id: str | None = None,
) -> dict:
    """Add a web-bookmark card to a KB page, appended to the end of its content.
    Automatically fetches the page's title/description/image; title/description
    override the fetched values if given."""
```

Requires `"normal"` role (matches `create_kb_entry`/`update_kb_entry`). Uses the
existing `_live_entry` helper to resolve `entry_id` (raises `ValueError` if
unknown/deleted, same as every other KB tool). Calls `fetch_link_preview`, applies
`title`/`description` overrides onto the returned `LinkPreview` if given, renders
the card, appends `"\n\n" + html + "\n"` to `entry.content`, bumps `updatedAt` (same
pattern the attachment tools use), calls `save_entry`, returns
`entry.model_dump()`.

### Frontend

`MarkdownEditor.svelte` gets a new optional prop `onInsertBookmark?: () =>
Promise<string | null>` (the resolved HTML to insert, or `null` if
cancelled/failed) and a new toolbar button (🔖), rendered only when the prop is
supplied — same conditional-rendering pattern the 📷 media button already uses for
`mediaItems.length > 0`. On click, calls `onInsertBookmark()` and, if non-null,
splices the result into `value` at the cursor via the existing `insert()` helper
(same as `insertMedia`).

`KBPage.svelte` implements `onInsertBookmark`, following the same callback-prop
delegation pattern already used for `onSlashPage`: opens a small modal (existing
shared `Modal`/`Input`/`Button` components) prompting for a URL, calls a new
`kbStore.fetchLinkPreview(url)` method (POSTs to the new endpoint, returns
`{html}`), and resolves the pending promise with the returned `html` (or `null` on
cancel).

**DOMPurify finding (verified empirically):** `MarkdownEditor.svelte`'s existing
`DOMPurify.sanitize(marked(value) as string)` call strips `target="_blank"` by
default, even though it keeps `class`/`data-*`/`rel`/`href`/`img[src]`. Left as-is,
clicking a bookmark card would navigate the whole SPA away instead of opening a new
tab. Fix: change that one call site to `DOMPurify.sanitize(marked(value) as string,
{ ADD_ATTR: ["target"] })`.

## Testing

- `fetch_link_preview`: og:title/description/image happy path; fallback chain
  (missing og:* → `<title>`/meta description → hostname); relative image/favicon
  URL resolution against the final URL; redirect-following with re-validation per
  hop; rejects private/loopback/link-local targets (mocked DNS resolution) and
  non-http(s) schemes (raises `ValueError`); response-size cap; non-HTML
  content-type is skipped without raising.
- `render_bookmark_html`: HTML-escaping of title/description containing `<`, `&`,
  quotes; favicon/image `<img>` omitted when absent.
- REST endpoint: happy path returns the expected shape; malformed URL → 400.
- MCP tool: happy path appends the card and bumps `updatedAt`; title/description
  overrides take precedence over fetched values; unknown `entry_id` raises
  `ValueError`.
- Frontend: a DOMPurify unit test confirming `target="_blank"` survives with the
  new `ADD_ATTR` config (regression guard for the finding above); MarkdownEditor
  renders the 🔖 button only when `onInsertBookmark` is supplied.

## Open questions / risks

- Fetching arbitrary user-supplied URLs from the backend is inherently a bigger
  attack surface than anything else in this app talks to; the SSRF guard is the
  load-bearing piece of this design and should get the most scrutiny in review.
- Sites that block simple/non-browser `User-Agent` headers may fall back to the
  hostname-only card more often than a real browser would see — acceptable given
  the "always returns something" design, but worth knowing as a UX limitation.
