#!/usr/bin/env python3
"""面談日程調整スクリプト群の共通処理。

- Google カレンダー認証（読み書き・削除可のスコープ）
- 営業時間・所要時間などの定数
- 候補ウィンドウ内の「空き連続帯」抽出（読み取り）
- 日時整形ヘルパー

秘密情報（client_secret.json / token.json）は ~/.config/interview-scheduler/
配下＝リポジトリ外に置く。ここには絶対に書かない・コミットしない。
"""
import os
import datetime as dt

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

CONFIG_DIR = os.path.expanduser("~/.config/interview-scheduler")
TOKEN = os.path.join(CONFIG_DIR, "token.json")
SCOPES = ["https://www.googleapis.com/auth/calendar"]

CALENDAR_ID = "primary"      # 畑田 真輝 / Asia/Tokyo
TZID = "Asia/Tokyo"
TZ = "+09:00"
JST = dt.timezone(dt.timedelta(hours=9))
BIZ_START = dt.time(10, 0)
BIZ_END = dt.time(20, 0)
MEETING_MIN = 60             # 標準所要時間（分）
BUFFER_MIN = 30             # 確定枠の前後バッファ（分）
WEEKDAY_JP = ["月", "火", "水", "木", "金", "土", "日"]

# 予定タイトルのプレフィックス（削除対象の特定にも使う）
ADJUST_PREFIX = "面談調整｜"   # 面談調整｜{クライアント} × {候補者}
CONFIRM_PREFIX = "【面談 / WEB】"  # 【面談 / WEB】{クライアント} × {候補者}

# 色（Google Calendar colorId）。面談調整=バナナ(5)、確定=トマト(11)、バッファ=グラファイト(8)
COLOR_ADJUST = "5"
COLOR_CONFIRM = "11"
COLOR_BUFFER = "8"


def service():
    creds = Credentials.from_authorized_user_file(TOKEN, SCOPES)
    return build("calendar", "v3", credentials=creds)


def dtime(date_str, t):
    """date 文字列 + time → JST の aware datetime。"""
    return dt.datetime.fromisoformat(f"{date_str}T{t.strftime('%H:%M')}:00{TZ}")


def rfc3339(date_str, t):
    return dtime(date_str, t).isoformat()


def fmt_date_jp(date_str):
    d = dt.date.fromisoformat(date_str)
    return f"{d.month}月{d.day}日（{WEEKDAY_JP[d.weekday()]}）"


def _busy_intervals(svc, day_start, day_end):
    """空き計算に使う「埋まっている」区間を返す。

    freebusy ではなく events.list を使い、予定の種類で判定する：
      - キャンセル済みは無視
      - 「空き時間」表示（transparency=transparent）の予定は無視
      - **面談調整ブロック（タイトルが ADJUST_PREFIX で始まる）は無視** →
        面談調整ブロックは実時間を確保（不透明）しつつ、空き計算では数えないので
        同じ枠を複数候補者へ並行提案でき、面談調整同士は重複してよい。
      - それ以外の予定（確定面談・通常予定・バッファ・終日の予定）は busy。
    """
    def parse_dt(s):
        return dt.datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(JST)

    evs = svc.events().list(
        calendarId=CALENDAR_ID,
        timeMin=day_start.isoformat(),
        timeMax=day_end.isoformat(),
        singleEvents=True,
        orderBy="startTime",
        maxResults=250,
    ).execute().get("items", [])

    out = []
    for e in evs:
        if e.get("status") == "cancelled":
            continue
        if e.get("transparency") == "transparent":
            continue
        if e.get("summary", "").startswith(ADJUST_PREFIX):
            continue  # 面談調整ブロックは空き計算に含めない（重複OK）
        s, en = e["start"], e["end"]
        if "dateTime" in s:
            bs, be = parse_dt(s["dateTime"]), parse_dt(en["dateTime"])
        else:  # 終日予定 → その日全体を busy（end.date は排他的）
            bs = dt.datetime.fromisoformat(f"{s['date']}T00:00:00{TZ}")
            be = dt.datetime.fromisoformat(f"{en['date']}T00:00:00{TZ}")
        out.append((bs, be))
    return out


def available_ranges(svc, date_str, start_t, end_t):
    """候補ウィンドウ内の空き連続帯 [(start_dt, end_dt), ...] を返す。

    - 土日は対象外
    - 営業時間 10:00〜20:00 にクリップ
    - 既存予定（busy）と重複しない連続帯のみ
    - 所要時間 MEETING_MIN 分以上入る帯だけ残す
    """
    d = dt.date.fromisoformat(date_str)
    if d.weekday() >= 5:
        return []
    s = max(start_t, BIZ_START)
    e = min(end_t, BIZ_END)
    if s >= e:
        return []
    win_start = dtime(date_str, s)
    win_end = dtime(date_str, e)
    busy = _busy_intervals(svc, win_start, win_end)
    busy.sort()
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
    dur = dt.timedelta(minutes=MEETING_MIN)
    return [(a, b) for a, b in free if b - a >= dur]
