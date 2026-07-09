#!/usr/bin/env python3
"""FreelanceBase 候補者詳細のコメントタブから最新1件のコメント本文を取得する.

使い方:
    python3 fetch_comment.py <management_id>
    python3 fetch_comment.py --internal-id 711
    python3 fetch_comment.py <management_id> --json

標準出力に最新コメントの本文を出す（--json 時は timestamp/author/body を JSON で出力）。
コメントが 0 件なら stderr に WARN を出し、stdout は空文字列。
"""
from __future__ import annotations

import argparse
import json
import sys

sys.path.insert(0, __import__("os").path.expanduser("~/.claude/snippets"))
sys.path.insert(0, __import__("os").path.expanduser("~/.claude/skills/freelance-meeting-summarize/scripts"))

from playwright.sync_api import sync_playwright  # noqa: E402
import playwright_freelancebase as fb  # noqa: E402
from freelancebase.comments import latest_candidate_comment  # noqa: E402
import crm_write  # noqa: E402


def fetch_latest_comment(internal_id: int) -> dict | None:
    """候補者詳細のコメントタブから最新1件を取得. dict or None."""
    with sync_playwright() as pw:
        browser, context, page = fb.login(pw, headless=True)
        try:
            page.goto(
                f"https://freelancebase.jp/enterprise/candidates/{internal_id}#comment-tab",
                wait_until="networkidle",
            )
            page.wait_for_timeout(2500)
            return latest_candidate_comment(page)
        finally:
            browser.close()


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("management_id", nargs="?", help="管理用ID (MJC...). --internal-id 指定時は不要")
    p.add_argument("--internal-id", type=int, help="既知の内部ID（指定時は解決スキップ）")
    p.add_argument("--json", action="store_true", help="author/timestamp/body を JSON で出力")
    args = p.parse_args()

    iid = args.internal_id
    if iid is None:
        if not args.management_id:
            p.error("management_id か --internal-id のいずれかが必要")
        with sync_playwright() as pw:
            browser, context, page = fb.login(pw, headless=True)
            try:
                iid = crm_write.resolve_internal_id(page, args.management_id)
            finally:
                browser.close()
        if iid is None:
            print(f"[ERR] 内部ID 解決失敗: {args.management_id}", file=sys.stderr)
            return 3

    latest = fetch_latest_comment(iid)
    if latest is None:
        print("[WARN] コメントが存在しません", file=sys.stderr)
        return 0
    if args.json:
        print(json.dumps(latest, ensure_ascii=False, indent=2))
    else:
        print(latest["body"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
