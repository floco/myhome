# packages/backend/src/myhome/property_search_dedup.py
"""Keys used to recognise a listing that was already suggested.

``url_key`` catches the same listing URL with cosmetic differences;
``fingerprint`` is a deliberately coarse cross-site key (the same plot
listed by two agencies). Over-merging is accepted: "never twice" matters
more than "never miss one".
"""
from __future__ import annotations

import re
import unicodedata
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

_DROP_PARAMS = {"fbclid", "gclid", "ref", "source"}


def url_key(url: str) -> str:
    parts = urlsplit(url.strip())
    host = parts.netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    params = sorted(
        (k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True)
        if not k.lower().startswith("utm_") and k.lower() not in _DROP_PARAMS
    )
    path = parts.path.rstrip("/")
    return urlunsplit((parts.scheme.lower(), host, path, urlencode(params), ""))


def _town(location: str) -> str:
    text = unicodedata.normalize("NFKD", location or "").encode("ascii", "ignore").decode().lower()
    text = re.sub(r"[^a-z0-9 ]", " ", text)
    return next((w for w in text.split() if len(w) >= 3), "")


def fingerprint(
    type: str | None, price: float | None, land: float | None, built: float | None, location: str,
) -> str | None:
    if price is None or (land is None and built is None):
        return None
    return (f"{type or '?'}|{int(round(price, -3))}|{int(round(land or 0, -1))}"
            f"|{int(round(built or 0))}|{_town(location)}")
