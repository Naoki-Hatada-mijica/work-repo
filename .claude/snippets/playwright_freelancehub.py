"""フリーランスHub Playwrightログインモジュール（freelance-hub.jp）

FreelanceBase（freelancebase.jp）とは別サービスである点に注意。

環境変数:
  FREELANCEHUB_LOGIN_KEY / FREELANCEHUB_EMAIL / FREELANCEHUB_PASSWORD

使い方:
  from playwright.sync_api import sync_playwright
  import sys; sys.path.insert(0, __import__("os").path.expanduser("~/.claude/snippets"))
  import playwright_freelancehub as fh

  with sync_playwright() as pw:
      browser, context, page = fh.login(pw)
      # page はログイン済み状態（応募者管理画面）
"""

from __future__ import annotations

import os
import sys
from typing import Optional

LOGIN_URL = "https://agent.freelance-hub.jp/login"
LOGIN_KEY_ENV = "FREELANCEHUB_LOGIN_KEY"
EMAIL_ENV = "FREELANCEHUB_EMAIL"
PASSWORD_ENV = "FREELANCEHUB_PASSWORD"


USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
)


def login(playwright, headless: bool = True, storage_state: Optional[str] = None):
    """フリーランスHub にログインし、(browser, context, page) を返す.

    Args:
        playwright: sync_playwright のインスタンス
        headless: ヘッドレスモード（デフォルト True）
        storage_state: 既存セッションの storage_state.json パス（あれば再利用）

    Returns:
        (browser, context, page)
    """
    login_key = os.environ.get(LOGIN_KEY_ENV)
    email = os.environ.get(EMAIL_ENV)
    password = os.environ.get(PASSWORD_ENV)

    if not (login_key and email and password):
        raise RuntimeError(
            f"環境変数 {LOGIN_KEY_ENV} / {EMAIL_ENV} / {PASSWORD_ENV} を設定してください"
        )

    browser = playwright.chromium.launch(headless=headless)
    context_args: dict = {"user_agent": USER_AGENT}
    if storage_state and os.path.exists(storage_state):
        context_args["storage_state"] = storage_state
    context = browser.new_context(**context_args)
    page = context.new_page()

    # 既存セッションで /entry にアクセスし、ログイン画面に飛ばされなければスキップ
    if storage_state and os.path.exists(storage_state):
        page.goto("https://agent.freelance-hub.jp/entry", wait_until="networkidle")
        if "/login" not in page.url:
            print("[INFO] freelancehub: 既存セッションを再利用", file=sys.stderr)
            return browser, context, page
        print("[INFO] freelancehub: セッション期限切れ、再ログイン", file=sys.stderr)

    print("[INFO] freelancehub: ログイン中...", file=sys.stderr)
    page.goto(LOGIN_URL, wait_until="networkidle")
    page.fill("input[name='login_key']", login_key)
    page.fill("input[name='email']", email)
    page.fill("input[name='password']", password)
    page.locator("button[type='submit']").first.click()
    page.wait_for_load_state("networkidle", timeout=15000)
    page.wait_for_timeout(2000)

    if "/login" in page.url:
        raise RuntimeError(f"freelancehub ログイン失敗: URL={page.url}")

    print(f"[INFO] freelancehub: ログイン成功 -> {page.url}", file=sys.stderr)

    if storage_state:
        context.storage_state(path=storage_state)

    return browser, context, page
