"""TechDirect スカウト除外フィルタ

候補者一覧を巡回し、除外条件に該当する候補者を「営業対象外」リストに追加する。
結果はJSON形式で標準出力に出力する。

使い方:
  python3 scout_filter.py [--dry-run]

環境変数:
  TECHDIRECT_EMAIL / TECHDIRECT_PASSWORD
  FREELANCEBASE_EMAIL / FREELANCEBASE_PASSWORD（フリーランスベース照合時）
  SLACK_WEBHOOK_NOTIFICATION_URL（Slack通知用）
"""

import argparse
import json
import os
import re
import sys
import urllib.request
from datetime import date

from playwright.sync_api import sync_playwright, TimeoutError as PwTimeout

sys.path.insert(0, os.path.expanduser("~/.claude/snippets"))
import playwright_techdirect as td
import playwright_freelancebase as fb

# --- 定数 ---
CANDIDATES_URLS = [
    "https://techdirect.jp/orgs/39336/portal/job-seekers-tabular?savedSearchId=1221&sort=id_desc",
    "https://techdirect.jp/orgs/39336/portal/job-seekers-tabular?savedSearchId=4505",
]
AGE_THRESHOLD = 57
CURRENT_YEAR = date.today().year

# フリーランスベース NG ステータス
NG_STATUSES = {"営業不可", "取引停止"}


def fetch_candidates(page) -> list[dict]:
    """TechDirect候補者一覧（複数URL）からリンクを収集する"""
    candidates = []
    seen = set()

    for list_url in CANDIDATES_URLS:
        page.goto(list_url, wait_until="networkidle")
        page.wait_for_timeout(3000)

        while True:
            table = page.query_selector("table")
            if not table:
                break

            links = table.query_selector_all("a[href*='/users/']")
            for link in links:
                href = link.get_attribute("href") or ""
                if not href or href in seen:
                    continue
                text = link.inner_text().strip()
                if text:  # テキスト付きリンク（ニックネーム）のみ取得
                    seen.add(href)
                    url = href if href.startswith("http") else f"https://techdirect.jp{href}"
                    candidates.append({"url": url, "nickname": text})

            # ページネーション
            next_btn = page.query_selector("[aria-label='Next']:not([disabled])")
            if next_btn:
                next_btn.click()
                page.wait_for_load_state("networkidle")
                page.wait_for_timeout(2000)
            else:
                break

    return candidates


def get_candidate_detail(context, url: str) -> dict:
    """候補者詳細画面（新しいタブ）から誕生年・氏名・都道府県を取得"""
    detail = {"url": url, "birth_year": None, "name": None, "prefecture": None}

    detail_page = context.new_page()
    try:
        detail_page.goto(url, wait_until="networkidle")
        detail_page.wait_for_timeout(2000)

        body = detail_page.inner_text("body")
        lines = [l.strip() for l in body.split("\n") if l.strip()]

        for i, line in enumerate(lines):
            # 誕生年: "誕生年" の次の行に "1967年 (58〜59歳)" がある
            if line == "誕生年" and i + 1 < len(lines):
                match = re.search(r"(\d{4})年", lines[i + 1])
                if match:
                    detail["birth_year"] = int(match.group(1))

            # 氏名: "氏名" の次の行に名前 or "非公開"
            if line == "氏名" and i + 1 < len(lines):
                name = lines[i + 1].strip()
                if name and name != "非公開":
                    detail["name"] = name

            # 都道府県: "都道府県" の次の行に値がある
            if line == "都道府県" and i + 1 < len(lines):
                detail["prefecture"] = lines[i + 1].strip()

        return detail
    finally:
        detail_page.close()


def check_age(birth_year: int) -> bool:
    """57歳以上ならTrueを返す"""
    return (CURRENT_YEAR - birth_year) >= AGE_THRESHOLD


def check_freelancebase(fb_page, name: str) -> dict:
    """フリーランスベースで同姓同名検索し、一覧テーブルから営業ステータスを確認"""
    result = {"found": False, "status": None}

    fb_page.goto("https://freelancebase.jp/enterprise/candidates#view-1", wait_until="networkidle")
    fb_page.wait_for_timeout(2000)

    # クイック検索に氏名入力
    search_input = fb_page.query_selector("input[placeholder='クイック検索']")
    if not search_input:
        return result

    search_input.fill(name)
    search_input.press("Enter")
    fb_page.wait_for_load_state("networkidle")
    fb_page.wait_for_timeout(2000)

    # 検索結果テーブルの行を確認（ヘッダー行を除く）
    rows = fb_page.query_selector_all("table tr")
    if len(rows) < 2:
        return result

    # テーブル行のテキストに営業ステータスが含まれている
    for row in rows[1:]:  # ヘッダー行スキップ
        row_text = row.inner_text()
        result["found"] = True
        for status in NG_STATUSES:
            if status in row_text:
                result["status"] = status
                return result

    return result


def add_to_exclusion_list(context, candidate_url: str) -> bool:
    """TechDirectで「営業対象外」リストに追加"""
    detail_page = context.new_page()
    try:
        detail_page.goto(candidate_url, wait_until="networkidle")
        detail_page.wait_for_timeout(2000)

        # 「リスト編集」ボタンをクリック
        list_btn = detail_page.get_by_role("button", name="リスト編集")
        list_btn.click()
        detail_page.wait_for_timeout(1000)

        # ドロップダウンから「営業対象外」を選択
        # exact=True 必須: 部分一致だと「Base登録済/営業対象外」と衝突してstrict mode violationになる
        exclusion_item = detail_page.get_by_text("営業対象外", exact=True)
        exclusion_item.click()
        detail_page.wait_for_timeout(1000)
        return True
    except (PwTimeout, Exception) as e:
        print(f"[WARN] リスト追加失敗: {e}", file=sys.stderr)
        return False
    finally:
        detail_page.close()


def format_results(candidates_processed: list[dict]) -> dict:
    """結果をJSON形式に整形"""
    excluded = [c for c in candidates_processed if c.get("excluded")]
    errors = [c for c in candidates_processed if c.get("error")]
    total = len(candidates_processed)

    return {
        "summary": {
            "total_candidates": total,
            "excluded_count": len(excluded),
            "scout_target_count": total - len(excluded) - len(errors),
            "errors": len(errors),
        },
        "excluded": [
            {
                "name": c.get("name") or c.get("nickname", "不明"),
                "url": c["url"],
                "reason": c["reason"],
                "action": c.get("action", ""),
            }
            for c in excluded
        ],
        "errors": [
            {"url": c["url"], "error": c["error"]}
            for c in errors
        ],
    }


def notify_slack(output: dict):
    """Webhook経由でSlack通知を送信"""
    webhook_url = os.environ.get("SLACK_WEBHOOK_NOTIFICATION_URL")
    if not webhook_url:
        print("[WARN] SLACK_WEBHOOK_NOTIFICATION_URL が未設定。通知スキップ", file=sys.stderr)
        return

    summary = output["summary"]
    lines = [f"*【TechDirectスカウト】除外フィルタ完了*\n"]

    if summary["excluded_count"] > 0:
        lines.append(f"除外対象: {summary['excluded_count']}名")
        for c in output["excluded"]:
            lines.append(f"  - {c['name']} / {c['reason']} / <{c['url']}|詳細>")
    else:
        lines.append("除外対象: 0名")

    lines.append(f"\n確認済み候補者: {summary['scout_target_count']}名（スカウト対象）")

    if summary["errors"] > 0:
        lines.append(f"エラー: {summary['errors']}件")

    text = "\n".join(lines)
    payload = json.dumps({"text": text}).encode("utf-8")

    req = urllib.request.Request(
        webhook_url,
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    try:
        urllib.request.urlopen(req)
        print("[INFO] Slack通知送信完了", file=sys.stderr)
    except Exception as e:
        print(f"[WARN] Slack通知失敗: {e}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description="TechDirectスカウト除外フィルタ")
    parser.add_argument("--dry-run", action="store_true", help="リスト追加を行わず判定結果のみ出力")
    args = parser.parse_args()

    results = []

    with sync_playwright() as pw:
        td_browser, td_context, td_page = td.login(pw)
        fb_browser = fb_page = None

        try:
            # 候補者一覧取得
            print("[INFO] 候補者一覧を取得中...", file=sys.stderr)
            candidates = fetch_candidates(td_page)
            print(f"[INFO] {len(candidates)}名の候補者を検出", file=sys.stderr)

            for i, candidate in enumerate(candidates):
                url = candidate["url"]
                nickname = candidate.get("nickname", "")
                print(f"[INFO] ({i+1}/{len(candidates)}) {nickname} を処理中...", file=sys.stderr)

                record = {"url": url, "nickname": nickname, "excluded": False}

                try:
                    detail = get_candidate_detail(td_context, url)
                    record["name"] = detail.get("name")
                    record["birth_year"] = detail.get("birth_year")

                    # 年齢チェック
                    if detail["birth_year"] and check_age(detail["birth_year"]):
                        age = CURRENT_YEAR - detail["birth_year"]
                        record["excluded"] = True
                        record["reason"] = f"年齢超過（{detail['birth_year']}年生まれ / {age}歳）"

                        if not args.dry_run:
                            ok = add_to_exclusion_list(td_context, url)
                            record["action"] = "営業対象外リストに追加済み" if ok else "リスト追加失敗"
                        else:
                            record["action"] = "dry-run: スキップ"

                        results.append(record)
                        continue

                    # 都道府県チェック（海外は除外）
                    if detail.get("prefecture") == "海外":
                        record["excluded"] = True
                        record["reason"] = "都道府県が海外"

                        if not args.dry_run:
                            ok = add_to_exclusion_list(td_context, url)
                            record["action"] = "営業対象外リストに追加済み" if ok else "リスト追加失敗"
                        else:
                            record["action"] = "dry-run: スキップ"

                        results.append(record)
                        continue

                    # フリーランスベース照合（氏名公開時のみ）
                    if detail["name"]:
                        if fb_page is None:
                            print("[INFO] フリーランスベースに接続中...", file=sys.stderr)
                            fb_browser, _, fb_page = fb.login(pw)

                        fb_result = check_freelancebase(fb_page, detail["name"])
                        if fb_result["found"] and fb_result["status"] in NG_STATUSES:
                            record["excluded"] = True
                            record["reason"] = f"CRM NG（{fb_result['status']}）"

                            if not args.dry_run:
                                ok = add_to_exclusion_list(td_context, url)
                                record["action"] = "営業対象外リストに追加済み" if ok else "リスト追加失敗"
                            else:
                                record["action"] = "dry-run: スキップ"

                except PwTimeout as e:
                    record["error"] = f"タイムアウト: {e}"
                except Exception as e:
                    record["error"] = str(e)

                results.append(record)

        finally:
            td_browser.close()
            if fb_browser:
                fb_browser.close()
            elif fb_page:
                fb_page.close()

    output = format_results(results)
    print(json.dumps(output, ensure_ascii=False, indent=2))

    # Slack通知
    notify_slack(output)


if __name__ == "__main__":
    main()
