#!/usr/bin/env python3
"""TechDirect 案件管理シートから先週分の案件を最大10件ピックする."""

import json
import sys
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

# --- 設定 ---
SPREADSHEET_ID = "1PStuFVOUtRM_zLhKJVElG-5uM-deGT5v3Lmd0cyGdwI"
TOKEN_PATH = Path.home() / ".config" / "claude-gdocs-token.json"
PICK_COUNT = 10
DATA_START_ROW = 2  # 1行目=ヘッダー, 2行目からデータ

# 優先スキルキーワード
PRIORITY_SKILLS = [
    "Python", "TypeScript", "Go", "Golang",
    "AWS", "Ruby", "Kotlin", "Swift", "iOS",
    "AI", "機械学習",
]

# 商流の優先度（小さいほど高優先）
SUPPLY_CHAIN_PRIORITY = {
    "エンド": 0,
    "元請": 1,
    "BP": 2,
}

# 言語カテゴリ判定用キーワード
LANGUAGE_CATEGORIES = {
    "Python": ["Python", "Django", "Flask", "FastAPI"],
    "TypeScript": ["TypeScript", "React", "Next.js", "Vue", "Angular", "Node.js", "JavaScript"],
    "Go": ["Go", "Golang"],
    "Ruby": ["Ruby", "Rails"],
    "Java": ["Java", "Spring", "Kotlin"],
    "PHP": ["PHP", "Laravel"],
    "C#": ["C#", ".NET"],
    "Swift": ["Swift", "iOS"],
    "AWS": ["AWS", "クラウド"],
    "AI": ["AI", "機械学習", "ML", "LLM"],
    "インフラ": ["インフラ", "SRE", "DevOps", "Terraform", "Kubernetes", "Docker"],
}

# 同一カテゴリの上限
CATEGORY_LIMIT = 4


def get_credentials():
    """Google API認証情報を取得する."""
    with open(TOKEN_PATH) as f:
        token_data = json.load(f)
    return Credentials(
        token=token_data["token"],
        refresh_token=token_data["refresh_token"],
        token_uri=token_data["token_uri"],
        client_id=token_data["client_id"],
        client_secret=token_data["client_secret"],
        scopes=token_data["scopes"],
    )


def get_last_week_range():
    """先週の日曜〜土曜の日付範囲を返す."""
    today = datetime.now().date()
    # 今週の日曜を求める（weekday: 月=0, 日=6）
    days_since_sunday = (today.weekday() + 1) % 7
    this_sunday = today - timedelta(days=days_since_sunday)
    # 先週の日曜〜土曜
    last_sunday = this_sunday - timedelta(days=7)
    last_saturday = last_sunday + timedelta(days=6)
    return last_sunday, last_saturday


def parse_date(date_str):
    """日付文字列をdateオブジェクトに変換する. 年なし形式は今年として扱う."""
    current_year = datetime.now().year
    for fmt in ("%Y/%m/%d", "%Y-%m-%d", "%m/%d/%Y", "%m/%d"):
        try:
            d = datetime.strptime(date_str.strip(), fmt).date()
            # 年なし形式の場合、年が1900になるので今年に補正
            if d.year == 1900:
                d = d.replace(year=current_year)
            return d
        except ValueError:
            continue
    return None


def classify_supply_chain(e_val):
    """商流を優先度に変換する."""
    text = e_val.strip()
    return SUPPLY_CHAIN_PRIORITY.get(text, 3)  # 不明は最低優先


def has_priority_skill(title):
    """タイトルに優先スキルキーワードが含まれるか判定する."""
    text = title.upper()
    for skill in PRIORITY_SKILLS:
        if skill.upper() in text:
            return True
    return False


def detect_language_category(title):
    """タイトルから言語カテゴリを判定する. 複数該当の場合は最初にマッチしたものを返す."""
    text_upper = title.upper()
    for category, keywords in LANGUAGE_CATEGORIES.items():
        for kw in keywords:
            if kw.upper() in text_upper:
                return category
    return "その他"


def fetch_candidates(service):
    """先週作成・未処理の候補行を取得する."""
    last_sunday, last_saturday = get_last_week_range()
    print(f"対象期間: {last_sunday} 〜 {last_saturday}")

    # シートメタデータ取得
    meta = service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
    sheet = meta["sheets"][0]
    sheet_name = sheet["properties"]["title"]
    total_rows = sheet["properties"]["gridProperties"]["rowCount"]

    if total_rows <= DATA_START_ROW:
        return [], sheet_name

    # データ取得（A〜E列）
    data_range = f"{sheet_name}!A{DATA_START_ROW}:E{total_rows}"
    result = service.spreadsheets().get(
        spreadsheetId=SPREADSHEET_ID,
        ranges=[data_range],
        includeGridData=True,
    ).execute()

    candidates = []
    for row_idx, row in enumerate(
        result["sheets"][0]["data"][0].get("rowData", []),
        start=DATA_START_ROW,
    ):
        cells = row.get("values", [])
        if len(cells) < 1:
            continue

        a_val = cells[0].get("formattedValue", "") if len(cells) > 0 else ""
        b_val = cells[1].get("formattedValue", "") if len(cells) > 1 else ""
        c_val = cells[2].get("formattedValue", "") if len(cells) > 2 else ""
        d_val = cells[3].get("formattedValue", "") if len(cells) > 3 else ""
        e_val = cells[4].get("formattedValue", "") if len(cells) > 4 else ""

        # A列の日付が先週に該当するか
        date = parse_date(a_val)
        if not date or date < last_sunday or date > last_saturday:
            continue

        # D列が空（未チェック）
        if d_val and d_val.upper() != "FALSE":
            continue

        # B列（タイトル）が空なら除外
        if not b_val:
            continue

        supply_priority = classify_supply_chain(e_val)
        skill_priority = 0 if has_priority_skill(b_val) else 1
        category = detect_language_category(b_val)

        candidates.append({
            "sheet_row": row_idx,
            "date": a_val,
            "title": b_val,
            "url": c_val,
            "supply_chain": e_val,
            "supply_priority": supply_priority,
            "skill_priority": skill_priority,
            "category": category,
        })

    return candidates, sheet_name


def select_cases(candidates, count=PICK_COUNT):
    """優先度に基づいて案件を選択する（多様性制約付き）."""
    # まず基本優先度でソート: 商流 → スキル優先 → 行番号降順
    candidates.sort(key=lambda c: (
        c["supply_priority"],
        c["skill_priority"],
        -c["sheet_row"],
    ))

    selected = []
    category_count = Counter()

    for case in candidates:
        if len(selected) >= count:
            break
        cat = case["category"]
        if category_count[cat] >= CATEGORY_LIMIT:
            continue
        selected.append(case)
        category_count[cat] += 1

    # カテゴリ制限で上限に達しなかった場合、制限を超えてでも埋める
    if len(selected) < count:
        selected_rows = {c["sheet_row"] for c in selected}
        for case in candidates:
            if len(selected) >= count:
                break
            if case["sheet_row"] not in selected_rows:
                selected.append(case)

    return selected


def write_results(service, selected, sheet_name):
    """選択した案件のD列にチェックを入れる."""
    meta = service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
    sheet_id = meta["sheets"][0]["properties"]["sheetId"]

    requests = []
    for case in selected:
        row = case["sheet_row"] - 1  # 0-indexed
        requests.append({
            "updateCells": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": row,
                    "endRowIndex": row + 1,
                    "startColumnIndex": 3,  # D列
                    "endColumnIndex": 4,
                },
                "rows": [{"values": [{"userEnteredValue": {"boolValue": True}}]}],
                "fields": "userEnteredValue",
            }
        })

    service.spreadsheets().batchUpdate(
        spreadsheetId=SPREADSHEET_ID,
        body={"requests": requests},
    ).execute()


def main():
    dry_run = "--dry-run" in sys.argv

    creds = get_credentials()
    service = build("sheets", "v4", credentials=creds)

    candidates, sheet_name = fetch_candidates(service)
    if not candidates:
        print("対象の案件がありません。")
        return

    selected = select_cases(candidates)
    if not selected:
        print("選択可能な案件がありません。")
        return

    print(f"\n選択した案件 ({len(selected)}件):")
    for case in selected:
        sc = case["supply_chain"] or "不明"
        cat = case["category"]
        print(f"  [{sc}] [{cat}] {case['title']}")
        print(f"    URL: {case['url']}")

    if dry_run:
        print("\n(ドライラン: 書き込みはスキップしました)")
    else:
        write_results(service, selected, sheet_name)
        print("\nスプレッドシートにチェックを入れました。")

    # Slack通知用の案件タイトル一覧
    print("\n--- Slack通知用タイトル ---")
    for case in selected:
        print(case["title"])


if __name__ == "__main__":
    main()
