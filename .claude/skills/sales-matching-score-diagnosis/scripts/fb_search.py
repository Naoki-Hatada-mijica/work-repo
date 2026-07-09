#!/usr/bin/env python3
"""FreelanceBase 検索フォールバック（案件 / 人材）。

シート（案件マスタ Doc）や input/Slack/Gmail で案件・人材情報が掴めないとき、
FreelanceBase を検索して情報を取得するための薄いラッパー。
共通基盤 `~/.claude/snippets/freelancebase/` と
`playwright_freelancebase.py`（OTP 不要・env 認証）を再利用する（スクリプトは複製しない）。

事前準備:
  - `~/.zshrc` 等に `FREELANCEBASE_EMAIL` / `FREELANCEBASE_PASSWORD` が設定済みであること
  - `pip3 install playwright && playwright install chromium`

使い方:
  # 案件をキーワード検索（一致した案件をフル整形 JSON で出力）
  python3 fb_search.py jobs "インフラ基盤構築支援"
  python3 fb_search.py jobs "生成AI" --limit 5

  # 人材をキーワード（氏名・スキル等）検索（生 JSON で出力）
  python3 fb_search.py candidates "山田"
  python3 fb_search.py candidates "SRE Terraform" --limit 10

出力は JSON（stdout）。ログ・進捗は stderr。認証ヘッダ等は出力しない。
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import sys

SNIPPETS = __import__("os").path.expanduser("~/.claude/snippets")
sys.path.insert(0, SNIPPETS)

STATE_PATH = os.path.expanduser("~/.cache/sales-matching/fb_state.json")
JOBS_URL = "https://freelancebase.jp/enterprise/jobs"
JOBS_INDEX_EP = "/api/enterprise/jobs/index"
CANDIDATES_INDEX_EP = "/api/enterprise/candidates/index"


def _kv_names(d):
    if not isinstance(d, dict):
        return None
    return [v.get("name") for v in d.values() if isinstance(v, dict) and v.get("name")]


def clean_job(j: dict) -> dict:
    """案件レコードからスコアリングに必要な項目だけ抽出する。"""
    return {
        "id": j.get("id"),
        "title": j.get("name") or j.get("title"),
        "detail": j.get("detail"),
        "required": j.get("required"),
        "welcome": j.get("welcome"),
        "skill_desc": j.get("skill_desc"),
        "monthly_price_from": j.get("monthly_price_f_num"),
        "monthly_price_to": j.get("monthly_price_l_num"),
        "monthly_payment_from": j.get("monthly_payment_f_num"),
        "monthly_payment_to": j.get("monthly_payment_l_num"),
        "expected_age_min": j.get("expected_age_min"),
        "expected_age_max": j.get("expected_age_max"),
        "accept_foreigner_type_id": j.get("accept_foreigner_type_id"),
        "accept_foreigner_desc": j.get("accept_foreigner_desc"),
        "inception_day": j.get("inception_day"),
        "work_style": _kv_names(j.get("work_styles_key_values")),
        "business_day": _kv_names(j.get("business_day_key_values")),
        "company": _kv_names(j.get("company_id_by_enterprise_key_values")),
        "prefecture": _kv_names(j.get("prefecture_key_values")),
        "skills": _kv_names(j.get("skill_key_values")),
        "occupation": _kv_names(j.get("occupation_key_values")),
        "dev_process": _kv_names(j.get("dev_process_key_values")),
        "working_schedule": j.get("working_schedule"),
    }


def search(kind: str, keyword: str, limit: int):
    import playwright_freelancebase as fb
    from freelancebase.api import capture_request_template, fetch_json
    from playwright.sync_api import sync_playwright

    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
    with sync_playwright() as pw:
        browser, context, page = fb.login(
            pw, headless=True, storage_state=STATE_PATH, save_storage_state=STATE_PATH
        )
        try:
            if kind == "jobs":
                ep, url, body_key, cleaner = JOBS_INDEX_EP, JOBS_URL, "jobs", clean_job
            else:
                from freelancebase.core import CANDIDATES_URL

                ep, url, body_key, cleaner = (
                    CANDIDATES_INDEX_EP,
                    CANDIDATES_URL,
                    "candidates",
                    lambda x: x,
                )
            auth, payload = capture_request_template(
                page,
                endpoint=ep,
                method="POST",
                trigger=lambda: page.goto(url, wait_until="networkidle"),
            )
            p = copy.deepcopy(payload)
            p["keyword"] = keyword
            p["page"] = 1
            r = fetch_json(
                page,
                endpoint=ep,
                method="POST",
                auth=auth,
                payload=p,
                dry_run=False,
                read_only=True,
            )
            body = r.get("body") or {}
            items = body.get(body_key) if isinstance(body, dict) else None
            items = items or []
            print(
                f"[fb_search] kind={kind} keyword={keyword!r} status={r.get('status')} hits={len(items)}",
                file=sys.stderr,
            )
            return [cleaner(it) for it in items[:limit]]
        finally:
            browser.close()


def main():
    ap = argparse.ArgumentParser(description="FreelanceBase 案件/人材 検索フォールバック")
    ap.add_argument("kind", choices=["jobs", "candidates"], help="検索対象")
    ap.add_argument("keyword", help="検索キーワード（案件タイトル / 氏名 / スキル等）")
    ap.add_argument("--limit", type=int, default=10, help="最大取得件数（既定10）")
    args = ap.parse_args()

    try:
        results = search(args.kind, args.keyword, args.limit)
    except Exception as e:  # noqa: BLE001
        print(f"[fb_search] ERROR: {e!r}", file=sys.stderr)
        sys.exit(1)
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
