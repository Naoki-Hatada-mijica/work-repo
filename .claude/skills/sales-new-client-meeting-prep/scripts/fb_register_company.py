"""FreelanceBase 企業登録＋担当者追加＋レポート投稿スクリプト

sales-new-client-meeting-prep スキルから呼ばれる。

フロー:
  1. ログイン (playwright_freelancebase.login)
  2. /enterprise/companies に goto
  3. クイック検索で社名検索
  4. ヒットあり → 既存企業の詳細画面を開く
     ヒットなし → 新規作成
  5. 「企業担当者」タブ → 既存担当者の重複チェック → 必要なら新規作成
  6. 「コメント」タブ → report.md 全文をコメント投稿

使用例:
  python3 fb_register_company.py \
    --company-name "株式会社サンプル" \
    --homepage "https://www.example.co.jp/" \
    --phone "03-1111-1111" \
    --contact-name "山田" \
    --contact-email "contact@example.co.jp" \
    --report-path "02_task/20260527-新規商談準備_サンプル社/report.md"

  --headless     ヘッドレスで実行
  --dry-run      実際の書き込みは行わない（流れの確認のみ）
  --self-owner   自社担当者1 にセットする氏名（デフォルト: 赤木 宏志）

  --company-type は指定可（"エンド" "元請け" "パートナー" "その他"）。
  デフォルトは未選択（チェックボックスを触らない）。
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, __import__("os").path.expanduser("~/.claude/snippets"))
import playwright_freelancebase as fb  # type: ignore
from freelancebase.companies import search_company_id_from_table
from freelancebase.core import COMPANIES_URL
from playwright.sync_api import Page, TimeoutError as PWTimeoutError, sync_playwright

import re

DEFAULT_SELF_OWNER = "赤木 宏志"
_COMPANY_DETAIL_RE = re.compile(r"/enterprise/companies/\d+")


def _is_company_detail_url(url: str) -> bool:
    return bool(_COMPANY_DETAIL_RE.search(url))


def log(msg: str) -> None:
    print(f"[fb_register] {msg}", file=sys.stderr)


def confirm(prompt: str) -> bool:
    """対話的に y/n を聞く（dry-run 時は False）"""
    sys.stderr.write(f"{prompt} [y/N]: ")
    sys.stderr.flush()
    try:
        ans = input().strip().lower()
    except EOFError:
        return False
    return ans in ("y", "yes")


def search_company(page: Page, name: str) -> str | None:
    """クイック検索で社名検索し、ヒットしたら最初の企業の詳細URL（/companies/{id}）を返す。ヒットなしなら None"""
    company_id = search_company_id_from_table(page, name)

    # 「検索条件に一致する企業はありません」をチェック
    no_result = page.get_by_text("検索条件に一致する企業はありません", exact=False)
    if company_id is None and no_result.count() > 0 and no_result.first.is_visible():
        log(f"検索結果: ヒットなし ('{name}')")
        return None

    if not company_id:
        log(f"[WARN] 企業ID が取れない（ヒット表示はあるが行抽出失敗）")
        screenshot_on_fail(page, "search_no_id")
        return None

    log(f"検索結果: 1件以上ヒット → 企業ID={company_id} の詳細画面へ直接 goto")
    detail_url = f"{COMPANIES_URL}/{company_id}"
    page.goto(detail_url, wait_until="networkidle")
    page.wait_for_timeout(2500)
    if _is_company_detail_url(page.url):
        log(f"既存企業詳細: {page.url}")
        return page.url

    log(f"[WARN] 詳細画面遷移失敗 URL={page.url}")
    screenshot_on_fail(page, "detail_goto_fail")
    return None


def set_self_owner_by_label(page: Page, owner_name: str) -> str:
    """ラベル「自社担当者1」直近の select に owner_name をセット（Vue.js 用に change/input イベントも dispatch）

    戻り値: 'ok' / 'label_not_found' / 'select_not_found' / 'option_not_found'
    """
    return page.evaluate(
        """
        (ownerName) => {
            const all = Array.from(document.querySelectorAll('*'));
            const label = all.find(e =>
                (e.innerText || '').trim() === '自社担当者1' &&
                e.children.length === 0
            );
            if (!label) return 'label_not_found';
            let parent = label.parentElement;
            let select = null;
            for (let i = 0; i < 8 && parent && !select; i++) {
                select = parent.querySelector('select');
                if (!select) parent = parent.parentElement;
            }
            if (!select) return 'select_not_found';
            const opt = Array.from(select.options).find(o => o.text.trim() === ownerName);
            if (!opt) return 'option_not_found';
            select.value = opt.value;
            select.dispatchEvent(new Event('change', {bubbles: true}));
            select.dispatchEvent(new Event('input', {bubbles: true}));
            return 'ok';
        }
        """,
        owner_name,
    )


def select_company_type(page: Page, type_label: str) -> None:
    """企業タイプ checkbox を選択。エンド/元請け/パートナー/その他

    実体の <input type="checkbox" name="company_type_ids"> は視覚的に非表示
    （Vue のカスタムチェックボックスで label/span が装飾を担う）。
    そのまま .check() すると "element is not visible" でタイムアウトするため、
    input を内包する可視ラベルをクリックして toggle し、状態を検証する。
    """
    try:
        # 各オプションは company_type_ids の input を直接内包する label。
        # その中で該当テキストを持つラベル（=エンド等の単一オプション）を特定する。
        option = page.locator(
            f"label:has(input[name='company_type_ids']):has-text('{type_label}')"
        ).first
        if option.count() == 0:
            # フォールバック: 完全一致テキストでクリック対象を探す
            option = page.get_by_text(type_label, exact=True).first
        cb = option.locator("input[type='checkbox']").first

        if cb.count() and cb.is_checked():
            log(f"企業タイプ 既にチェック済み: {type_label}")
            return

        option.click()
        page.wait_for_timeout(200)

        # クリックで反映されなければ force でフォールバック
        if cb.count() and not cb.is_checked():
            cb.check(force=True)
            page.wait_for_timeout(200)

        if cb.count() and not cb.is_checked():
            log(f"[WARN] 企業タイプ {type_label}: クリック後もチェックされていません")
        else:
            log(f"企業タイプ チェック: {type_label}")
    except Exception as e:
        log(f"[WARN] 企業タイプ {type_label}: {e}")


def screenshot_on_fail(page: Page, prefix: str) -> None:
    p = f"/tmp/fb_register_{prefix}_{int(time.time())}.png"
    try:
        page.screenshot(path=p, full_page=True)
        log(f"[DEBUG] screenshot: {p}")
    except Exception:
        pass


def create_company(
    page: Page,
    name: str,
    homepage: str | None,
    phone: str | None,
    company_type: str | None,
    self_owner: str | None,
) -> str:
    """新規企業作成。作成後の詳細URLを返す"""
    # 一覧画面右上の「企業を作成」ボタン
    page.get_by_role("button", name="企業を作成").first.click()
    # ドロワー内の「企業名」プレースホルダ入力欄を待つ
    try:
        page.wait_for_selector("input[placeholder='INSTANTROOM株式会社']", state="visible", timeout=10000)
    except PWTimeoutError:
        screenshot_on_fail(page, "drawer_open")
        raise

    # ページ全体で fill（ドロワー内のフィールドはプレースホルダが unique）
    page.locator("input[placeholder='INSTANTROOM株式会社']").first.fill(name)
    if homepage:
        page.locator("input[placeholder='https://freelancebase.jp/']").first.fill(homepage)
    if phone:
        page.locator("input[placeholder='03-1111-1111']").first.fill(phone)
    if company_type:
        select_company_type(page, company_type)
    if self_owner:
        # ドロワーのレンダリングが落ち着くまで少し待ってから set
        page.wait_for_timeout(800)
        result = set_self_owner_by_label(page, self_owner)
        if result == "ok":
            log(f"自社担当者1 セット: {self_owner}")
        else:
            log(f"[WARN] 自社担当者1 セット失敗: {result}")

    page.wait_for_timeout(800)
    # 保存ボタン: 「企業を作成」テキストの primary ボタン。
    # 一覧画面の「企業を作成」ボタンとドロワー内の保存ボタンが両方存在するため、
    # 「キャンセル」ボタンの兄弟である方（=フォーム送信側）を取る
    save_btn = page.locator("button.bg-primary").filter(has_text="企業を作成").last
    save_btn.click()
    log("新規企業 保存ボタン押下、詳細画面への遷移を待機...")
    try:
        page.wait_for_url("**/enterprise/companies/*", timeout=15000)
    except PWTimeoutError:
        log("[INFO] 自動遷移しなかったので、検索しなおして詳細画面を開く")
    page.wait_for_timeout(2000)

    if _is_company_detail_url(page.url):
        log(f"新規企業作成完了: {page.url}")
        return page.url

    # 保存後にドロワーが閉じて一覧に戻る挙動の場合、再検索して開く
    url = search_company(page, name)
    if url:
        log(f"新規企業作成完了 (再検索経由): {url}")
        return url
    screenshot_on_fail(page, "create_no_detail")
    raise RuntimeError("新規企業作成後の詳細画面到達に失敗")


def list_existing_contacts(page: Page) -> list[dict]:
    """企業担当者タブを開き、既存担当者の (name, email) を返す"""
    tab = page.get_by_role("tab", name="企業担当者").first
    if tab.count() == 0:
        # ナビゲーション要素として存在する場合
        tab = page.locator("a, button").filter(has_text="企業担当者").first
    tab.click()
    page.wait_for_timeout(2500)

    contacts = []
    rows = page.locator("table tbody tr").all()
    for r in rows[:50]:
        try:
            cells = r.locator("td").all()
            if len(cells) >= 3:
                name = cells[1].inner_text().strip()
                email = cells[3].inner_text().strip() if len(cells) > 3 else ""
                if name:
                    contacts.append({"name": name, "email": email})
        except Exception:
            pass
    log(f"既存担当者: {len(contacts)}件")
    return contacts


def create_contact(
    page: Page,
    contact_name: str,
    contact_email: str | None,
    contact_phone: str | None,
    self_owner: str | None,
) -> None:
    """企業担当者を作成"""
    btn = page.get_by_role("button", name="企業担当者を作成").first
    btn.click()
    page.wait_for_timeout(2500)

    # 氏名フィールドは「姓 placeholder=田中」と「名 placeholder=太郎」の2分割
    try:
        page.wait_for_selector("input[placeholder='田中']", state="visible", timeout=10000)
    except PWTimeoutError:
        screenshot_on_fail(page, "contact_drawer_open")
        raise

    # contact_name を姓/名に分割（空白区切りがあれば姓・名、なければ全部姓に）
    parts = contact_name.split(None, 1)
    last_name = parts[0]
    first_name = parts[1] if len(parts) > 1 else ""

    page.locator("input[placeholder='田中']").last.fill(last_name)
    if first_name:
        page.locator("input[placeholder='太郎']").last.fill(first_name)
    log(f"氏名入力: 姓='{last_name}' 名='{first_name}'")

    # メールアドレス
    if contact_email:
        try:
            page.locator("input[placeholder='contact@freelancebase.jp']").last.fill(contact_email)
            log(f"メール入力: {contact_email}")
        except Exception as e:
            log(f"[WARN] メール入力失敗: {e}")

    if contact_phone:
        try:
            page.locator("input[placeholder='03-1111-1111']").last.fill(contact_phone)
        except Exception:
            pass

    if self_owner:
        page.wait_for_timeout(800)
        result = set_self_owner_by_label(page, self_owner)
        if result == "ok":
            log(f"自社担当者1 セット: {self_owner}")
        else:
            log(f"[WARN] 自社担当者1 セット失敗: {result}")

    page.wait_for_timeout(800)
    # 保存ボタン: JS click（テキスト '企業担当者を作成'）
    saved = page.evaluate(
        """
        () => {
            const btns = Array.from(document.querySelectorAll('button'));
            // 最後の保存ボタン（ドロワー内）を取得するために reverse して find
            const t = btns.reverse().find(b => (b.innerText || '').trim() === '企業担当者を作成');
            if (t) { t.click(); return true; }
            return false;
        }
        """
    )
    log(f"[INFO] JS click 企業担当者保存ボタン: {saved}")
    page.wait_for_timeout(4000)

    # 氏名フィールド（placeholder='田中'）が消えていれば保存成功
    if page.locator("input[placeholder='田中']").count() == 0:
        log("担当者作成 保存完了")
    else:
        screenshot_on_fail(page, "contact_save_failed")
        log("[WARN] 担当者ドロワーが閉じていない → バリデーションエラー等の可能性")


def _js_click_text(page: Page, prefix: str, tags: tuple[str, ...] = ("button", "a", "li", "span", "div")) -> bool:
    """テキストが prefix で始まる最初の要素を JS で click"""
    selector = ", ".join(tags)
    return bool(page.evaluate(
        """
        ([selector, prefix]) => {
            const els = Array.from(document.querySelectorAll(selector));
            const t = els.find(e => (e.innerText || '').trim().startsWith(prefix) && (e.innerText || '').trim().length < 60);
            if (t) { t.click(); return true; }
            return false;
        }
        """,
        [selector, prefix],
    ))


def create_comment(page: Page, body: str) -> None:
    """コメントタブで report 全文を投稿"""
    # タブテキストは「コメント(N件)」形式。正規表現で厳密にマッチさせ、最も内側の要素を click
    clicked = page.evaluate(
        """
        () => {
            const all = Array.from(document.querySelectorAll('button, a, li, span, div'));
            const re = /^コメント\\(\\d+件\\)$/;
            const candidates = all.filter(e => re.test((e.innerText || '').trim()));
            // innerText が同一かつ最も子要素が少ない＝最も内側を click
            candidates.sort((a, b) => a.children.length - b.children.length);
            if (candidates[0]) { candidates[0].click(); return true; }
            return false;
        }
        """
    )
    log(f"[INFO] JS click 'コメント(N件)' tab: {clicked}")
    page.wait_for_timeout(2500)

    # 「コメントを作成」ボタン
    clicked_btn = page.evaluate(
        """
        () => {
            const btns = Array.from(document.querySelectorAll('button'));
            const t = btns.find(b => (b.innerText || '').trim() === 'コメントを作成');
            if (t) { t.click(); return true; }
            return false;
        }
        """
    )
    log(f"[INFO] JS click 'コメントを作成' ボタン: {clicked_btn}")
    page.wait_for_timeout(2500)

    try:
        page.wait_for_selector("textarea", state="visible", timeout=10000)
    except PWTimeoutError:
        screenshot_on_fail(page, "comment_drawer_open")
        raise
    textarea = page.locator("textarea").last
    textarea.fill(body)
    page.wait_for_timeout(800)

    # コメントモーダルの保存ボタンは「コメントを投稿」
    saved = page.evaluate(
        """
        () => {
            const btns = Array.from(document.querySelectorAll('button'));
            const t = btns.reverse().find(b => {
                const txt = (b.innerText || '').trim();
                return txt === 'コメントを投稿';
            });
            if (t) { t.click(); return true; }
            return false;
        }
        """
    )
    log(f"[INFO] JS click 'コメントを投稿' ボタン: {saved}")
    page.wait_for_timeout(4000)
    page.wait_for_timeout(3500)
    log("コメント投稿完了")


def run(args: argparse.Namespace) -> int:
    report_text = Path(args.report_path).read_text(encoding="utf-8") if args.report_path else ""

    with sync_playwright() as pw:
        browser, context, page = fb.login(pw, headless=args.headless)
        try:
            # 1-4. 検索
            detail_url = search_company(page, args.company_name)

            if args.dry_run:
                if detail_url:
                    log(f"[DRY-RUN] 既存企業がヒット: {detail_url} → 担当者追加とコメント投稿の予定")
                else:
                    log(f"[DRY-RUN] 未登録 → 新規作成 + 担当者 + コメントの予定")
                return 0

            # 5. 既存なし → 新規作成
            if not detail_url:
                detail_url = create_company(
                    page,
                    name=args.company_name,
                    homepage=args.homepage,
                    phone=args.phone,
                    company_type=args.company_type,
                    self_owner=args.self_owner,
                )

            # 6. 担当者
            if args.contact_name:
                existing = list_existing_contacts(page)
                dup = [
                    c for c in existing
                    if c["name"] == args.contact_name
                    or (args.contact_email and c["email"] == args.contact_email)
                ]
                if dup:
                    log(f"重複担当者検出: {dup}")
                    if not confirm("それでも新しい担当者を追加しますか？"):
                        log("担当者作成をスキップ")
                    else:
                        create_contact(page, args.contact_name, args.contact_email, args.contact_phone, args.self_owner)
                else:
                    create_contact(page, args.contact_name, args.contact_email, args.contact_phone, args.self_owner)

            # 7. コメント投稿
            if report_text:
                create_comment(page, report_text)

            log(f"完了: {detail_url}")
            print(detail_url)
            return 0
        finally:
            if not args.headless:
                page.wait_for_timeout(5000)
            browser.close()


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--company-name", required=True)
    p.add_argument("--company-type", default=None, choices=[None, "エンド", "元請け", "パートナー", "その他"])
    p.add_argument("--homepage", default=None)
    p.add_argument("--phone", default=None)
    p.add_argument("--contact-name", default=None)
    p.add_argument("--contact-email", default=None)
    p.add_argument("--contact-phone", default=None)
    p.add_argument("--report-path", default=None)
    p.add_argument("--self-owner", default=DEFAULT_SELF_OWNER)
    p.add_argument("--headless", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    return run(args)


if __name__ == "__main__":
    sys.exit(main())
