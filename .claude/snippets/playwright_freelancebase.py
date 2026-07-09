"""フリーランスベース Playwrightログインモジュール

環境変数:
  FREELANCEBASE_EMAIL / FREELANCEBASE_PASSWORD

注意:
  - OTP不要。ログイン後 /enterprise/candidates にリダイレクト
  - ページ仕様調査・API捕捉・候補者/企業 helper は `freelancebase.*`
    パッケージ側に分離している。このファイルは後方互換の入口として使う。

使い方:
  from playwright.sync_api import sync_playwright
  import sys; sys.path.insert(0, __import__("os").path.expanduser("~/.claude/snippets"))
  import playwright_freelancebase as fb

  with sync_playwright() as pw:
      browser, context, page = fb.login(pw)
      # page はログイン済み状態（人材一覧画面）
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

from freelancebase import (  # noqa: F401
    BASE_URL,
    CANDIDATES_URL,
    COMPANIES_URL,
    LOGIN_URL,
    build_url,
    candidate_detail_url,
    company_detail_url,
    goto,
)
from freelancebase.core import USER_AGENT

EMAIL_ENV = "FREELANCEBASE_EMAIL"
PASSWORD_ENV = "FREELANCEBASE_PASSWORD"


def login(
    playwright: Any,
    headless: bool = True,
    storage_state: str | os.PathLike[str] | None = None,
    save_storage_state: str | os.PathLike[str] | None = None,
    timeout_ms: int = 15_000,
    slow_mo: int = 0,
):
    """フリーランスベースにログインし、browser, context, page を返す.

    既存互換:
        `browser, context, page = fb.login(pw)` は従来通り動作する。

    Args:
        playwright: sync_playwright のインスタンス
        headless: ヘッドレス実行するか（既定 True。可視ブラウザで確認したい時のみ False を渡す）
        storage_state: 既存セッション state のパス。存在すれば先に再利用を試す
        save_storage_state: ログイン成功後に state を保存するパス
        timeout_ms: ログイン遷移待ちタイムアウト
        slow_mo: Chromium launch の slow_mo
    """
    email = os.environ.get(EMAIL_ENV)
    password = os.environ.get(PASSWORD_ENV)

    storage_state_path = Path(storage_state).expanduser() if storage_state else None
    save_storage_state_path = (
        Path(save_storage_state).expanduser() if save_storage_state else storage_state_path
    )

    can_try_existing_state = bool(storage_state_path and storage_state_path.exists())
    if not can_try_existing_state and (not email or not password):
        raise RuntimeError(f"環境変数 {EMAIL_ENV} / {PASSWORD_ENV} を設定してください")

    browser = playwright.chromium.launch(headless=headless, slow_mo=slow_mo)
    context_args: dict[str, Any] = {"user_agent": USER_AGENT}
    if can_try_existing_state:
        context_args["storage_state"] = str(storage_state_path)
    context = browser.new_context(**context_args)
    page = context.new_page()

    if storage_state_path and storage_state_path.exists():
        page.goto(CANDIDATES_URL, wait_until="networkidle", timeout=timeout_ms)
        if "/enterprise/signin" not in page.url:
            print("[INFO] freelancebase: 既存セッションを再利用", file=sys.stderr)
            return browser, context, page
        print("[INFO] freelancebase: セッション期限切れ、再ログイン", file=sys.stderr)
        if not email or not password:
            raise RuntimeError(f"環境変数 {EMAIL_ENV} / {PASSWORD_ENV} を設定してください")

    print("[INFO] freelancebase: ログイン中...", file=sys.stderr)
    page.goto(LOGIN_URL, wait_until="networkidle")

    # フォーム入力
    page.get_by_role("textbox", name="contact@freelancebase.jp").fill(email)
    page.get_by_role("textbox", name="半角英数字8文字").fill(password)
    page.get_by_role("button", name="ログインする").click()

    try:
        page.wait_for_load_state("networkidle", timeout=timeout_ms)
    except Exception:
        pass
    page.wait_for_timeout(5000)
    print(f"[INFO] freelancebase: ログイン後URL: {page.url}", file=sys.stderr)

    if "/enterprise/signin" in page.url:
        raise RuntimeError(f"freelancebase ログイン失敗: URL={page.url}")

    if save_storage_state_path:
        save_storage_state_path.parent.mkdir(parents=True, exist_ok=True)
        context.storage_state(path=str(save_storage_state_path))
        print(f"[INFO] freelancebase: storage_state 保存: {save_storage_state_path}", file=sys.stderr)

    return browser, context, page
