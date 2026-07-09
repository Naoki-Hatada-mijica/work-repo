"""TechDirect Playwrightログインモジュール

環境変数:
  TECHDIRECT_EMAIL / TECHDIRECT_PASSWORD

OTP対応:
  ログイン後にOTP画面（/login_email_otp）に遷移した場合、
  標準出力に "OTP_REQUIRED" を出力し、/tmp/techdirect_otp.txt への
  OTPコード書き込みを待機する。
  Claude CodeがGmail MCPでOTPを取得し、ファイルに書き込む想定。
    - Gmail検索: label:"01D.Claude" subject:ワンタイムパスワード newer_than:3m
      （TechDirect OTPメールはフィルタで 01D.Claude に自動アーカイブされる）
    - snippetから6桁の数字を抽出

注意:
  - headless=True（Playwright 1.58+ではnew headlessがデフォルト）
  - reCAPTCHA v3（invisible）あり。headlessモードなら通過可能

使い方:
  from playwright.sync_api import sync_playwright
  import sys; sys.path.insert(0, __import__("os").path.expanduser("~/.claude/snippets"))
  import playwright_techdirect as td

  with sync_playwright() as pw:
      browser, context, page = td.login(pw)
      # page はログイン済み状態
"""

import os
import sys
import time

LOGIN_URL = "https://techdirect.jp/login"
EMAIL_ENV = "TECHDIRECT_EMAIL"
PASSWORD_ENV = "TECHDIRECT_PASSWORD"
OTP_FILE = "/tmp/techdirect_otp.txt"
OTP_TIMEOUT = 120


def login(playwright, headless=True):
    """TechDirectにログインし、browser, context, page を返す"""
    email = os.environ.get(EMAIL_ENV)
    password = os.environ.get(PASSWORD_ENV)

    if not email or not password:
        raise RuntimeError(f"環境変数 {EMAIL_ENV} / {PASSWORD_ENV} を設定してください")

    print("[INFO] techdirect: ログイン中...", file=sys.stderr)
    browser = playwright.chromium.launch(headless=headless)
    context = browser.new_context()
    page = context.new_page()
    page.goto(LOGIN_URL, wait_until="networkidle")

    # フォーム入力
    page.locator("input#email").fill(email)
    page.locator("input#password").fill(password)
    page.locator("button[type='submit']").click()

    page.wait_for_timeout(8000)
    print(f"[INFO] techdirect: ログイン後URL: {page.url}", file=sys.stderr)

    # エラーチェック
    error = page.query_selector(".invalid-feedback")
    if error and error.is_visible():
        raise RuntimeError(f"techdirect: ログイン失敗 - {error.inner_text().strip()}")

    # OTP画面の検知
    if "login_email_otp" in page.url:
        otp_code = _wait_for_otp()
        _submit_otp(page, otp_code)

    return browser, context, page


def _wait_for_otp() -> str:
    """OTPファイルへの書き込みを待機する"""
    if os.path.exists(OTP_FILE):
        os.remove(OTP_FILE)

    print("OTP_REQUIRED", flush=True)
    print(f"[INFO] OTPコードを {OTP_FILE} に書き込んでください（{OTP_TIMEOUT}秒以内）", file=sys.stderr)

    start = time.time()
    while time.time() - start < OTP_TIMEOUT:
        if os.path.exists(OTP_FILE):
            with open(OTP_FILE) as f:
                code = f.read().strip()
            if code:
                os.remove(OTP_FILE)
                print("[INFO] OTPコード受信", file=sys.stderr)
                return code
        time.sleep(1)

    raise RuntimeError("OTP取得タイムアウト")


def _submit_otp(page, otp_code: str):
    """OTP画面でワンタイムパスワードを入力"""
    otp_input = page.locator("input[placeholder*='ワンタイムパスワード'], input[type='text']").first
    otp_input.fill(otp_code)
    page.locator("button[type='submit'], button:has-text('ログイン')").first.click()
    page.wait_for_timeout(5000)
    print(f"[INFO] techdirect: OTP認証後URL: {page.url}", file=sys.stderr)
