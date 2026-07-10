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
    body = {
        "timeMin": day_start.isoformat(),
        "timeMax": day_end.isoformat(),
        "items": [{"id": CALENDAR_ID}],
    }
    fb = svc.freebusy().query(body=body).execute()

    def parse(s):
        # freebusy は UTC の 'Z' 表記で返すことがある → JST に正規化
        return dt.datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(JST)

    key = CALENDAR_ID
    cals = fb["calendars"]
    if key not in cals:  # primary は実アドレスで返ることがある
        key = next(iter(cals))
    return [(parse(b["start"]), parse(b["end"])) for b in cals[key]["busy"]]


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
