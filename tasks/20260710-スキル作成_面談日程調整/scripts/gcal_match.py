#!/usr/bin/env python3
"""候補日程 → 対応可能日時の抽出・整形（読み取りのみ／カレンダーには書き込まない）。

入力: 候補ウィンドウの JSON を標準入力から受け取る。
  [{"date":"2026-07-15","start":"10:00","end":"20:00"}, ...]
  - "終日" は呼び出し側で start=10:00 end=20:00 に展開して渡す
  - 終了時刻不明は end を省略（営業終了 20:00 まで見る）

処理:
  - 平日 10:00〜20:00（営業時間）にクリップ、土日は除外
  - Google カレンダー freebusy と突合し、空いている連続帯を抽出
  - 所要時間（既定 60 分）以上入る帯だけ残す
  - 「候補の幅をそのまま返す」= 空き連続帯を ○:○○〜○:○○ で出力

出力: 指定フォーマットのテキスト（▼面談可能日時 …）
"""
import os
import sys
import json
import datetime as dt

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

CONFIG_DIR = os.path.expanduser("~/.config/interview-scheduler")
TOKEN = os.path.join(CONFIG_DIR, "token.json")
SCOPES = ["https://www.googleapis.com/auth/calendar"]

TZ = "+09:00"  # Asia/Tokyo
JST = dt.timezone(dt.timedelta(hours=9))
BIZ_START = dt.time(10, 0)
BIZ_END = dt.time(20, 0)
MEETING_MIN = 60  # 標準所要時間（分）
WEEKDAY_JP = ["月", "火", "水", "木", "金", "土", "日"]


def _svc():
    creds = Credentials.from_authorized_user_file(TOKEN, SCOPES)
    return build("calendar", "v3", credentials=creds)


def _dtime(date_str, t):
    return dt.datetime.fromisoformat(f"{date_str}T{t.strftime('%H:%M')}:00{TZ}")


def _busy_intervals(svc, day_start, day_end):
    body = {
        "timeMin": day_start.isoformat(),
        "timeMax": day_end.isoformat(),
        "items": [{"id": "primary"}],
    }
    fb = svc.freebusy().query(body=body).execute()

    def parse(s):
        # freebusy は UTC の 'Z' 表記で返すことがある → JST に正規化
        return dt.datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(JST)

    out = []
    for b in fb["calendars"]["primary"]["busy"]:
        out.append((parse(b["start"]), parse(b["end"])))
    return out


def available_ranges(svc, date_str, start_t, end_t):
    """1 日の候補ウィンドウ内の空き連続帯を返す（[(start_dt,end_dt), ...]）。"""
    d = dt.date.fromisoformat(date_str)
    if d.weekday() >= 5:  # 土日は対象外
        return []
    # 営業時間にクリップ
    s = max(start_t, BIZ_START)
    e = min(end_t, BIZ_END)
    if s >= e:
        return []
    win_start = _dtime(date_str, s)
    win_end = _dtime(date_str, e)
    busy = _busy_intervals(svc, win_start, win_end)
    busy.sort()
    # 空き = ウィンドウ - busy
    free = []
    cur = win_start
    for bs, be in busy:
        bs = max(bs, win_start)
        be = min(be, win_end)
        if bs > cur:
            free.append((cur, bs))
        cur = max(cur, be)
    if cur < win_end:
        free.append((cur, win_end))
    # 所要時間以上入る帯だけ
    dur = dt.timedelta(minutes=MEETING_MIN)
    return [(a, b) for a, b in free if b - a >= dur]


def fmt_line(date_str, a, b):
    d = dt.date.fromisoformat(date_str)
    w = WEEKDAY_JP[d.weekday()]
    return f"・{d.month}月{d.day}日（{w}）{a.strftime('%H:%M')}～{b.strftime('%H:%M')}"


def main():
    windows = json.load(sys.stdin)
    svc = _svc()
    lines = []
    for w in windows:
        st = dt.time.fromisoformat(w.get("start", "10:00"))
        et = dt.time.fromisoformat(w.get("end", "20:00"))
        for a, b in available_ranges(svc, w["date"], st, et):
            lines.append(fmt_line(w["date"], a, b))
    print("--------------------------------------")
    print("▼面談可能日時")
    if lines:
        for ln in lines:
            print(ln)
    else:
        print("（対応可能な枠がありませんでした）")
    print("--------------------------------------")


if __name__ == "__main__":
    main()
