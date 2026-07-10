#!/usr/bin/env python3
"""フェーズ1：対応可能枠を「面談調整」ブロックとしてカレンダーに登録する。

入力(stdin): JSON
  {
    "client": "A社",
    "candidate": "山田太郎",
    "windows": [{"date":"2026-07-15","start":"10:00","end":"20:00"}, ...],
    "apply": false          # true で実際に登録。省略/false は下見（作成せず一覧のみ）
  }

処理:
  - available_ranges で候補ウィンドウ内の空き連続帯を抽出
  - 各帯に予定を作成: タイトル「面談調整｜{client} × {candidate}」（色=バナナ）
  - apply=false のときは作成せず、作成予定の一覧だけを表示（下見）

出力: 作成した（または作成予定の）予定の一覧と、整形返信フォーマット（▼面談可能日時）
"""
import sys
import json
import datetime as dt

from gcal_common import (
    service, available_ranges, dtime, fmt_date_jp,
    CALENDAR_ID, TZID, ADJUST_PREFIX, COLOR_ADJUST,
)


def build_events(client, candidate, windows):
    """(date_str, start_dt, end_dt) の作成候補リストを返す。"""
    svc = service()
    title = f"{ADJUST_PREFIX}{client} × {candidate}"
    events = []
    for w in windows:
        st = dt.time.fromisoformat(w.get("start", "10:00"))
        et = dt.time.fromisoformat(w.get("end", "20:00"))
        for a, b in available_ranges(svc, w["date"], st, et):
            events.append((w["date"], a, b, title))
    return svc, title, events


def create_event(svc, date_str, a, b, title):
    body = {
        "summary": title,
        "start": {"dateTime": a.isoformat(), "timeZone": TZID},
        "end": {"dateTime": b.isoformat(), "timeZone": TZID},
        "colorId": COLOR_ADJUST,
        "transparency": "transparent",  # 仮押さえ（他予定をブロックしない）
        "description": "面談日程調整スキルが自動作成した仮押さえブロックです。",
    }
    return svc.events().insert(calendarId=CALENDAR_ID, body=body).execute()


def main():
    data = json.load(sys.stdin)
    client = data["client"]
    candidate = data["candidate"]
    windows = data["windows"]
    apply = bool(data.get("apply", False))

    svc, title, events = build_events(client, candidate, windows)

    if not events:
        print("対応可能な枠がありませんでした。登録するものはありません。")
        return

    mode = "登録しました" if apply else "登録予定（下見・未登録）"
    print(f"■ 面談調整ブロック {mode}：{title}")
    print("--------------------------------------")
    for date_str, a, b, _t in events:
        line = f"・{fmt_date_jp(date_str)}{a.strftime('%H:%M')}～{b.strftime('%H:%M')}"
        if apply:
            ev = create_event(svc, date_str, a, b, title)
            line += f"  [作成OK id={ev['id']}]"
        print(line)
    print("--------------------------------------")

    # 整形返信フォーマット（そのままクライアントへ）
    print()
    print("▼整形返信（このまま返信に使えます）")
    print("--------------------------------------")
    print("▼面談可能日時")
    for date_str, a, b, _t in events:
        print(f"・{fmt_date_jp(date_str)}{a.strftime('%H:%M')}～{b.strftime('%H:%M')}")
    print("--------------------------------------")

    if not apply:
        print()
        print("※ まだ登録していません。この内容で登録する場合は apply=true で再実行してください。")


if __name__ == "__main__":
    main()
