#!/usr/bin/env python3
"""クラウドワークス スカウト用案件管理シートから毎日3件の案件をピックする."""

import json
import os
import sys
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path

import jpholiday
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

# --- 設定 ---
SPREADSHEET_ID = "1_J2UsFr8JeUsDCxforI8Fkaf7CgfY9gsVGZuLF6VgFM"
SHEET_NAME = "スカウト用案件管理"
TOKEN_PATH = Path(
    os.environ.get("GDOCS_TOKEN_PATH")
    or Path.home() / ".config" / "claude-gdocs-token.json"
)
PICK_COUNT = 3
WEEKLY_CAP = 12  # 週あたりの最大ピック件数（金曜起点〜木曜終点）
DATA_START_ROW = 3  # 1行目=カテゴリ, 2行目=ヘッダー, 3行目からデータ

# Slack通知設定
SLACK_CHANNEL_ID = "C08SMK9UMFV"
SLACK_MENTION_USER_ID = "U09J9FJHKJ4"
SLACK_THREAD_TS = "1760520785.812989"

# 背景色の判定閾値（RGB 0-1）
COLOR_BLUE = (0.81, 0.89, 0.95)
COLOR_RED = (0.92, 0.82, 0.86)
COLOR_TOLERANCE = 0.05

# 優先スキルキーワード
PRIORITY_SKILLS = [
    "Python", "TypeScript", "Go", "Golang",
    "AWS", "Ruby", "Kotlin", "Swift", "iOS",
    "AI", "機械学習",
]


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


def classify_color(bg):
    """背景色を分類する. 返り値: 0=青(最優先), 1=赤, 2=白."""
    r = bg.get("red", 0)
    g = bg.get("green", 0)
    b = bg.get("blue", 0)

    def near(actual, expected):
        return all(
            abs(a - e) < COLOR_TOLERANCE
            for a, e in zip(actual, expected)
        )

    if near((r, g, b), COLOR_BLUE):
        return 0  # 青
    if near((r, g, b), COLOR_RED):
        return 1  # 赤
    return 2  # 白/その他


def has_priority_skill(e_val, f_val):
    """E列/F列に優先スキルキーワードが含まれるか判定する."""
    text = f"{e_val} {f_val}".upper()
    for skill in PRIORITY_SKILLS:
        if skill.upper() in text:
            return True
    return False


def current_week_window(today):
    """金曜起点〜木曜終点の週ウィンドウ (start, end) を返す."""
    # weekday(): Mon=0..Sun=6, Fri=4
    days_since_friday = (today.weekday() - 4) % 7
    start = today - timedelta(days=days_since_friday)  # 直近の金曜
    end = start + timedelta(days=6)                    # 翌週木曜
    return start, end


def count_picked_today(service, today):
    """B列の日付を見て、本日ピック済みの件数を返す."""
    today_str = today.strftime("%Y/%m/%d")
    result = service.spreadsheets().values().get(
        spreadsheetId=SPREADSHEET_ID,
        range=f"{SHEET_NAME}!B{DATA_START_ROW}:B",
    ).execute()
    rows = result.get("values", [])
    return sum(1 for row in rows if row and row[0] == today_str)


def count_picked_this_week(service, today):
    """B列の日付を見て、当週(金〜木)にピック済みの件数を返す."""
    start, end = current_week_window(today)
    result = service.spreadsheets().values().get(
        spreadsheetId=SPREADSHEET_ID,
        range=f"{SHEET_NAME}!B{DATA_START_ROW}:B",
    ).execute()
    rows = result.get("values", [])
    count = 0
    for row in rows:
        if not row or not row[0]:
            continue
        try:
            picked = datetime.strptime(row[0], "%Y/%m/%d").date()
        except ValueError:
            continue
        if start <= picked <= end:
            count += 1
    return count


def fetch_candidates(service):
    """未処理の候補行を取得する."""
    # まずA列でデータ範囲を特定
    values_result = service.spreadsheets().values().get(
        spreadsheetId=SPREADSHEET_ID,
        range=f"{SHEET_NAME}!A:A",
    ).execute()
    total_rows = len(values_result.get("values", []))

    if total_rows <= DATA_START_ROW:
        return []

    # フォーマット付きでデータ取得
    data_range = f"{SHEET_NAME}!A{DATA_START_ROW}:F{total_rows}"
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
        if len(cells) < 4:
            continue

        a_val = cells[0].get("formattedValue", "") if len(cells) > 0 else ""
        b_val = cells[1].get("formattedValue", "") if len(cells) > 1 else ""
        c_val = cells[2].get("formattedValue", "") if len(cells) > 2 else ""
        d_val = cells[3].get("formattedValue", "") if len(cells) > 3 else ""
        e_val = cells[4].get("formattedValue", "") if len(cells) > 4 else ""
        f_val = cells[5].get("formattedValue", "") if len(cells) > 5 else ""

        # 未処理判定: B空, C=FALSE, D空, A/Eあり
        if not a_val or not e_val:
            continue
        if b_val or c_val not in ("", "FALSE") or d_val:
            continue

        a_bg = cells[0].get("effectiveFormat", {}).get("backgroundColor", {})
        color_rank = classify_color(a_bg)
        skill_priority = 0 if has_priority_skill(e_val, f_val) else 1

        candidates.append({
            "sheet_row": row_idx,
            "case_no": a_val,
            "color_rank": color_rank,
            "skill_priority": skill_priority,
            "main_skill": e_val,
            "sub_skill": f_val,
        })

    return candidates


def select_cases(candidates, count=PICK_COUNT):
    """優先度に基づいて案件を選択する."""
    # ソート: 色優先(青→赤→白) → スキル優先 → 行番号降順(新しい方優先)
    candidates.sort(key=lambda c: (
        c["color_rank"],
        c["skill_priority"],
        -c["sheet_row"],
    ))
    return candidates[:count]


def write_results(service, selected):
    """選択した案件のB/C/D列に記入する."""
    today = datetime.now().strftime("%Y/%m/%d")

    requests = []
    sheet_id = None

    # シートIDを取得
    meta = service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
    for sheet in meta["sheets"]:
        if sheet["properties"]["title"] == SHEET_NAME:
            sheet_id = sheet["properties"]["sheetId"]
            break

    for case in selected:
        row = case["sheet_row"] - 1  # 0-indexed

        # B列: 日付
        requests.append({
            "updateCells": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": row,
                    "endRowIndex": row + 1,
                    "startColumnIndex": 1,  # B
                    "endColumnIndex": 2,
                },
                "rows": [{"values": [{"userEnteredValue": {"stringValue": today}}]}],
                "fields": "userEnteredValue",
            }
        })

        # C列: TRUE (チェックボックス)
        requests.append({
            "updateCells": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": row,
                    "endRowIndex": row + 1,
                    "startColumnIndex": 2,  # C
                    "endColumnIndex": 3,
                },
                "rows": [{"values": [{"userEnteredValue": {"boolValue": True}}]}],
                "fields": "userEnteredValue",
            }
        })

        # D列: open
        requests.append({
            "updateCells": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": row,
                    "endRowIndex": row + 1,
                    "startColumnIndex": 3,  # D
                    "endColumnIndex": 4,
                },
                "rows": [{"values": [{"userEnteredValue": {"stringValue": "open"}}]}],
                "fields": "userEnteredValue",
            }
        })

    service.spreadsheets().batchUpdate(
        spreadsheetId=SPREADSHEET_ID,
        body={"requests": requests},
    ).execute()


def notify_slack(selected):
    """Slack Web API (chat.postMessage) でスレッドに案件NOを通知する."""
    bot_token = os.environ.get("SLACK_BOT_TOKEN")
    if not bot_token:
        print("SLACK_BOT_TOKEN が未設定のため Slack通知をスキップします。")
        return

    lines = [f"<@{SLACK_MENTION_USER_ID}>", "お願いします！"]
    for case in selected:
        lines.append(f"- {case['case_no']}")
    text = "\n".join(lines)

    payload = {
        "channel": SLACK_CHANNEL_ID,
        "thread_ts": SLACK_THREAD_TS,
        "text": text,
    }
    req = urllib.request.Request(
        "https://slack.com/api/chat.postMessage",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "Authorization": f"Bearer {bot_token}",
        },
    )
    with urllib.request.urlopen(req) as resp:
        body = json.loads(resp.read().decode("utf-8"))
        if not body.get("ok"):
            raise RuntimeError(f"Slack通知に失敗: {body}")
    print("Slack通知を送信しました。")


def is_skip_day(today):
    """土日または日本の祝日なら True を返す."""
    if today.weekday() >= 5:  # Sat=5, Sun=6
        return True, "土日"
    if jpholiday.is_holiday(today):
        name = jpholiday.is_holiday_name(today)
        return True, f"祝日({name})"
    return False, ""


def main():
    dry_run = "--dry-run" in sys.argv
    notify = "--notify-slack" in sys.argv

    today = datetime.now().date()
    skip, reason = is_skip_day(today)
    if skip:
        print(f"本日は{reason}のためスキップします。")
        return

    creds = get_credentials()
    service = build("sheets", "v4", credentials=creds)

    candidates = fetch_candidates(service)
    if not candidates:
        print("未処理の候補がありません。")
        return

    # 日次冪等チェック: 本日すでにピック済みなら no-op
    today_count = count_picked_today(service, today)
    if today_count > 0:
        print(f"本日すでに{today_count}件ピック済みのためスキップします。")
        return

    already = count_picked_this_week(service, today)
    remaining = WEEKLY_CAP - already
    pick_count = min(PICK_COUNT, max(0, remaining))
    print(
        f"今週ピック済み: {already}件 / 上限{WEEKLY_CAP}件 "
        f"→ 今回ピック上限: {pick_count}件"
    )
    if pick_count == 0:
        print("週上限に到達したため今回はスキップします。")
        return

    selected = select_cases(candidates, count=pick_count)
    if not selected:
        print("選択可能な案件がありません。")
        return

    color_labels = {0: "青", 1: "赤", 2: "白"}
    print(f"\n選択した案件 ({len(selected)}件):")
    for case in selected:
        color = color_labels.get(case["color_rank"], "?")
        skill = case["main_skill"]
        sub = f" / {case['sub_skill']}" if case["sub_skill"] else ""
        print(f"  案件NO: {case['case_no']}  [{color}]  {skill}{sub}")

    if dry_run:
        print("\n(ドライラン: 書き込みはスキップしました)")
    else:
        write_results(service, selected)
        print("\nスプレッドシートに記入しました。")

    # 案件NOのみ出力
    print("\n--- 選択した案件NO ---")
    for case in selected:
        print(case["case_no"])

    if notify and not dry_run:
        notify_slack(selected)


if __name__ == "__main__":
    main()
