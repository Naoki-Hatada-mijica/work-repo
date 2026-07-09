#!/usr/bin/env python3
"""Non-destructive CRUD surface probe for all known FreelanceBase pages."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

SNIPPETS_DIR = Path(__file__).resolve().parents[1]
if str(SNIPPETS_DIR) not in sys.path:
    sys.path.insert(0, str(SNIPPETS_DIR))

from playwright.sync_api import TimeoutError as PWTimeoutError, sync_playwright  # noqa: E402

import playwright_freelancebase as fb  # noqa: E402
from freelancebase.api import ApiRecorder, is_destructive_candidate  # noqa: E402
from freelancebase.core import BASE_URL, build_url, ensure_local_output_dir  # noqa: E402


@dataclass(frozen=True)
class RouteSpec:
    name: str
    path: str
    category: str
    detail_path: str | None = None
    id_header_candidates: tuple[str, ...] = ()


ROUTES: list[RouteSpec] = [
    RouteSpec("人材", "/enterprise/candidates#view-1", "core", "/enterprise/candidates/{id}", ("人材ID",)),
    RouteSpec("企業", "/enterprise/companies#view-2", "core", "/enterprise/companies/{id}", ("企業ID",)),
    RouteSpec("企業担当者", "/enterprise/company_members#view-9", "core", "/enterprise/company_members/{id}", ("企業担当者ID", "担当者ID")),
    RouteSpec("案件", "/enterprise/jobs#view-3", "core", "/enterprise/jobs/{id}", ("案件ID",)),
    RouteSpec("商談", "/enterprise/opportunities#view-4", "core", "/enterprise/opportunities/{id}", ("商談ID",)),
    RouteSpec("契約", "/enterprise/contracts#view-5", "contract", "/enterprise/contracts/{id}", ("契約ID",)),
    RouteSpec("稼働", "/enterprise/contract_operations#view-6", "contract", None, ("稼働ID",)),
    RouteSpec("請求・支払", "/enterprise/billing_payments#view-7", "contract", None, ("請求・支払ID",)),
    RouteSpec("合算請求書", "/enterprise/billing_merges#view-10", "contract", None, ("合算請求書ID",)),
    RouteSpec("自動化", "/enterprise/automation_emails#new-tab", "marketing"),
    RouteSpec("フォーム", "/enterprise/questionnaire_forms", "marketing"),
    RouteSpec("配信", "/enterprise/broadcasts#all-tab", "marketing"),
    RouteSpec("案件サイト", "/enterprise/sites#contents-tab_mainvisual-menu", "marketing"),
    RouteSpec("記事", "/enterprise/articles", "marketing"),
    RouteSpec("提案", "/enterprise/restrictions/proposals", "proposal"),
    RouteSpec("応募", "/enterprise/applies#view-8", "apply"),
    RouteSpec("レポート", "/enterprise/report_summaries/contract", "report"),
    RouteSpec("担当別レポート", "/enterprise/report_billing_payments", "report"),
    RouteSpec("商談レポート", "/enterprise/report_opportunities", "report"),
]

CREATE_RE = re.compile(r"(を作成|新規作成|追加)$")
SKIP_CREATE_TEXTS = {
    "インポート",
    "エクスポート",
    "詳細フィルター",
    "表示列を編集",
    "ビューを保存",
    "営業担当に相談する",
}
DELETE_RE = re.compile(r"(削除|アーカイブ|解除|公開停止$|停止する)")
UPDATE_TEXTS = {"編集する", "変更", "保存する", "保存"}
WRITE_LIKE_RE = re.compile(
    r"^(保存|保存する|公開する|リリース|下書き保存|本番に公開|"
    r"成約を確定|見送り|辞退|合算請求候補を抽出|処理順を編集)$"
)
VIEW_SETTING_TEXTS = {"ビューを保存", "表示列を編集", "詳細フィルター", "詳細フィルター(2件)"}
NUMERIC_PATH_RE = re.compile(r"/\d+(?=/?(?:#|\?|$))")


@dataclass
class Surface:
    kind: str
    trigger: str
    title: str = ""
    buttons: list[str] = field(default_factory=list)
    inputs: list[dict[str, Any]] = field(default_factory=list)
    tables: list[dict[str, Any]] = field(default_factory=list)


def _visible_texts(page: Any, selector: str, limit: int = 100) -> list[str]:
    return page.evaluate(
        """({selector, limit}) => {
            const visible = el => {
                const r = el.getBoundingClientRect();
                const s = getComputedStyle(el);
                return r.width > 0 && r.height > 0 && s.display !== 'none' && s.visibility !== 'hidden';
            };
            return Array.from(document.querySelectorAll(selector))
                .filter(visible)
                .map(e => ((e.innerText || e.textContent || e.getAttribute('aria-label') || '') + '').replace(/\\s+/g, ' ').trim())
                .filter(Boolean)
                .filter(t => t.length <= 120)
                .slice(0, limit);
        }""",
        {"selector": selector, "limit": limit},
    )


def collect_page_summary(page: Any) -> dict[str, Any]:
    return page.evaluate(
        """() => {
            const visible = el => {
                const r = el.getBoundingClientRect();
                const s = getComputedStyle(el);
                return r.width > 0 && r.height > 0 && s.display !== 'none' && s.visibility !== 'hidden';
            };
            const txt = el => ((el.innerText || el.textContent || el.getAttribute('aria-label') || '') + '').replace(/\\s+/g, ' ').trim().slice(0, 160);
            const inputs = Array.from(document.querySelectorAll('input, textarea, select')).filter(visible).map(el => ({
                tag: el.tagName.toLowerCase(),
                type: el.getAttribute('type') || '',
                name: el.getAttribute('name') || '',
                placeholder: el.getAttribute('placeholder') || '',
                ariaLabel: el.getAttribute('aria-label') || '',
                optionCount: el.tagName === 'SELECT' ? el.options.length : undefined,
            })).slice(0, 120);
            const tables = Array.from(document.querySelectorAll('table')).filter(visible).map(t => ({
                headers: Array.from(t.querySelectorAll('th')).map(txt).filter(Boolean),
                rowCount: t.querySelectorAll('tbody tr').length,
                firstRowCellCount: t.querySelector('tbody tr') ? t.querySelector('tbody tr').querySelectorAll('td').length : 0,
            })).slice(0, 20);
            return {
                url: location.href,
                title: document.title,
                headings: Array.from(document.querySelectorAll('h1,h2,h3,h4,h5,h6')).filter(visible).map(txt).filter(Boolean).slice(0, 40),
                buttons: Array.from(document.querySelectorAll('button')).filter(visible).map(txt).filter(Boolean).slice(0, 80),
                tabs: Array.from(document.querySelectorAll('[role=tab], a[href^="#"]')).filter(visible).map(txt).filter(Boolean).slice(0, 80),
                inputs,
                tables,
            };
        }"""
    )


def normalize_href(href: str | None) -> str:
    if not href:
        return ""
    path = href.replace(BASE_URL, "")
    path = path.split("?", 1)[0]
    return NUMERIC_PATH_RE.sub("/{id}", path)


def normalize_row_affordances(row: dict[str, Any]) -> dict[str, Any]:
    return {
        **row,
        "linkHrefs": sorted({normalize_href(href) for href in row.get("linkHrefs", []) if href}),
    }


def collect_row_affordances(page: Any) -> dict[str, Any]:
    """Collect first-row action shapes without cell values."""
    return page.evaluate(
        """() => {
            const visible = el => {
                const r = el.getBoundingClientRect();
                const s = getComputedStyle(el);
                return r.width > 0 && r.height > 0 && s.display !== 'none' && s.visibility !== 'hidden';
            };
            const txt = el => ((el.innerText || el.textContent || el.getAttribute('aria-label') || '') + '').replace(/\\s+/g, ' ').trim().slice(0, 80);
            const row = document.querySelector('table tbody tr');
            if (!row) return {hasRow: false, cellCount: 0, linkHrefs: [], buttonLabels: [], actionLabels: []};
            const links = Array.from(row.querySelectorAll('a[href]')).filter(visible).map(a => a.href).filter(Boolean).slice(0, 20);
            const buttons = Array.from(row.querySelectorAll('button')).filter(visible).map(txt).filter(Boolean).slice(0, 20);
            const actionLike = Array.from(row.querySelectorAll('button, a, [role=button], span, div'))
                .filter(visible)
                .map(txt)
                .filter(t => t && t.length <= 40)
                .filter(t => /(詳細|編集|表示|開く|見る|作成|出力|承認|見送り|辞退|削除|停止|変更|アクション|⋮|…)/.test(t))
                .slice(0, 30);
            return {
                hasRow: true,
                cellCount: row.querySelectorAll('td').length,
                linkHrefs: links,
                buttonLabels: buttons,
                actionLabels: Array.from(new Set(actionLike)),
            };
        }"""
    )


def collect_overlay(page: Any, kind: str, trigger: str) -> Surface:
    data = page.evaluate(
        """() => {
            const visible = el => {
                const r = el.getBoundingClientRect();
                const s = getComputedStyle(el);
                return r.width > 0 && r.height > 0 && s.display !== 'none' && s.visibility !== 'hidden';
            };
            const txt = el => ((el.innerText || el.textContent || el.getAttribute('aria-label') || '') + '').replace(/\\s+/g, ' ').trim().slice(0, 160);
            const roots = Array.from(document.querySelectorAll('.modal_content, [role=dialog], .modal, .drawer, body'))
                .filter(visible);
            const root = roots.find(r => r !== document.body && r.querySelector('input,textarea,select,button')) || document.body;
            const inputs = Array.from(root.querySelectorAll('input, textarea, select')).filter(visible).map(el => ({
                tag: el.tagName.toLowerCase(),
                type: el.getAttribute('type') || '',
                name: el.getAttribute('name') || '',
                placeholder: el.getAttribute('placeholder') || '',
                ariaLabel: el.getAttribute('aria-label') || '',
                optionCount: el.tagName === 'SELECT' ? el.options.length : undefined,
            })).slice(0, 120);
            const tables = Array.from(root.querySelectorAll('table')).filter(visible).map(t => ({
                headers: Array.from(t.querySelectorAll('th')).map(txt).filter(Boolean),
                rowCount: t.querySelectorAll('tbody tr').length,
            })).slice(0, 20);
            return {
                title: Array.from(root.querySelectorAll('h1,h2,h3,h4,h5,h6')).filter(visible).map(txt).find(Boolean) || txt(root).slice(0, 80),
                buttons: Array.from(root.querySelectorAll('button')).filter(visible).map(txt).filter(Boolean).slice(0, 60),
                inputs,
                tables,
            };
        }"""
    )
    return Surface(kind=kind, trigger=trigger, **data)


def close_overlay(page: Any) -> None:
    for text in ("キャンセル", "閉じる"):
        clicked = page.evaluate(
            """(text) => {
                const visible = el => {
                    const r = el.getBoundingClientRect();
                    const s = getComputedStyle(el);
                    return r.width > 0 && r.height > 0 && s.display !== 'none' && s.visibility !== 'hidden';
                };
                const els = Array.from(document.querySelectorAll('button, a, span, div'))
                  .filter(visible)
                  .filter(e => ((e.innerText || '') + '').replace(/\\s+/g, ' ').trim() === text);
                els.sort((a,b) => a.children.length - b.children.length);
                if (els[0]) { els[0].click(); return true; }
                return false;
            }""",
            text,
        )
        if clicked:
            page.wait_for_timeout(800)
            return
    try:
        page.keyboard.press("Escape")
        page.wait_for_timeout(500)
    except Exception:
        pass


def click_visible_exact(page: Any, text: str, *, prefer_button: bool = False) -> bool:
    return bool(
        page.evaluate(
            """([text, preferButton]) => {
                const visible = el => {
                    const r = el.getBoundingClientRect();
                    const s = getComputedStyle(el);
                    return r.width > 0 && r.height > 0 && s.display !== 'none' && s.visibility !== 'hidden';
                };
                const els = Array.from(document.querySelectorAll('button, a, li, span, div'))
                  .filter(visible)
                  .filter(e => ((e.innerText || e.textContent || '') + '').replace(/\\s+/g, ' ').trim() === text);
                els.sort((a,b) => {
                    if (preferButton && a.tagName !== b.tagName) {
                        if (a.tagName === 'BUTTON') return -1;
                        if (b.tagName === 'BUTTON') return 1;
                    }
                    return a.children.length - b.children.length;
                });
                if (els[0]) { els[0].click(); return true; }
                return false;
            }""",
            [text, prefer_button],
        )
    )


def create_triggers(buttons: list[str]) -> list[str]:
    out: list[str] = []
    for text in buttons:
        if text in SKIP_CREATE_TEXTS:
            continue
        if CREATE_RE.search(text) and text not in out:
            out.append(text)
    return out[:5]


def update_triggers(buttons: list[str]) -> list[str]:
    return sorted({text for text in buttons if text in UPDATE_TEXTS})


def delete_triggers(buttons: list[str]) -> list[str]:
    return sorted({text for text in buttons if DELETE_RE.search(text)})


def write_like_actions(buttons: list[str]) -> list[str]:
    return sorted(
        {
            text
            for text in buttons
            if text not in VIEW_SETTING_TEXTS and WRITE_LIKE_RE.search(text)
        }
    )


def inspect_create_surfaces(page: Any, triggers: list[str]) -> list[Surface]:
    surfaces: list[Surface] = []
    for trigger in triggers:
        if not click_visible_exact(page, trigger, prefer_button=True):
            continue
        page.wait_for_timeout(1000)
        menu_items = _visible_texts(page, ".ele-dropdown-body a, .ele-dropdown-body li, [role=menu] *, a, li", limit=40)
        chosen = None
        for candidate in ("通常作成", "新規作成", "手動作成", "作成"):
            if candidate in menu_items and click_visible_exact(page, candidate):
                chosen = candidate
                page.wait_for_timeout(1500)
                break
        actual_trigger = f"{trigger} > {chosen}" if chosen else trigger
        surfaces.append(collect_overlay(page, "create", actual_trigger))
        close_overlay(page)
        page.wait_for_timeout(700)
    return surfaces


def first_row_id(page: Any, id_headers: tuple[str, ...]) -> str | None:
    if not id_headers:
        return None
    return page.evaluate(
        """(idHeaders) => {
            const norm = s => ((s || '') + '').replace(/\\s+/g, '').trim();
            const ths = Array.from(document.querySelectorAll('table thead th'));
            const headers = ths.map(th => norm(th.innerText));
            let idx = -1;
            for (const h of idHeaders) {
                idx = headers.indexOf(norm(h));
                if (idx >= 0) break;
            }
            if (idx < 0) return null;
            const row = document.querySelector('table tbody tr');
            if (!row) return null;
            const cells = Array.from(row.querySelectorAll('td'));
            if (!cells[idx]) return null;
            const value = norm(cells[idx].innerText);
            return /^[0-9]+$/.test(value) ? value : null;
        }""",
        list(id_headers),
    )


def inspect_detail_surface(page: Any, route: RouteSpec) -> tuple[Surface | None, list[Surface]]:
    if route.detail_path:
        rid = first_row_id(page, route.id_header_candidates)
        if rid:
            try:
                page.goto(build_url(route.detail_path.format(id=rid)), wait_until="networkidle", timeout=12_000)
                page.wait_for_timeout(1500)
            except Exception:
                pass
    tables = page.locator("table tbody tr")
    if route.detail_path and "/enterprise/" in page.url and re.search(r"/\d+", page.url):
        detail = collect_overlay(page, "detail", "first visible row id direct")
    elif tables.count() == 0:
        return None, []
    else:
        try:
            tables.first.click(force=True)
            page.wait_for_timeout(1300)
        except Exception:
            return None, []
        if page.get_by_text("詳細を見る", exact=True).count() > 0:
            try:
                page.get_by_text("詳細を見る", exact=True).first.click(force=True)
                page.wait_for_load_state("networkidle", timeout=10_000)
                page.wait_for_timeout(1500)
            except Exception:
                page.wait_for_timeout(1000)
        detail = collect_overlay(page, "detail", "first visible row")
    edit_surfaces: list[Surface] = []
    edit_buttons = _visible_texts(page, "button", limit=120)
    if "編集する" in edit_buttons and click_visible_exact(page, "編集する"):
        page.wait_for_timeout(1200)
        edit_surfaces.append(collect_overlay(page, "update", "編集する"))
        close_overlay(page)
    return detail, edit_surfaces


def probe_route(page: Any, route: RouteSpec, *, include_detail: bool = True) -> dict[str, Any]:
    with ApiRecorder(page) as recorder:
        page.goto(build_url(route.path), wait_until="networkidle")
        page.wait_for_timeout(2200)
        summary = collect_page_summary(page)
        row_affordances = normalize_row_affordances(collect_row_affordances(page))
        create = inspect_create_surfaces(page, create_triggers(summary.get("buttons", [])))
        detail = None
        updates: list[Surface] = []
        if include_detail:
            detail, updates = inspect_detail_surface(page, route)
        page.wait_for_timeout(300)
    buttons = summary.get("buttons", [])
    api_calls = recorder.to_dicts()
    return {
        "name": route.name,
        "category": route.category,
        "path": route.path,
        "final_url": summary.get("url"),
        "title": summary.get("title"),
        "list": summary,
        "crud": {
            "list": bool(summary.get("tables")) or any("/index" in c.get("path", "") for c in api_calls),
            "row_affordances": row_affordances,
            "create_triggers": create_triggers(buttons),
            "create_surfaces": [asdict(s) for s in create],
            "detail_surface": asdict(detail) if detail else None,
            "update_triggers": update_triggers(buttons),
            "update_surfaces": [asdict(s) for s in updates],
            "delete_triggers": delete_triggers(buttons),
            "write_like_actions": write_like_actions(buttons),
            "api_calls": api_calls,
            "write_api_candidates": [
                c for c in api_calls if is_destructive_candidate(c.get("method", ""), c.get("path", ""))
            ],
        },
    }


def render_markdown(result: dict[str, Any]) -> str:
    lines = [
        "# FreelanceBase CRUD Probe",
        "",
        f"- generated_at: `{result['generated_at']}`",
        f"- pages: `{len(result['pages'])}`",
        "- mode: non-destructive; save/post/delete buttons were not clicked",
        "",
        "## Summary",
        "",
        "| Page | URL | List | Create UI | Update UI | Delete UI | Write-like UI | Write API observed |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for page in result["pages"]:
        crud = page["crud"]
        lines.append(
            "| {name} | `{url}` | {list_} | {create} | {update} | {delete} | {write_like} | {write_api} |".format(
                name=page["name"],
                url=page.get("final_url") or page["path"],
                list_="yes" if crud["list"] else "no",
                create=len(crud["create_surfaces"]) or len(crud["create_triggers"]),
                update=len(crud["update_surfaces"]) or len(crud["update_triggers"]),
                delete=len(crud["delete_triggers"]),
                write_like=len(crud.get("write_like_actions", [])),
                write_api=len(crud["write_api_candidates"]),
            )
        )
    for page in result["pages"]:
        crud = page["crud"]
        lines += [
            "",
            f"## {page['name']}",
            "",
            f"- URL: `{page.get('final_url') or page['path']}`",
            f"- title: `{page.get('title')}`",
            f"- list tables: `{len(page['list'].get('tables', []))}`",
            f"- create triggers: {', '.join(crud['create_triggers']) or 'none'}",
            f"- update triggers: {', '.join(crud['update_triggers']) or 'none'}",
            f"- delete triggers: {', '.join(crud['delete_triggers']) or 'none'}",
            f"- write-like actions: {', '.join(crud.get('write_like_actions', [])) or 'none'}",
            f"- row affordances: links={len(crud.get('row_affordances', {}).get('linkHrefs', []))}, buttons={crud.get('row_affordances', {}).get('buttonLabels', [])[:8]}",
            f"- row link patterns: {', '.join(crud.get('row_affordances', {}).get('linkHrefs', [])) or 'none'}",
            f"- row action labels: {', '.join(crud.get('row_affordances', {}).get('actionLabels', [])) or 'none'}",
            "- API:",
        ]
        if crud["api_calls"]:
            for call in crud["api_calls"]:
                flag = " write-candidate" if call.get("destructive_candidate") else ""
                lines.append(
                    f"  - `{call.get('method')} {call.get('path')}` status={call.get('status')}{flag}"
                )
        else:
            lines.append("  - none")
        if crud["create_surfaces"]:
            lines.append("- Create surfaces:")
            for surf in crud["create_surfaces"]:
                lines.append(
                    f"  - `{surf['trigger']}` inputs={len(surf.get('inputs', []))} buttons={surf.get('buttons', [])[:8]}"
                )
        if crud["update_surfaces"]:
            lines.append("- Update surfaces:")
            for surf in crud["update_surfaces"]:
                lines.append(
                    f"  - `{surf['trigger']}` inputs={len(surf.get('inputs', []))} buttons={surf.get('buttons', [])[:8]}"
                )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", default="/tmp/freelancebase-crud-probe")
    parser.add_argument("--headed", action="store_true")
    parser.add_argument("--no-detail", action="store_true", help="Skip first-row detail probing")
    parser.add_argument("--limit", type=int, default=0, help="Limit number of routes for smoke tests")
    args = parser.parse_args()

    routes = ROUTES[: args.limit] if args.limit else ROUTES
    out = ensure_local_output_dir(args.out_dir)
    with sync_playwright() as pw:
        browser, context, page = fb.login(pw, headless=not args.headed)
        try:
            pages = [probe_route(page, route, include_detail=not args.no_detail) for route in routes]
        finally:
            browser.close()
    result = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "base_url": BASE_URL,
        "mode": "non_destructive",
        "pages": pages,
    }
    json_path = out / "crud-probe.json"
    md_path = out / "crud-probe.md"
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(render_markdown(result), encoding="utf-8")
    print(f"json: {json_path}")
    print(f"markdown: {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
