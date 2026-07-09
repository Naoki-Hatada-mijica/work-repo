#!/usr/bin/env python3
"""FreelanceBase 候補者詳細に v1サマリ由来の JSON payload を書き込む.

使い方:
    python3 crm_write.py <payload.json>

payload.json のスキーマは `SCHEMA.md` を参照。
書き込み対象セクション: 基本情報 / 営業情報 / スキル・経験情報 / 希望条件 / 管理情報

動作方針:
  - 1 度だけ詳細ページに遷移し、各セクションごとに 編集する → 入力 → 保存 → キャンセル で閉じる
  - page.goto() によるリロードは禁忌（Vue SPA の状態が壊れる）
  - 保存成功判定は PUT /api/enterprise/candidates/update/{id} の 200 応答
  - payload の null 項目はスキップ（既存値を維持）
  - セクション単位で try/except。失敗時は screenshot を残し次に進む
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, __import__("os").path.expanduser("~/.claude/snippets"))

from playwright.sync_api import sync_playwright, Page, Locator  # noqa: E402
import playwright_freelancebase as fb  # noqa: E402

DRAWER_SEL = ".modal_content.right-modal.right-open"
UPDATE_API_RE = re.compile(r"/api/enterprise/candidates/update/(\d+)")

# 住所（都道府県）select の value マップ（UI dump で取得）
PREFECTURE_MAP: dict[str, str] = {
    "北海道": "1", "青森県": "2", "岩手県": "3", "宮城県": "4", "秋田県": "5",
    "山形県": "6", "福島県": "7", "茨城県": "8", "栃木県": "9", "群馬県": "10",
    "埼玉県": "11", "千葉県": "12", "東京都": "13", "神奈川県": "14", "新潟県": "15",
    "富山県": "16", "石川県": "17", "福井県": "18", "山梨県": "19", "長野県": "20",
    "岐阜県": "21", "静岡県": "22", "愛知県": "23", "三重県": "24", "滋賀県": "25",
    "京都府": "26", "大阪府": "27", "兵庫県": "28", "奈良県": "29", "和歌山県": "30",
    "鳥取県": "31", "島根県": "32", "岡山県": "33", "広島県": "34", "山口県": "35",
    "徳島県": "36", "香川県": "37", "愛媛県": "38", "高知県": "39", "福岡県": "40",
    "佐賀県": "41", "長崎県": "42", "熊本県": "43", "大分県": "44", "宮崎県": "45",
    "鹿児島県": "46", "沖縄県": "47", "その他": "48",
}

# 情報から一括追加 後に CRM が行う名称正規化との差分を吸収するエイリアス
# （payload の main_skill_name ↔ DOM 上のスキル表示名）
SKILL_NAME_ALIASES: dict[str, list[str]] = {
    "Go": ["Go言語"],
    "Golang": ["Go言語"],
    "Vue": ["Vue.js"],
    "Vue.js": ["Vue.js"],
    "Node": ["Node.js"],
    "Node.js": ["Node.js"],
}
# screenshot は候補者名を含みうる PII。tmp に退避し、明示的に残すオプションが無ければ削除する
SCREENSHOT_DIR = Path(tempfile.gettempdir()) / "crm_write_screenshots"


def log(msg: str) -> None:
    print(f"[crm_write] {msg}", file=sys.stderr)


def notify_slack(
    webhook_url: str,
    management_id: str,
    internal_id: int | None,
    results: list[tuple[str, bool, str]],
    dry_run: bool,
    screenshots: list[Path],
) -> bool:
    """書き込み結果を Slack webhook に通知する（氏名・連絡先は含めない）."""
    icon = "✅" if all(ok for _, ok, _ in results) else "⚠️"
    mode = "dry-run" if dry_run else "write"
    lines = [
        f"{icon} *freelance-meeting-summarize* CRM書き込み結果（{mode}）",
        f"• management_id: `{management_id}`" + (f" (internal_id={internal_id})" if internal_id else ""),
    ]
    for section, ok, msg in results:
        mark = "✓" if ok else "✗"
        lines.append(f"• [{mark}] {section}: {msg}")
    if screenshots:
        lines.append(f"• debug screenshots: `{SCREENSHOT_DIR}` ({len(screenshots)}件)")
    payload = {"text": "\n".join(lines)}
    try:
        req = urllib.request.Request(
            webhook_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            ok = 200 <= r.status < 300
            if not ok:
                log(f"[WARN] Slack webhook status={r.status}")
            return ok
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
        log(f"[WARN] Slack 通知失敗: {e}")
        return False


# ---------- ID 解決 ----------

def resolve_internal_id(page: Page, management_id: str) -> int | None:
    """管理用ID（MJC...）→ 内部ID を解決.

    流れ: クイック検索 → `p:has-text(mgmt_id)` をクリック → プレビュードロワー内の
    「詳細を見る」を押して遷移し、URL から内部IDを抜き取る。
    """
    page.goto("https://freelancebase.jp/enterprise/candidates#view-1", wait_until="networkidle")
    page.wait_for_timeout(2000)

    search_box = page.get_by_placeholder("クイック検索").first
    if not search_box.count():
        search_box = page.locator("input[placeholder*='検索']").first
    search_box.click()
    search_box.fill(management_id)
    page.wait_for_timeout(500)
    # クイック検索は Enter でテーブル検索を実行する。fill() だけでは絞り込みが走らず、
    # 代わりに頼っていたオートコンプリート候補は管理用IDの一致をレコードによって取りこぼす
    # （例: MJC48537741_HT は候補0件）。Enter を押してテーブルを絞り込む経路に統一する。
    search_box.press("Enter")
    page.wait_for_timeout(3000)

    # 絞り込まれたテーブルから管理用IDを含む行を特定し、その管理用IDセルをクリック
    row = page.locator(f"table tbody tr:has-text('{management_id}')").first
    if not row.count():
        log(f"[ERR] 管理用ID '{management_id}' が検索結果にない")
        return None
    target = row.locator(f":has-text('{management_id}')").last
    target.scroll_into_view_if_needed()
    target.click(force=True)
    page.wait_for_timeout(1500)

    detail_btn = page.get_by_role("button", name="詳細を見る").first
    if not detail_btn.count():
        # aタグの可能性もある
        detail_btn = page.get_by_role("link", name="詳細を見る").first
    if not detail_btn.count():
        log("[ERR] プレビュードロワーに『詳細を見る』が見つからない")
        return None

    # href 属性があれば直接抽出（新タブを開かずに済む）
    href = detail_btn.get_attribute("href") or ""
    m = re.search(r"/enterprise/candidates/(\d+)", href)
    if m:
        return int(m.group(1))

    # 新タブで開くパターン: popup を捕捉
    try:
        with page.context.expect_page(timeout=8000) as new_page_info:
            detail_btn.click()
        new_page = new_page_info.value
        new_page.wait_for_load_state("domcontentloaded", timeout=8000)
        url = new_page.url
        new_page.close()
        m = re.search(r"/enterprise/candidates/(\d+)", url)
        if m:
            return int(m.group(1))
        log(f"[ERR] 新タブURL から ID 抽出失敗: url={url}")
    except Exception:
        # 同タブ遷移のフォールバック
        detail_btn.click()
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1500)
        m = re.search(r"/enterprise/candidates/(\d+)", page.url)
        if m:
            return int(m.group(1))
        log(f"[ERR] URL から ID 抽出失敗: url={page.url}")
    return None


# ---------- ドロワー操作 ----------

def open_section(page: Page, name: str) -> bool:
    heading = page.locator("h6.fs-18").filter(has_text=name).first
    if not heading.count():
        log(f"[WARN] h6 見出し '{name}' が見つからない")
        return False
    row = heading.locator(
        "xpath=ancestor::div[contains(@class,'row') and contains(@class,'align-items-center')][1]"
    )
    btn = row.get_by_role("button", name="編集する").first
    if not btn.count():
        log(f"[WARN] 編集する ボタンが見つからない ({name})")
        return False
    btn.scroll_into_view_if_needed()
    btn.click(force=True)
    try:
        page.wait_for_selector(DRAWER_SEL, timeout=10000)
    except Exception:
        return False
    for _ in range(20):
        page.wait_for_timeout(250)
        titles = page.locator(DRAWER_SEL).evaluate_all(
            "els => els.map(e => { for (const n of e.querySelectorAll('*')) { const t=(n.innerText||'').trim(); if (t.endsWith('を編集') && t.length < 40) return t; } return ''; })"
        )
        if any(name in t for t in titles):
            return True
    log(f"[WARN] ドロワータイトルが '{name}' に一致しない")
    return False


def get_drawer(page: Page, section: str) -> Locator:
    """タイトルが section を含み、かつ配下に入力要素を持つ実体ドロワーを返す.

    `.modal_content.right-modal.right-open` は空の shell が並列マッチすることがあり、
    タイトル一致だけで選ぶと inputs 0 の空ドロワーを掴んでしまう事がある。
    """
    drawers = page.locator(DRAWER_SEL)
    best: Locator | None = None
    best_inputs = -1
    for i in range(drawers.count()):
        d = drawers.nth(i)
        try:
            info = d.evaluate(
                """el => {
                    let title = '';
                    for (const n of el.querySelectorAll('*')) {
                        const t=(n.innerText||'').trim();
                        if (t.endsWith('を編集') && t.length < 40) { title = t; break; }
                    }
                    return { title, inputs: el.querySelectorAll('input, textarea, select').length };
                }"""
            )
        except Exception:
            continue
        if section in info.get("title", "") and info.get("inputs", 0) > best_inputs:
            best = d
            best_inputs = info["inputs"]
    return best if best is not None else drawers.first


def close_drawer(page: Page) -> None:
    if page.locator(DRAWER_SEL).count() == 0:
        return
    cancel = page.locator(f"{DRAWER_SEL} button").filter(has_text="キャンセル").first
    if cancel.count():
        cancel.click(force=True)
        page.wait_for_timeout(1200)


def save_drawer(page: Page, drawer: Locator, internal_id: int) -> bool:
    """保存する をクリックし、PUT /update/{id} が 200 を返すまで待つ."""
    save_btn = drawer.locator("button").filter(has_text="保存する").first
    if not save_btn.count():
        log("[ERR] 保存する ボタン未検出")
        return False
    save_btn.scroll_into_view_if_needed()
    try:
        with page.expect_response(
            lambda r: (
                UPDATE_API_RE.search(r.url) is not None
                and r.request.method in ("POST", "PUT", "PATCH")
            ),
            timeout=15000,
        ) as resp_info:
            save_btn.click(force=True)
        resp = resp_info.value
        if resp.status >= 400:
            log(f"[ERR] update API が {resp.status} を返した url={resp.url}")
            return False
        log(f"[OK] update API {resp.status} ({resp.request.method} {resp.url})")
        page.wait_for_timeout(1000)
        return True
    except Exception as e:
        log(f"[ERR] save 失敗: {e}")
        return False


# ---------- ヘルパー（入力系） ----------

def set_textarea_by_label(drawer: Locator, label: str, value: str | None) -> bool:
    if value is None:
        return True
    handle = drawer.evaluate_handle(
        """(root, label) => {
            const all = Array.from(root.querySelectorAll('textarea'));
            // 1) placeholder 完全/部分一致を最優先
            for (const ta of all) {
                const ph = ta.placeholder || '';
                if (ph.includes(label)) return ta;
            }
            // 2) ancestor に label を含む、かつその ancestor 配下の textarea がこの 1 つだけ（曖昧さ回避）
            for (const ta of all) {
                let p = ta.parentElement;
                for (let i=0; i<6 && p; i++, p = p.parentElement) {
                    const txt = p.innerText || '';
                    if (txt.includes(label) && p.querySelectorAll('textarea').length === 1) {
                        return ta;
                    }
                }
            }
            return null;
        }""",
        label,
    )
    # evaluate_handle は null でも JSHandle を返す。要素化チェックを明示する
    el = handle.as_element() if handle else None
    if el is None:
        log(f"[WARN] textarea '{label}' 未検出")
        return False
    el.evaluate(
        """(el, v) => {
            el.focus();
            el.value = v;
            el.dispatchEvent(new Event('input', {bubbles:true}));
            el.dispatchEvent(new Event('change', {bubbles:true}));
        }""",
        value,
    )
    return True


def set_text_input_by_label(drawer: Locator, label: str, value: str | None) -> bool:
    """label に紐づく <input type=text> を 1 つ特定して value をセット."""
    if value is None:
        return True
    handle = drawer.evaluate_handle(
        """(root, label) => {
            const inputs = Array.from(root.querySelectorAll("input[type='text']"));
            for (const inp of inputs) {
                let p = inp.parentElement;
                for (let i=0; i<8 && p; i++, p = p.parentElement) {
                    const txt = p.innerText || '';
                    if (txt.includes(label) && p.querySelectorAll("input[type='text']").length === 1) {
                        return inp;
                    }
                }
            }
            return null;
        }""",
        label,
    )
    el = handle.as_element() if handle else None
    if el is None:
        log(f"[WARN] text input '{label}' 未検出")
        return False
    el.evaluate(
        """(el, v) => {
            el.focus();
            el.value = v;
            el.dispatchEvent(new Event('input', {bubbles:true}));
            el.dispatchEvent(new Event('change', {bubbles:true}));
            el.blur();
        }""",
        value,
    )
    return True


def set_select_by_label(drawer: Locator, label: str, value: str | None) -> bool:
    """label に紐づく <select> を 1 つ特定して value で選択."""
    if value is None:
        return True
    handle = drawer.evaluate_handle(
        """(root, label) => {
            const sels = Array.from(root.querySelectorAll("select"));
            for (const s of sels) {
                let p = s.parentElement;
                for (let i=0; i<8 && p; i++, p = p.parentElement) {
                    const txt = p.innerText || '';
                    if (txt.includes(label) && p.querySelectorAll("select").length === 1) {
                        return s;
                    }
                }
            }
            return null;
        }""",
        label,
    )
    el = handle.as_element() if handle else None
    if el is None:
        log(f"[WARN] select '{label}' 未検出")
        return False
    el.evaluate(
        """(el, v) => {
            el.value = v;
            el.dispatchEvent(new Event('input', {bubbles:true}));
            el.dispatchEvent(new Event('change', {bubbles:true}));
        }""",
        str(value),
    )
    return True


def set_radio(drawer: Locator, name: str, value: str | None) -> bool:
    if value is None:
        return True
    sel = f"input[type='radio'][name='{name}'][value='{value}']"
    radio = drawer.locator(sel).first
    if not radio.count():
        log(f"[WARN] radio {name}={value} 未検出")
        return False
    radio.evaluate(
        """el => {
            el.checked = true;
            el.dispatchEvent(new Event('input', {bubbles:true}));
            el.dispatchEvent(new Event('change', {bubbles:true}));
            el.click();
        }"""
    )
    return True


def set_checkbox_multi(drawer: Locator, name: str, values: list | None) -> bool:
    """複数選択 checkbox. values=None は触らない（既存維持）. values=[] は全解除."""
    if values is None:
        return True
    want = {str(v) for v in values}
    boxes = drawer.locator(f"input[type='checkbox'][name='{name}']").all()
    for box in boxes:
        v = box.get_attribute("value") or ""
        should = v in want
        is_checked = box.is_checked()
        if should != is_checked:
            box.evaluate("el => el.click()")
    return True


def set_personal_price_range(drawer: Locator, min_val, max_val) -> bool:
    """本人希望単価/月 の text × 2（範囲）を設定する.

    注意: 提案単価/月 は `<input type="number" placeholder="700000">`、
    本人希望単価/月 の上限は `<input placeholder="700000">` (type属性なし) なので、
    type セレクタで分ける (`[type=text]`) と HTML 属性なし側がマッチしない。
    ここでは `:not([type='number'])` で number input を明示的に除外する。
    """
    if min_val is None and max_val is None:
        return True
    min_inp = drawer.locator("input[placeholder='450000']:not([type='number'])").first
    max_inp = drawer.locator("input[placeholder='700000']:not([type='number'])").first
    if not min_inp.count() or not max_inp.count():
        log("[WARN] 本人希望単価 input × 2 未検出")
        return False
    if min_val is not None:
        min_inp.fill(str(min_val))
    if max_val is not None:
        max_inp.fill(str(max_val))
    return True


def set_station_autocomplete(page: Page, drawer: Locator, station_name: str) -> bool:
    """最寄り駅 autocomplete に station_name を入力し、候補から選択する."""
    inp = drawer.locator("input[name='station_id']").first
    if not inp.count():
        log("[WARN] station_id input 未検出")
        return False
    inp.scroll_into_view_if_needed()
    inp.click()
    inp.fill("")
    page.wait_for_timeout(200)
    inp.type(station_name, delay=30)
    page.wait_for_timeout(1200)
    # 候補リストは body 直下に出る（drawer の外側）ため page スコープで探す
    suggestion = page.locator("ul.suggestions li").filter(has_text=station_name).first
    if not suggestion.count():
        suggestion = page.locator("ul.suggestions li").first
    if not suggestion.count():
        log(f"[WARN] station 候補リスト未検出")
        return False
    suggestion.click()
    page.wait_for_timeout(400)
    return True


def set_prefecture_select(drawer: Locator, prefecture_name: str | None) -> bool:
    """住所（都道府県）select に prefecture_name を選択する.

    `name` 属性がないため options 内容で select を特定する（"北海道" を含む選択肢を持つもの）.
    """
    if prefecture_name is None:
        return True
    value = PREFECTURE_MAP.get(prefecture_name)
    if not value:
        log(f"[WARN] 都道府県マスタ未ヒット: {prefecture_name}")
        return False
    handle = drawer.evaluate_handle(
        """root => {
            for (const s of root.querySelectorAll('select')) {
                const labels = Array.from(s.options).map(o => o.text);
                if (labels.includes('北海道') && labels.includes('東京都')) return s;
            }
            return null;
        }"""
    )
    el = handle.as_element() if handle else None
    if el is None:
        log("[WARN] 住所(都道府県) select 未検出")
        return False
    el.evaluate(
        """(s, v) => {
            s.value = v;
            s.dispatchEvent(new Event('input',{bubbles:true}));
            s.dispatchEvent(new Event('change',{bubbles:true}));
        }""",
        value,
    )
    return True


def click_bulk_add_skills(page: Page, drawer: Locator) -> bool:
    """スキル・経験情報ドロワー内の『情報から一括追加』ボタンを押す.

    クリックすると career_summary textarea の内容を解析してスキルタグを
    インライン追加する（サブモーダルは出ない）. 同じ内容でも再押下で重複は発生しない.
    """
    btn = drawer.locator("button").filter(has_text="情報から一括追加").first
    if not btn.count():
        log("[WARN] 『情報から一括追加』ボタン未検出")
        return False
    btn.scroll_into_view_if_needed()
    btn.click(force=True)
    page.wait_for_timeout(2500)
    return True


def _normalize_skill(name: str) -> str:
    return name.strip().lower().replace(" ", "").replace(".", "").replace("-", "")


def set_main_skill(drawer: Locator, main_skill_name: str | None) -> bool:
    """スキルタグ一覧のうち main_skill_name に一致する行のメインスキル checkbox を ON.

    名称ゆれ（"Go" vs "Go言語" 等）は SKILL_NAME_ALIASES と正規化で吸収する.
    既に他スキルがメインに設定されている場合はそのまま（1 つだけメイン、の運用は UI 側制約）.
    """
    if not main_skill_name:
        return True
    candidates = [main_skill_name] + SKILL_NAME_ALIASES.get(main_skill_name, [])
    wanted = {_normalize_skill(c) for c in candidates}
    rows = drawer.locator("#form-label-skill_ids .row.align-items-center.mt-15").all()
    hit = None
    for row in rows:
        try:
            name = row.locator(".col span.fs-14").first.inner_text(timeout=500).strip()
        except Exception:
            continue
        if _normalize_skill(name) in wanted:
            hit = row
            break
    if hit is None:
        log(f"[WARN] メインスキル対象のタグ未検出: {main_skill_name}")
        return False
    cb = hit.locator("input[type='checkbox'][name^='thumbtack_']").first
    if not cb.count():
        log(f"[WARN] メインスキル checkbox 未検出: {main_skill_name}")
        return False
    if not cb.is_checked():
        cb.evaluate("el => el.click()")
    return True


def set_number_input(drawer: Locator, placeholder_or_label: str, value) -> bool:
    if value is None:
        return True
    inp = drawer.locator(f"input[type='number'][placeholder*='{placeholder_or_label}']").first
    if not inp.count():
        # placeholder でヒットしなければ label 経由
        inp = drawer.locator(f"input[type='number']").first
    if not inp.count():
        log(f"[WARN] number input '{placeholder_or_label}' 未検出")
        return False
    inp.fill(str(value))
    return True


# ---------- セクション別フィラー ----------

def set_text_by_placeholder_if_empty(drawer: Locator, placeholder: str, value: str | None) -> bool:
    """placeholder 完全一致の <input type=text> を特定して、現在値が空の場合のみ value をセット.

    既存値がある場合はスキップ（[SKIP] ログを出力）。PII は値を出力しない.
    """
    if value is None or value == "":
        return True
    inp = drawer.locator(f"input[type='text'][placeholder='{placeholder}']").first
    if not inp.count():
        log(f"[WARN] text input ph='{placeholder}' 未検出")
        return False
    current = (inp.input_value() or "").strip()
    if current:
        log(f"[SKIP] ph='{placeholder}': 既存値あり、上書きしない")
        return True
    inp.evaluate(
        """(el, v) => {
            el.focus();
            el.value = v;
            el.dispatchEvent(new Event('input',{bubbles:true}));
            el.dispatchEvent(new Event('change',{bubbles:true}));
            el.blur();
        }""",
        value,
    )
    return True


def set_birth_date_if_empty(drawer: Locator, year, month, day) -> bool:
    """生年月日（年/月/日）の select × 3 にセット。3 つすべて未選択（"0"）の場合のみ書き込む.

    生年月日 select トリオは「options に '1950' を含む select」で識別する.
    """
    if year is None and month is None and day is None:
        return True
    handle = drawer.evaluate_handle(
        """root => {
            const sels = Array.from(root.querySelectorAll('select'));
            // 1950 を options に含む select を年とみなし、その兄弟（直後 2 つ）を月/日とする
            for (let i = 0; i < sels.length; i++) {
                const s = sels[i];
                const vals = Array.from(s.options).map(o => o.value);
                if (vals.includes('1950') && vals.length > 50) {
                    return [s, sels[i+1] || null, sels[i+2] || null];
                }
            }
            return null;
        }"""
    )
    arr = handle.evaluate("a => a") if handle else None
    if not arr:
        log("[WARN] 生年月日 select トリオ未検出")
        return False
    # 既存値チェック: 3 つすべて "0" 以外なら既登録としてスキップ
    current = handle.evaluate("a => a.map(s => s ? s.value : null)")
    nonzero = [v for v in current if v not in (None, "", "0")]
    if nonzero:
        log("[SKIP] 生年月日: 既存値あり、上書きしない")
        return True
    handle.evaluate(
        """(a, vals) => {
            for (let i = 0; i < 3; i++) {
                if (!a[i] || vals[i] == null) continue;
                a[i].value = String(vals[i]);
                a[i].dispatchEvent(new Event('input',{bubbles:true}));
                a[i].dispatchEvent(new Event('change',{bubbles:true}));
            }
        }""",
        [year, month, day],
    )
    log("[OK] 生年月日: 書き込み完了")
    return True


def fill_basic_info(page: Page, drawer: Locator, data: dict) -> None:
    set_radio(drawer, "gender_id", data.get("gender_id"))
    set_radio(drawer, "nationality_type_id", data.get("nationality_type_id"))

    # 氏名（姓/名）・フリガナ（セイ/メイ）— 空欄の時のみ書き込み
    set_text_by_placeholder_if_empty(drawer, "田中", data.get("name_sei"))
    set_text_by_placeholder_if_empty(drawer, "太郎", data.get("name_mei"))
    set_text_by_placeholder_if_empty(drawer, "たなか", data.get("name_kana_sei"))
    set_text_by_placeholder_if_empty(drawer, "たろう", data.get("name_kana_mei"))

    # 生年月日（年/月/日 selects）— 3 つすべて未選択の場合のみ書き込み
    birth = data.get("birth_date") or {}
    set_birth_date_if_empty(drawer, birth.get("year"), birth.get("month"), birth.get("day"))

    # 年齢（旧仕様、生年月日があれば不要。data.age が指定されていれば「空のときだけ」書く）
    age = data.get("age")
    if age is not None:
        age_handle = drawer.evaluate_handle(
            """root => {
                for (const el of root.querySelectorAll('input[type="number"]')) {
                    let p = el.parentElement;
                    for (let i=0; i<5 && p; i++, p=p.parentElement) {
                        if ((p.innerText||'').includes('年齢')) return el;
                    }
                }
                return null;
            }"""
        )
        age_el = age_handle.as_element() if age_handle else None
        if age_el is None:
            log("[WARN] 年齢 input 未検出")
        else:
            current_age = (age_el.evaluate("el => el.value") or "").strip()
            if current_age:
                log("[SKIP] 年齢: 既存値あり、上書きしない")
            else:
                age_el.evaluate(
                    "(el, v) => { el.focus(); el.value = v; el.dispatchEvent(new Event('input',{bubbles:true})); el.dispatchEvent(new Event('change',{bubbles:true})); }",
                    str(age),
                )
    # 最寄り駅（autocomplete）。値自体は PII なのでログには出さない
    station = data.get("station_name")
    if station:
        if not set_station_autocomplete(page, drawer, station):
            log("[WARN] 最寄り駅の autocomplete 選択に失敗")
    # 最寄り駅が存在する都道府県を 住所（都道府県）select にセット
    prefecture = data.get("prefecture_name")
    if prefecture:
        set_prefecture_select(drawer, prefecture)
    # オンライン登録面談 録画URL（AI議事録 Doc URL も可）
    set_text_input_by_label(drawer, "オンライン登録面談 録画URL", data.get("recording_url"))
    # 連絡手段（LINE / メール / Slack 等の自由記述）
    set_text_input_by_label(drawer, "連絡手段", data.get("contact_method"))


def fill_sales_info(page: Page, drawer: Locator, data: dict) -> None:
    set_checkbox_multi(drawer, "work_styles_ids", data.get("work_styles_ids"))
    set_checkbox_multi(drawer, "business_day_ids", data.get("business_day_ids"))

    # 年/月/日 select は 3 つで 1 トリオ。ドロワー内に順に 稼働開始日 / 営業開始日
    # / 営業終了日（独占営業期間）の 3 トリオが並ぶ。
    # options[i].text は空（Vue レンダリングで textContent が遅延設定）なので、
    # **options の value で年/月/日 select を識別する**:
    #   - options[1].value が 4 桁数字（"2021" 等） → 年 select
    #   - options 数 == 13 (0-12) → 月 select
    #   - options 数 == 32 (0-31) → 日 select
    # name 属性も label もないため、DOM 順を信頼してトリオを構築する.
    all_selects = drawer.locator("select").all()
    date_selects: list[Locator] = []
    for s in all_selects:
        opt_vals = s.evaluate("el => Array.from(el.options).map(o => o.value)")
        if len(opt_vals) < 2:
            continue
        v1 = opt_vals[1] if len(opt_vals) > 1 else ""
        is_year = bool(re.fullmatch(r"\d{4}", v1 or ""))
        is_month = len(opt_vals) == 13 and opt_vals[0] == "0"
        is_day = len(opt_vals) == 32 and opt_vals[0] == "0"
        if is_year or is_month or is_day:
            date_selects.append(s)

    def set_trio(trio: list[Locator], year, month, day) -> None:
        vals = [year, month, day]
        for i, sel in enumerate(trio[:3]):
            v = vals[i]
            if v is None:
                continue
            try:
                sel.select_option(value=str(v))
            except Exception:
                sel.select_option(label=str(v))

    start = data.get("start_date") or {}
    if any(start.get(k) is not None for k in ("year", "month", "day")):
        if len(date_selects) >= 3:
            set_trio(date_selects[0:3], start.get("year"), start.get("month"), start.get("day"))
        else:
            log("[WARN] 稼働開始日 select トリオ未検出")

    biz = data.get("business_start_date") or {}
    if any(biz.get(k) is not None for k in ("year", "month", "day")):
        if len(date_selects) >= 6:
            set_trio(date_selects[3:6], biz.get("year"), biz.get("month"), biz.get("day"))
        else:
            log("[WARN] 営業開始日 select トリオ未検出")
    price = data.get("proposed_price_monthly")
    if price is not None:
        # 提案単価/月（type=number, placeholder=700000）— 本人希望の text も同 placeholder を
        # 使うが、そちらは type=text なので type=number で絞る
        price_inp = drawer.locator("input[type='number'][placeholder='700000']").first
        if price_inp.count():
            price_inp.fill(str(price))
        else:
            log("[WARN] 提案単価 input 未検出")
    price_range = data.get("personal_price_range") or {}
    if price_range.get("min") is not None or price_range.get("max") is not None:
        set_personal_price_range(drawer, price_range.get("min"), price_range.get("max"))
    comment = data.get("sales_comment")
    if comment is not None:
        set_textarea_by_label(drawer, "人材担当コメント", comment)
    # 提案方法（select: 1=先出しOK / 2=案件確認）
    set_select_by_label(drawer, "提案方法", data.get("proposal_method"))


def fill_skill_exp_info(page: Page, drawer: Locator, data: dict) -> None:
    set_checkbox_multi(drawer, "occupation_ids", data.get("occupation_ids"))
    set_checkbox_multi(drawer, "dev_process_ids", data.get("dev_process_ids"))
    summary = data.get("career_summary")
    if summary is not None:
        set_textarea_by_label(drawer, "スキル・経験サマリー", summary)
    # 情報から一括追加（career_summary をソースにスキルタグを自動追加）
    # 既定で有効、payload に bulk_add_from_info=False が明示されていればスキップ
    if data.get("bulk_add_from_info", True) and summary:
        click_bulk_add_skills(page, drawer)
    # メインスキル（頻出首位の言語・FW）のチェック
    main_skill = data.get("main_skill_name")
    if main_skill:
        set_main_skill(drawer, main_skill)


def fill_wish_info(page: Page, drawer: Locator, data: dict) -> None:
    if data.get("work_location") is not None:
        set_textarea_by_label(drawer, "希望の作業場所", data["work_location"])
    if data.get("work_content") is not None:
        set_textarea_by_label(drawer, "希望の作業内容", data["work_content"])
    if data.get("work_time") is not None:
        set_textarea_by_label(drawer, "希望の作業時間", data["work_time"])
    if data.get("other_wish") is not None:
        set_textarea_by_label(drawer, "その他希望", data["other_wish"])


def fill_invoice_info(page: Page, drawer: Locator, data: dict) -> None:
    """適格請求書発行事業者 登録番号（13桁半角数字）を入力する.

    - CRM の入力欄は placeholder='13桁半角数字を入力' の単一 text input。
      T プレフィックスは含めず 13 桁数字のみを渡す（payload 側で除去する）。
    - 既存値がある場合は上書きしない（空欄時のみ書き込み）。
    """
    number = data.get("registration_number_13")
    if not number:
        return
    inp = drawer.locator("input[placeholder='13桁半角数字を入力']").first
    if not inp.count():
        inp = drawer.locator("input[type='text']").first
    if not inp.count():
        log("[WARN] 登録番号 input 未検出")
        return
    cur = (inp.input_value() or "").strip()
    if cur:
        log("[SKIP] 適格請求書登録番号は既存値あり、上書きしない")
        return
    inp.click()
    inp.fill(str(number))


def set_select_by_option_texts(drawer: Locator, option_hints: list[str], value: str) -> bool:
    """option の text に hint がすべて含まれる <select> を 1 つ特定して value で選択.

    管理情報ドロワーには label のない select が複数並ぶため、選択肢のラベル文字列
    （例: ['営業終了', '取引停止']）で当該 select を識別する.
    """
    selects = drawer.locator("select")
    for i in range(selects.count()):
        s = selects.nth(i)
        try:
            opts = s.evaluate("el => Array.from(el.options).map(o => o.text)")
        except Exception:
            continue
        if all(any(h in opt for opt in opts) for h in option_hints):
            try:
                s.select_option(value=str(value))
            except Exception:
                try:
                    s.select_option(label=str(value))
                except Exception:
                    return False
            return True
    log(f"[WARN] select by options {option_hints} 未検出")
    return False


def fill_management_info(page: Page, drawer: Locator, data: dict) -> None:
    # 営業ステータス: 1=営業中 / 2=営業終了 / 3=営業不可 / 4=取引停止
    sales_status = data.get("sales_status")
    if sales_status is not None:
        set_select_by_option_texts(drawer, ["営業終了", "取引停止"], str(sales_status))


SECTION_PLAN = [
    ("基本情報", "basic_info", fill_basic_info),
    ("営業情報", "sales_info", fill_sales_info),
    ("スキル・経験情報", "skill_exp_info", fill_skill_exp_info),
    ("希望条件", "wish_info", fill_wish_info),
    ("管理情報", "management_info", fill_management_info),
    ("適格請求書発行事業者 登録番号", "invoice_info", fill_invoice_info),
]


# ---------- メイン ----------

def process_section(page: Page, internal_id: int, section: str, filler, data: dict) -> tuple[bool, str]:
    """1 セクションを処理. 戻り値: (success, message)"""
    if not data:
        return True, "skipped (no data)"
    if all(v is None or v == [] for v in data.values()):
        return True, "skipped (all null)"

    if not open_section(page, section):
        return False, "open failed"
    drawer = get_drawer(page, section)
    try:
        filler(page, drawer, data)
    except Exception as e:
        try:
            SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
            drawer.screenshot(path=str(SCREENSHOT_DIR / f"{section}_fill_err.png"))
        except Exception:
            pass
        close_drawer(page)
        return False, f"fill error: {e}"

    ok = save_drawer(page, drawer, internal_id)
    close_drawer(page)
    return ok, "saved" if ok else "save failed"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("payload", help="payload.json path")
    parser.add_argument("--headless", action="store_true", default=True)
    parser.add_argument("--no-headless", dest="headless", action="store_false")
    parser.add_argument("--internal-id", type=int, help="既知の内部ID（指定時は ID 解決をスキップ）")
    parser.add_argument("--dry-run", action="store_true", help="ドロワー開閉のみで保存しない")
    parser.add_argument(
        "--notify",
        choices=["auto", "on", "off"],
        default="auto",
        help="Slack 通知 (auto: $SLACK_WEBHOOK_NOTIFICATION_URL があれば on / dry-run は off)",
    )
    parser.add_argument(
        "--keep-screenshots",
        action="store_true",
        help="失敗時 screenshot を tmp に残す（デフォルトは実行後削除。PII を含む）",
    )
    args = parser.parse_args()

    payload_path = Path(args.payload)
    payload = json.loads(payload_path.read_text(encoding="utf-8"))
    management_id = payload.get("candidate_id")
    if not management_id:
        print("[ERR] payload.candidate_id が必要", file=sys.stderr)
        return 2

    results: list[tuple[str, bool, str]] = []
    internal_id: int | None = args.internal_id

    with sync_playwright() as pw:
        browser, context, page = fb.login(pw, headless=args.headless)
        try:
            if internal_id is None:
                internal_id = resolve_internal_id(page, management_id)
            if internal_id is None:
                log(f"[ERR] 内部ID 解決失敗: {management_id}")
                results.append(("ID解決", False, "internal_id 解決失敗"))
            else:
                log(f"internal_id={internal_id} management_id={management_id}")
                page.goto(
                    f"https://freelancebase.jp/enterprise/candidates/{internal_id}#outline-tab",
                    wait_until="networkidle",
                )
                page.wait_for_timeout(3000)

                for section, key, filler in SECTION_PLAN:
                    data = payload.get(key) or {}
                    if args.dry_run:
                        if not open_section(page, section):
                            results.append((section, False, "open failed"))
                            continue
                        close_drawer(page)
                        results.append((section, True, "dry-run open/close"))
                        continue
                    ok, msg = process_section(page, internal_id, section, filler, data)
                    results.append((section, ok, msg))
                    log(f"{section}: {'OK' if ok else 'NG'} — {msg}")
        finally:
            browser.close()

    print("\n=== 書き込み結果 ===")
    for s, ok, m in results:
        print(f"  [{'OK' if ok else 'NG'}] {s}: {m}")

    # Slack 通知
    screenshots: list[Path] = (
        sorted(SCREENSHOT_DIR.glob("*.png")) if SCREENSHOT_DIR.exists() else []
    )
    webhook = os.environ.get("SLACK_WEBHOOK_NOTIFICATION_URL", "").strip()
    notify_enabled = (args.notify == "on") or (
        args.notify == "auto" and webhook and not args.dry_run
    )
    if notify_enabled:
        if not webhook:
            log("[WARN] --notify 要求だが SLACK_WEBHOOK_NOTIFICATION_URL 未設定")
        else:
            notify_slack(webhook, management_id, internal_id, results, args.dry_run, screenshots)

    # screenshot のクリーンアップ（PII 対策）
    if screenshots and not args.keep_screenshots:
        shutil.rmtree(SCREENSHOT_DIR, ignore_errors=True)
        log(f"[INFO] screenshots {len(screenshots)} 件を削除（--keep-screenshots で保持可）")
    elif screenshots:
        log(f"[INFO] screenshots 保持: {SCREENSHOT_DIR}（PII 注意）")

    return 0 if all(ok for _, ok, _ in results) else 1


if __name__ == "__main__":
    sys.exit(main())
