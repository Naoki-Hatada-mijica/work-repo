#!/usr/bin/env python3
"""FreelanceBase の候補者インデックス API から既存プロフィールを取得する.

登録面談サマリ生成の「第5のソース」として、すでに FreelanceBase に登録済みの
プロフィール情報（氏名・生年月日・稼働形態・希望単価・希望条件・経験職種・
インボイス番号など）を取得し、最新の面談情報との突合に使う。

使い方:
    python3 fetch_profile.py <management_id>            # 候補者レコード全量を JSON 出力
    python3 fetch_profile.py <management_id> --summary  # 加えて主要フィールドを stderr に併記
    python3 fetch_profile.py <management_id> --raw       # 全量出力（既定と同じ・互換用）
    python3 fetch_profile.py --internal-id 4350          # 内部IDで直接引く

stdout に候補者レコード（candidates/index API の body）を JSON で出力する。
management_id (MJC...) は name_for_company と完全一致で突合する。
0 件なら stderr に WARN を出し、exit 2（既存情報なしとして処理を続ける）。

備考: フィールド名は実 API を実測して確定済み（`birth_date` / `occupation_key_values`
/ `work_styles_key_values` / `monthly_price_num` / `station_key_values` /
`qualified_invoice_registration_number` / `desired_*` 等）。
"""
from __future__ import annotations

import argparse
import json
import sys

sys.path.insert(0, __import__("os").path.expanduser("~/.claude/snippets"))
sys.path.insert(0, __import__("os").path.expanduser("~/.claude/skills/freelance-meeting-summarize/scripts"))

from playwright.sync_api import sync_playwright  # noqa: E402
import playwright_freelancebase as fb  # noqa: E402
from freelancebase.candidates import search_candidates, find_candidate_matches  # noqa: E402

# 突合に効く主要フィールド（--summary で stderr に出す）。実 API のキー名に準拠。
KEY_FIELDS = [
    "name", "name_kana", "birth_date", "age", "gender_id", "nationality_type_id",
    "location", "station_key_values", "work_styles_key_values", "business_day_key_values",
    "monthly_price_num", "monthly_price_f_num", "qualified_invoice_registration_number",
    "occupation_key_values", "dev_process_ids", "contact_method",
    "desired_location", "desired_detail", "desired_working_schedule", "desired_other",
    "online_interview_recording_url", "sales_status_id", "traffic_source_key_values",
]


def fetch_record(management_id: str) -> dict | None:
    """管理用IDで index API を検索し、一致するレコードを返す。"""
    with sync_playwright() as pw:
        browser, context, page = fb.login(pw, headless=True)
        try:
            # 管理用IDの MJC 部分（末尾の _XX を落とす）で広めに検索
            key = management_id.split("_")[0] if "_" in management_id else management_id
            results = search_candidates(page, key)
            if not results:
                # フルの管理用IDでも試す
                results = search_candidates(page, management_id)
            matches = find_candidate_matches(results, management_id=management_id)
            if matches:
                if len(matches) > 1:
                    print(f"[WARN] 複数ヒット ({len(matches)}件)。先頭を採用", file=sys.stderr)
                return matches[0]
            # name_for_company 完全一致で拾えなかった場合は候補が1件ならそれを採用
            return results[0] if len(results) == 1 else None
        finally:
            browser.close()


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("management_id", nargs="?", help="管理用ID (MJC..._XX)")
    p.add_argument("--internal-id", type=int, help="既知の内部ID (id_by_enterprise_id)")
    p.add_argument("--summary", action="store_true", help="主要フィールドを stderr に併記")
    p.add_argument("--raw", action="store_true", help="全量出力（既定と同じ・互換用）")
    args = p.parse_args()

    if not args.management_id and args.internal_id is None:
        p.error("management_id か --internal-id のいずれかが必要")

    rec: dict | None = None
    if args.management_id:
        rec = fetch_record(args.management_id)
    else:
        # internal-id 指定時は index を id_by_enterprise_id で絞る
        with sync_playwright() as pw:
            browser, context, page = fb.login(pw, headless=True)
            try:
                results = search_candidates(page, str(args.internal_id))
                rec = next(
                    (r for r in results if r.get("id_by_enterprise_id") == args.internal_id),
                    None,
                )
            finally:
                browser.close()

    if rec is None:
        print("[WARN] 既存プロフィールが見つかりません（FB 未登録 / 新規登録直後 等）", file=sys.stderr)
        return 2

    if args.summary:
        picked = {k: rec.get(k) for k in KEY_FIELDS}
        print("=== 既存プロフィール要点 ===", file=sys.stderr)
        print(json.dumps(picked, ensure_ascii=False, indent=2), file=sys.stderr)

    print(json.dumps(rec, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
