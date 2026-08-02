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
from urllib.parse import urljoin, urlparse, urlunparse

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


def _resolve_allowed_ip(hostname: str) -> str:
    try:
        infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror as exc:
        raise ValueError(f"Cannot resolve host {hostname!r}") from exc
    ips = [ipaddress.ip_address(sockaddr[0]) for *_rest, sockaddr in infos]
    for ip in ips:
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast or ip.is_unspecified:
            raise ValueError(f"Refusing to fetch private/internal address {ip}")
    return str(ips[0])


def _pin_host(url: str, ip: str) -> str:
    """Rewrite url's host to the literal, pre-validated ip -- the caller sends the
    real hostname separately via the Host header + sni_hostname extension. This
    closes a DNS-rebinding TOCTOU gap: without pinning, _resolve_allowed_ip
    validates one address but httpx would independently re-resolve the hostname
    itself at connect time, so an attacker-controlled DNS server could return a
    public IP for the validation lookup and a private one moments later for the
    real connection."""
    parsed = urlparse(url)
    host_part = f"[{ip}]" if ":" in ip else ip
    netloc = f"{host_part}:{parsed.port}" if parsed.port else host_part
    return urlunparse(parsed._replace(netloc=netloc))


def _fetch_html(url: str) -> tuple[str, str]:
    current = url  # logical (hostname-based) URL; updated to the redirect target each hop
    with httpx.Client(follow_redirects=False, timeout=_TIMEOUT) as client:
        for _ in range(_MAX_REDIRECTS + 1):
            hostname = urlparse(current).hostname
            if not hostname:
                raise ValueError(f"Invalid URL {current!r}")
            ip = _resolve_allowed_ip(hostname)
            pinned_url = _pin_host(current, ip)
            with client.stream(
                "GET", pinned_url, headers={"Host": hostname}, extensions={"sni_hostname": hostname},
            ) as resp:
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
