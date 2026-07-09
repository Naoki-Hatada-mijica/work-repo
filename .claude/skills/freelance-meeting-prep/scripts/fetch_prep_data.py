#!/usr/bin/env python3
"""登録面談の事前準備に使う FreelanceBase 情報を読み取り専用で取得する薄いラッパー。

共通基盤 `~/.claude/snippets/freelancebase/` と
`playwright_freelancebase.py`（OTP 不要・env 認証）を再利用する（ロジックは複製しない）。

事前準備:
  - `~/.zshrc` 等に `FREELANCEBASE_EMAIL` / `FREELANCEBASE_PASSWORD` が設定済みであること
  - Playwright が入った Python で実行する（例: `~/.pyenv/versions/3.12.13/bin/python3`）

使い方:
  # 候補者マスタを氏名 or 管理ID で検索して JSON 出力（--out 省略時は stdout）
  python3 fetch_prep_data.py candidate "髙橋 竜二" --out input/fb_candidate.json
  python3 fetch_prep_data.py candidate 4298 --out input/fb_candidate.json

  # 保存済みビュー（既定: view-105 募集中エンド直案件）の案件を全件取得
  python3 fetch_prep_data.py jobs --out input/fb_jobs.json
  python3 fetch_prep_data.py jobs --view 105 --label "募集中エンド直案件" --out input/fb_jobs.json

検証情報（ビュー適用の確認）は stdout に出力する。認証ヘッダ等は出力しない。
"""
from __future__ import annotations

import argparse
import json
import os
import sys

SNIPPETS = os.path.expanduser("~/.claude/snippets")
sys.path.insert(0, SNIPPETS)

STATE_PATH = os.path.expanduser("~/.cache/freelance-meeting-prep/fb_state.json")
DEFAULT_VIEW_ID = 105
DEFAULT_VIEW_LABEL = "募集中エンド直案件"


def _write(data, out: str | None) -> None:
    text = json.dumps(data, ensure_ascii=False, indent=2)
    if out:
        os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
        with open(out, "w") as f:
            f.write(text)
        print(f"[fetch_prep_data] wrote {out}", file=sys.stderr)
    else:
        print(text)


def run_candidate(query: str, out: str | None) -> None:
    import playwright_freelancebase as fb
    from freelancebase.candidates import search_candidates
    from playwright.sync_api import sync_playwright

    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
    with sync_playwright() as pw:
        browser, context, page = fb.login(
            pw, headless=True, storage_state=STATE_PATH, save_storage_state=STATE_PATH
        )
        try:
            # 氏名そのままでヒットしない場合に備え、姓のみ等でも引けるよう素直に検索する
            cands = search_candidates(page, query, raise_on_error=True)
        finally:
            browser.close()

    q_digits = query.strip()
    matched = [
        c
        for c in cands
        if q_digits.isdigit()
        and str(q_digits) in (str(c.get("id_by_enterprise_id")), str(c.get("id")))
    ]
    if not matched:
        norm = query.replace(" ", "").replace("　", "")
        matched = [c for c in cands if norm and norm in (c.get("name") or "").replace(" ", "").replace("　", "")]
    if not matched:
        matched = cands  # フォールバック: 検索結果をそのまま渡し、Claude 側で同定

    print(
        f"[fetch_prep_data] candidate query={query!r} hits={len(cands)} matched={len(matched)}",
        file=sys.stderr,
    )
    for c in matched:
        print(
            f"  - id_by_enterprise_id={c.get('id_by_enterprise_id')} "
            f"name={c.get('name')!r}",
            file=sys.stderr,
        )
    _write(matched, out)


def run_jobs(view_id: int, label: str | None, out: str | None, raw: bool) -> None:
    import playwright_freelancebase as fb
    from freelancebase.jobs import fetch_view_jobs
    from playwright.sync_api import sync_playwright

    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
    with sync_playwright() as pw:
        browser, context, page = fb.login(
            pw, headless=True, storage_state=STATE_PATH, save_storage_state=STATE_PATH
        )
        try:
            jobs, verification = fetch_view_jobs(
                page, view_id, expected_label=label, raw=raw
            )
        finally:
            browser.close()

    print("=== VIEW VERIFICATION ===")
    print(json.dumps(verification, ensure_ascii=False, indent=2))
    _write(jobs, out)


def main() -> None:
    ap = argparse.ArgumentParser(description="登録面談 事前準備用 FreelanceBase 取得")
    sub = ap.add_subparsers(dest="kind", required=True)

    pc = sub.add_parser("candidate", help="候補者マスタを氏名/管理IDで検索")
    pc.add_argument("query", help="氏名（例: 髙橋 竜二）または enterprise ID（例: 4298）")
    pc.add_argument("--out", help="出力先 JSON パス（省略時 stdout）")

    pj = sub.add_parser("jobs", help="保存済みビューの案件を全件取得")
    pj.add_argument("--view", type=int, default=DEFAULT_VIEW_ID, help=f"ビューID（既定 {DEFAULT_VIEW_ID}）")
    pj.add_argument("--label", default=DEFAULT_VIEW_LABEL, help="ビュータブのラベル（適用検証用）")
    pj.add_argument("--out", help="出力先 JSON パス（省略時 stdout）")
    pj.add_argument("--raw", action="store_true", help="clean_job せず生レコードで出力")

    args = ap.parse_args()
    try:
        if args.kind == "candidate":
            run_candidate(args.query, args.out)
        else:
            run_jobs(args.view, args.label, args.out, args.raw)
    except Exception as e:  # noqa: BLE001
        print(f"[fetch_prep_data] ERROR: {e!r}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
