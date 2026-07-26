from starlette.applications import Starlette
from starlette.routing import Mount
from starlette.testclient import TestClient

from myhome.caching_static import CachingStaticFiles


def _make_client(tmp_path):
    (tmp_path / "index.html").write_text("<html>shell</html>")
    assets_dir = tmp_path / "assets"
    assets_dir.mkdir()
    (assets_dir / "app-abc123.js").write_text("console.log(1)")
    app = Starlette(routes=[Mount("/", app=CachingStaticFiles(directory=str(tmp_path), html=True))])
    return TestClient(app)


def test_index_html_is_not_cached(tmp_path):
    client = _make_client(tmp_path)
    resp = client.get("/")
    assert resp.status_code == 200
    assert resp.headers["cache-control"] == "no-cache"


def test_hashed_asset_is_cached_immutably(tmp_path):
    client = _make_client(tmp_path)
    resp = client.get("/assets/app-abc123.js")
    assert resp.status_code == 200
    assert resp.headers["cache-control"] == "public, max-age=31536000, immutable"
