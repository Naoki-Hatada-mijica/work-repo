"""Candidate read helpers for FreelanceBase."""

from __future__ import annotations

import copy
import re
from typing import Any

from .api import capture_request_template, fetch_json
from .core import CANDIDATES_URL, candidate_detail_url

CANDIDATE_INDEX_ENDPOINT = "/api/enterprise/candidates/index"


def capture_candidate_index_template(page: Any) -> tuple[dict[str, str], dict[str, Any]]:
    return capture_request_template(
        page,
        endpoint=CANDIDATE_INDEX_ENDPOINT,
        method="POST",
        trigger=lambda: page.goto(CANDIDATES_URL, wait_until="networkidle"),
    )


def search_candidates(
    page: Any,
    keyword: str,
    *,
    auth: dict[str, str] | None = None,
    payload: dict[str, Any] | None = None,
    raise_on_error: bool = False,
) -> list[dict[str, Any]]:
    """Search candidates via the observed `/candidates/index` endpoint."""
    if auth is None or payload is None:
        auth, payload = capture_candidate_index_template(page)
    next_payload = copy.deepcopy(payload)
    next_payload["keyword"] = keyword
    next_payload["page"] = 1
    result = fetch_json(
        page,
        endpoint=CANDIDATE_INDEX_ENDPOINT,
        method="POST",
        auth=auth,
        payload=next_payload,
        dry_run=False,
        read_only=True,
    )
    if result.get("status") != 200:
        if raise_on_error:
            raise RuntimeError(
                f"FB candidates/index API status={result.get('status')} query={keyword!r}"
            )
        return []
    body = result.get("body") or {}
    return body.get("candidates", []) if isinstance(body, dict) else []


def normalize_name(value: str | None) -> str:
    return (value or "").replace(" ", "").replace("　", "").strip()


def find_candidate_matches(
    candidates: list[dict[str, Any]],
    *,
    full_name: str | None = None,
    last_name: str | None = None,
    first_name: str | None = None,
    management_id: str | None = None,
    email: str | None = None,
) -> list[dict[str, Any]]:
    """Filter candidate search results to likely exact matches."""
    target_name = normalize_name(full_name or f"{last_name or ''}{first_name or ''}")
    out: list[dict[str, Any]] = []
    for candidate in candidates:
        if management_id and candidate.get("name_for_company") == management_id:
            out.append(candidate)
            continue
        if email and candidate.get("email") == email:
            out.append(candidate)
            continue
        c_last = (candidate.get("l_name") or "").strip()
        c_first = (candidate.get("f_name") or "").strip()
        if last_name and first_name and c_last == last_name and c_first == first_name:
            out.append(candidate)
            continue
        if target_name:
            names = [
                normalize_name(candidate.get("name")),
                normalize_name(candidate.get("supplier_name")),
                normalize_name(f"{c_last}{c_first}"),
            ]
            if target_name in names:
                out.append(candidate)
    return out


def candidate_id(candidate: dict[str, Any]) -> int | None:
    value = candidate.get("id_by_enterprise_id")
    return value if isinstance(value, int) else None


def open_candidate_detail(page: Any, candidate_id_value: int | str, *, tab: str | None = None) -> str:
    url = candidate_detail_url(candidate_id_value, tab=tab)
    page.goto(url, wait_until="networkidle")
    return page.url


def parse_candidate_id_from_url(url: str) -> int | None:
    match = re.search(r"/enterprise/candidates/(\d+)", url)
    return int(match.group(1)) if match else None
