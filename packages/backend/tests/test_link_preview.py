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
        respx.get("http://93.184.216.34/page").mock(
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
        respx.get("http://93.184.216.34/page").mock(
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
        respx.get("http://93.184.216.34/page").mock(
            return_value=Response(200, headers={"content-type": "text/html"}, html="<html></html>")
        )
        preview = fetch_link_preview("http://example.com/page")
    assert preview.title == "example.com"
    assert preview.description == ""


def test_fetch_link_preview_follows_redirect_and_revalidates_host():
    with respx.mock:
        respx.get("http://93.184.216.34/page").mock(
            return_value=Response(301, headers={"location": "http://example.com/final"})
        )
        respx.get("http://93.184.216.34/final").mock(
            return_value=Response(
                200,
                headers={"content-type": "text/html"},
                html='<meta property="og:title" content="Final Page">',
            )
        )
        preview = fetch_link_preview("http://example.com/page")
    assert preview.title == "Final Page"


def test_fetch_link_preview_pins_connection_to_validated_ip_with_original_host_header():
    # Regression test for a DNS-rebinding TOCTOU gap: the request must be sent to
    # the specific IP _resolve_allowed_ip already validated, not to whatever the
    # hostname re-resolves to at connect time (which httpx would do on its own if
    # given the hostname-based URL directly). The Host header/SNI must still carry
    # the original hostname so the origin server sees the right virtual host.
    with respx.mock:
        route = respx.get("http://93.184.216.34/page").mock(
            return_value=Response(200, headers={"content-type": "text/html"}, html="<title>T</title>")
        )
        fetch_link_preview("http://example.com/page")
    assert route.called
    sent_request = route.calls[0].request
    assert sent_request.url.host == "93.184.216.34"
    assert sent_request.headers.get("host") == "example.com"


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
        respx.get("http://93.184.216.34/file.pdf").mock(
            return_value=Response(200, headers={"content-type": "application/pdf"}, content=b"%PDF-1.4")
        )
        preview = fetch_link_preview("http://example.com/file.pdf")
    assert preview.title == "example.com"


def test_fetch_link_preview_falls_back_on_connection_error():
    with respx.mock:
        respx.get("http://93.184.216.34/page").mock(side_effect=httpx.ConnectError("boom"))
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
