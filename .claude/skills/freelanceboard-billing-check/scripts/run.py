"""freelanceboard-billing-check: フリーランスボード 月次請求対象チェック

実行モード:
  /usr/bin/python3 scripts/run.py --csv /path/to/FreelanceBoard_応募者一覧_YYYYMMDD~YYYYMMDD_株式会社mijica.csv \
      --output-dir /path/to/output
    Phase 1〜5: CSV読込 → Slack突合 → FB突合（ステータス+メモ） → 判定 → レポート出力

  /usr/bin/python3 scripts/run.py --make-csv --report /path/to/result.json \
      [--overrides /path/to/overrides.json] --output-dir /path/to/output
    Phase 6: 返却CSV生成（C列=承認ステータス, D列=承認備考）
    要判断の候補者が overrides で解決されていない場合はエラー終了する。
    overrides JSON 形式: {"氏名": {"status": "承認"|"非承認", "reason": "非承認理由"}}

フリーランスHub版 (freelancehub-billing-check) との違い:
  - 入力は管理画面スクレイピングではなく、運営から送られてくるCSV
  - 管理画面でのステータス変更は無い
  - 代わりに返却CSV（承認ステータス・承認備考を記入）を生成し、ユーザーが運営に返送する
  - 年齢基準は 60歳以上（Hubは50歳）
  - FreelanceBase のメモ（コメントタブ）も取得して判定材料にする（Hub版未実装の新規機能）

判定の基本方針:
  CSVの情報だけで判断しない。Slack #inquiries と FreelanceBase メモの過去情報が
  最重要の判断材料。突合に失敗した候補者は「要判断」に分類し失敗を明記する。
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any

# 既存スニペット
sys.path.insert(0, __import__("os").path.expanduser("~/.claude/snippets"))
import playwright_freelancebase as fb  # noqa: E402  type: ignore

from playwright.sync_api import Page, sync_playwright  # noqa: E402

SKILL_DIR = Path(__file__).resolve().parent.parent
STATE_DIR = SKILL_DIR / "state"
DEBUG_DIR = STATE_DIR / "debug"

AGE_THRESHOLD = 60  # フリーランスボードの年齢基準（Hubは50）
PAST_INFLOW_DAYS = 14  # 応募日よりこの日数以上前の Slack/FBメモ があれば「過去流入」とみなす


def log(msg: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", file=sys.stderr)


# ========== Phase 1: CSV 読み込み ==========

CSV_FILENAME_PERIOD_RE = re.compile(r"(\d{8})[~〜](\d{8})")


def parse_period_from_filename(csv_path: Path) -> tuple[str, str, str]:
    """ファイル名から (start_date, end_date, month) を抽出する.

    例: FreelanceBoard_応募者一覧_20260501~20260531_株式会社mijica.csv
        → ('2026-05-01', '2026-05-31', '2026-05')
    """
    m = CSV_FILENAME_PERIOD_RE.search(csv_path.name)
    if not m:
        raise ValueError(
            f"ファイル名から期間を抽出できません: {csv_path.name}"
            "（YYYYMMDD~YYYYMMDD 形式を含む必要があります。--month で明示指定してください）"
        )
    s, e = m.group(1), m.group(2)
    start = f"{s[:4]}-{s[4:6]}-{s[6:]}"
    end = f"{e[:4]}-{e[4:6]}-{e[6:]}"
    return start, end, start[:7]


def _parse_date(s: str) -> datetime | None:
    """日付文字列を datetime に。失敗時 None."""
    if not s:
        return None
    s = s.strip()
    for fmt in (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y/%m/%d %H:%M:%S",
        "%Y/%m/%d %H:%M",
        "%Y-%m-%d",
        "%Y/%m/%d",
    ):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def _calc_age(birthday: str, at: datetime | None) -> int | None:
    """生年月日と基準日から年齢を計算する."""
    b = _parse_date(birthday)
    if not b:
        return None
    base = at or datetime.now()
    age = base.year - b.year - ((base.month, base.day) < (b.month, b.day))
    return age


def load_candidates_from_csv(csv_path: Path) -> list[dict[str, Any]]:
    """CSVから候補者プロファイルを読み込む.

    同一人物（氏名+メール一致）の複数応募は1候補者にまとめ、応募案件をリスト化する。
    """
    with csv_path.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    log(f"CSV読込: {len(rows)} 行")

    by_key: dict[tuple[str, str], dict[str, Any]] = {}
    for row in rows:
        name = (row.get("氏名") or "").strip()
        email = (row.get("メールアドレス") or "").strip()
        applied_at = (row.get("応募日時") or "").strip()
        applied_dt = _parse_date(applied_at)
        key = (name, email)

        application = {
            "applied_at": applied_at,
            "project_title": (row.get("応募案件") or "").strip(),
            "agent": (row.get("応募エージェント") or "").strip(),
            "apply_type": (row.get("応募種類") or "").strip(),
        }

        if key in by_key:
            by_key[key]["applications"].append(application)
            # 最も古い応募日時を基準にする（過去流入判定を厳しめに）
            existing_dt = _parse_date(by_key[key]["applied_at"])
            if applied_dt and (not existing_dt or applied_dt < existing_dt):
                by_key[key]["applied_at"] = applied_at
            continue

        birthday = (row.get("生年月日") or "").strip()
        cand: dict[str, Any] = {
            "name": name,
            "name_kana": (row.get("かな") or "").strip(),
            "email": email,
            "tel": (row.get("電話番号") or "").strip().lstrip("#"),
            "tel_verified": (row.get("電話番号認証") or "").strip(),
            "birthday": birthday,
            "age": _calc_age(birthday, applied_dt),
            "prefecture": (row.get("住まいの地域") or "").strip(),
            "working_status": (row.get("現在の状況") or "").strip(),
            "skillsheet_url": (row.get("経歴書・スキルシート（URL）") or "").strip(),
            "self_pr": (row.get("自己PR") or "").strip(),
            "job_types": (row.get("経験職種") or "").strip(),
            "industries": (row.get("経験業界") or "").strip(),
            "skills": (row.get("経験スキル") or "").strip(),
            "languages": (row.get("言語") or "").strip(),
            "desired_price": (row.get("希望単価（円）") or "").strip(),
            "start_timing": (row.get("稼働開始時期") or "").strip(),
            "work_style": (row.get("稼働形態") or "").strip(),
            "capacity": (row.get("稼働日数") or "").strip(),
            "applied_at": applied_at,
            "applications": [application],
            # 突合結果（後続フェーズで埋める）
            "slack_hits": None,      # None=未実行/失敗, []=実行済みヒットなし
            "slack_error": None,
            "fb_matches": None,
            "fb_unsellable": None,
            "fb_memos": None,
            "fb_error": None,
        }
        by_key[key] = cand

    candidates = list(by_key.values())
    log(f"候補者数（重複応募まとめ後）: {len(candidates)} 名")
    return candidates


# ========== Phase 2: Slack #inquiries 検索（Hub版から流用） ==========

INQUIRIES_CHANNEL_NAME = "inquiries"

_SLACK_LAST_CALL_TS = 0.0
SLACK_MIN_INTERVAL = 3.2  # search.messages = Tier2 (20回/分) を確実に下回る


def _slack_search_raw(query: str, count: int, max_retry: int = 3) -> list[dict[str, Any]]:
    global _SLACK_LAST_CALL_TS
    token = os.environ.get("SLACK_USER_TOKEN")
    if not token:
        return []
    url = "https://slack.com/api/search.messages?" + urllib.parse.urlencode(
        {"query": query, "count": str(count), "sort": "timestamp"}
    )
    for attempt in range(max_retry + 1):
        wait = SLACK_MIN_INTERVAL - (time.time() - _SLACK_LAST_CALL_TS)
        if wait > 0:
            time.sleep(wait)
        try:
            req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
            with urllib.request.urlopen(req, timeout=15) as r:
                _SLACK_LAST_CALL_TS = time.time()
                data = json.loads(r.read().decode("utf-8"))
            if not data.get("ok"):
                err = data.get("error")
                if err == "ratelimited" and attempt < max_retry:
                    log(f"  slack search ratelimited ({query}); retry in 30s")
                    time.sleep(30)
                    continue
                log(f"  slack search err ({query}): {err}")
                return []
            return data.get("messages", {}).get("matches", [])
        except urllib.error.HTTPError as e:
            _SLACK_LAST_CALL_TS = time.time()
            if e.code == 429 and attempt < max_retry:
                retry_after = int(e.headers.get("Retry-After") or 30)
                log(f"  slack 429 ({query}); sleep {retry_after}s (attempt {attempt+1})")
                time.sleep(retry_after)
                continue
            log(f"  slack search HTTPError ({query}): {e}")
            return []
        except Exception as e:
            log(f"  slack search exception ({query}): {e}")
            return []
    return []


def _slack_fetch_thread(channel: str, thread_ts: str) -> list[dict[str, Any]]:
    """conversations.replies でスレッド全体を取得."""
    global _SLACK_LAST_CALL_TS
    token = os.environ.get("SLACK_USER_TOKEN")
    if not token or not channel or not thread_ts:
        return []
    url = "https://slack.com/api/conversations.replies?" + urllib.parse.urlencode(
        {"channel": channel, "ts": thread_ts, "limit": "200"}
    )
    for attempt in range(4):
        wait = SLACK_MIN_INTERVAL - (time.time() - _SLACK_LAST_CALL_TS)
        if wait > 0:
            time.sleep(wait)
        try:
            req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
            with urllib.request.urlopen(req, timeout=15) as r:
                _SLACK_LAST_CALL_TS = time.time()
                data = json.loads(r.read().decode("utf-8"))
            if not data.get("ok"):
                err = data.get("error")
                if err == "ratelimited" and attempt < 3:
                    time.sleep(30)
                    continue
                log(f"  slack replies err ({channel}/{thread_ts}): {err}")
                return []
            return data.get("messages", []) or []
        except urllib.error.HTTPError as e:
            _SLACK_LAST_CALL_TS = time.time()
            if e.code == 429 and attempt < 3:
                retry_after = int(e.headers.get("Retry-After") or 30)
                time.sleep(retry_after)
                continue
            log(f"  slack replies HTTPError ({channel}/{thread_ts}): {e}")
            return []
        except Exception as e:
            log(f"  slack replies exception ({channel}/{thread_ts}): {e}")
            return []
    return []


def slack_search(query: str, count: int = 5) -> list[dict[str, Any]]:
    """Slack search.messages を呼んで応募者名にマッチするメッセージを返す.

    フリーランスボードの氏名は「姓 名」(スペース区切り) で来るが、Slack上の
    表記は揺らぐ:
      - 「姓 名」(スペース込みフルネーム)
      - 「姓名」(スペース無しフルネーム)
      - 「姓さん」「姓のみ」など姓だけの言及
    そのため複数クエリで OR 検索し、姓のみクエリ分は本文に姓 or 名が含まれる
    メッセージに限定して同姓別人を弾く。重複は ts+channel で除去。
    ヒットしたメッセージのスレッド全体（リプライ含む）も取得する。
    """
    if not os.environ.get("SLACK_USER_TOKEN"):
        return []

    parts = [p for p in re.split(r"[\s　]+", query.strip()) if p]
    surname = parts[0] if parts else query.strip()
    given = parts[1] if len(parts) >= 2 else ""
    full_with_space = query.strip()
    full_no_space = "".join(parts) if parts else query.strip()

    queries: list[tuple[str, bool]] = []  # (query, requires_body_filter)
    queries.append((f'"{full_with_space}" in:#{INQUIRIES_CHANNEL_NAME}', False))
    if full_no_space and full_no_space != full_with_space:
        queries.append((f'"{full_no_space}" in:#{INQUIRIES_CHANNEL_NAME}', False))
    if surname and surname not in (full_with_space, full_no_space):
        queries.append((f'"{surname}" in:#{INQUIRIES_CHANNEL_NAME}', True))

    seen: set[tuple[str, str]] = set()  # (channel_id, ts)
    out: list[dict[str, Any]] = []
    threads_to_fetch: set[tuple[str, str]] = set()  # (channel_id, thread_ts)

    def _add_hit(msg: dict[str, Any], channel_id: str, permalink: str | None) -> None:
        ts = str(msg.get("ts") or "")
        key = (channel_id, ts)
        if key in seen or not ts:
            return
        seen.add(key)
        text = (msg.get("text") or "")[:500]
        out.append(
            {
                "ts": msg.get("ts"),
                "user": msg.get("username") or msg.get("user"),
                "text": text,
                "permalink": permalink,
                "channel": channel_id,
                "thread_ts": msg.get("thread_ts"),
                "is_reply": bool(
                    msg.get("thread_ts") and msg.get("thread_ts") != msg.get("ts")
                ),
            }
        )

    for q, needs_filter in queries:
        msgs = _slack_search_raw(q, count)
        for m in msgs:
            text = m.get("text") or ""
            if needs_filter:
                if not (
                    full_with_space in text
                    or full_no_space in text
                    or (given and given in text)
                    or f"{surname}さん" in text
                ):
                    continue
            channel_id = (m.get("channel") or {}).get("id") or ""
            _add_hit(m, channel_id, m.get("permalink"))
            thread_ts = m.get("thread_ts") or m.get("ts")
            if channel_id and thread_ts:
                threads_to_fetch.add((channel_id, str(thread_ts)))

    # スレッド本体＋全リプライを取得
    for channel_id, thread_ts in threads_to_fetch:
        replies = _slack_fetch_thread(channel_id, thread_ts)
        for r_msg in replies:
            _add_hit(r_msg, channel_id, None)

    return out


# ========== Phase 3: FreelanceBase 突合（Hub版から流用 + メモ取得を新規実装） ==========


def fb_capture_auth(fb_page: Page) -> tuple[dict[str, str], dict[str, Any]]:
    """FreelanceBase /api/enterprise/candidates/index の認証ヘッダ＋ペイロードを捕捉する."""
    state: dict[str, Any] = {"headers": None, "payload": None}

    def _on_req(req: Any) -> None:
        if "/api/enterprise/candidates/index" in req.url and req.method == "POST":
            if state["headers"] is None:
                state["headers"] = dict(req.headers)
                try:
                    state["payload"] = json.loads(req.post_data or "{}")
                except Exception:
                    pass

    fb_page.on("request", _on_req)
    try:
        fb_page.goto(
            "https://freelancebase.jp/enterprise/candidates", wait_until="networkidle"
        )
        fb_page.wait_for_timeout(2500)
    finally:
        fb_page.remove_listener("request", _on_req)

    if not state["headers"] or not state["payload"]:
        raise RuntimeError("FB candidates/index API の認証ヘッダ取得失敗")

    auth = {
        "X-CSRF-Token": state["headers"].get("x-csrf-token", ""),
        "uid": state["headers"].get("uid", ""),
        "client": state["headers"].get("client", ""),
        "access-token": state["headers"].get("access-token", ""),
        "token-type": "Bearer",
        "strategies": "enterprise",
    }
    return auth, state["payload"]


def fb_search_by_name(
    fb_page: Page, auth: dict[str, str], payload: dict[str, Any], full_name: str
) -> list[dict[str, Any]]:
    """FreelanceBase で氏名検索し、候補者リストを返す."""
    result = fb_page.evaluate(
        """async ({payload, auth, kw}) => {
            payload.keyword = kw;
            payload.page = 1;
            const h = {'Content-Type':'application/json','Accept':'application/json',...auth};
            const r = await fetch('/api/enterprise/candidates/index', {
                method:'POST', credentials:'include', headers:h,
                body: JSON.stringify(payload),
            });
            return {status: r.status, body: await r.text()};
        }""",
        {"payload": payload, "auth": auth, "kw": full_name},
    )
    if result["status"] != 200:
        return []
    data = json.loads(result["body"])
    return data.get("candidates", [])


# FB 営業ステータス: 1=営業中 / 2=営業終了 / 3=営業不可 / 4=取引停止
# 営業中・営業終了 = 営業活動を実施済み → 課金対象（承認）として扱う（2026-06-01 ユーザー指示:
# 「営業開始または営業終了ステータスになっている方は、基本的に課金対象でOK」）
# 営業不可・取引停止 のみ非承認の判定材料とする
FB_BILLABLE_STATUS_IDS = {1, 2}
FB_NON_OK_STATUS_IDS = {3, 4}
FB_STATUS_LABEL = {1: "営業中", 2: "営業終了", 3: "営業不可", 4: "取引停止"}


def fb_filter_name_matches(
    candidates_in_fb: list[dict[str, Any]], target_name: str
) -> list[dict[str, Any]]:
    """FB 候補者リストから氏名一致するものをすべて返す（ステータス問わず）.

    メモ取得対象の特定にも使うため、営業中(OK)の候補者も返す。
    """
    target_no_space = target_name.replace(" ", "").replace("　", "")
    out = []
    for c in candidates_in_fb:
        name = (c.get("name") or "").replace(" ", "").replace("　", "")
        supplier = (c.get("supplier_name") or "").replace(" ", "").replace("　", "")
        if name == target_no_space or supplier == target_no_space:
            status_id = c.get("sales_status_id")
            out.append(
                {
                    "id_by_enterprise_id": c.get("id_by_enterprise_id"),
                    "name": c.get("name"),
                    "name_for_company": c.get("name_for_company"),
                    "sales_status_id": status_id,
                    "sales_status_label": FB_STATUS_LABEL.get(
                        status_id, f"id={status_id}"
                    ),
                    "raw": c,  # メモ系フィールドが含まれる可能性があるため生データも保持
                }
            )
    return out


def fb_fetch_memos(fb_page: Page, id_by_enterprise_id: Any) -> list[dict[str, Any]]:
    """FB 候補者詳細ページのコメントタブからメモ（コメント）を全件取得する.

    Hub版では未実装だった機能。取得経路は2系統:
      1. コメントタブ表示時の comment_candidates API レスポンスをネットワーク捕捉
      2. 失敗時は DOM からコメントテキストをスクレイピング
    """
    if not id_by_enterprise_id:
        return []
    url = f"https://freelancebase.jp/enterprise/candidates/{id_by_enterprise_id}"
    api_payloads: list[Any] = []

    def _on_resp(resp: Any) -> None:
        if "comment_candidates" in resp.url and resp.status == 200:
            try:
                api_payloads.append(resp.json())
            except Exception:
                pass

    fb_page.on("response", _on_resp)
    try:
        fb_page.goto(url, wait_until="networkidle")
        fb_page.wait_for_timeout(1500)
        # コメントタブをクリック
        tab = fb_page.locator("a[href='#comment-tab']").first
        if tab.count() == 0:
            tab = fb_page.locator("a:has-text('コメント')").first
        if tab.count() > 0:
            tab.click()
            fb_page.wait_for_timeout(2000)
    except Exception as e:
        log(f"  FBメモ取得エラー (id={id_by_enterprise_id}): {e}")
    finally:
        fb_page.remove_listener("response", _on_resp)

    memos: list[dict[str, Any]] = []

    # 1) APIレスポンスから抽出
    for payload in api_payloads:
        items = []
        if isinstance(payload, list):
            items = payload
        elif isinstance(payload, dict):
            for key in ("comments", "comment_candidates", "data", "items"):
                if isinstance(payload.get(key), list):
                    items = payload[key]
                    break
        for item in items:
            if not isinstance(item, dict):
                continue
            text = item.get("comment") or item.get("body") or item.get("content") or ""
            created = item.get("created_at") or item.get("date") or ""
            author = item.get("user_name") or item.get("author") or ""
            if text:
                memos.append({"date": str(created), "author": str(author), "text": str(text)})

    # APIレスポンスが複数回捕捉されることがある（ページロード時+タブクリック時）ため重複排除
    seen_keys: set[tuple[str, str]] = set()
    deduped: list[dict[str, Any]] = []
    for m in memos:
        key = ((m.get("date") or "")[:10], (m.get("text") or "").strip())
        if key in seen_keys:
            continue
        seen_keys.add(key)
        deduped.append(m)
    memos = deduped

    # 2) DOM フォールバック（API構造が想定と違う場合）
    if not memos:
        try:
            dom_texts = fb_page.evaluate(
                """() => {
                    const tab = document.querySelector('#comment-tab');
                    if (!tab) return [];
                    // コメントカード単位で innerText を取得（短すぎる要素は除外）
                    const blocks = Array.from(tab.querySelectorAll('div, li, article'))
                        .map(el => (el.innerText || '').trim())
                        .filter(t => t.length >= 10 && t.length <= 3000);
                    // 他のブロックを内包する外側ブロックを除去（最小単位のブロックだけ残す）
                    return blocks.filter(t => !blocks.some(o => o !== t && t.includes(o)));
                }"""
            )
            # 重複・包含を除いた上で日付らしき文字列を抽出
            seen_texts: set[str] = set()
            for t in dom_texts:
                if t in seen_texts or any(t in s for s in seen_texts):
                    continue
                seen_texts.add(t)
                date_m = re.search(r"\d{4}[/-]\d{1,2}[/-]\d{1,2}", t)
                memos.append(
                    {"date": date_m.group(0) if date_m else "", "author": "", "text": t}
                )
        except Exception as e:
            log(f"  FBメモ DOM取得エラー (id={id_by_enterprise_id}): {e}")

    return memos


# ========== Phase 4: 判定ロジック ==========

# 判定理由 → 返却CSV「承認備考」(D列) での表記（優先度順: 上にあるほど優先）
REJECT_REASONS: list[tuple[str, str]] = [
    ("営業不可（FB）", "登録済営業不可人材"),
    ("60歳以上", "60歳オーバーのため"),
    ("正社員（副業推定）", "正社員副業のため"),
    ("海外在住", "海外在住のため"),
    ("稼働日数不足", "稼働日数不足のため"),
    ("経歴詐称", "経歴に虚偽の疑いがあるため"),
    ("日本語能力不足", "日本語能力不足のため"),
    ("過去流入", "過去に別経路でご紹介済みのため"),
    ("経験不足", "実務経験不足のため"),
    ("ヒューマンNG", "対応不可人材のため"),
    ("営業行為", "営業行為のため"),
]
REJECT_REASON_MAP = dict(REJECT_REASONS)
REJECT_PRIORITY = [name for name, _ in REJECT_REASONS]


def _history_texts(cand: dict[str, Any]) -> list[tuple[str, str]]:
    """Slack履歴とFBメモの全テキストを (出所, テキスト) のリストで返す."""
    out: list[tuple[str, str]] = []
    for hit in cand.get("slack_hits") or []:
        out.append(("Slack", hit.get("text") or ""))
    for memo in cand.get("fb_memos") or []:
        out.append(("FBメモ", memo.get("text") or ""))
    return out


def _ascii_ratio(s: str) -> float:
    if not s:
        return 0.0
    return sum(1 for c in s if ord(c) < 128) / len(s)


def detect_overseas(cand: dict[str, Any]) -> tuple[bool, str]:
    """海外在住判定.

    - 住まいの地域に明示的な海外地名 → 該当
    - 「その他」単独では該当としない（複合判定: 言語/自己PR/Slack/FBメモに海外シグナルがある場合のみ該当）
    """
    region = cand.get("prefecture", "")
    if not region:
        return False, ""
    if any(suffix in region for suffix in ["都", "道", "府", "県"]):
        return False, ""
    overseas_keywords = [
        "海外", "アメリカ", "USA", "中国", "上海", "北京", "韓国", "ソウル",
        "シンガポール", "タイ", "バンコク", "フィリピン", "マニラ", "インドネシア",
        "ベトナム", "ハノイ", "インド", "デリー", "ドイツ", "フランス", "イギリス",
        "カナダ", "オーストラリア", "ブラジル",
    ]
    for kw in overseas_keywords:
        if kw in region:
            return True, f"住まいの地域='{region}' に '{kw}' を含む"

    if region == "その他":
        signals: list[str] = []
        langs = cand.get("languages", "")
        if langs and "日本語" not in langs:
            signals.append(f"言語='{langs}' に日本語なし")
        self_pr = cand.get("self_pr", "")
        ratio = _ascii_ratio(self_pr)
        if self_pr and len(self_pr) > 30 and ratio > 0.5:
            signals.append(f"自己PRの英語比率 {ratio:.0%}")
        for source, text in _history_texts(cand):
            for kw in ["海外", "国外", "日本にいない", "日本国外", "外国在住"]:
                if kw in text:
                    signals.append(f"{source}に '{kw}' 言及")
                    break
        if signals:
            return True, "住まいの地域='その他' + " + " / ".join(signals)
        return False, ""  # 単独 → judge側で要判断に送る
    return False, ""


def detect_age_high(cand: dict[str, Any]) -> tuple[bool, str]:
    age = cand.get("age")
    if isinstance(age, int) and age >= AGE_THRESHOLD:
        return True, f"年齢={age}歳 ({AGE_THRESHOLD}歳以上, 生年月日={cand.get('birthday')})"
    return False, ""


def detect_workdays_short(cand: dict[str, Any]) -> tuple[bool, str]:
    """稼働日数不足判定. 週1〜2日のみなら明確に該当."""
    cap = cand.get("capacity") or ""
    days = re.findall(r"週(\d)日", cap)
    if not days:
        return False, ""
    days_int = sorted({int(d) for d in days})
    if days_int and max(days_int) <= 2:
        return True, f"稼働日数='{cap}' (週2日以下)"
    return False, ""


def detect_fake_history(cand: dict[str, Any]) -> tuple[bool, str]:
    """経歴詐称の簡易判定. 自己PR・履歴の不自然な記述、Slack/FBメモでの言及で検出."""
    self_pr = (cand.get("self_pr") or "")[:1500]
    suspicious = [
        "すべての言語", "全言語", "全領域", "全てに精通", "あらゆる",
        "100以上", "全プロジェクト",
    ]
    for kw in suspicious:
        if kw in self_pr:
            return True, f"自己PR に '{kw}' を含む"
    # Slack / FBメモでの経歴詐称言及
    mention_keywords = ["経歴詐称", "経歴改ざん", "経歴に虚偽", "詐称", "経歴盛り"]
    for source, text in _history_texts(cand):
        for kw in mention_keywords:
            if kw in text:
                return True, f"{source}に '{kw}' を含む言及"
    return False, ""


def detect_human_ng(cand: dict[str, Any]) -> tuple[bool, str]:
    """ヒューマンNG: Slack履歴 / FBメモに明確な NG 表現がある場合のみ.

    「見送り / お見送り」単独では対象外にしない（お見送り理由が対象外要件に
    該当した場合のみ、他検出器が拾う）。
    """
    ng_keywords = [
        "クレーム", "対応NG", "ブラックリスト", "NG人材", "対応不可",
        "NGにしておきます",
    ]
    for source, text in _history_texts(cand):
        for kw in ng_keywords:
            if kw in text:
                return True, f"{source}に '{kw}' を含む言及"
    return False, ""


def detect_past_inflow(cand: dict[str, Any]) -> tuple[bool, str]:
    """過去流入: 応募日より 14 日以上前の Slack #inquiries メッセージ、
    または応募日より 14 日以上前の FB メモがある場合."""
    applied_dt = _parse_date(cand.get("applied_at", ""))
    if not applied_dt:
        return False, ""
    # Slack
    for hit in cand.get("slack_hits") or []:
        ts = hit.get("ts")
        if not ts:
            continue
        try:
            hit_dt = datetime.fromtimestamp(float(ts))
        except (TypeError, ValueError):
            continue
        if (applied_dt - hit_dt).days >= PAST_INFLOW_DAYS:
            return True, f"応募日 {applied_dt.date()} より前の Slack 履歴あり ({hit_dt.date()})"
    # FBメモ
    for memo in cand.get("fb_memos") or []:
        memo_dt = _parse_date((memo.get("date") or "")[:19].replace("T", " "))
        if memo_dt and (applied_dt - memo_dt).days >= PAST_INFLOW_DAYS:
            return True, f"応募日 {applied_dt.date()} より前の FBメモあり ({memo_dt.date()})"
    return False, ""


def detect_experience_low(cand: dict[str, Any]) -> tuple[bool, str]:
    """経験不足: Slack / FBメモで経験浅さに言及されている場合のみ判定.

    CSVの経験スキル欄は自己申告のため自動判定の根拠にしない。
    """
    keywords = [
        "未経験", "ほぼ未経験", "経験浅", "経験不足", "経験が浅",
        "ジュニア", "新人", "経験少な", "経験が少な",
    ]
    short_year_re = re.compile(r"経験[が＝=:：\s]*(?:0|半|1|２|2)[年ヶ月]")
    for source, text in _history_texts(cand):
        for kw in keywords:
            if kw in text:
                return True, f"{source}に '{kw}' を含む言及（経験不足）"
        m = short_year_re.search(text)
        if m:
            return True, f"{source}に '{m.group(0)}' を含む言及（経験不足）"
    return False, ""


def detect_japanese_low(cand: dict[str, Any]) -> tuple[bool, str]:
    """日本語能力不足: 言語欄に日本語なし / 自己PRが英語のみ / Slack・FBメモでの言及."""
    langs = cand.get("languages", "")
    if langs and "日本語" not in langs:
        return True, f"言語='{langs}' に日本語が含まれない"
    self_pr = (cand.get("self_pr") or "").strip()
    if self_pr and len(self_pr) > 30:
        ratio = _ascii_ratio(self_pr)
        if ratio > 0.92:
            return True, f"自己PR が英語比率 {ratio:.0%}（日本語ほぼなし）"
    mention_keywords = ["日本語が怪しい", "日本語能力", "日本語に不安", "日本語が不安", "日本語NG", "日本語力"]
    for source, text in _history_texts(cand):
        for kw in mention_keywords:
            if kw in text:
                return True, f"{source}に '{kw}' を含む言及"
    return False, ""


def detect_full_time_employee(cand: dict[str, Any]) -> tuple[bool, str]:
    """正社員判定. 単独では対象外候補にしない（フリーランス転向組がいる）.

    複合条件（正社員 + 週1〜2日 = 副業推定）または Slack/FBメモで正社員副業と
    言及されている場合のみ対象外候補に格上げする。
    """
    status = cand.get("working_status", "")
    is_employee = status == "正社員"
    # Slack / FBメモで正社員・副業言及
    for source, text in _history_texts(cand):
        for kw in ["正社員のため", "正社員副業", "副業のため", "副業希望", "本業があ"]:
            if kw in text:
                return True, f"{source}に '{kw}' を含む言及" + (
                    f"（現在の状況='{status}'）" if status else ""
                )
    if not is_employee:
        return False, ""
    cap = cand.get("capacity") or ""
    days = re.findall(r"週(\d)日", cap)
    if days and max(int(d) for d in days) <= 2:
        return True, f"現在の状況='正社員' + 稼働日数='{cap}' (週2日以下=副業推定)"
    return False, ""


def detect_sales_pitch(cand: dict[str, Any]) -> tuple[bool, str]:
    """営業行為: 自己PRで自社製品宣伝/URL誘導/求職以外の文脈."""
    self_pr = (cand.get("self_pr") or "")[:1500]
    if not self_pr:
        return False, ""
    sales_keywords = [
        "I am the maker", "We are looking for", "our company", "弊社サービス",
        "$ ", "USD", "100,000,000", "investment", "fundraising", "co-founder",
    ]
    for kw in sales_keywords:
        if kw.lower() in self_pr.lower():
            return True, f"自己PR に '{kw}' を含む（営業/勧誘の典型句）"
    return False, ""


def _fb_summary(fb_hits: list[dict[str, Any]]) -> str:
    parts = []
    for c in fb_hits:
        label = c.get("sales_status_label") or "非OK"
        fid = c.get("id_by_enterprise_id")
        parts.append(f"{label} (id: {fid})")
    return ", ".join(parts)


def detect_fb_unsellable(cand: dict[str, Any]) -> tuple[bool, str]:
    """FB 非OKステータス（営業終了/営業不可/取引停止）の判定.

    今回応募の書類落ち結果としてステータス登録された可能性があるため、
    過去流入の証跡（Slack の応募日14日以上前のメッセージ、または応募日より前の
    FBメモ）がある場合のみ「請求対象外候補」へ格上げする。
    証跡が無い場合は False を返し、judge_candidate 側で要判断扱いとする。
    """
    fb_hits = cand.get("fb_unsellable") or []
    if not fb_hits:
        return False, ""
    summary = _fb_summary(fb_hits)
    applied_dt = _parse_date(cand.get("applied_at", ""))
    if not applied_dt:
        return False, ""
    # Slack 過去流入の証跡
    for hit in cand.get("slack_hits") or []:
        ts = hit.get("ts")
        if not ts:
            continue
        try:
            hit_dt = datetime.fromtimestamp(float(ts))
        except (TypeError, ValueError):
            continue
        if (applied_dt - hit_dt).days >= PAST_INFLOW_DAYS:
            return True, f"FB {summary} + 過去流入Slack履歴 ({hit_dt.date()})"
    # FBメモの証跡（応募日より前のメモ = 過去に接点があった）
    for memo in cand.get("fb_memos") or []:
        memo_dt = _parse_date((memo.get("date") or "")[:19].replace("T", " "))
        if memo_dt and memo_dt < applied_dt:
            return True, f"FB {summary} + 応募日以前のFBメモあり ({memo_dt.date()})"
    return False, ""


def judge_candidate(cand: dict[str, Any]) -> dict[str, Any]:
    """1人の候補者を判定し、判定結果を返す."""
    rules: list[tuple[str, Any]] = [
        ("営業不可（FB）", detect_fb_unsellable),
        ("60歳以上", detect_age_high),
        ("正社員（副業推定）", detect_full_time_employee),
        ("海外在住", detect_overseas),
        ("稼働日数不足", detect_workdays_short),
        ("経歴詐称", detect_fake_history),
        ("日本語能力不足", detect_japanese_low),
        ("過去流入", detect_past_inflow),
        ("経験不足", detect_experience_low),
        ("ヒューマンNG", detect_human_ng),
        ("営業行為", detect_sales_pitch),
    ]
    matched: list[dict[str, str]] = []
    for internal_name, fn in rules:
        try:
            hit, evidence = fn(cand)
            if hit:
                matched.append({"internal_reason": internal_name, "evidence": evidence})
        except Exception as e:
            log(f"  judge error '{internal_name}' for {cand.get('name')}: {e}")

    # 要判断ポイント（情報不足・グレー・突合失敗）
    info_gaps: list[str] = []

    # 突合失敗・未実施 → CSVのみで判定しない（必ず要判断に送る）
    if cand.get("slack_error"):
        info_gaps.append(f"⚠ Slack突合失敗: {cand['slack_error']}")
    elif cand.get("slack_hits") is None:
        info_gaps.append("⚠ Slack突合が未実施（CSVのみでの判定は不可）")
    if cand.get("fb_error"):
        info_gaps.append(f"⚠ FB突合失敗: {cand['fb_error']}")
    elif cand.get("fb_matches") is None:
        info_gaps.append("⚠ FB突合が未実施（CSVのみでの判定は不可）")

    # 正社員単独はフリーランス転向の可能性があるため要判断扱い
    if cand.get("working_status") == "正社員" and not any(
        m["internal_reason"] == "正社員（副業推定）" for m in matched
    ):
        info_gaps.append("現在の状況=正社員（フリーランス転向の可能性あり、要確認）")

    # 住まいの地域=その他 単独（海外シグナルなし）→ 要判断
    if cand.get("prefecture") == "その他" and not any(
        m["internal_reason"] == "海外在住" for m in matched
    ):
        info_gaps.append("住まいの地域=「その他」（海外在住の可能性あり、要確認）")

    # FB 非OKステータスがヒットしたが過去流入の証跡が確認できない → 要判断
    fb_hits = cand.get("fb_unsellable") or []
    if fb_hits and not any(m["internal_reason"] == "営業不可（FB）" for m in matched):
        info_gaps.append(
            f"FB {_fb_summary(fb_hits)} — 今回応募の書類落ち結果の可能性あり、過去流入の有無を要確認"
        )

    # FB 営業中/営業終了ステータス → 課金対象（営業活動を実施済み = 課金は正当）
    # 他の判定理由・要判断ポイントより優先する
    fb_billable = [
        m for m in (cand.get("fb_matches") or [])
        if m.get("sales_status_id") in FB_BILLABLE_STATUS_IDS
    ]
    if fb_billable and not cand.get("fb_error"):
        note = f"FB {_fb_summary(fb_billable)}（営業活動実施済みのため課金対象）"
        if matched:
            note += " ※他の判定理由該当あり: " + ", ".join(
                m["internal_reason"] for m in matched
            )
        return {
            "category": "請求対象",
            "matched_reasons": matched,  # 透明性のため記録は残す
            "info_gaps": [],
            "reject_reason": "",
            "memo": note,
            "fb_billable": True,
        }

    # 分類
    if matched:
        category = "請求対象外候補"
    elif info_gaps:
        category = "要判断"
    else:
        category = "請求対象"

    # 返却CSV「承認備考」の理由表記（最優先の1つ）
    reject_reason = ""
    for reason_name in REJECT_PRIORITY:
        if any(m["internal_reason"] == reason_name for m in matched):
            reject_reason = REJECT_REASON_MAP[reason_name]
            break

    # 内部メモ（複数理由の統合、人手参照用）
    memo = " / ".join(f"{m['internal_reason']}（{m['evidence']}）" for m in matched)

    return {
        "category": category,
        "matched_reasons": matched,
        "info_gaps": info_gaps,
        "reject_reason": reject_reason,
        "memo": memo,
    }


# ========== Phase 5/6: 返却CSV ==========


def csv_plan_for_candidate(c: dict[str, Any]) -> tuple[str, str]:
    """候補者の判定結果から返却CSVの (承認ステータス, 承認備考) を返す.

    要判断は ('要レビュー', '') を返し、Phase 6 では overrides で解決されるまでエラーになる。
    """
    j = c.get("judgment") or {}
    category = j.get("category", "要判断")
    if category == "請求対象外候補":
        return "非承認", j.get("reject_reason") or "登録対象外"
    if category == "請求対象":
        return "承認", ""
    return "要レビュー", ""


def make_return_csv(
    report_path: Path, overrides_path: Path | None, output_dir: Path
) -> Path:
    """実行結果JSONと overrides から返却CSVを生成する.

    - 元のCSVと同一の行構成・列構成・エンコーディング（UTF-8 BOM付き）で出力
    - C列「承認ステータス」: 承認 / 非承認
    - D列「承認備考」: 非承認理由（承認時は空欄）
    - 要判断の候補者が overrides で解決されていない場合は ValueError
    """
    data = json.loads(report_path.read_text(encoding="utf-8"))
    src_csv = Path(data["csv_path"])
    if not src_csv.exists():
        raise FileNotFoundError(f"元のCSVが見つかりません: {src_csv}")

    overrides: dict[str, dict[str, str]] = {}
    if overrides_path:
        overrides = json.loads(overrides_path.read_text(encoding="utf-8"))

    # 候補者ごとの (承認ステータス, 承認備考) を決定
    plan: dict[tuple[str, str], tuple[str, str]] = {}  # (氏名, メール) → (status, reason)
    unresolved: list[str] = []
    for c in data["candidates"]:
        name = c.get("name", "")
        email = c.get("email", "")
        status, reason = csv_plan_for_candidate(c)
        ov = overrides.get(name)
        if ov:
            status = ov.get("status", status)
            reason = ov.get("reason", "") if status == "非承認" else ""
        if status not in ("承認", "非承認"):
            unresolved.append(name)
            continue
        if status == "非承認" and not reason:
            raise ValueError(
                f"非承認の理由が空です: {name}（overrides に reason を指定してください）"
            )
        plan[(name, email)] = (status, reason)

    if unresolved:
        raise ValueError(
            "要判断の候補者が未解決です。レポートを確認し、overrides JSON で承認/非承認を指定してください: "
            + ", ".join(unresolved)
        )

    # 元のCSVを読み、承認ステータス/承認備考列を埋めて書き出す
    with src_csv.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.reader(f))
    header = rows[0]
    try:
        name_idx = header.index("氏名")
        email_idx = header.index("メールアドレス")
        status_idx = header.index("承認ステータス")
        note_idx = header.index("承認備考")
    except ValueError as e:
        raise ValueError(f"元のCSVに必要な列がありません: {e}")

    missing: list[str] = []
    for row in rows[1:]:
        key = (row[name_idx].strip(), row[email_idx].strip())
        if key not in plan:
            missing.append(row[name_idx])
            continue
        status, reason = plan[key]
        row[status_idx] = status
        row[note_idx] = reason
    if missing:
        raise ValueError(
            f"判定結果に存在しない行があります（CSVと実行結果JSONの不一致）: {', '.join(missing)}"
        )

    out_path = output_dir / f"{src_csv.stem}_返却.csv"
    with out_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f, quoting=csv.QUOTE_ALL)
        writer.writerows(rows)
    return out_path


# ========== Phase 5: Markdown レポート ==========


def render_report(month: str, candidates: list[dict[str, Any]]) -> str:
    """Markdown レポートを生成する."""
    by_cat: dict[str, list[dict[str, Any]]] = {
        "請求対象外候補": [],
        "要判断": [],
        "請求対象": [],
    }
    for c in candidates:
        j = c.get("judgment") or {}
        by_cat.setdefault(j.get("category", "要判断"), []).append(c)

    lines: list[str] = []
    lines.append(f"# フリーランスボード 請求対象チェック - {month}")
    lines.append("")
    lines.append(f"- 候補者数: {len(candidates)}")
    lines.append(
        f"- 判定内訳: 請求対象外候補 {len(by_cat['請求対象外候補'])} / "
        f"要判断 {len(by_cat['要判断'])} / 請求対象 {len(by_cat['請求対象'])}"
    )
    lines.append("")

    def render_history(c: dict[str, Any]) -> list[str]:
        """Slack履歴とFBメモを古い順でレンダリング."""
        out: list[str] = []
        slack = c.get("slack_hits") or []
        if slack:
            out.append("- Slack #inquiries 履歴:")
            sorted_hits = sorted(
                slack,
                key=lambda h: (
                    float(h.get("thread_ts") or h.get("ts") or 0),
                    float(h.get("ts") or 0),
                ),
            )
            for s in sorted_hits:
                ts = s.get("ts")
                try:
                    date_str = datetime.fromtimestamp(float(ts)).strftime("%Y-%m-%d")
                except (TypeError, ValueError):
                    date_str = "?"
                permalink = s.get("permalink") or ""
                text = (s.get("text") or "").strip()
                text = re.sub(r"<@U[A-Z0-9]+\|[^>]+>\s*", "", text)
                inner = [ln for ln in text.split("\n") if ln.strip()]
                head = inner[0] if inner else ""
                prefix = "    ↳ " if s.get("is_reply") else "  - "
                indent = "      " if s.get("is_reply") else "    "
                link_part = f"  <{permalink}>" if permalink else ""
                out.append(f"{prefix}[{date_str}] {head}{link_part}")
                for ln in inner[1:]:
                    out.append(f"{indent}{ln}")
        memos = c.get("fb_memos") or []
        if memos:
            out.append("- FreelanceBase メモ:")
            for m in memos:
                d = (m.get("date") or "?")[:10]
                first, *rest = [ln for ln in (m.get("text") or "").split("\n") if ln.strip()] or [""]
                out.append(f"  - [{d}] {first}")
                for ln in rest:
                    out.append(f"    {ln}")
        return out

    def render_candidate(c: dict[str, Any], category: str) -> list[str]:
        out: list[str] = []
        name = c.get("name", "")
        age = c.get("age", "?")
        out.append(f"### {name} ({age}歳)")
        out.append(
            f"- 在住: {c.get('prefecture','-')} / 稼働: {c.get('capacity','-')} / "
            f"現在の状況: {c.get('working_status','-')} / 言語: {c.get('languages','-') or '-'}"
        )
        apps = c.get("applications") or []
        if apps:
            out.append(f"- 応募: {apps[0].get('applied_at','')} 「{apps[0].get('project_title','')}」"
                       + (f" 他{len(apps)-1}件" if len(apps) > 1 else ""))
        fbm = c.get("fb_matches") or []
        if fbm:
            out.append(f"- FB照合: {_fb_summary(fbm)}")
        else:
            out.append("- FB照合: 一致なし")
        j = c.get("judgment") or {}
        if category == "請求対象外候補":
            out.append(f"- 承認備考（非承認理由）: **{j.get('reject_reason','')}**")
            out.append("- 判定根拠:")
            for r in j.get("matched_reasons", []):
                out.append(f"  - {r['internal_reason']}: {r['evidence']}")
        elif category == "要判断":
            out.append("- 論点:")
            for gap in j.get("info_gaps", []):
                out.append(f"  - {gap}")
        elif category == "請求対象" and j.get("memo"):
            out.append(f"- 備考: {j['memo']}")
        out.extend(render_history(c))
        if c.get("self_pr"):
            pr = c["self_pr"][:200].replace("\n", " ")
            out.append(f"- 自己PR抜粋: {pr}")
        return out

    for cat in ["請求対象外候補", "要判断", "請求対象"]:
        items = by_cat.get(cat, [])
        lines.append(f"## {cat} ({len(items)}件)")
        if not items:
            lines.append("(該当なし)")
            lines.append("")
            continue
        lines.append("")
        for c in items:
            lines.extend(render_candidate(c, cat))
            lines.append("")

    # 返却CSVプレビュー
    lines.append("## 返却CSVプレビュー（C列=承認ステータス / D列=承認備考）")
    lines.append("")
    lines.append("| 氏名 | 承認ステータス | 承認備考 |")
    lines.append("|---|---|---|")
    for c in candidates:
        status, reason = csv_plan_for_candidate(c)
        status_disp = "⚠ 要レビュー" if status == "要レビュー" else status
        lines.append(f"| {c.get('name','')} | {status_disp} | {reason} |")
    lines.append("")
    lines.append(
        "※ 「⚠ 要レビュー」の候補者について承認/非承認を判断した上で、"
        "`--make-csv --overrides <json>` で返却CSVを生成してください。"
    )
    lines.append("")
    return "\n".join(lines)


# ========== Phase 5: HTML レポート ==========


def _h(s: str) -> str:
    import html as _html
    return _html.escape(s or "", quote=True)


_URL_RE = re.compile(r"https?://[^\s<>]+")


def _autolink(text: str) -> str:
    parts: list[str] = []
    last = 0
    for m in _URL_RE.finditer(text):
        parts.append(_h(text[last:m.start()]))
        url = m.group(0)
        parts.append(f'<a href="{_h(url)}" target="_blank" rel="noopener">{_h(url)}</a>')
        last = m.end()
    parts.append(_h(text[last:]))
    return "".join(parts)


def render_report_html(month: str, candidates: list[dict[str, Any]]) -> str:
    """HTML レポートを生成する.

    - Slack permalink / FB候補者URL / スキルシートURL をクリック可能リンクに
    - Slack履歴・FBメモ・自己PRは <details> で折りたたみ
    - カテゴリごとに色分けバッジ
    - 返却CSVプレビュー（C列=承認ステータス / D列=承認備考）
    """
    by_cat: dict[str, list[dict[str, Any]]] = {
        "請求対象外候補": [],
        "要判断": [],
        "請求対象": [],
    }
    for c in candidates:
        j = c.get("judgment") or {}
        by_cat.setdefault(j.get("category", "要判断"), []).append(c)

    cat_color = {
        "請求対象外候補": "#d93025",
        "要判断": "#f29900",
        "請求対象": "#188038",
    }

    def render_slack(c: dict[str, Any]) -> str:
        slack = c.get("slack_hits") or []
        if not slack:
            return '<p class="meta no-history">Slack #inquiries 履歴: なし</p>'
        sorted_hits = sorted(
            slack,
            key=lambda h: (
                float(h.get("thread_ts") or h.get("ts") or 0),
                float(h.get("ts") or 0),
            ),
        )
        items_html: list[str] = []
        for s in sorted_hits:
            ts = s.get("ts")
            try:
                date_str = datetime.fromtimestamp(float(ts)).strftime("%Y-%m-%d")
            except (TypeError, ValueError):
                date_str = "?"
            permalink = s.get("permalink") or ""
            text = (s.get("text") or "").strip()
            text = re.sub(r"<@U[A-Z0-9]+\|[^>]+>\s*", "", text)
            body_html = _autolink(text).replace("\n", "<br>")
            link = (
                f'<a href="{_h(permalink)}" target="_blank" rel="noopener">Slack で開く</a>'
                if permalink else ""
            )
            reply_class = " slack-reply" if s.get("is_reply") else ""
            reply_marker = "↳ " if s.get("is_reply") else ""
            items_html.append(
                f'<li class="slack-item{reply_class}"><span class="date">{reply_marker}[{date_str}]</span> {link}'
                f'<div class="hist-body">{body_html}</div></li>'
            )
        return (
            f'<details class="history" open><summary>Slack #inquiries 履歴 ({len(slack)}件)</summary>'
            f'<ul>{"".join(items_html)}</ul></details>'
        )

    def render_fb_memos(c: dict[str, Any]) -> str:
        memos = c.get("fb_memos") or []
        fbm = c.get("fb_matches") or []
        if not fbm:
            return '<p class="meta no-history">FreelanceBase: 一致なし</p>'
        # FB候補者リンク
        links = []
        for m in fbm:
            fid = m.get("id_by_enterprise_id")
            label = m.get("sales_status_label", "")
            if fid:
                links.append(
                    f'<a href="https://freelancebase.jp/enterprise/candidates/{_h(str(fid))}" '
                    f'target="_blank" rel="noopener">FB詳細 (id:{_h(str(fid))} / {_h(label)}) ↗</a>'
                )
        links_html = '<p class="meta">' + " / ".join(links) + "</p>" if links else ""
        if not memos:
            return links_html + '<p class="meta no-history">FreelanceBase メモ: なし</p>'
        items_html: list[str] = []
        for m in memos:
            d = (m.get("date") or "?")[:10]
            author = m.get("author") or ""
            body_html = _autolink((m.get("text") or "").strip()).replace("\n", "<br>")
            author_part = f" ({_h(author)})" if author else ""
            items_html.append(
                f'<li><span class="date">[{_h(d)}]</span>{author_part}'
                f'<div class="hist-body">{body_html}</div></li>'
            )
        return (
            links_html
            + f'<details class="history" open><summary>FreelanceBase メモ ({len(memos)}件)</summary>'
            f'<ul>{"".join(items_html)}</ul></details>'
        )

    def render_candidate(c: dict[str, Any], category: str) -> str:
        j = c.get("judgment") or {}
        name = c.get("name", "")
        age = c.get("age", "?")
        out: list[str] = ['<div class="card">']
        out.append(f'<h3>{_h(name)} <span class="age">({_h(str(age))}歳)</span></h3>')
        meta_parts = [
            f"在住: {_h(c.get('prefecture','-'))}",
            f"稼働: {_h(c.get('capacity','-'))}",
            f"現在の状況: <strong>{_h(c.get('working_status','-'))}</strong>",
        ]
        if c.get("languages"):
            meta_parts.append(f"言語: {_h(c['languages'])}")
        out.append('<p class="meta">' + " / ".join(meta_parts) + "</p>")
        apps = c.get("applications") or []
        if apps:
            app_str = f"{apps[0].get('applied_at','')} 「{apps[0].get('project_title','')}」"
            if len(apps) > 1:
                app_str += f" 他{len(apps)-1}件"
            out.append(f'<p class="meta">応募: {_h(app_str)}</p>')
        if c.get("skillsheet_url"):
            out.append(
                f'<p class="meta"><a href="{_h(c["skillsheet_url"])}" target="_blank" rel="noopener">スキルシート ↗</a></p>'
            )
        if category == "請求対象外候補":
            out.append(
                f'<p class="msg-label">承認備考（非承認理由）: <strong>{_h(j.get("reject_reason",""))}</strong></p>'
            )
            out.append('<ul class="evidence">')
            for r in j.get("matched_reasons", []):
                out.append(
                    f'<li><strong>{_h(r["internal_reason"])}:</strong> {_h(r["evidence"])}</li>'
                )
            out.append("</ul>")
        elif category == "要判断":
            out.append('<ul class="evidence">')
            for gap in j.get("info_gaps", []):
                out.append(f"<li>{_h(gap)}</li>")
            out.append("</ul>")
            # 要判断者を非承認にする場合の理由候補を併記
            if j.get("info_gaps"):
                hints = []
                if any("正社員" in g for g in j["info_gaps"]):
                    hints.append("正社員副業のため")
                if any("その他" in g for g in j["info_gaps"]):
                    hints.append("海外在住のため")
                if any("FB " in g for g in j["info_gaps"]):
                    hints.append("登録済営業不可人材")
                if hints:
                    out.append(
                        f'<p class="meta">→ 非承認と判断する場合の承認備考候補: {_h(" / ".join(hints))}</p>'
                    )
        elif category == "請求対象" and j.get("memo"):
            out.append(f'<p class="meta">{_h(j["memo"])}</p>')
        out.append(render_slack(c))
        out.append(render_fb_memos(c))
        if c.get("self_pr"):
            pr = c["self_pr"]
            out.append(
                f'<details class="self-pr"><summary>自己PR ({len(pr)}文字)</summary>'
                f'<div class="hist-body">{_autolink(pr).replace(chr(10),"<br>")}</div></details>'
            )
        out.append("</div>")
        return "\n".join(out)

    counts = {k: len(v) for k, v in by_cat.items()}
    title = f"フリーランスボード 請求対象チェック - {month}"
    css = """
:root { color-scheme: light dark; }
body { font-family: -apple-system, BlinkMacSystemFont, "Hiragino Sans", "Yu Gothic UI", sans-serif;
       max-width: 980px; margin: 1.5rem auto; padding: 0 1rem; line-height: 1.55; color: #202124; }
h1 { font-size: 1.5rem; border-bottom: 2px solid #1a73e8; padding-bottom: .3rem; }
h2 { margin-top: 2.2rem; padding: .35rem .6rem; border-radius: 4px; color: white; font-size: 1.2rem; }
h2.c0 { background: #d93025; } h2.c1 { background: #f29900; } h2.c2 { background: #188038; }
h2.cmsg { background: #1a73e8; }
.summary { background: #f1f3f4; padding: .8rem 1rem; border-radius: 6px; }
.summary span { display: inline-block; margin-right: 1.2rem; }
.summary .badge { padding: .15rem .5rem; border-radius: 10px; color: white; font-weight: 600; font-size: .9rem; }
.card { border: 1px solid #dadce0; border-radius: 8px; padding: .9rem 1.1rem; margin-bottom: 1rem;
        background: white; box-shadow: 0 1px 2px rgba(0,0,0,.04); }
.card h3 { margin: 0 0 .5rem; font-size: 1.05rem; }
.card .age { color: #5f6368; font-weight: 400; font-size: .95rem; }
.card .meta { margin: .25rem 0; color: #3c4043; font-size: .92rem; }
.card .no-history { color: #80868b; }
.msg-label { background: #fce8e6; padding: .35rem .6rem; border-left: 3px solid #d93025; margin: .4rem 0;
             font-size: .92rem; }
.evidence { margin: .4rem 0 .4rem 1.2rem; padding: 0; }
details { margin: .5rem 0; }
details summary { cursor: pointer; font-weight: 600; color: #1a73e8; font-size: .92rem; }
.history ul { padding-left: 1.2rem; margin: .4rem 0; }
.history li { margin-bottom: .6rem; }
.history .date { color: #5f6368; font-weight: 600; margin-right: .4rem; }
.history .slack-reply { margin-left: 1.4rem; }
.history .slack-reply .hist-body { border-left: 2px solid #c8ccd1; }
.hist-body { background: #f8f9fa; padding: .4rem .6rem; border-radius: 4px; margin-top: .25rem;
             font-size: .9rem; white-space: normal; }
.csv-preview { border-collapse: collapse; width: 100%; font-size: .92rem; }
.csv-preview th, .csv-preview td { border: 1px solid #dadce0; padding: .45rem .7rem; text-align: left; }
.csv-preview th { background: #f1f3f4; }
.csv-preview td.approve { color: #188038; font-weight: 600; }
.csv-preview td.reject { color: #d93025; font-weight: 600; }
.csv-preview td.review { color: #f29900; font-weight: 600; }
a { color: #1a73e8; text-decoration: none; word-break: break-all; }
a:hover { text-decoration: underline; }
@media (prefers-color-scheme: dark) {
  body { background: #202124; color: #e8eaed; }
  .summary { background: #303134; }
  .card { background: #2d2e30; border-color: #5f6368; box-shadow: none; }
  .hist-body { background: #303134; color: #e8eaed; }
  .msg-label { background: #3c1d1a; color: #f6aea9; }
  .csv-preview th { background: #303134; }
  .csv-preview th, .csv-preview td { border-color: #5f6368; }
}
"""
    parts: list[str] = [
        "<!DOCTYPE html>",
        '<html lang="ja"><head><meta charset="utf-8">',
        f"<title>{_h(title)}</title>",
        f"<style>{css}</style>",
        "</head><body>",
        f"<h1>{_h(title)}</h1>",
        '<div class="summary">',
        f"<span>候補者数: <strong>{len(candidates)}</strong></span>",
        f'<span><span class="badge" style="background:{cat_color["請求対象外候補"]}">請求対象外候補 {counts.get("請求対象外候補",0)}</span></span>',
        f'<span><span class="badge" style="background:{cat_color["要判断"]}">要判断 {counts.get("要判断",0)}</span></span>',
        f'<span><span class="badge" style="background:{cat_color["請求対象"]}">請求対象 {counts.get("請求対象",0)}</span></span>',
        "</div>",
    ]

    # 返却CSVプレビュー（先頭に配置）
    parts.append('<h2 class="cmsg">返却CSVプレビュー（C列=承認ステータス / D列=承認備考）</h2>')
    parts.append(
        '<table class="csv-preview"><thead><tr>'
        "<th>氏名</th><th>承認ステータス</th><th>承認備考</th>"
        "</tr></thead><tbody>"
    )
    for c in candidates:
        status, reason = csv_plan_for_candidate(c)
        if status == "要レビュー":
            cls, disp = "review", "⚠ 要レビュー"
        elif status == "非承認":
            cls, disp = "reject", "非承認"
        else:
            cls, disp = "approve", "承認"
        parts.append(
            f'<tr><td>{_h(c.get("name",""))}</td><td class="{cls}">{disp}</td><td>{_h(reason)}</td></tr>'
        )
    parts.append("</tbody></table>")
    parts.append(
        '<p class="meta">※ 「⚠ 要レビュー」の候補者について承認/非承認を判断した上で、'
        "返却CSVを生成してください（要レビューが残ったままではCSVを生成できません）。"
        "返送はご自身で行ってください。</p>"
    )

    for idx, cat in enumerate(["請求対象外候補", "要判断", "請求対象"]):
        items = by_cat.get(cat, [])
        parts.append(f'<h2 class="c{idx}">{_h(cat)} ({len(items)}件)</h2>')
        if not items:
            parts.append('<p class="meta">(該当なし)</p>')
            continue
        for c in items:
            parts.append(render_candidate(c, cat))
    parts.append("</body></html>")
    return "\n".join(parts)


# ========== メイン ==========


def run(args) -> int:
    csv_path = Path(args.csv).expanduser()
    if not csv_path.exists():
        log(f"CSVが見つかりません: {csv_path}")
        return 1

    if args.month:
        month = args.month
        start_date, end_date = f"{month}-01", f"{month}-31"
    else:
        start_date, end_date, month = parse_period_from_filename(csv_path)
    log(f"対象期間: {start_date} 〜 {end_date} (month={month})")

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    DEBUG_DIR.mkdir(parents=True, exist_ok=True)

    # Phase 1: CSV読込
    log("Phase 1: CSV読込")
    candidates = load_candidates_from_csv(csv_path)
    if not candidates:
        log("候補者が0件です")
        return 1

    # Phase 2: Slack #inquiries 突合（必須）
    if not os.environ.get("SLACK_USER_TOKEN"):
        raise RuntimeError(
            "SLACK_USER_TOKEN が未設定です。Slack 突合は必須のため処理を中断します。"
            " ~/.zshrc に xoxp- トークンを export してから再実行してください。"
        )
    log(f"Phase 2: Slack #inquiries 突合 ({len(candidates)} 名)")
    for i, c in enumerate(candidates):
        if not c.get("name"):
            c["slack_error"] = "氏名が空欄"
            continue
        try:
            c["slack_hits"] = slack_search(c["name"], count=3)
            log(f"  [{i+1}/{len(candidates)}] {c['name']}: Slack {len(c['slack_hits'])} 件")
        except Exception as e:
            c["slack_error"] = str(e)
            log(f"  [{i+1}/{len(candidates)}] {c['name']}: Slack検索失敗 {e}")

    # Phase 3: FreelanceBase 突合（ステータス + メモ）
    if args.skip_fb:
        log("Phase 3: FB突合をスキップ (--skip-fb)")
        for c in candidates:
            c["fb_error"] = "FB突合をスキップ (--skip-fb)"
    else:
        log("Phase 3: FreelanceBase 突合")
        with sync_playwright() as pw:
            try:
                fb_browser, fb_context, fb_page = fb.login(pw, headless=args.headless)
            except Exception as e:
                log(f"FB ログイン失敗: {e}")
                for c in candidates:
                    c["fb_error"] = f"FBログイン失敗: {e}"
                fb_browser = None
            if fb_browser:
                try:
                    auth, payload = fb_capture_auth(fb_page)
                    # 3a: 氏名検索 + ステータス確認
                    for i, c in enumerate(candidates):
                        if not c.get("name"):
                            c["fb_error"] = "氏名が空欄"
                            continue
                        try:
                            fb_results = fb_search_by_name(fb_page, auth, payload, c["name"])
                            matches = fb_filter_name_matches(fb_results, c["name"])
                            # 生データはJSONサイズ削減のため debug にのみ保存
                            for m in matches:
                                raw = m.pop("raw", None)
                                if raw is not None:
                                    debug_path = DEBUG_DIR / f"fb_raw_{c['name'].replace(' ','')}_{m.get('id_by_enterprise_id')}.json"
                                    debug_path.write_text(
                                        json.dumps(raw, ensure_ascii=False, indent=2),
                                        encoding="utf-8",
                                    )
                            c["fb_matches"] = matches
                            c["fb_unsellable"] = [
                                m for m in matches
                                if m.get("sales_status_id") in FB_NON_OK_STATUS_IDS
                            ]
                            log(
                                f"  [{i+1}/{len(candidates)}] {c['name']}: "
                                f"FB一致 {len(matches)} 件 (非OK {len(c['fb_unsellable'])} 件)"
                            )
                        except Exception as e:
                            c["fb_error"] = str(e)
                            log(f"  [{i+1}/{len(candidates)}] {c['name']}: FB検索失敗 {e}")

                    # 3b: メモ（コメントタブ）取得 — FB一致があった候補者のみ
                    memo_page = fb_context.new_page()
                    for i, c in enumerate(candidates):
                        matches = c.get("fb_matches") or []
                        if not matches:
                            c["fb_memos"] = []
                            continue
                        all_memos: list[dict[str, Any]] = []
                        for m in matches:
                            fid = m.get("id_by_enterprise_id")
                            try:
                                memos = fb_fetch_memos(memo_page, fid)
                                all_memos.extend(memos)
                            except Exception as e:
                                log(f"  {c['name']} (FB id={fid}): メモ取得失敗 {e}")
                        c["fb_memos"] = all_memos
                        log(f"  [{i+1}/{len(candidates)}] {c['name']}: FBメモ {len(all_memos)} 件")
                    memo_page.close()
                except Exception as e:
                    log(f"FB 突合エラー: {e}")
                    for c in candidates:
                        if c.get("fb_matches") is None and not c.get("fb_error"):
                            c["fb_error"] = f"FB突合エラー: {e}"
                finally:
                    fb_browser.close()

    # Phase 4: 判定
    log("Phase 4: 判定")
    for c in candidates:
        c["judgment"] = judge_candidate(c)

    # Phase 5: レポート出力（返却CSVプレビュー込み）
    log("Phase 5: レポート出力")

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    result = {
        "month": month,
        "start_date": start_date,
        "end_date": end_date,
        "csv_path": str(csv_path),
        "fetched_at": datetime.now().isoformat(),
        "count": len(candidates),
        "candidates": candidates,
    }
    json_path = out_dir / f"{month}_freelanceboard_candidates_{ts}.json"
    json_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    # state にも保存（再実行時の参照用）
    (STATE_DIR / f"run_{ts}.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    log(f"JSON保存: {json_path}")

    md = render_report(month, candidates)
    md_path = out_dir / f"{month}_フリーランスボード請求チェック.md"
    md_path.write_text(md, encoding="utf-8")
    html = render_report_html(month, candidates)
    html_path = out_dir / f"{month}_フリーランスボード請求チェック.html"
    html_path.write_text(html, encoding="utf-8")
    log(f"レポート: {md_path}")
    log(f"HTML: {html_path}")

    # 概要表示
    cats: dict[str, int] = {}
    for c in candidates:
        cat = c.get("judgment", {}).get("category", "?")
        cats[cat] = cats.get(cat, 0) + 1
    print("\n=== 完了 ===")
    print(f"対象期間: {start_date} 〜 {end_date}")
    print(f"候補者数: {len(candidates)}")
    for k in ["請求対象外候補", "要判断", "請求対象"]:
        print(f"  {k}: {cats.get(k, 0)}")
    print(f"JSON: {json_path}")
    print(f"レポート: {md_path}")
    print(f"HTML: {html_path}")
    print()
    print("次のステップ:")
    print("  レポートをレビューし、要判断の候補者の承認/非承認を決めた上で返却CSVを生成:")
    print(f"  /usr/bin/python3 {Path(__file__).resolve()} --make-csv --report {json_path} \\")
    print(f"    [--overrides /path/to/overrides.json] --output-dir {out_dir}")
    return 0


def run_make_csv(args) -> int:
    """Phase 6: 返却CSV生成."""
    report_path = Path(args.report)
    if not report_path.exists():
        log(f"実行結果JSONが見つかりません: {report_path}")
        return 1
    overrides_path = Path(args.overrides) if args.overrides else None
    if overrides_path and not overrides_path.exists():
        log(f"overrides JSONが見つかりません: {overrides_path}")
        return 1
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        out_path = make_return_csv(report_path, overrides_path, out_dir)
    except (ValueError, FileNotFoundError) as e:
        log(f"返却CSV生成エラー: {e}")
        return 1

    # 生成結果のサマリ表示
    with out_path.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    n_approve = sum(1 for r in rows if r.get("承認ステータス") == "承認")
    n_reject = sum(1 for r in rows if r.get("承認ステータス") == "非承認")
    print("\n=== 返却CSV生成完了 ===")
    print(f"出力: {out_path}")
    print(f"行数: {len(rows)}（承認 {n_approve} / 非承認 {n_reject}）")
    print("\n非承認の内訳:")
    seen_names = set()
    for r in rows:
        if r.get("承認ステータス") == "非承認" and r.get("氏名") not in seen_names:
            seen_names.add(r.get("氏名"))
            print(f"  {r.get('氏名')}: {r.get('承認備考')}")
    print("\nこのCSVをユーザー自身が運営に返送してください。")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", help="フリーランスボードの応募者CSVパス（Phase 1-5 実行時に必須）")
    ap.add_argument("--output-dir", required=True, help="出力ディレクトリ")
    ap.add_argument(
        "--month",
        help="対象年月 (例: 2026-05)。省略時はCSVファイル名から自動抽出",
    )
    ap.add_argument("--skip-fb", action="store_true", help="FB突合をスキップ（テスト用。本番では使わない）")
    ap.add_argument("--no-headless", action="store_true", help="ブラウザを表示する")
    ap.add_argument("--make-csv", action="store_true", help="Phase 6: 返却CSVを生成する")
    ap.add_argument("--report", help="Phase 6 で読む実行結果JSONのパス")
    ap.add_argument(
        "--overrides",
        help='Phase 6 の要判断解決用JSON。形式: {"氏名": {"status": "承認"|"非承認", "reason": "非承認理由"}}',
    )
    args = ap.parse_args()
    args.headless = not args.no_headless

    if args.make_csv:
        if not args.report:
            log("--make-csv には --report が必要です")
            return 1
        return run_make_csv(args)

    if not args.csv:
        log("Phase 1-5 実行には --csv が必要です")
        return 1
    return run(args)


if __name__ == "__main__":
    sys.exit(main())
