#!/usr/bin/env python3
"""フェーズ2：面談確定 → 確定ブロック＋バッファ登録／メモ記入／面談調整ブロック削除。

入力(stdin): JSON
  {
    "client": "A社",
    "candidate": "山田太郎",
    "candidate_kana": "やまだたろう",   # 任意（メモの氏名表記に使用）
    "date": "2026-07-15",
    "start": "14:00",
    "duration_min": 60,                 # 任意（既定60）
    "tool": "Google Meet",              # 任意
    "url": "",                          # 任意
    "search_from": "2026-07-01",        # 削除対象を探す期間の開始（任意・既定=今日）
    "search_to":   "2026-08-31",        # 同 終了（任意・既定=+60日）
    "apply": false                      # true で「確定登録＋調整ブロック削除」を実行
  }

安全設計:
  - apply=false（既定）は下見。確定ブロック/バッファは作らず、削除対象の面談調整
    ブロックを列挙するだけ（破壊的操作は確認してから、のルールに準拠）。
  - apply=true で初めて 登録＋削除 を実行する。
"""
import sys
import json
import datetime as dt

from gcal_common import (
    service, dtime, fmt_date_jp,
    CALENDAR_ID, TZID, JST, WEEKDAY_JP,
    MEETING_MIN, BUFFER_MIN,
    ADJUST_PREFIX, CONFIRM_PREFIX, COLOR_CONFIRM, COLOR_BUFFER,
)


def build_memo(client, candidate, candidate_kana, date_str, start_t, tool, url):
    d = dt.date.fromisoformat(date_str)
    ymd = f"{d.month}月{d.day}日（{WEEKDAY_JP[d.weekday()]}）"
    hm = start_t.strftime("%H：%M")
    name = f"{candidate}（{candidate_kana}）" if candidate_kana else candidate
    return f"""【面談 / WEB】{name} 様
--------------------------------------
<面談詳細>
日時　：{ymd} {hm} 開始（30 ~ 60分想定）
ツール：{tool}
URL　：{url}
担当　：mijica 畑田（080-7159-0335）
※開始時刻を過ぎても面談が開始されない場合はご連絡ください。

<注意事項>
・開始3分前までにアクセスをお願いします。
　※ツール操作や更新漏れによる遅延が増えております。
・氏名はフルネームで表示してください。
・明るい場所でのご参加を推奨し、背景は「ぼかし」または「バーチャル背景」をご利用ください。
・服装はビジネスカジュアルを推奨します。
・スキルシートを画面共有しながらご説明いただけるようご準備ください。
・所属会社名の開示はご遠慮ください。
・貴社営業担当者の同席は不可となります。

<アジェンダ>
1）企業様より、案件概要および募集ポジションのご説明
2）{candidate}様より、自己紹介ならびにプロジェクト内容に関連したご経歴のご説明
3）質疑応答
--------------------------------------"""


def find_adjust_blocks(svc, client, candidate, t_from, t_to):
    """該当クライアント×候補者の「面談調整」ブロックを列挙する。"""
    exact = f"{ADJUST_PREFIX}{client} × {candidate}"
    res = svc.events().list(
        calendarId=CALENDAR_ID,
        timeMin=t_from.isoformat(),
        timeMax=t_to.isoformat(),
        q=ADJUST_PREFIX,
        singleEvents=True,
        orderBy="startTime",
        maxResults=250,
    ).execute()
    hits = []
    for ev in res.get("items", []):
        if ev.get("summary", "") == exact:
            hits.append(ev)
    return exact, hits


def _ev_when(ev):
    s = ev["start"].get("dateTime", ev["start"].get("date"))
    e = ev["end"].get("dateTime", ev["end"].get("date"))
    sd = dt.datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(JST)
    ed = dt.datetime.fromisoformat(e.replace("Z", "+00:00")).astimezone(JST)
    return f"{fmt_date_jp(sd.date().isoformat())}{sd.strftime('%H:%M')}～{ed.strftime('%H:%M')}"


def create_event(svc, summary, start_dt, end_dt, color, desc=None):
    body = {
        "summary": summary,
        "start": {"dateTime": start_dt.isoformat(), "timeZone": TZID},
        "end": {"dateTime": end_dt.isoformat(), "timeZone": TZID},
        "colorId": color,
    }
    if desc is not None:
        body["description"] = desc
    return svc.events().insert(calendarId=CALENDAR_ID, body=body).execute()


def main():
    data = json.load(sys.stdin)
    client = data["client"]
    candidate = data["candidate"]
    candidate_kana = data.get("candidate_kana", "")
    date_str = data["date"]
    start_t = dt.time.fromisoformat(data["start"])
    dur = int(data.get("duration_min", MEETING_MIN))
    tool = data.get("tool", "")
    url = data.get("url", "")
    apply = bool(data.get("apply", False))

    today = dt.datetime.now(JST)
    t_from = (dt.datetime.fromisoformat(data["search_from"] + "T00:00:00" + "+09:00")
              if data.get("search_from") else today - dt.timedelta(days=1))
    t_to = (dt.datetime.fromisoformat(data["search_to"] + "T23:59:59" + "+09:00")
            if data.get("search_to") else today + dt.timedelta(days=60))

    svc = service()

    start_dt = dtime(date_str, start_t)
    end_dt = start_dt + dt.timedelta(minutes=dur)
    buf_before_s = start_dt - dt.timedelta(minutes=BUFFER_MIN)
    buf_after_e = end_dt + dt.timedelta(minutes=BUFFER_MIN)

    confirm_title = f"{CONFIRM_PREFIX}{client} × {candidate}"
    memo = build_memo(client, candidate, candidate_kana, date_str, start_t, tool, url)

    # 削除対象の面談調整ブロックを検索
    exact, hits = find_adjust_blocks(svc, client, candidate, t_from, t_to)

    print(f"■ 面談確定処理：{client} × {candidate}")
    print(f"  確定枠　：{fmt_date_jp(date_str)}{start_t.strftime('%H:%M')}"
          f"～{end_dt.strftime('%H:%M')}（{dur}分）")
    print(f"  バッファ：前 {buf_before_s.strftime('%H:%M')}～{start_dt.strftime('%H:%M')}"
          f" / 後 {end_dt.strftime('%H:%M')}～{buf_after_e.strftime('%H:%M')}")
    print(f"  確定タイトル：{confirm_title}")
    print("--------------------------------------")
    print(f"■ 削除対象の「面談調整」ブロック（{exact}）: {len(hits)}件")
    for ev in hits:
        print(f"  - {_ev_when(ev)}  [id={ev['id']}]")
    print("--------------------------------------")

    if not apply:
        print("※ これは下見です。まだカレンダーは変更していません。")
        print("※ 上記の確定登録・バッファ登録・削除を実行する場合は apply=true で再実行してください。")
    else:
        conf = create_event(svc, confirm_title, start_dt, end_dt, COLOR_CONFIRM, desc=memo)
        create_event(svc, f"バッファ（{client} × {candidate}）",
                     buf_before_s, start_dt, COLOR_BUFFER)
        create_event(svc, f"バッファ（{client} × {candidate}）",
                     end_dt, buf_after_e, COLOR_BUFFER)
        print(f"✓ 確定ブロック作成 id={conf['id']}（メモ欄フォーマット記入済み）")
        print("✓ 前後30分バッファ作成")
        for ev in hits:
            svc.events().delete(calendarId=CALENDAR_ID, eventId=ev["id"]).execute()
        print(f"✓ 面談調整ブロック {len(hits)}件 削除")

    # 候補者へ送る確定フォーマット
    print()
    print("▼候補者への面談確定フォーマット（このまま共有できます）")
    print(memo)


if __name__ == "__main__":
    main()
