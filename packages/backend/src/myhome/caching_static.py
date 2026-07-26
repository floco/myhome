# packages/backend/src/myhome/caching_static.py
"""A StaticFiles variant that sets sane Cache-Control headers.

Plain Starlette StaticFiles sends only Last-Modified/ETag with no explicit
Cache-Control, which lets browsers apply their own caching heuristics to
index.html -- so after a fresh deploy, a client can keep rendering the old
UI until something forces a revalidation. index.html is tiny, so we just
disable caching on it outright; everything else (Vite's content-hashed
JS/CSS/asset files) is safe to cache for a long time, since a new build
always produces new filenames.
"""
from __future__ import annotations

import os

from starlette.staticfiles import FileResponse, Headers, NotModifiedResponse, StaticFiles


class CachingStaticFiles(StaticFiles):
    def file_response(self, full_path, stat_result, scope, status_code=200):
        request_headers = Headers(scope=scope)
        response = FileResponse(full_path, status_code=status_code, stat_result=stat_result)
        if os.path.basename(str(full_path)) == "index.html":
            response.headers["cache-control"] = "no-cache"
        else:
            response.headers["cache-control"] = "public, max-age=31536000, immutable"
        if self.is_not_modified(response.headers, request_headers):
            return NotModifiedResponse(response.headers)
        return response
