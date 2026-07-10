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
import sys
import json
import datetime as dt

from gcal_common import service, available_ranges, WEEKDAY_JP


def fmt_line(date_str, a, b):
    d = dt.date.fromisoformat(date_str)
    w = WEEKDAY_JP[d.weekday()]
    return f"・{d.month}月{d.day}日（{w}）{a.strftime('%H:%M')}～{b.strftime('%H:%M')}"


def main():
    windows = json.load(sys.stdin)
    svc = service()
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
