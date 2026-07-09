"""Shared constants and navigation helpers for FreelanceBase automation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

BASE_URL = "https://freelancebase.jp"
LOGIN_URL = f"{BASE_URL}/enterprise/signin"
CANDIDATES_URL = f"{BASE_URL}/enterprise/candidates"
COMPANIES_URL = f"{BASE_URL}/enterprise/companies"
PROJECTS_URL = f"{BASE_URL}/enterprise/projects"
ENTERPRISE_API_PREFIX = "/api/enterprise/"

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
)


@dataclass(frozen=True)
class LoginOptions:
    """Options for creating a logged-in browser context."""

    headless: bool = False
    storage_state: str | Path | None = None
    save_storage_state: str | Path | None = None
    timeout_ms: int = 15_000
    slow_mo: int = 0


def build_url(path_or_url: str) -> str:
    """Return an absolute FreelanceBase URL for a path or existing URL."""
    if path_or_url.startswith("http://") or path_or_url.startswith("https://"):
        return path_or_url
    if not path_or_url.startswith("/"):
        path_or_url = f"/{path_or_url}"
    return urljoin(BASE_URL, path_or_url)


def goto(page: Any, path_or_url: str, *, wait_until: str = "networkidle", timeout: int = 30_000) -> str:
    """Navigate to a FreelanceBase page and return the final URL."""
    url = build_url(path_or_url)
    page.goto(url, wait_until=wait_until, timeout=timeout)
    return page.url


def candidate_detail_url(candidate_id: int | str, tab: str | None = None) -> str:
    """Build a candidate detail URL.

    `candidate_id` must be the enterprise-visible integer ID
    (`id_by_enterprise_id`), not the auth/user table ID.
    """
    suffix = f"#{tab}" if tab else ""
    return f"{CANDIDATES_URL}/{candidate_id}{suffix}"


def company_detail_url(company_id: int | str, tab: str | None = None) -> str:
    suffix = f"#{tab}" if tab else ""
    return f"{COMPANIES_URL}/{company_id}{suffix}"


def short_text(value: str | None, limit: int = 120) -> str:
    """Normalize UI text for logs/spec summaries without dumping full content."""
    if not value:
        return ""
    text = " ".join(value.split())
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "..."


def ensure_local_output_dir(path: str | Path) -> Path:
    out = Path(path).expanduser()
    out.mkdir(parents=True, exist_ok=True)
    return out

