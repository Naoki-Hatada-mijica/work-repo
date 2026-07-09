"""freelancehub-billing-check: フリーランスHub 月次課金対象チェック

実行モード:
  python3 scripts/run.py --month 2026-04 --output-dir /path/to/output
    Phase 1〜5: 取得 → 詳細 → 突合（Slack/FB） → 判定 → レポート出力

  python3 scripts/run.py --apply-reject --report /path/to/report.json
    Phase 6 段階A: 非承認候補を一括で非承認にする

  python3 scripts/run.py --apply-approve --report /path/to/report.json
    Phase 6 段階B: 承認推奨を一括承認する
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from calendar import monthrange
from datetime import datetime
from pathlib import Path
from typing import Any

# 既存スニペット
sys.path.insert(0, __import__("os").path.expanduser("~/.claude/snippets"))
import playwright_freelancehub as fh  # noqa: E402  type: ignore
import playwright_freelancebase as fb  # noqa: E402  type: ignore
from freelancebase.candidates import (  # noqa: E402
    capture_candidate_index_template,
    search_candidates,
)

from playwright.sync_api import Page, sync_playwright  # noqa: E402

SKILL_DIR = Path(__file__).resolve().parent.parent
STATE_DIR = SKILL_DIR / "state"
DEBUG_DIR = STATE_DIR / "debug"
SESSION_PATH = STATE_DIR / "session.json"


def log(msg: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", file=sys.stderr)


def parse_month(s: str) -> tuple[str, str]:
    """'2026-04' または '2026年4月' を ('2026-04-01', '2026-04-30') に変換"""
    m = re.match(r"^(\d{4})[-年/](\d{1,2})月?$", s.strip())
    if not m:
        raise ValueError(f"--month の形式が不正: {s!r} (例: 2026-04)")
    year, month = int(m.group(1)), int(m.group(2))
    last_day = monthrange(year, month)[1]
    return f"{year:04d}-{month:02d}-01", f"{year:04d}-{month:02d}-{last_day:02d}"


def fetch_unapproved_list(page: Page, start_date: str, end_date: str, approval_status: int = 1) -> list[dict[str, Any]]:
    """応募者一覧から未承認の候補者をすべて取得する.

    各行: 氏名 / かな / 年齢 / メール / 電話 / 在住地域 / 稼働日数 /
          応募日時 / 案件名 / 詳細URL / 行内のステータス
    """
    url = (
        "https://agent.freelance-hub.jp/entry"
        f"?start_date={start_date}&end_date={end_date}&approval_status={approval_status}"
    )
    log(f"応募者一覧へアクセス: {url}")
    page.goto(url, wait_until="networkidle")
    page.wait_for_timeout(3500)

    # 件数表示の取得（"1 - 33 件 / 全33件"）
    total = None
    try:
        body_text = page.content()
        m = re.search(r"全\s*(\d+)\s*件", body_text)
        if m:
            total = int(m.group(1))
            log(f"総件数: {total} 件")
    except Exception:
        pass

    # 行を全件取得（ページネーション対応）。各ページで行クリック→ドロワー→detail URL 取得まで実施
    all_rows: list[dict[str, Any]] = []
    page_num = 1
    while True:
        page.wait_for_selector("table tbody tr", timeout=10000)
        page.wait_for_timeout(500)
        rows = page.evaluate(
            """() => {
                const trs = Array.from(document.querySelectorAll('table tbody tr'));
                return trs.map(tr => {
                    const tds = Array.from(tr.querySelectorAll('td'));
                    const links = Array.from(tr.querySelectorAll('a')).map(a => a.href);
                    return {
                        cells: tds.map(td => td.innerText.trim()),
                        rowLinks: links,
                    };
                });
            }"""
        )
        log(f"  page {page_num}: {len(rows)} 行")

        # このページ内で各行クリック→ drawer 表示を待ってから detail URL を取得
        row_locator = page.locator("table tbody tr")
        for idx, row in enumerate(rows):
            row["detailHref"] = None
            row["_page_num"] = page_num
            row["_row_idx"] = idx
            for attempt in range(3):
                try:
                    # 行中央には案件リンクがある場合があり、その場合はドロワーが開かない。
                    # 候補者名セルをクリックして詳細ドロワーを確実に開く。
                    row_locator.nth(idx).locator("td").nth(0).click()
                    # ドロワー内の detail link が現れるまで待つ
                    page.wait_for_selector(
                        'a[href*="/entry/detail/"]',
                        timeout=5000 + attempt * 2000,
                        state="attached",
                    )
                    href = page.evaluate(
                        "() => { const a = document.querySelector('a[href*=\"/entry/detail/\"]'); return a ? a.getAttribute('href') : null; }"
                    )
                    if href:
                        row["detailHref"] = href
                    # ドロワーを閉じる: detail link が消えるまで待つ
                    page.keyboard.press("Escape")
                    try:
                        page.wait_for_selector(
                            'a[href*="/entry/detail/"]', state="detached", timeout=3000
                        )
                    except Exception:
                        page.wait_for_timeout(500)
                    if href:
                        break
                except Exception as e:
                    log(f"  page {page_num} row {idx} attempt{attempt}: {e}")
                    page.keyboard.press("Escape")
                    page.wait_for_timeout(1000)

        all_rows.extend(rows)

        if total is not None and len(all_rows) >= total:
            log(f"  全件取得完了 ({len(all_rows)}/{total})")
            break

        # 次ページボタン
        try:
            next_buttons = page.locator("button.MuiPaginationItem-previousNext").all()
            clicked = False
            for btn in next_buttons:
                cls = btn.evaluate("el => el.className")
                if "Mui-disabled" in cls:
                    continue
                aria = btn.get_attribute("aria-label") or ""
                if "next" in aria.lower():
                    btn.click()
                    page.wait_for_timeout(3000)
                    clicked = True
                    page_num += 1
                    break
            if not clicked:
                break
        except Exception as e:
            log(f"  next page error: {e}")
            break

    log(f"行データ取得完了: {len(all_rows)} 行")

    # 失敗行をページごとに再取得（B案）
    failed = [r for r in all_rows if not r.get("detailHref")]
    if failed:
        log(f"再取得対象: {len(failed)} 件")
        # ページ番号ごとにグループ化
        from collections import defaultdict
        by_page: dict[int, list[dict[str, Any]]] = defaultdict(list)
        for r in failed:
            by_page[r["_page_num"]].append(r)

        for target_page in sorted(by_page.keys()):
            log(f"  page {target_page} に戻って {len(by_page[target_page])} 件を再取得")
            # ページ番号ボタンをクリック
            try:
                page.locator(f"button.MuiPaginationItem-root").filter(has_text=str(target_page)).first.click()
                page.wait_for_timeout(2500)
                page.wait_for_selector("table tbody tr", timeout=10000)
            except Exception as e:
                log(f"  page切替エラー: {e}")
                continue

            row_locator = page.locator("table tbody tr")
            for r in by_page[target_page]:
                idx = r["_row_idx"]
                for attempt in range(2):
                    try:
                        row_locator.nth(idx).locator("td").nth(0).click()
                        page.wait_for_timeout(1500 + attempt * 500)
                        href = page.evaluate(
                            "() => { const a = document.querySelector('a[href*=\"/entry/detail/\"]'); return a ? a.getAttribute('href') : null; }"
                        )
                        page.keyboard.press("Escape")
                        page.wait_for_timeout(500)
                        if href:
                            r["detailHref"] = href
                            break
                    except Exception as e:
                        log(f"  retry page{target_page} row{idx} attempt{attempt}: {e}")
                        page.keyboard.press("Escape")
                        page.wait_for_timeout(1000)

        still_failed = sum(1 for r in all_rows if not r.get("detailHref"))
        log(f"再取得後: 未取得={still_failed}件 / 全{len(all_rows)}件")

    # 内部用フィールドを削除
    for r in all_rows:
        r.pop("_page_num", None)
        r.pop("_row_idx", None)

    return all_rows


def parse_row(raw: dict[str, Any]) -> dict[str, Any]:
    """生の行データを構造化する.

    cells:
      [0] 氏名 (漢字\\nかな\\n(年齢))
      [1] 応募者情報 (メール\\n電話\\n在住地域\\n稼働日数)
      [2] 応募日時
      [3] 応募内容 (案件名 (元ページ)\\n（N回目）)
      [4] 承認ステータス (例: 未確認\\n変更)
      [5] 対応ステータス
      [6] 対応メモ
    """
    cells = raw.get("cells", [])

    def cell(i: int) -> str:
        return cells[i] if i < len(cells) else ""

    # 氏名セル — 一部の候補者は「スカウト回数: N回」プレフィックスが入る
    name_cell = cell(0)
    raw_lines = [l.strip() for l in name_cell.split("\n") if l.strip()]
    scout_count = None
    name_lines: list[str] = []
    for line in raw_lines:
        m = re.match(r"スカウト回数:\s*(\d+)回", line)
        if m:
            scout_count = int(m.group(1))
            continue
        if re.match(r"^\(\d+歳\)$", line):
            continue
        name_lines.append(line)
    name = name_lines[0] if name_lines else ""
    name_kana = name_lines[1] if len(name_lines) >= 2 else ""
    age_match = re.search(r"\((\d+)歳\)", name_cell)
    age = int(age_match.group(1)) if age_match else None

    # 応募者情報セル
    info_cell = cell(1)
    info_lines = [l.strip() for l in info_cell.split("\n") if l.strip()]
    email = next((l for l in info_lines if "@" in l), "")
    tel = next((l for l in info_lines if re.match(r"^\d{8,15}$", l)), "")
    prefecture = ""
    capacity = ""
    for line in info_lines:
        if line in (email, tel):
            continue
        if "週" in line and "日" in line:
            capacity = line
        elif not prefecture and ("都" in line or "道" in line or "府" in line or "県" in line or len(line) <= 6):
            prefecture = line

    # 応募内容
    content_cell = cell(3)
    project_match = re.match(r"^(.*?)\(元ページ\)", content_cell, re.S)
    project_title = (project_match.group(1).strip() if project_match else content_cell.split("\n")[0]).strip()
    apply_count_match = re.search(r"（(\d+)回目）", content_cell)
    apply_count = int(apply_count_match.group(1)) if apply_count_match else None

    # 元ページリンク
    project_url = ""
    for link in raw.get("rowLinks", []):
        if "freelance-hub.jp/project" in link or "mijica-job.com" in link:
            project_url = link
            break

    # 詳細URL（行クリックで取得済み）
    detail_href = raw.get("detailHref")
    detail_url = "https://agent.freelance-hub.jp" + detail_href if detail_href else None

    return {
        "detail_url": detail_url,
        "name": name,
        "name_kana": name_kana,
        "age": age,
        "scout_count": scout_count,
        "email": email,
        "tel": tel,
        "prefecture": prefecture,
        "capacity": capacity,
        "applied_at": cell(2),
        "project_title": project_title,
        "project_url": project_url,
        "apply_count": apply_count,
        "approval_status_cell": cell(4),
        "response_status_cell": cell(5),
        "response_memo": cell(6),
    }


# ========== Phase 3: Slack 検索 ==========

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

    フリーランスHub氏名は「姓 名」(全角/半角スペース区切り) で来るが、Slack上の
    表記は揺らぐ:
      - 「姓 名」(スペース込みフルネーム)
      - 「姓名」(スペース無しフルネーム)
      - 「姓さん」「姓のみ」など姓だけの言及
    そのため複数クエリで OR 検索し、姓のみクエリ分は本文に姓 or 名が含まれる
    メッセージに限定して同姓別人を弾く。重複は ts+permalink で除去。
    """
    if not os.environ.get("SLACK_USER_TOKEN"):
        return []

    parts = [p for p in re.split(r"[\s　]+", query.strip()) if p]
    surname = parts[0] if parts else query.strip()
    given = parts[1] if len(parts) >= 2 else ""
    full_with_space = query.strip()
    full_no_space = "".join(parts) if parts else query.strip()

    queries: list[tuple[str, bool]] = []  # (query, requires_body_filter)
    # 1) フルネーム (スペース込み) — 完全一致狙い
    queries.append((f'"{full_with_space}" in:#{INQUIRIES_CHANNEL_NAME}', False))
    # 2) フルネーム (スペース無し)
    if full_no_space and full_no_space != full_with_space:
        queries.append((f'"{full_no_space}" in:#{INQUIRIES_CHANNEL_NAME}', False))
    # 3) 姓のみ — 同姓別人混入リスクがあるので本文フィルタを掛ける
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
            # thread_ts があれば後でスレッド全体を取得
            thread_ts = m.get("thread_ts") or m.get("ts")
            if channel_id and thread_ts:
                threads_to_fetch.add((channel_id, str(thread_ts)))

    # スレッド本体＋全リプライを取得
    for channel_id, thread_ts in threads_to_fetch:
        replies = _slack_fetch_thread(channel_id, thread_ts)
        for r_msg in replies:
            _add_hit(r_msg, channel_id, None)

    return out


# ========== Phase 3: FreelanceBase 突合 ==========


def fb_capture_auth(fb_page: Page) -> tuple[dict[str, str], dict[str, Any]]:
    """FreelanceBase /api/enterprise/candidates/index の認証ヘッダ＋ペイロードを捕捉する."""
    return capture_candidate_index_template(fb_page)


def fb_search_by_name(
    fb_page: Page, auth: dict[str, str], payload: dict[str, Any], full_name: str
) -> list[dict[str, Any]]:
    """FreelanceBase で氏名検索し、候補者リストを返す."""
    return search_candidates(fb_page, full_name, auth=auth, payload=payload)


# FB 営業ステータス: 1=営業中(OK) / 2=営業終了 / 3=営業不可 / 4=取引停止
# 1以外は非OKとみなし、突合ヒット対象に含める。
FB_NON_OK_STATUS_IDS = {2, 3, 4}
FB_STATUS_LABEL = {1: "営業中", 2: "営業終了", 3: "営業不可", 4: "取引停止"}


def fb_find_unsellable_match(
    candidates_in_fb: list[dict[str, Any]], target_name: str
) -> list[dict[str, Any]]:
    """FB 候補者リストから「非OKステータス (営業終了/営業不可/取引停止)」かつ氏名一致するものを返す."""
    target_no_space = target_name.replace(" ", "").replace("　", "")
    out = []
    for c in candidates_in_fb:
        name = (c.get("name") or "").replace(" ", "").replace("　", "")
        supplier = (c.get("supplier_name") or "").replace(" ", "").replace("　", "")
        if name == target_no_space or supplier == target_no_space:
            status_id = c.get("sales_status_id")
            if status_id in FB_NON_OK_STATUS_IDS:
                out.append(
                    {
                        "id_by_enterprise_id": c.get("id_by_enterprise_id"),
                        "name": c.get("name"),
                        "name_for_company": c.get("name_for_company"),
                        "sales_status_id": status_id,
                        "sales_status_label": FB_STATUS_LABEL.get(status_id, f"id={status_id}"),
                    }
                )
    return out


def fetch_detail(page: Page, detail_url: str) -> dict[str, Any]:
    """detail_url を開いて基本情報・スキルシート情報を辞書で返す."""
    page.goto(detail_url, wait_until="networkidle")
    page.wait_for_timeout(1500)

    info: dict[str, Any] = {"detail_url": detail_url}

    # 「承認 / 応募ステータス」タブの基本情報
    try:
        page.get_by_role("tab", name=re.compile(r"承認.*ステータス")).click()
        page.wait_for_timeout(800)
    except Exception:
        pass

    # 「職務経歴書 / スキルシート」タブで取得（基本情報も同タブから読める）
    try:
        page.get_by_role("tab", name=re.compile(r"職務経歴書|スキルシート")).click()
        page.wait_for_timeout(1000)
    except Exception:
        pass

    # MUI Box (css-j0ozid) パターン: <div><p body2>{label}</p><p body1>{value}</p></div>
    # 各ラベルと値のペアを抽出
    pairs = page.evaluate(
        """() => {
            const out = {};
            // ラベル/値のペア構造: 内側の<p>が2つある<div>
            const boxes = document.querySelectorAll('div');
            boxes.forEach(box => {
                const ps = box.querySelectorAll(':scope > p');
                if (ps.length === 2) {
                    const label = ps[0].innerText.trim();
                    const value = ps[1].innerText.trim();
                    // label が短く、典型的なラベルパターンに合致するもののみ
                    if (label && label.length <= 12 && value !== undefined) {
                        out[label] = value;
                    }
                }
            });
            return out;
        }"""
    )
    info["pairs"] = pairs

    # 主要フィールド
    info["birthday"] = pairs.get("生年月日", "")
    info["residence_area"] = pairs.get("お住まいの地域", "")
    info["nearest_station"] = pairs.get("最寄り駅", "")
    info["working_status"] = pairs.get("現在の状況", "")
    info["contract_type"] = pairs.get("契約形態", "")
    info["occupation"] = pairs.get("職業", "")
    info["job_type"] = pairs.get("職種", "")
    info["start_timing"] = pairs.get("稼働開始時期", "")
    info["desired_price"] = pairs.get("希望単価", "")
    info["work_days"] = pairs.get("作業可能日数", "")
    info["work_location"] = pairs.get("作業場所の条件", "")

    # 自己PR / スキルシート系: ラベル文字列を含む要素を探し、その全テキストから値を抽出
    pr_data = page.evaluate(
        """() => {
            const result = {self_pr: '', urls: []};
            // 自己PR: 直接子の textNode で "自己PR :" を持ち、ネストされた div に値が入る
            document.querySelectorAll('div, p').forEach(el => {
                const own = el.firstChild && el.firstChild.nodeType === 3 ? (el.firstChild.textContent || '').trim() : '';
                if (own === '自己PR :' || own === '自己PR :' || own.startsWith('自己PR')) {
                    // 子div の innerText
                    const child = el.querySelector('div, p, span');
                    if (child) {
                        result.self_pr = (child.innerText || '').trim();
                    } else {
                        // own から自己PR :を除いた残り
                        result.self_pr = (el.innerText || '').replace(/^自己PR\\s*[:：]\\s*/, '').trim();
                    }
                }
            });
            // スキルシート/ポートフォリオ/GitHub: <p>GitHub : <a>...</a></p> パターン
            document.querySelectorAll('p').forEach(el => {
                const txt = (el.innerText || '').trim();
                const m = txt.match(/^(スキルシート\\d|ポートフォリオ\\d|GitHub)\\s*[:：]\\s*(https?:\\/\\/.+)$/);
                if (m) {
                    result.urls.push({label: m[1], url: m[2]});
                }
            });
            return result;
        }"""
    )
    info["self_pr"] = (pr_data.get("self_pr") or "")[:2000]
    info["skillsheet_urls"] = pr_data.get("urls", [])

    # 国籍は日本語UI上には現れないことが多い → 名前から推測する別ロジックで補完予定
    return info


# ========== Phase 4: 判定ロジック ==========

# システム上の非承認理由8項目（チェックボックスのラベル / 完全一致でチェック付与）
# 表示順: 在住地域 / 年齢(高) / 経験不足 / 稼働日数不足 / 経歴詐称 / ヒューマンNG / 日本語能力不足 / その他
SYS_REASON_RESIDENCE = "在住地域"
SYS_REASON_AGE_HIGH = "年齢(高)"
SYS_REASON_EXPERIENCE = "経験不足"
SYS_REASON_WORKDAYS = "稼働日数不足"
SYS_REASON_FAKE_HISTORY = "経歴詐称"
SYS_REASON_HUMAN_NG = "ヒューマンNG"
SYS_REASON_LANG = "日本語能力不足"
SYS_REASON_OTHER = "その他"


def detect_overseas(cand: dict[str, Any]) -> tuple[bool, str]:
    """海外在住判定. (該当, 根拠)"""
    pref = cand.get("prefecture", "")
    detail = cand.get("detail", {}) or {}
    residence = detail.get("residence_area", "") or pref
    overseas_keywords = [
        "海外", "アメリカ", "USA", "中国", "上海", "北京", "韓国", "ソウル",
        "シンガポール", "タイ", "バンコク", "フィリピン", "マニラ", "インドネシア",
        "ベトナム", "ハノイ", "インド", "デリー", "ドイツ", "フランス", "イギリス",
        "カナダ", "オーストラリア", "ブラジル",
    ]
    for kw in overseas_keywords:
        if kw in residence:
            return True, f"在住='{residence}' に '{kw}' を含む"
    # 都道府県でない場合は要注意
    if residence and not any(
        suffix in residence for suffix in ["都", "道", "府", "県"]
    ):
        return True, f"在住='{residence}' が日本の都道府県でない"
    return False, ""


def detect_age_high(cand: dict[str, Any]) -> tuple[bool, str]:
    age = cand.get("age")
    if isinstance(age, int) and age >= 50:
        return True, f"年齢={age}歳 (50歳以上)"
    return False, ""


def detect_workdays_short(cand: dict[str, Any]) -> tuple[bool, str]:
    """稼働日数不足判定. 週1〜2日のみなら明確に該当."""
    cap = cand.get("capacity") or (cand.get("detail") or {}).get("work_days") or ""
    days = re.findall(r"週(\d)日", cap)
    if not days:
        return False, ""
    days_int = sorted({int(d) for d in days})
    if days_int and max(days_int) <= 2:
        return True, f"作業可能日数='{cap}' (週2日以下)"
    return False, ""


def detect_fake_history(cand: dict[str, Any]) -> tuple[bool, str]:
    """経歴詐称の簡易判定。経験スキル・年数の不自然な多さで検出."""
    detail = cand.get("detail", {}) or {}
    pairs = detail.get("pairs", {}) or {}
    self_pr = (detail.get("self_pr") or "")[:1000]
    # MUI ペアから経験スキル等を見るのは難しいので、自己PR の不自然な記述で判定
    # 例: "全言語5年以上" "全領域マスター" 等
    suspicious = [
        "すべての言語", "全言語", "全領域", "全てに精通", "あらゆる",
        "100以上", "全プロジェクト",
    ]
    for kw in suspicious:
        if kw in self_pr:
            return True, f"自己PR に '{kw}' を含む"
    return False, ""


def detect_human_ng(cand: dict[str, Any]) -> tuple[bool, str]:
    """ヒューマンNG: Slack 履歴に明確な NG 表現がある場合のみ.

    「見送り / お見送り」単独では非承認にしない（お見送り理由が対象外要件に
    該当した場合のみ、他検出器=経験不足/過去流入/海外/正社員等が拾う）。
    ここではお見送り理由を問わず確実に対象外とすべき強い表現のみを対象とする。
    """
    slack = cand.get("slack_hits", []) or []
    ng_keywords = [
        "クレーム", "対応NG", "ブラックリスト", "NG人材", "N人材", "対応不可",
        "NGにしておきます",
    ]
    for hit in slack:
        text = hit.get("text", "")
        for kw in ng_keywords:
            if kw in text:
                return True, f"Slack履歴に '{kw}' を含む発言"
    return False, ""


def detect_past_inflow(cand: dict[str, Any]) -> tuple[bool, str]:
    """過去流入: 応募日より 14 日以上前の Slack #inquiries メッセージあり.

    FB営業不可ヒットの有無に関わらず、過去にも応募履歴があったと推定できる場合は
    非承認候補に格上げする。
    """
    applied_dt = _parse_applied_at(cand.get("applied_at", ""))
    slack = cand.get("slack_hits") or []
    if not applied_dt or not slack:
        return False, ""
    for hit in slack:
        ts = hit.get("ts")
        if not ts:
            continue
        try:
            hit_dt = datetime.fromtimestamp(float(ts))
        except (TypeError, ValueError):
            continue
        if (applied_dt - hit_dt).days >= 14:
            return True, f"応募日 {applied_dt.date()} より前の Slack 履歴あり ({hit_dt.date()})"
    return False, ""


def detect_experience_low_slack(cand: dict[str, Any]) -> tuple[bool, str]:
    """経験不足: Slack #inquiries で経験浅さに言及されている場合のみ判定.

    Hub 管理画面の「経験年数」欄は未登録のまま応募する人が多いため、自動判定の
    根拠にはしない。代わりに Slack で Hatada さん等が経験不足を指摘していた場合
    のみ非承認候補に格上げする。
    """
    slack = cand.get("slack_hits", []) or []
    keywords = [
        "未経験", "ほぼ未経験", "経験浅", "経験不足", "経験が浅",
        "ジュニア", "新人", "経験少な", "経験が少な",
    ]
    # 「経験1年」「経験半年」「経験〇ヶ月」等のパターン
    short_year_re = re.compile(r"経験[が＝=:：\s]*(?:0|半|1|２|2)[年ヶ月]")
    for hit in slack:
        text = hit.get("text", "")
        for kw in keywords:
            if kw in text:
                return True, f"Slack履歴に '{kw}' を含む発言（経験不足言及）"
        m = short_year_re.search(text)
        if m:
            return True, f"Slack履歴に '{m.group(0)}' を含む発言（経験不足言及）"
    return False, ""


def detect_japanese_low(cand: dict[str, Any]) -> tuple[bool, str]:
    """日本語能力不足: 自己PR が英語のみ等."""
    detail = cand.get("detail", {}) or {}
    self_pr = (detail.get("self_pr") or "").strip()
    if not self_pr:
        return False, ""
    # ASCII 比率が高い = 英語
    ascii_chars = sum(1 for c in self_pr if ord(c) < 128)
    ratio = ascii_chars / len(self_pr)
    if ratio > 0.92 and len(self_pr) > 30:
        return True, f"自己PR が英語比率 {ratio:.0%}（日本語ほぼなし）"
    return False, ""


def detect_full_time_employee(cand: dict[str, Any]) -> tuple[bool, str]:
    """正社員判定. 単独では非承認候補にしない（フリーランス転向組がいる）.

    判定対象は以下の複合条件のいずれか:
      - 契約形態=正社員 + 稼働可能日数=週1〜2日（副業推定）
      - 契約形態=正社員 + 在住=海外
    上記に該当しない単純な「正社員」は要判断扱いとし、judge_candidate 側の
    info_gaps に追加して人間判断を仰ぐ。
    """
    detail = cand.get("detail", {}) or {}
    contract = detail.get("contract_type", "")
    if contract != "正社員":
        return False, ""
    # 副業推定: 稼働可能日数が週1〜2日のみ
    cap = (cand.get("capacity") or detail.get("work_days") or "")
    days = re.findall(r"週(\d)日", cap)
    if days and max(int(d) for d in days) <= 2:
        return True, f"契約形態='正社員' + 稼働可能日数='{cap}' (週2日以下=副業推定)"
    return False, ""


def detect_sales_pitch(cand: dict[str, Any]) -> tuple[bool, str]:
    """営業行為: 自己PRで自社製品宣伝/URL誘導/求職以外の文脈."""
    detail = cand.get("detail", {}) or {}
    self_pr = (detail.get("self_pr") or "")[:1000]
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


def _parse_applied_at(s: str):
    """応募日文字列を datetime に。失敗時 None."""
    if not s:
        return None
    for fmt in ("%Y/%m/%d %H:%M", "%Y-%m-%d %H:%M", "%Y/%m/%d", "%Y-%m-%d"):
        try:
            return datetime.strptime(s.strip(), fmt)
        except ValueError:
            continue
    return None


def _fb_summary(fb_hits: list[dict[str, Any]]) -> str:
    """FBヒットを 'ステータス名 (id)' 形式で要約."""
    parts = []
    for c in fb_hits:
        label = c.get("sales_status_label") or "非OK"
        fid = c.get("id_by_enterprise_id")
        parts.append(f"{label} (id: {fid})")
    return ", ".join(parts)


def detect_fb_unsellable(cand: dict[str, Any]) -> tuple[bool, str]:
    """FB 非OKステータス（営業終了/営業不可/取引停止）は単独で非承認決定打にしない。

    今回応募の書類落ち結果としてステータス登録された可能性があるため、
    Slack #inquiries に応募日より 14 日以上前のメッセージ（=過去流入の証跡）
    がある場合のみ「非承認候補」へ格上げする。
    過去流入の証跡が無い／確認できない場合は False を返し、judge_candidate
    側で info_gaps に追加して要判断扱いとする。
    """
    fb = cand.get("fb_unsellable", []) or []
    if not fb:
        return False, ""
    summary = _fb_summary(fb)
    applied_dt = _parse_applied_at(cand.get("applied_at", ""))
    slack = cand.get("slack_hits") or []
    if not applied_dt or not slack:
        return False, ""
    for hit in slack:
        ts = hit.get("ts")
        if not ts:
            continue
        try:
            hit_dt = datetime.fromtimestamp(float(ts))
        except (TypeError, ValueError):
            continue
        if (applied_dt - hit_dt).days >= 14:
            return True, (
                f"FB {summary} + 過去流入Slack履歴 ({hit_dt.date()})"
            )
    return False, ""


def judge_candidate(cand: dict[str, Any]) -> dict[str, Any]:
    """1人の候補者を判定し、判定結果を返す."""
    rules: list[tuple[str, str, callable]] = [
        ("海外在住", SYS_REASON_RESIDENCE, detect_overseas),
        ("50歳以上", SYS_REASON_AGE_HIGH, detect_age_high),
        ("稼働日数不足", SYS_REASON_WORKDAYS, detect_workdays_short),
        ("経歴詐称", SYS_REASON_FAKE_HISTORY, detect_fake_history),
        ("ヒューマンNG", SYS_REASON_HUMAN_NG, detect_human_ng),
        ("経験不足（Slack言及）", SYS_REASON_EXPERIENCE, detect_experience_low_slack),
        ("日本語能力不足", SYS_REASON_LANG, detect_japanese_low),
        ("正社員", SYS_REASON_OTHER, detect_full_time_employee),
        ("営業行為", SYS_REASON_OTHER, detect_sales_pitch),
        # 過去流入のある営業対象外人材は Hub 側指示により「ヒューマンNG」へ寄せる（2026-06 奥山さん回答）
        ("過去流入（Slack）", SYS_REASON_HUMAN_NG, detect_past_inflow),
        ("営業不可（FB）", SYS_REASON_HUMAN_NG, detect_fb_unsellable),
    ]
    matched: list[dict[str, str]] = []
    for internal_name, sys_reason, fn in rules:
        try:
            hit, evidence = fn(cand)
            if hit:
                matched.append(
                    {
                        "internal_reason": internal_name,
                        "system_reason": sys_reason,
                        "evidence": evidence,
                    }
                )
        except Exception as e:
            log(f"  judge error '{internal_name}' for {cand.get('name')}: {e}")

    # 判定根拠用の情報不足チェック
    detail = cand.get("detail", {}) or {}
    info_gaps: list[str] = []
    if not detail.get("contract_type"):
        info_gaps.append("契約形態が空欄")
    if not detail.get("self_pr"):
        info_gaps.append("自己PR が空欄")
    # 正社員単独はフリーランス転向の可能性があるため要判断扱い
    if detail.get("contract_type") == "正社員" and not any(
        m["internal_reason"] == "正社員" for m in matched
    ):
        info_gaps.append("契約形態=正社員（フリーランス転向の可能性あり、要確認）")
    # FB 非OKステータスがヒットしたが過去流入の証跡が確認できない → 要判断
    fb_hits = cand.get("fb_unsellable") or []
    if fb_hits and not any(m["internal_reason"] == "営業不可（FB）" for m in matched):
        info_gaps.append(
            f"FB {_fb_summary(fb_hits)} — 今回応募の書類落ち結果の可能性あり、過去流入の有無を要確認"
        )

    # 分類
    if matched:
        category = "非承認候補"
    elif info_gaps:
        category = "要判断"
    else:
        category = "承認推奨"

    # 承認理由メモ生成（複数理由を統合）
    if matched:
        memo_parts = []
        # 「その他」マッピングは詳しく記述
        for m in matched:
            if m["system_reason"] == SYS_REASON_OTHER:
                memo_parts.append(f"{m['internal_reason']}（{m['evidence']}）")
            else:
                memo_parts.append(m["internal_reason"])
        approval_memo = " / ".join(memo_parts)
    else:
        approval_memo = ""

    # 適用すべきシステム理由のユニーク集合
    sys_reasons = sorted({m["system_reason"] for m in matched})

    return {
        "category": category,
        "matched_reasons": matched,
        "system_reasons": sys_reasons,
        "info_gaps": info_gaps,
        "approval_memo": approval_memo,
    }


# ========== Phase 5: レポート生成 ==========


def render_report(month: str, candidates: list[dict[str, Any]]) -> str:
    """Markdown レポートを生成する."""
    by_cat: dict[str, list[dict[str, Any]]] = {
        "非承認候補": [],
        "要判断": [],
        "承認推奨": [],
    }
    for c in candidates:
        j = c.get("judgment") or {}
        by_cat.setdefault(j.get("category", "要判断"), []).append(c)

    lines: list[str] = []
    lines.append(f"# フリーランスHub 課金対象チェック - {month}")
    lines.append("")
    lines.append(f"- 取得件数: {len(candidates)}")
    lines.append(
        f"- 判定内訳: 非承認候補 {len(by_cat['非承認候補'])} / "
        f"要判断 {len(by_cat['要判断'])} / 承認推奨 {len(by_cat['承認推奨'])}"
    )
    lines.append("")

    def render_slack_history(c: dict[str, Any]) -> list[str]:
        """Slack #inquiries の過去会話を、ニュアンスを保ったまま全件レンダリング。"""
        slack = c.get("slack_hits") or []
        if not slack:
            return []
        out: list[str] = ["- Slack #inquiries 履歴:"]
        # 古い順で並べる（過去経緯が頭に来るように）
        sorted_hits = sorted(
            slack,
            key=lambda h: (float(h.get("thread_ts") or h.get("ts") or 0), float(h.get("ts") or 0)),
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
            lines_inner = [ln for ln in text.split("\n") if ln.strip()]
            head = lines_inner[0] if lines_inner else ""
            prefix = "    ↳ " if s.get("is_reply") else "  - "
            indent = "      " if s.get("is_reply") else "    "
            link_part = f"  <{permalink}>" if permalink else ""
            out.append(f"{prefix}[{date_str}] {head}{link_part}")
            for ln in lines_inner[1:]:
                out.append(f"{indent}{ln}")
        return out

    def render_candidate(c: dict[str, Any], category: str) -> list[str]:
        out: list[str] = []
        name = c.get("name", "")
        age = c.get("age", "?")
        out.append(f"### {name} ({age}歳)")
        url = c.get("detail_url") or "(URL未取得)"
        out.append(f"- 詳細URL: {url}")
        out.append(
            f"- 在住: {c.get('prefecture','-')} / 稼働: {c.get('capacity','-')} / "
            f"スカウト経験: {c.get('scout_count') or '無'}"
        )
        d = c.get("detail") or {}
        if d.get("contract_type"):
            out.append(f"- 契約形態: {d['contract_type']}")
        j = c.get("judgment") or {}
        if category == "非承認候補":
            out.append(f"- システム非承認理由（複数可）: {', '.join(j.get('system_reasons', []))}")
            out.append(f"- 内部判定理由: {', '.join(r['internal_reason'] for r in j.get('matched_reasons', []))}")
            out.append("- 判定根拠:")
            for r in j.get("matched_reasons", []):
                out.append(f"  - {r['internal_reason']}: {r['evidence']}")
            out.append(f"- 承認理由メモ案: {j.get('approval_memo','')}")
        elif category == "要判断":
            if j.get("info_gaps"):
                out.append(f"- 情報不足: {', '.join(j['info_gaps'])}")
        # Slack 履歴は3カテゴリ共通で全件表示（過去経緯のニュアンスを保持）
        out.extend(render_slack_history(c))
        if d.get("self_pr"):
            pr = d["self_pr"][:200].replace("\n", " ")
            out.append(f"- 自己PR抜粋: {pr}")
        return out

    for cat in ["非承認候補", "要判断", "承認推奨"]:
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
    return "\n".join(lines)


# ========== Phase 5: HTML レポート ==========


def _h(s: str) -> str:
    """HTMLエスケープ。"""
    import html as _html
    return _html.escape(s or "", quote=True)


_URL_RE = re.compile(r"https?://[^\s<>]+")


def _autolink(text: str) -> str:
    """URLを <a> に置換しつつ周辺文字はエスケープ。"""
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
    """Markdown レポートと同等内容を HTML で生成する。

    - 詳細URL / Slack permalink / Hub URL をクリック可能リンクに
    - Slack履歴と自己PRは <details> で折りたたみ
    - カテゴリごとに色分けバッジ
    """
    by_cat: dict[str, list[dict[str, Any]]] = {
        "非承認候補": [],
        "要判断": [],
        "承認推奨": [],
    }
    for c in candidates:
        j = c.get("judgment") or {}
        by_cat.setdefault(j.get("category", "要判断"), []).append(c)

    cat_color = {
        "非承認候補": "#d93025",
        "要判断": "#f29900",
        "承認推奨": "#188038",
    }

    def render_slack(c: dict[str, Any]) -> str:
        slack = c.get("slack_hits") or []
        if not slack:
            return ""
        sorted_hits = sorted(
            slack,
            key=lambda h: (float(h.get("thread_ts") or h.get("ts") or 0), float(h.get("ts") or 0)),
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
                f'<div class="slack-body">{body_html}</div></li>'
            )
        return (
            f'<details class="slack-history" open><summary>Slack #inquiries 履歴 ({len(slack)}件)</summary>'
            f'<ul>{"".join(items_html)}</ul></details>'
        )

    def render_candidate(c: dict[str, Any], category: str) -> str:
        d = c.get("detail") or {}
        j = c.get("judgment") or {}
        name = c.get("name", "")
        age = c.get("age", "?")
        url = c.get("detail_url") or ""
        out: list[str] = [f'<div class="card">']
        out.append(f'<h3>{_h(name)} <span class="age">({_h(str(age))}歳)</span></h3>')
        if url:
            out.append(
                f'<p class="meta"><a class="detail-link" href="{_h(url)}" target="_blank" rel="noopener">Hub 詳細を開く ↗</a></p>'
            )
        out.append(
            f'<p class="meta">在住: {_h(c.get("prefecture","-"))} / 稼働: {_h(c.get("capacity","-"))} / '
            f'スカウト経験: {_h(str(c.get("scout_count") or "無"))}'
            + (f' / 契約形態: <strong>{_h(d.get("contract_type",""))}</strong>' if d.get("contract_type") else "")
            + "</p>"
        )
        if category == "非承認候補":
            sysr = ", ".join(j.get("system_reasons", []))
            intr = ", ".join(r["internal_reason"] for r in j.get("matched_reasons", []))
            out.append(
                f'<p class="meta"><strong>システム非承認理由:</strong> {_h(sysr)}<br>'
                f'<strong>内部判定理由:</strong> {_h(intr)}</p>'
            )
            out.append('<ul class="evidence">')
            for r in j.get("matched_reasons", []):
                out.append(f'<li><strong>{_h(r["internal_reason"])}:</strong> {_h(r["evidence"])}</li>')
            out.append("</ul>")
            out.append(
                f'<p class="memo"><strong>承認理由メモ案:</strong> {_h(j.get("approval_memo",""))}</p>'
            )
        elif category == "要判断":
            if j.get("info_gaps"):
                out.append(
                    '<p class="meta"><strong>情報不足:</strong> '
                    + _h(", ".join(j["info_gaps"]))
                    + "</p>"
                )
        out.append(render_slack(c))
        if d.get("self_pr"):
            pr = d["self_pr"]
            out.append(
                f'<details class="self-pr"><summary>自己PR ({len(pr)}文字)</summary>'
                f'<div class="self-pr-body">{_autolink(pr).replace(chr(10),"<br>")}</div></details>'
            )
        out.append("</div>")
        return "\n".join(out)

    counts = {k: len(v) for k, v in by_cat.items()}
    title = f"フリーランスHub 課金対象チェック - {month}"
    css = """
:root { color-scheme: light dark; }
body { font-family: -apple-system, BlinkMacSystemFont, "Hiragino Sans", "Yu Gothic UI", sans-serif;
       max-width: 980px; margin: 1.5rem auto; padding: 0 1rem; line-height: 1.55; color: #202124; }
h1 { font-size: 1.5rem; border-bottom: 2px solid #1a73e8; padding-bottom: .3rem; }
h2 { margin-top: 2.2rem; padding: .35rem .6rem; border-radius: 4px; color: white; font-size: 1.2rem; }
h2.c0 { background: #d93025; } h2.c1 { background: #f29900; } h2.c2 { background: #188038; }
.summary { background: #f1f3f4; padding: .8rem 1rem; border-radius: 6px; }
.summary span { display: inline-block; margin-right: 1.2rem; }
.summary .badge { padding: .15rem .5rem; border-radius: 10px; color: white; font-weight: 600; font-size: .9rem; }
.card { border: 1px solid #dadce0; border-radius: 8px; padding: .9rem 1.1rem; margin-bottom: 1rem;
        background: white; box-shadow: 0 1px 2px rgba(0,0,0,.04); }
.card h3 { margin: 0 0 .5rem; font-size: 1.05rem; }
.card .age { color: #5f6368; font-weight: 400; font-size: .95rem; }
.card .meta { margin: .25rem 0; color: #3c4043; font-size: .92rem; }
.card .detail-link { display: inline-block; padding: .15rem .55rem; border: 1px solid #1a73e8;
                     border-radius: 4px; color: #1a73e8; text-decoration: none; font-size: .85rem; }
.card .detail-link:hover { background: #e8f0fe; }
.evidence { margin: .4rem 0 .4rem 1.2rem; padding: 0; }
.memo { background: #fff8e1; padding: .35rem .6rem; border-left: 3px solid #f29900; margin: .4rem 0;
        font-size: .9rem; }
details { margin: .5rem 0; }
details summary { cursor: pointer; font-weight: 600; color: #1a73e8; font-size: .92rem; }
.slack-history ul { padding-left: 1.2rem; margin: .4rem 0; }
.slack-history li { margin-bottom: .6rem; }
.slack-history .date { color: #5f6368; font-weight: 600; margin-right: .4rem; }
.slack-history .slack-reply { margin-left: 1.4rem; }
.slack-history .slack-reply .slack-body { border-left: 2px solid #c8ccd1; }
.slack-body { background: #f8f9fa; padding: .4rem .6rem; border-radius: 4px; margin-top: .25rem;
              font-size: .9rem; white-space: normal; }
.self-pr-body { background: #f8f9fa; padding: .5rem .8rem; border-radius: 4px; font-size: .88rem;
                color: #3c4043; }
a { color: #1a73e8; text-decoration: none; word-break: break-all; }
a:hover { text-decoration: underline; }
@media (prefers-color-scheme: dark) {
  body { background: #202124; color: #e8eaed; }
  .summary { background: #303134; }
  .card { background: #2d2e30; border-color: #5f6368; box-shadow: none; }
  .slack-body, .self-pr-body { background: #303134; color: #e8eaed; }
  .memo { background: #3c2c08; color: #fdd663; }
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
        f'<span>取得件数: <strong>{len(candidates)}</strong></span>',
        f'<span><span class="badge" style="background:{cat_color["非承認候補"]}">非承認候補 {counts.get("非承認候補",0)}</span></span>',
        f'<span><span class="badge" style="background:{cat_color["要判断"]}">要判断 {counts.get("要判断",0)}</span></span>',
        f'<span><span class="badge" style="background:{cat_color["承認推奨"]}">承認推奨 {counts.get("承認推奨",0)}</span></span>',
        "</div>",
    ]
    for idx, cat in enumerate(["非承認候補", "要判断", "承認推奨"]):
        items = by_cat.get(cat, [])
        parts.append(f'<h2 class="c{idx}">{_h(cat)} ({len(items)}件)</h2>')
        if not items:
            parts.append('<p class="meta">(該当なし)</p>')
            continue
        for c in items:
            parts.append(render_candidate(c, cat))
    parts.append("</body></html>")
    return "\n".join(parts)


# ========== Phase 6: 一括ステータス変更 ==========


def change_status(
    page: Page,
    detail_url: str,
    target_status: str,
    reasons: list[str] | None = None,
    memo: str = "",
) -> tuple[bool, str]:
    """1候補者のステータスを変更する。

    target_status: '非承認' / '承認' （モーダルdropdownのオプションラベル）
    reasons: 非承認時のシステム理由ラベル（例: ['在住地域', '年齢(高)']）
    memo: 承認理由メモ
    Returns: (成功, エラーメッセージ)
    """
    try:
        page.goto(detail_url, wait_until="networkidle")
        page.wait_for_timeout(1500)
        page.get_by_role("tab", name=re.compile(r"承認.*ステータス")).click()
        page.wait_for_timeout(1000)

        # 「変更」ボタンは2つあり、index1 が承認情報側
        change_buttons = page.get_by_role("button", name="変更").all()
        if len(change_buttons) < 2:
            return False, "変更ボタンが見つからない"
        change_buttons[1].click()
        page.wait_for_timeout(1500)

        # 承認ステータス dropdown 切替（exact=True で完全一致、第1候補にフォールバック）
        page.get_by_role("combobox").last.click()
        page.wait_for_timeout(800)
        try:
            page.get_by_role("option", name=target_status, exact=True).click(timeout=8000)
        except Exception:
            page.get_by_role("option", name=target_status).first.click(timeout=8000)
        page.wait_for_timeout(1500)

        # 非承認時: 理由 checkbox を ON
        # MUI Checkbox はラベルテキストの隣に input がある構造
        # Hub は非承認時に理由を最低1つ必須とするため、ラベル一致に失敗した場合は
        # 「その他」へフォールバックして保存可能な状態を保つ（重複クリック防止に1回のみ）。
        if target_status == "非承認" and reasons:
            other_checked = SYS_REASON_OTHER in reasons
            for reason_label in reasons:
                try:
                    # label のテキストをクリックすれば紐づく checkbox がトグルされる
                    page.locator(f"label:has-text('{reason_label}')").first.click()
                except Exception as e:
                    log(f"  reason check '{reason_label}' err: {e}")
                    if not other_checked:
                        log(f"  fallback to '{SYS_REASON_OTHER}'")
                        try:
                            page.locator(
                                f"label:has-text('{SYS_REASON_OTHER}')"
                            ).first.click()
                            other_checked = True
                        except Exception as e2:
                            log(f"  fallback '{SYS_REASON_OTHER}' err: {e2}")

        # 承認ステータス変更モーダルにメモ入力欄は存在しない（対応メモは別フロー）。
        # 生成済みの approval_memo はレポート (MD/HTML/JSON) 上の人手参照用に
        # 保持するのみで Hub への書き込みは行わない。
        page.wait_for_timeout(500)
        # 保存ボタン
        page.get_by_role("button", name="保存").click()
        page.wait_for_timeout(2500)

        # モーダルが閉じたか確認
        try:
            page.wait_for_selector("text=承認ステータス変更", state="detached", timeout=5000)
        except Exception:
            pass
        return True, ""
    except Exception as e:
        return False, str(e)


def apply_status_changes(
    page: Page,
    candidates: list[dict[str, Any]],
    target_status: str,
) -> dict[str, int]:
    """候補者リストにステータス変更を一括適用する."""
    success = 0
    failed = 0
    skipped = 0
    for i, c in enumerate(candidates):
        if not c.get("detail_url"):
            log(f"  [{i+1}] {c.get('name')}: detail_url 無しスキップ")
            skipped += 1
            continue
        j = c.get("judgment") or {}
        reasons = j.get("system_reasons", []) if target_status == "非承認" else None
        memo = j.get("approval_memo", "") if target_status == "非承認" else ""
        ok, err = change_status(
            page, c["detail_url"], target_status, reasons=reasons, memo=memo
        )
        if ok:
            success += 1
            log(f"  [{i+1}/{len(candidates)}] {c.get('name')}: {target_status} OK")
        else:
            failed += 1
            log(f"  [{i+1}/{len(candidates)}] {c.get('name')}: 失敗 {err}")
    return {"success": success, "failed": failed, "skipped": skipped}


def run_fetch_phases(args) -> int:
    """Phase 1〜5: 取得→詳細→突合→判定→レポート."""
    start_date, end_date = parse_month(args.month)
    log(f"対象期間: {start_date} 〜 {end_date}")

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    DEBUG_DIR.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as pw:
        browser, context, page = fh.login(pw, headless=args.headless, storage_state=str(SESSION_PATH))
        try:
            # Phase 1: 一覧取得 + 詳細URL
            raw_rows = fetch_unapproved_list(page, start_date, end_date, args.approval_status)
            candidates = [parse_row(r) for r in raw_rows]

            # Phase 2: 各候補者の詳細情報
            if not args.skip_detail:
                detail_targets = candidates if args.limit == 0 else candidates[: args.limit]
                log(f"Phase 2: 詳細情報取得 ({len(detail_targets)} 件)")
                detail_page = context.new_page()
                for i, cand in enumerate(detail_targets):
                    if not cand.get("detail_url"):
                        continue
                    try:
                        info = fetch_detail(detail_page, cand["detail_url"])
                        cand["detail"] = {k: v for k, v in info.items() if k != "detail_url"}
                    except Exception as e:
                        log(f"  [{i+1}] {cand.get('name')}: 詳細取得エラー {e}")
                        cand["detail"] = {"error": str(e)}
                detail_page.close()

            # Phase 3a: Slack #inquiries 突合（必須）
            if not os.environ.get("SLACK_USER_TOKEN"):
                raise RuntimeError(
                    "SLACK_USER_TOKEN が未設定です。Slack 突合は必須のため処理を中断します。"
                    " ~/.zshrc に xoxp- トークンを export してから再実行してください。"
                )
            log(f"Phase 3a: Slack 突合 ({len(candidates)} 件)")
            for c in candidates:
                if c.get("name"):
                    c["slack_hits"] = slack_search(c["name"], count=3)

            # Phase 3b: FreelanceBase 営業不可突合
            if not args.skip_fb:
                try:
                    log("Phase 3b: FreelanceBase 認証ヘッダ取得")
                    fb_browser, fb_context, fb_page = fb.login(pw, headless=args.headless)
                    try:
                        auth, payload = fb_capture_auth(fb_page)
                        log(f"  FB 突合 ({len(candidates)} 件)")
                        for c in candidates:
                            if not c.get("name"):
                                continue
                            try:
                                fb_results = fb_search_by_name(fb_page, auth, payload, c["name"])
                                c["fb_unsellable"] = fb_find_unsellable_match(fb_results, c["name"])
                            except Exception as e:
                                log(f"  FB '{c['name']}': {e}")
                                c["fb_unsellable"] = []
                    finally:
                        fb_browser.close()
                except Exception as e:
                    log(f"FB 突合スキップ（ログイン失敗等）: {e}")

            # Phase 4: 判定
            log("Phase 4: 判定")
            for c in candidates:
                c["judgment"] = judge_candidate(c)

            # 保存
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            json_path = out_dir / f"{args.month}_freelancehub_candidates_{ts}.json"
            json_path.write_text(
                json.dumps(
                    {
                        "month": args.month,
                        "start_date": start_date,
                        "end_date": end_date,
                        "fetched_at": datetime.now().isoformat(),
                        "count": len(candidates),
                        "candidates": candidates,
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            log(f"JSON保存: {json_path}")

            # Phase 5: Markdown / HTML レポート
            md = render_report(args.month, candidates)
            md_path = out_dir / f"{args.month}_フリーランスHub課金対象チェック.md"
            md_path.write_text(md, encoding="utf-8")
            html = render_report_html(args.month, candidates)
            html_path = out_dir / f"{args.month}_フリーランスHub課金対象チェック.html"
            html_path.write_text(html, encoding="utf-8")
            log(f"レポート: {md_path}")
            log(f"HTML: {html_path}")

            # 概要表示
            cats: dict[str, int] = {}
            for c in candidates:
                cats[c.get("judgment", {}).get("category", "?")] = cats.get(
                    c.get("judgment", {}).get("category", "?"), 0
                ) + 1
            print("\n=== Phase 1〜5 完了 ===")
            print(f"対象期間: {start_date} 〜 {end_date}")
            print(f"件数: {len(candidates)}")
            for k in ["非承認候補", "要判断", "承認推奨"]:
                print(f"  {k}: {cats.get(k, 0)}")
            print(f"JSON: {json_path}")
            print(f"レポート: {md_path}")
            print(f"HTML: {html_path}")
            print()
            print("次のステップ:")
            print(f"  Phase 6 段階A (一括非承認): python3 {Path(__file__).resolve()} --apply-reject --report {json_path}")
        finally:
            context.storage_state(path=str(SESSION_PATH))
            browser.close()
    return 0


def run_apply_phase(args) -> int:
    """Phase 6: 一括ステータス変更."""
    report_path = Path(args.report)
    if not report_path.exists():
        log(f"レポート JSON が見つからない: {report_path}")
        return 1
    data = json.loads(report_path.read_text(encoding="utf-8"))
    candidates = data.get("candidates", [])

    target_category = "非承認候補" if args.apply_reject else "承認推奨"
    # モーダル dropdown のラベル: 未確認 / 承認 / 非承認
    target_status = "非承認" if args.apply_reject else "承認"
    targets = [c for c in candidates if c.get("judgment", {}).get("category") == target_category]

    print(f"\n=== Phase 6: {target_status} 一括変更 ===")
    print(f"対象: {len(targets)} 件 ({target_category})")
    if not targets:
        print("対象なし")
        return 0

    # 各候補の一覧を表示
    for c in targets:
        nm = c.get("name", "")
        url = c.get("detail_url", "")
        if args.apply_reject:
            j = c.get("judgment", {})
            print(f"  - {nm}: {','.join(j.get('system_reasons', []))} / メモ: {j.get('approval_memo','')}")
        else:
            print(f"  - {nm}")

    if not args.yes:
        ans = input(f"\n上記 {len(targets)} 件を「{target_status}」に変更します。続行しますか? [y/N] ")
        if ans.strip().lower() != "y":
            print("中断しました")
            return 0

    with sync_playwright() as pw:
        browser, context, page = fh.login(pw, headless=args.headless, storage_state=str(SESSION_PATH))
        try:
            stats = apply_status_changes(page, targets, target_status)
            print("\n=== 結果 ===")
            print(f"成功: {stats['success']} / 失敗: {stats['failed']} / スキップ: {stats['skipped']}")
        finally:
            context.storage_state(path=str(SESSION_PATH))
            browser.close()
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--month", help="対象年月 (例: 2026-04)。Phase 1-5 実行時に必須")
    ap.add_argument("--output-dir", help="出力ディレクトリ。Phase 1-5 実行時に必須")
    ap.add_argument("--skip-detail", action="store_true", help="Phase 2 (詳細取得) をスキップ")
    ap.add_argument("--skip-fb", action="store_true", help="Phase 3b (FB 突合) をスキップ")
    ap.add_argument("--limit", type=int, default=0, help="詳細取得を最初のN件だけに制限（テスト用、0=無制限）")
    ap.add_argument("--approval-status", type=int, default=1, help="承認ステータスフィルター値 (1=未承認, 2=承認済, 3=非承認)。デフォルト1")
    ap.add_argument("--apply-reject", action="store_true", help="Phase 6 段階A: 非承認候補を一括非承認")
    ap.add_argument("--apply-approve", action="store_true", help="Phase 6 段階B: 承認推奨を一括承認")
    ap.add_argument("--report", help="Phase 6 で読む JSON レポートのパス")
    ap.add_argument("--yes", action="store_true", help="確認プロンプトをスキップ")
    ap.add_argument("--no-headless", action="store_true", help="ブラウザを表示する（Phase 6 の目視確認用）")
    args = ap.parse_args()
    args.headless = not args.no_headless

    if args.apply_reject or args.apply_approve:
        if not args.report:
            log("--apply-* には --report が必要")
            return 1
        return run_apply_phase(args)

    if not args.month or not args.output_dir:
        log("Phase 1-5 実行には --month と --output-dir が必要")
        return 1
    return run_fetch_phases(args)


if __name__ == "__main__":
    sys.exit(main())
