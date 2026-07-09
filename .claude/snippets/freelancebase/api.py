"""FreelanceBase internal API observation helpers.

These helpers intentionally default to read-only behavior. They record endpoint
shape and auth headers without dumping full payloads or responses that may
contain PII.
"""

from __future__ import annotations

import copy
import json
import time
from dataclasses import asdict, dataclass
from typing import Any, Callable

from .core import ENTERPRISE_API_PREFIX

SENSITIVE_HEADERS = {
    "access-token",
    "authorization",
    "client",
    "cookie",
    "set-cookie",
    "uid",
    "x-csrf-token",
}

WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
READISH_POST_ENDPOINTS = {
    "/api/enterprise/candidates/index",
    "/api/enterprise/companies/index",
    "/api/enterprise/projects/index",
}


@dataclass
class ApiCallSummary:
    method: str
    url: str
    path: str
    status: int | None = None
    request_keys: list[str] | None = None
    response_keys: list[str] | None = None
    elapsed_ms: int | None = None
    destructive_candidate: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def api_path(url: str) -> str:
    marker = ENTERPRISE_API_PREFIX
    if marker in url:
        return marker + url.split(marker, 1)[1].split("?", 1)[0]
    return url


def is_enterprise_api(url: str) -> bool:
    return ENTERPRISE_API_PREFIX in url


def is_destructive_candidate(method: str, path: str) -> bool:
    method = method.upper()
    if method in {"PUT", "PATCH", "DELETE"}:
        return True
    if method == "POST" and (
        path in READISH_POST_ENDPOINTS
        or path.endswith("/index")
        or path.endswith("/search")
    ):
        return False
    if method == "POST" and (path.endswith("/preview") or path.endswith("_preview")):
        return False
    if method == "POST":
        return True
    return False


def redact_headers(headers: dict[str, str]) -> dict[str, str]:
    redacted: dict[str, str] = {}
    for key, value in headers.items():
        if key.lower() in SENSITIVE_HEADERS:
            redacted[key] = "<redacted>"
        else:
            redacted[key] = value
    return redacted


def enterprise_auth_headers(headers: dict[str, str]) -> dict[str, str]:
    """Extract headers needed for same-session API calls."""
    lowered = {k.lower(): v for k, v in headers.items()}
    return {
        "X-CSRF-Token": lowered.get("x-csrf-token", ""),
        "uid": lowered.get("uid", ""),
        "client": lowered.get("client", ""),
        "access-token": lowered.get("access-token", ""),
        "token-type": lowered.get("token-type", "Bearer"),
        "strategies": lowered.get("strategies", "enterprise"),
    }


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


def request_payload_keys(post_data: str | None) -> list[str]:
    return _json_keys(post_data)


class ApiRecorder:
    """Record summarized `/api/enterprise/...` traffic for page-spec probing."""

    def __init__(self, page: Any, *, include_response_keys: bool = True):
        self.page = page
        self.include_response_keys = include_response_keys
        self.calls: list[ApiCallSummary] = []
        self._started: dict[Any, float] = {}
        self._request_handler: Callable[[Any], None] | None = None
        self._response_handler: Callable[[Any], None] | None = None

    def __enter__(self) -> "ApiRecorder":
        def on_request(req: Any) -> None:
            if not is_enterprise_api(req.url):
                return
            path = api_path(req.url)
            self._started[req] = time.time()
            self.calls.append(
                ApiCallSummary(
                    method=req.method,
                    url=req.url,
                    path=path,
                    request_keys=request_payload_keys(getattr(req, "post_data", None)),
                    destructive_candidate=is_destructive_candidate(req.method, path),
                )
            )

        def on_response(resp: Any) -> None:
            req = resp.request
            if not is_enterprise_api(resp.url):
                return
            path = api_path(resp.url)
            target = None
            for call in reversed(self.calls):
                if call.path == path and call.method == req.method and call.status is None:
                    target = call
                    break
            if target is None:
                target = ApiCallSummary(method=req.method, url=resp.url, path=path)
                self.calls.append(target)
            target.status = resp.status
            started = self._started.get(req)
            if started:
                target.elapsed_ms = int((time.time() - started) * 1000)
            if self.include_response_keys:
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


def capture_request_template(
    page: Any,
    *,
    endpoint: str,
    trigger: Callable[[], Any],
    method: str = "POST",
    timeout_ms: int = 10_000,
) -> tuple[dict[str, str], dict[str, Any]]:
    """Capture auth headers and JSON payload for an API request.

    The `trigger` callback should navigate or interact with the page so the
    target request is naturally emitted by the browser session.
    """
    state: dict[str, Any] = {"headers": None, "payload": None}
    method = method.upper()

    def on_request(req: Any) -> None:
        if endpoint in req.url and req.method.upper() == method and state["headers"] is None:
            state["headers"] = dict(req.headers)
            try:
                state["payload"] = json.loads(req.post_data or "{}")
            except Exception:
                state["payload"] = {}

    page.on("request", on_request)
    try:
        trigger()
        page.wait_for_timeout(min(timeout_ms, 3000))
    finally:
        page.remove_listener("request", on_request)

    if not state["headers"]:
        raise RuntimeError(f"API request template capture failed: {method} {endpoint}")
    return enterprise_auth_headers(state["headers"]), state["payload"] or {}


def fetch_json(
    page: Any,
    *,
    endpoint: str,
    method: str = "POST",
    auth: dict[str, str] | None = None,
    payload: dict[str, Any] | None = None,
    dry_run: bool = True,
    read_only: bool = True,
) -> dict[str, Any]:
    """Call a same-origin API endpoint from the browser context.

    Defaults are safe for read-only POST endpoints such as `/index`. To perform
    actual writes, call with `dry_run=False` and `read_only=False`.
    """
    method = method.upper()
    path = api_path(endpoint)
    if is_destructive_candidate(method, path) and (dry_run or read_only):
        return {
            "dry_run": True,
            "skipped": True,
            "method": method,
            "endpoint": endpoint,
            "reason": "destructive_candidate",
            "payload_keys": sorted((payload or {}).keys()),
        }

    payload_copy = copy.deepcopy(payload or {})
    result = page.evaluate(
        """async ({endpoint, method, payload, auth}) => {
            const headers = {'Accept':'application/json', ...auth};
            const init = {method, credentials:'include', headers};
            if (method !== 'GET') {
                headers['Content-Type'] = 'application/json';
                init.body = JSON.stringify(payload || {});
            }
            const r = await fetch(endpoint, init);
            return {status: r.status, text: await r.text()};
        }""",
        {"endpoint": endpoint, "method": method, "payload": payload_copy, "auth": auth or {}},
    )
    text = result.get("text") or ""
    try:
        body = json.loads(text)
    except Exception:
        body = {"raw_text_head": text[:500]}
    return {"status": result.get("status"), "body": body}
