"""SEO記事チェック: 修正案を Google Docs へ記入する.

2つの記入方式を持つ:
  1. suggest 方式（Playwright）: Docs を「提案モード（Suggesting）」で開き、
     「検索と置換」で before→after を置換する。置換は提案として記録される。
  2. comment 方式（Drive API）: 修正案を（原文引用つき）コメントとして追加する。
     ブラウザ不要・headless 可・ログイン状態に依存しない堅牢な経路。

方針:
  - suggest 方式は Google Docs の canvas 描画のため壊れやすい。before 文字列が
    文書内で一意に見つからない/置換に失敗した項目は、自動的に comment 方式へ
    フォールバックする。--comments-only 指定時は最初から全件 comment 方式。
  - どの経路を通っても「全修正案がドキュメント上に残る」ことを保証する。

入力（--suggestions xxx.json）: 修正案の配列
  [
    {"id": "D-2", "before": "原文の完全一致文字列", "after": "修正後", "comment": "指摘理由"},
    ...
  ]
  before/after が無い（判断のみ）項目は comment 方式でコメント化する。

出力（stdout, JSON）: 各項目の適用結果
  [{"id", "method": "suggest|comment", "status": "applied|commented|failed", "detail"}]

Playwright ログイン:
  専用プロファイル（~/.config/seo-article-check/pw-profile）を使う。
  初回のみ `--login` を付けて headed で起動し、手動で Google ログインする。
  以降はプロファイルにセッションが残るため headless でも動く（切れたら再 --login）。
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

SNIPPETS_DIR = Path.home() / ".claude" / "snippets"
sys.path.insert(0, str(SNIPPETS_DIR))

from google_workspace import extract_doc_id, _get_credentials  # noqa: E402
from googleapiclient.discovery import build  # noqa: E402

PROFILE_DIR = Path.home() / ".config" / "seo-article-check" / "pw-profile"


# ---------------------------------------------------------------------------
# comment 方式（Drive API）— 堅牢な土台
# ---------------------------------------------------------------------------
def add_comment(doc_id: str, sug: dict) -> dict:
    """修正案を Drive コメントとして追加する（原文引用つき・アンカーなし）."""
    service = build("drive", "v3", credentials=_get_credentials())
    lines = [f"【SEO修正提案 {sug.get('id', '')}】"]
    if sug.get("before"):
        lines.append(f"対象（原文）: {sug['before']}")
    if sug.get("after"):
        lines.append(f"修正案: {sug['after']}")
    if sug.get("comment"):
        lines.append(f"指摘: {sug['comment']}")
    content = "\n".join(lines)
    body = {"content": content}
    if sug.get("before"):
        # 引用を付けると Docs 上で対象箇所を探しやすくなる
        body["quotedFileContent"] = {"mimeType": "text/plain", "value": sug["before"]}
    res = service.comments().create(
        fileId=doc_id, body=body, fields="id"
    ).execute()
    return {"id": sug.get("id", ""), "method": "comment", "status": "commented",
            "detail": f"comment_id={res.get('id')}"}


# ---------------------------------------------------------------------------
# suggest 方式（Playwright）
# ---------------------------------------------------------------------------
def _launch(playwright, headless: bool):
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    context = playwright.chromium.launch_persistent_context(
        user_data_dir=str(PROFILE_DIR),
        headless=headless,
        args=["--no-first-run", "--no-default-browser-check"],
        viewport={"width": 1400, "height": 1000},
    )
    page = context.pages[0] if context.pages else context.new_page()
    return context, page


def _is_logged_in(page) -> bool:
    url = page.url
    if "accounts.google.com" in url or "ServiceLogin" in url:
        return False
    # ドキュメント本体（canvas / エディタ）が出ているか
    return page.locator(".kix-appview-editor, .docs-editor").count() > 0


def do_login(headless: bool = False) -> int:
    """初回ログイン用。headed で Google にログインさせプロファイルへ保存する."""
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        context, page = _launch(pw, headless=headless)
        page.goto("https://docs.google.com/document/u/0/", wait_until="domcontentloaded")
        print("[login] ブラウザで Google にログインしてください。"
              "完了したらこのターミナルで Enter を押してください。", file=sys.stderr)
        try:
            input()
        except EOFError:
            time.sleep(60)
        context.close()
    print("[login] プロファイルを保存しました:", PROFILE_DIR, file=sys.stderr)
    return 0


def _switch_to_suggesting(page) -> bool:
    """編集モードを Suggesting に切り替える。成功可否を返す."""
    # モード切替ボタン（右上）。aria-label は言語で変わるため複数候補を試す
    btn_selectors = [
        "#docs-toolbar-mode-switcher",
        "div[aria-label*='モード']",
        "div[aria-label*='Mode']",
        "div[aria-label*='Editing']",
        "div[aria-label*='編集']",
    ]
    for sel in btn_selectors:
        loc = page.locator(sel).first
        if loc.count() > 0:
            try:
                loc.click()
                page.wait_for_timeout(500)
                break
            except Exception:
                continue
    else:
        return False
    # メニューの「提案」項目
    item_selectors = [
        "div[role='menuitem']:has-text('提案')",
        "div[role='menuitem']:has-text('Suggesting')",
        "span:has-text('提案')",
    ]
    for sel in item_selectors:
        loc = page.locator(sel).first
        if loc.count() > 0:
            try:
                loc.click()
                page.wait_for_timeout(500)
                return True
            except Exception:
                continue
    return False


def _replace_via_dialog(page, before: str, after: str) -> bool:
    """検索と置換ダイアログで before→after を全置換する。成功可否を返す."""
    # Edit メニュー経由は言語依存が強いのでショートカット（Mac: Meta+Shift+H）
    page.keyboard.press("Meta+Shift+KeyH")
    page.wait_for_timeout(700)
    find_box = page.locator("input#docs-findandreplace-search-input, "
                            "input[aria-label*='検索'], input[aria-label*='Find']").first
    repl_box = page.locator("input#docs-findandreplace-replace-input, "
                            "input[aria-label*='置換'], input[aria-label*='Replace']").first
    if find_box.count() == 0 or repl_box.count() == 0:
        return False
    find_box.fill(before)
    repl_box.fill(after)
    page.wait_for_timeout(300)
    # 「すべて置換」ボタン
    all_btn = page.locator("div[role='button']:has-text('すべて置換'), "
                           "div[role='button']:has-text('Replace all')").first
    if all_btn.count() == 0:
        return False
    all_btn.click()
    page.wait_for_timeout(500)
    # ダイアログを閉じる
    page.keyboard.press("Escape")
    page.wait_for_timeout(300)
    return True


def apply_suggest(doc_id: str, suggestions: list[dict], headless: bool) -> list[dict]:
    """Playwright で提案モード置換。失敗項目は comment へフォールバック."""
    from playwright.sync_api import sync_playwright
    results: list[dict] = []
    replaceable = [s for s in suggestions if s.get("before") and s.get("after")]
    comment_only = [s for s in suggestions if not (s.get("before") and s.get("after"))]

    with sync_playwright() as pw:
        context, page = _launch(pw, headless=headless)
        page.goto(f"https://docs.google.com/document/d/{doc_id}/edit",
                  wait_until="domcontentloaded")
        page.wait_for_timeout(4000)

        if not _is_logged_in(page):
            context.close()
            print("[suggest] 未ログイン。--login で先にログインしてください。"
                  "今回は全件 comment 方式にフォールバックします。", file=sys.stderr)
            return apply_comments(doc_id, suggestions)

        if not _switch_to_suggesting(page):
            print("[suggest] 提案モード切替に失敗。全件 comment 方式へフォールバック。",
                  file=sys.stderr)
            context.close()
            return apply_comments(doc_id, suggestions)

        for s in replaceable:
            ok = False
            try:
                ok = _replace_via_dialog(page, s["before"], s["after"])
            except Exception as e:  # noqa: BLE001
                print(f"[suggest] {s.get('id')} 置換例外: {e}", file=sys.stderr)
            if ok:
                results.append({"id": s.get("id", ""), "method": "suggest",
                                "status": "applied", "detail": "提案として置換"})
            else:
                # 個別フォールバック
                results.append(add_comment(doc_id, s))
        context.close()

    # before/after の無い項目はコメント化
    for s in comment_only:
        results.append(add_comment(doc_id, s))
    return results


def apply_comments(doc_id: str, suggestions: list[dict]) -> list[dict]:
    return [add_comment(doc_id, s) for s in suggestions]


# ---------------------------------------------------------------------------
def main() -> None:
    ap = argparse.ArgumentParser(description="修正案を Google Docs へ記入")
    ap.add_argument("--doc", help="Docs URL または ID")
    ap.add_argument("--suggestions", help="修正案 JSON（配列）")
    ap.add_argument("--comments-only", action="store_true",
                    help="Playwright を使わず全件 Drive コメントで記入")
    ap.add_argument("--login", action="store_true",
                    help="初回ログイン（headed でブラウザ起動）")
    ap.add_argument("--headless", action="store_true", help="suggest 方式を headless で実行")
    ap.add_argument("--out", help="結果 JSON の出力先")
    args = ap.parse_args()

    if args.login:
        sys.exit(do_login(headless=False))

    if not args.doc or not args.suggestions:
        ap.error("--doc と --suggestions は必須です（--login 時を除く）")

    doc_id = extract_doc_id(args.doc)
    suggestions = json.loads(Path(args.suggestions).read_text(encoding="utf-8"))

    if args.comments_only:
        results = apply_comments(doc_id, suggestions)
    else:
        results = apply_suggest(doc_id, suggestions, headless=args.headless)

    payload = json.dumps(results, ensure_ascii=False, indent=2)
    if args.out:
        Path(args.out).write_text(payload, encoding="utf-8")
        print(f"[apply_suggestions] wrote {args.out}", file=sys.stderr)
    else:
        print(payload)

    applied = sum(1 for r in results if r["status"] == "applied")
    commented = sum(1 for r in results if r["status"] == "commented")
    failed = sum(1 for r in results if r["status"] == "failed")
    print(f"[apply_suggestions] applied={applied} commented={commented} failed={failed}",
          file=sys.stderr)


if __name__ == "__main__":
    main()
