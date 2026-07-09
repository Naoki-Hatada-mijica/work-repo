"""Shared constants and login helpers for TechDirect automation."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

SNIPPETS_DIR = Path(__file__).resolve().parents[1]
if str(SNIPPETS_DIR) not in sys.path:
    sys.path.insert(0, str(SNIPPETS_DIR))

import playwright_techdirect as td  # noqa: E402

BASE_URL = "https://techdirect.jp"
LOGIN_URL = f"{BASE_URL}/login"
ORG_ID = "39336"
STATE_PATH = Path("/tmp/td_state.json")


def build_url(path_or_url: str) -> str:
    if path_or_url.startswith("http://") or path_or_url.startswith("https://"):
        return path_or_url
    if not path_or_url.startswith("/"):
        path_or_url = f"/{path_or_url}"
    return urljoin(BASE_URL, path_or_url)


def ensure_local_output_dir(path: str | Path) -> Path:
    out = Path(path).expanduser()
    out.mkdir(parents=True, exist_ok=True)
    return out


def login_with_cache(playwright: Any, *, headless: bool = True, state_path: str | Path = STATE_PATH) -> tuple[Any, Any, Any]:
    """Login to TechDirect, preferring a local storage_state cache."""
    state = Path(state_path)
    if state.exists():
        browser = playwright.chromium.launch(headless=headless)
        context = browser.new_context(storage_state=str(state))
        page = context.new_page()
        page.goto(build_url("/jobs"), wait_until="networkidle")
        page.wait_for_timeout(2000)
        if "login" not in page.url:
            return browser, context, page
        browser.close()

    browser, context, page = td.login(playwright, headless=headless)
    try:
        context.storage_state(path=str(state))
    except Exception:
        pass
    return browser, context, page
