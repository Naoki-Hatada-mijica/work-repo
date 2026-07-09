"""TechDirect API observation and write guard helpers."""

from __future__ import annotations

import json
import re
import time
from dataclasses import asdict, dataclass
from typing import Any, Callable
from urllib.parse import urlsplit

API_HOSTS = {"api.codeal.work", "techdirect.jp"}
SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


@dataclass
class ApiCallSummary:
    method: str
    host: str
    path: str
    status: int | None = None
    response_keys: list[str] | None = None
    elapsed_ms: int | None = None
    write_candidate: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def normalize_path(url: str) -> tuple[str, str]:
    parsed = urlsplit(url)
    host = parsed.netloc
    path = parsed.path
    path = re.sub(r"/[0-9a-f]{8}-[0-9a-f-]{27,36}(?=/|$)", "/{uuid}", path, flags=re.IGNORECASE)
    path = re.sub(r"/\d+(?=/|$)", "/{id}", path)
    return host, path


def is_techdirect_api(url: str) -> bool:
    parsed = urlsplit(url)
    if parsed.netloc == "api.codeal.work":
        return True
    return parsed.netloc == "techdirect.jp" and (parsed.path.startswith("/api/") or "/api/" in parsed.path)


def is_write_candidate(method: str, url: str) -> bool:
    if not is_techdirect_api(url):
        return False
    return method.upper() not in SAFE_METHODS


def _json_keys(text: str | None) -> list[str]:
    if not text:
        return []
    try:
        obj = json.loads(text)
    except Exception:
        return []
    if isinstance(obj, dict):
        return sorted(str(k) for k in obj.keys())[:80]
    if isinstance(obj, list) and obj and isinstance(obj[0], dict):
        return sorted(str(k) for k in obj[0].keys())[:80]
    return []


class ApiRecorder:
    """Record summarized TechDirect/Codeal API calls without bodies or auth headers."""

    def __init__(self, page: Any):
        self.page = page
        self.calls: list[ApiCallSummary] = []
        self._started: dict[Any, float] = {}
        self._request_handler: Callable[[Any], None] | None = None
        self._response_handler: Callable[[Any], None] | None = None

    def __enter__(self) -> "ApiRecorder":
        def on_request(req: Any) -> None:
            if not is_techdirect_api(req.url):
                return
            host, path = normalize_path(req.url)
            self._started[req] = time.time()
            self.calls.append(
                ApiCallSummary(
                    method=req.method,
                    host=host,
                    path=path,
                    write_candidate=is_write_candidate(req.method, req.url),
                )
            )

        def on_response(resp: Any) -> None:
            if not is_techdirect_api(resp.url):
                return
            req = resp.request
            host, path = normalize_path(resp.url)
            target = None
            for call in reversed(self.calls):
                if call.host == host and call.path == path and call.method == req.method and call.status is None:
                    target = call
                    break
            if target is None:
                target = ApiCallSummary(
                    method=req.method,
                    host=host,
                    path=path,
                    write_candidate=is_write_candidate(req.method, resp.url),
                )
                self.calls.append(target)
            target.status = resp.status
            started = self._started.get(req)
            if started:
                target.elapsed_ms = int((time.time() - started) * 1000)
            try:
                target.response_keys = _json_keys(resp.text())
            except Exception:
                target.response_keys = []

        self._request_handler = on_request
        self._response_handler = on_response
        self.page.on("request", on_request)
        self.page.on("response", on_response)
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        if self._request_handler:
            self.page.remove_listener("request", self._request_handler)
        if self._response_handler:
            self.page.remove_listener("response", self._response_handler)

    def to_dicts(self) -> list[dict[str, Any]]:
        return [call.to_dict() for call in self.calls]


def install_write_guard(page: Any, blocked: list[dict[str, Any]]) -> None:
    def handler(route: Any, request: Any) -> None:
        if is_write_candidate(request.method, request.url):
            host, path = normalize_path(request.url)
            blocked.append({"method": request.method, "host": host, "path": path, "reason": "aborted_by_techdirect_probe"})
            route.abort()
            return
        route.continue_()

    page.route("**/*", handler)
