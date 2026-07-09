#!/usr/bin/env python3
"""Non-destructive TechDirect catalog and danger-action probe."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

SNIPPETS_DIR = Path(__file__).resolve().parents[1]
if str(SNIPPETS_DIR) not in sys.path:
    sys.path.insert(0, str(SNIPPETS_DIR))

from playwright.sync_api import sync_playwright  # noqa: E402

from techdirect.api import ApiRecorder, install_write_guard, normalize_path  # noqa: E402
from techdirect.core import BASE_URL, build_url, ensure_local_output_dir, login_with_cache  # noqa: E402
from techdirect.routes import ROUTES, RouteSpec  # noqa: E402


WRITE_LABEL_RE = re.compile(
    r"(送信|保存|追加|解除|削除|スカウト|応募|見送り|採用|承認|却下|"
    r"アーカイブ|ミュート|ブロック|リスト|ラベル|興味|面談|返信)"
)
UUID_RE = re.compile(r"[0-9a-f]{8}-[0-9a-f-]{27,36}", re.IGNORECASE)
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+")
PHONE_RE = re.compile(r"0\d{1,4}-\d{1,4}-\d{3,4}")
LIVE_TEXT_RE = re.compile(r"(株式会社|有限会社|合同会社|@|メール|電話番号|氏名)")
DYNAMIC_OPTION_RE = re.compile(r"(候補者|ユーザー|企業|案件|担当|メンバー|メール|配信|添付|ファイル|user|job|member)", re.IGNORECASE)
STATIC_OPTION_HINT_RE = re.compile(
    r"(職種|種類|稼働|場所|地域|募集状況|ステータス|カテゴリ|条件|可否|有無|都道府県|"
    r"項目|カラム|列|添付ファイル|プロフィール|年齢|年収|雇用|経歴|日|単価|備考|URL|ニックネーム)"
)
AUTO_ID_RE = re.compile(r"^__cid__\d+$")
MENU_OPTION_ALLOW_RE = re.compile(
    r"(編集|削除|追加|保存|下書き|公開|停止|アーカイブ|ミュート|リセット|検索|条件|職種|地域|都道府県|"
    r"ステータス|リスト|スカウト|メッセージ|テンプレート|定型文|案件|求職者|応募|採用|見送り|プール|"
    r"稼働|雇用|年収|経歴|スキル|単価|年齢|担当者|ファイル|プロフィール|ニックネーム|URL|正社員|"
    r"戻る|営業対象外|他媒体|対応保留|再スカウト|NW|Base登録済|↑|↓)"
)


@dataclass
class Choice:
    label: str
    value: str = ""
    disabled: bool = False


@dataclass
class FieldItem:
    label: str
    control: str
    type: str = ""
    name: str = ""
    required: bool = False
    disabled: bool = False
    readonly: bool = False
    options: list[Choice] = field(default_factory=list)
    option_count: int = 0
    options_omitted: bool = False
    omit_reason: str = ""


@dataclass
class ChoiceGroup:
    label: str
    control: str
    name: str = ""
    options: list[Choice] = field(default_factory=list)
    option_count: int = 0
    options_omitted: bool = False
    omit_reason: str = ""


@dataclass
class Surface:
    kind: str
    trigger: str
    title: str = ""
    table_columns: list[list[str]] = field(default_factory=list)
    labels: list[str] = field(default_factory=list)
    fields: list[FieldItem] = field(default_factory=list)
    choice_groups: list[ChoiceGroup] = field(default_factory=list)
    buttons: list[str] = field(default_factory=list)
    link_patterns: list[str] = field(default_factory=list)
    danger_labels: list[str] = field(default_factory=list)
    menu_options: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


CATALOG_JS = r"""([kind, trigger]) => {
    const visible = el => {
        const r = el.getBoundingClientRect();
        const s = getComputedStyle(el);
        return r.width > 0 && r.height > 0 && s.display !== 'none' && s.visibility !== 'hidden';
    };
    const norm = value => ((value || '') + '').replace(/\s+/g, ' ').trim();
    const short = (value, max = 100) => norm(value).slice(0, max);
    const ownText = el => Array.from(el.childNodes)
        .filter(n => n.nodeType === Node.TEXT_NODE)
        .map(n => n.textContent)
        .join(' ');
    const explicitLabel = el => {
        const id = el.getAttribute('id');
        if (id) {
            const label = Array.from(document.querySelectorAll('label')).find(l => l.htmlFor === id);
            if (label && visible(label)) return short(label.innerText || label.textContent);
        }
        const wrapped = el.closest('label');
        if (wrapped && visible(wrapped)) return short(ownText(wrapped) || wrapped.innerText || wrapped.textContent);
        return '';
    };
    const neighborLabel = el => {
        let cur = el;
        for (let depth = 0; depth < 6 && cur; depth++) {
            const prev = cur.previousElementSibling;
            if (prev && visible(prev) && !prev.querySelector('input, textarea, select')) {
                const text = short(prev.innerText || prev.textContent);
                if (text && text.length <= 80) return text;
            }
            cur = cur.parentElement;
        }
        return '';
    };
    const fieldLabel = el => short(
        explicitLabel(el) || el.getAttribute('aria-label') || neighborLabel(el) ||
        el.getAttribute('placeholder') || el.getAttribute('name') || ''
    );
    const groupLabel = el => {
        const fieldset = el.closest('fieldset');
        if (fieldset) {
            const legend = fieldset.querySelector('legend');
            if (legend && visible(legend)) return short(legend.innerText || legend.textContent);
        }
        const base = fieldLabel(el);
        if (base && !/^__cid__\d+$/.test(base)) return base;
        let cur = el.parentElement;
        for (let depth = 0; depth < 5 && cur; depth++) {
            const text = short(cur.innerText || cur.textContent, 160);
            if (text && !/^__cid__\d+/.test(text)) {
                const parts = text.split(/\s+/).filter(Boolean);
                const first = parts.slice(0, 8).join(' ');
                if (first && first.length <= 80) return first;
            }
            cur = cur.parentElement;
        }
        return base;
    };
    const optionLabel = input => {
        const label = explicitLabel(input);
        if (label) return label;
        const parent = input.parentElement;
        if (!parent) return '';
        return short(parent.innerText || parent.textContent || input.getAttribute('value') || '');
    };
    const root = document.querySelector('main') || document.body;
    const fields = Array.from(root.querySelectorAll('input, textarea, select'))
        .filter(visible)
        .filter(el => {
            const type = (el.getAttribute('type') || '').toLowerCase();
            return !['hidden', 'radio', 'checkbox', 'submit', 'button', 'file'].includes(type);
        })
        .map(el => {
            const tag = el.tagName.toLowerCase();
            const type = (el.getAttribute('type') || '').toLowerCase();
            const options = tag === 'select'
                ? Array.from(el.options).map(opt => ({
                    label: short(opt.textContent || opt.label || ''),
                    value: short(opt.value || '', 80),
                    disabled: !!opt.disabled,
                })).filter(opt => opt.label || opt.value)
                : [];
            return {
                label: fieldLabel(el),
                control: tag,
                type,
                name: el.getAttribute('name') || '',
                required: !!el.required || el.getAttribute('aria-required') === 'true',
                disabled: !!el.disabled || el.getAttribute('aria-disabled') === 'true',
                readonly: !!el.readOnly || el.getAttribute('readonly') !== null,
                options,
            };
        });
    const grouped = new Map();
    Array.from(root.querySelectorAll('input[type=radio], input[type=checkbox]')).forEach(input => {
        const type = (input.getAttribute('type') || '').toLowerCase();
        const name = input.getAttribute('name') || '';
        const key = `${type}:${name || groupLabel(input)}`;
        if (!grouped.has(key)) {
            grouped.set(key, {label: groupLabel(input), control: type, name, options: []});
        }
        grouped.get(key).options.push({
            label: optionLabel(input),
            value: short(input.getAttribute('value') || '', 80),
            disabled: !!input.disabled || input.getAttribute('aria-disabled') === 'true',
        });
    });
    const tableColumns = Array.from(root.querySelectorAll('table'))
        .filter(visible)
        .map(table => Array.from(table.querySelectorAll('thead th, tr:first-child th'))
            .map(th => short(th.innerText || th.textContent, 80))
            .filter(Boolean))
        .filter(cols => cols.length);
    const labels = Array.from(root.querySelectorAll('label, dt, th'))
        .filter(visible)
        .map(el => short(el.innerText || el.textContent, 80))
        .filter(Boolean);
    const buttons = Array.from(root.querySelectorAll('button, [role=button]'))
        .filter(visible)
        .map(el => short(el.innerText || el.textContent || el.getAttribute('aria-label'), 80))
        .filter(Boolean);
    const links = Array.from(root.querySelectorAll('a[href]'))
        .filter(visible)
        .map(a => ({text: short(a.innerText || a.textContent, 80), href: a.href}))
        .filter(item => item.href);
    return {
        kind,
        trigger,
        title: document.title || '',
        table_columns: tableColumns,
        labels: Array.from(new Set(labels)),
        fields,
        choice_groups: Array.from(grouped.values()),
        buttons: Array.from(new Set(buttons)),
        links,
    };
}"""


def clean_text(text: str) -> str:
    text = " ".join((text or "").split())
    text = UUID_RE.sub("{uuid}", text)
    text = EMAIL_RE.sub("{email}", text)
    text = PHONE_RE.sub("{phone}", text)
    text = re.sub(r"合計\s+\d+", "合計件数", text)
    text = re.sub(r"求職者一覧\s*\([^)]*\)", "求職者一覧件数", text)
    text = re.sub(r"\(\s*\d+\s*\)", "(件数)", text)
    return text[:120]


def safe_label(text: str) -> bool:
    if not text:
        return False
    if UUID_RE.search(text) or EMAIL_RE.search(text) or PHONE_RE.search(text):
        return False
    if len(text) > 100:
        return False
    return True


def display_label(text: str, fallback: str = "-") -> str:
    text = clean_text(text)
    if not text or AUTO_ID_RE.match(text):
        return fallback
    return text


def normalize_href(href: str) -> str:
    parsed = urlsplit(href)
    if parsed.netloc and parsed.netloc != "techdirect.jp":
        path = re.sub(r"/[A-Za-z0-9_-]{12,}", "/{id}", parsed.path)
        path = re.sub(r"/\d+(?=/|$)", "/{id}", path)
        return f"{parsed.netloc}{path}"
    path = parsed.path
    path = re.sub(r"/users/[0-9a-f-]{36}", "/users/{uuid}", path, flags=re.IGNORECASE)
    path = re.sub(r"/\d+(?=/|$)", "/{id}", path)
    return path or href


def sanitize_choices(label: str, name: str, choices: list[Choice]) -> tuple[list[Choice], int, bool, str]:
    deduped: list[Choice] = []
    seen: set[tuple[str, str]] = set()
    for choice in choices:
        choice.label = clean_text(choice.label)
        choice.value = clean_text(choice.value)
        key = (choice.label, choice.value)
        if key not in seen:
            seen.add(key)
            deduped.append(choice)
    count = len(deduped)
    target = f"{label} {name}"
    dynamic_hint = DYNAMIC_OPTION_RE.search(target) and not STATIC_OPTION_HINT_RE.search(target)
    if count > 40 or dynamic_hint or any(LIVE_TEXT_RE.search(c.label) for c in deduped):
        return [], count, True, "dynamic or live-data option set"
    if any("{uuid}" in c.label or "{uuid}" in c.value for c in deduped):
        return [], count, True, "row-selection or live-data option set"
    return deduped, count, False, ""


def safe_menu_option(text: str) -> bool:
    if not safe_label(text):
        return False
    if "Claude" in text:
        return False
    if "(件数)" in text:
        return False
    if re.search(r"\d{4}/\d{1,2}/\d{1,2}", text):
        return False
    if re.fullmatch(r"[\d,]+", text):
        return False
    return bool(MENU_OPTION_ALLOW_RE.search(text))


def field_item(raw: dict[str, Any]) -> FieldItem:
    choices = [Choice(**choice) for choice in raw.get("options", [])]
    label = clean_text(raw.get("label", ""))
    item = FieldItem(
        label=label,
        control=raw.get("control", ""),
        type=raw.get("type", ""),
        name=raw.get("name", ""),
        required=bool(raw.get("required")),
        disabled=bool(raw.get("disabled")),
        readonly=bool(raw.get("readonly")),
    )
    item.options, item.option_count, item.options_omitted, item.omit_reason = sanitize_choices(label, item.name, choices)
    return item


def choice_group(raw: dict[str, Any]) -> ChoiceGroup:
    choices = [Choice(**choice) for choice in raw.get("options", [])]
    label = clean_text(raw.get("label", ""))
    group = ChoiceGroup(label=label, control=raw.get("control", ""), name=raw.get("name", ""))
    group.options, group.option_count, group.options_omitted, group.omit_reason = sanitize_choices(label, group.name, choices)
    return group


def collect_surface(page: Any, kind: str, trigger: str) -> Surface:
    raw = page.evaluate(CATALOG_JS, [kind, trigger])
    link_patterns = sorted({normalize_href(item.get("href", "")) for item in raw.get("links", []) if item.get("href")})
    buttons = [clean_text(text) for text in raw.get("buttons", []) if safe_label(clean_text(text))]
    labels = [clean_text(text) for text in raw.get("labels", []) if safe_label(clean_text(text))]
    danger_labels = sorted({label for label in buttons if WRITE_LABEL_RE.search(label)})
    return Surface(
        kind=kind,
        trigger=trigger,
        title=clean_text(raw.get("title", "")),
        table_columns=[[clean_text(col) for col in cols if safe_label(clean_text(col))] for cols in raw.get("table_columns", [])],
        labels=labels,
        fields=[field_item(item) for item in raw.get("fields", [])],
        choice_groups=[choice_group(group) for group in raw.get("choice_groups", [])],
        buttons=buttons,
        link_patterns=[pattern for pattern in link_patterns if pattern],
        danger_labels=danger_labels,
    )


def click_menu_trigger(page: Any, trigger: str) -> bool:
    return bool(
        page.evaluate(
            """trigger => {
                const visible = el => {
                    const r = el.getBoundingClientRect();
                    const s = getComputedStyle(el);
                    return r.width > 0 && r.height > 0 && s.display !== 'none' && s.visibility !== 'hidden';
                };
                const norm = value => ((value || '') + '').replace(/\s+/g, ' ').trim();
                const candidates = Array.from(document.querySelectorAll('button, [role=button]'))
                    .filter(visible)
                    .filter(el => {
                        const text = norm(el.innerText || el.textContent || el.getAttribute('aria-label'));
                        if (trigger === 'メニューを開く') {
                            return text === trigger;
                        }
                        return text === trigger;
                    });
                if (!candidates.length) return false;
                candidates[0].click();
                return true;
            }""",
            trigger,
        )
    )


def collect_visible_options(page: Any) -> list[str]:
    options = page.evaluate(
        """() => {
            const visible = el => {
                const r = el.getBoundingClientRect();
                const s = getComputedStyle(el);
                return r.width > 0 && r.height > 0 && s.display !== 'none' && s.visibility !== 'hidden';
            };
            const norm = value => ((value || '') + '').replace(/\s+/g, ' ').trim();
            return Array.from(document.querySelectorAll(
                'label, [role=menuitem], [role=option], [role=checkbox], [role=radio], option, button, a'
            ))
                .filter(visible)
                .map(el => norm(el.innerText || el.textContent || el.getAttribute('aria-label')))
                .filter(text => text && text.length <= 100);
        }"""
    )
    cleaned: list[str] = []
    seen: set[str] = set()
    for option in options:
        option = clean_text(option)
        if safe_menu_option(option) and option not in seen:
            seen.add(option)
            cleaned.append(option)
    return cleaned


def open_menu_surfaces(page: Any, triggers: tuple[str, ...]) -> list[dict[str, Any]]:
    surfaces: list[dict[str, Any]] = []
    for trigger in triggers:
        try:
            clicked = click_menu_trigger(page, trigger)
            if not clicked:
                continue
            page.wait_for_timeout(800)
            surface = collect_surface(page, "menu", trigger)
            surface.menu_options = collect_visible_options(page)
            surfaces.append(asdict(surface))
            page.keyboard.press("Escape")
            page.wait_for_timeout(400)
        except Exception:
            try:
                page.keyboard.press("Escape")
            except Exception:
                pass
    return surfaces


def first_user_url_from_page(page: Any) -> str | None:
    href = page.evaluate(
        """() => {
            const visible = el => {
                const r = el.getBoundingClientRect();
                const s = getComputedStyle(el);
                return r.width > 0 && r.height > 0 && s.display !== 'none' && s.visibility !== 'hidden';
            };
            const a = Array.from(document.querySelectorAll("a[href*='/users/']")).find(visible);
            return a ? a.href : null;
        }"""
    )
    return href


def first_href_matching(page: Any, pattern: str) -> str | None:
    return page.evaluate(
        """pattern => {
            const re = new RegExp(pattern);
            const visible = el => {
                const r = el.getBoundingClientRect();
                const s = getComputedStyle(el);
                return r.width > 0 && r.height > 0 && s.display !== 'none' && s.visibility !== 'hidden';
            };
            const a = Array.from(document.querySelectorAll('a[href]')).find(el => visible(el) && re.test(el.href));
            return a ? a.href : null;
        }""",
        pattern,
    )


def first_job_url_from_page(page: Any) -> str | None:
    return first_href_matching(page, r"/jobs/\d+")


def first_application_url_from_page(page: Any) -> str | None:
    return first_href_matching(page, r"/portal/applications/\d+")


def first_detail_url(page: Any, detail_kind: str) -> str | None:
    if detail_kind == "candidate":
        return first_user_url_from_page(page)
    if detail_kind == "application":
        return first_application_url_from_page(page)
    if detail_kind == "job":
        return first_job_url_from_page(page)
    return None


def open_list_menu(page: Any) -> tuple[list[str], list[str]]:
    notes: list[str] = []
    options: list[str] = []
    for text in ("リスト", "リスト編集"):
        loc = page.get_by_role("button", name=text).first
        if loc.count() == 0:
            loc = page.locator(f"button:has-text('{text}')").first
        if loc.count() == 0:
            continue
        try:
            loc.click()
            page.wait_for_timeout(1000)
            options = page.evaluate(
                """() => {
                    const visible = el => {
                        const r = el.getBoundingClientRect();
                        const s = getComputedStyle(el);
                        return r.width > 0 && r.height > 0 && s.display !== 'none' && s.visibility !== 'hidden';
                    };
                    return Array.from(document.querySelectorAll('label, [role=menuitem], .dropdown-menu *'))
                        .filter(visible)
                        .map(el => ((el.innerText || el.textContent || '') + '').replace(/\s+/g, ' ').trim())
                        .filter(Boolean)
                        .filter(text => text.length <= 100);
                }"""
            )
            page.keyboard.press("Escape")
            page.wait_for_timeout(500)
            break
        except Exception as exc:
            notes.append(f"{text} menu open failed: {type(exc).__name__}")
    cleaned = []
    seen = set()
    for opt in options:
        opt = clean_text(opt)
        if safe_label(opt) and opt not in seen:
            seen.add(opt)
            cleaned.append(opt)
    return cleaned, notes


def probe_route(page: Any, route: RouteSpec, blocked: list[dict[str, Any]]) -> dict[str, Any]:
    before = len(blocked)
    route_url = build_url(route.path)
    with ApiRecorder(page) as recorder:
        page.goto(route_url, wait_until="networkidle")
        page.wait_for_timeout(3000)
        list_surface = collect_surface(page, "list", route.name)
        menu_surfaces = open_menu_surfaces(page, route.menu_triggers)
        detail_url = first_detail_url(page, route.detail_kind)
        detail_surface = None
        if route.detail_kind and detail_url:
            page.goto(detail_url, wait_until="networkidle")
            page.wait_for_timeout(3000)
            detail_surface = collect_surface(page, "detail", f"first visible {route.detail_kind}")
            menu_options, notes = open_list_menu(page)
            detail_surface.menu_options = menu_options
            detail_surface.notes.extend(notes)
        elif route.detail_kind:
            detail_surface = Surface(kind="detail", trigger="no detail opened", notes=[f"no visible {route.detail_kind} detail link"])
        api_calls = recorder.to_dicts()
    return {
        "name": route.name,
        "category": route.category,
        "path": normalize_href(route.path),
        "list": asdict(list_surface),
        "menus": menu_surfaces,
        "detail": asdict(detail_surface) if detail_surface else None,
        "api_calls": api_calls,
        "blocked_requests": blocked[before:],
    }


def _unique_column_sets(surface: dict[str, Any]) -> list[list[str]]:
    seen: set[tuple[str, ...]] = set()
    out: list[list[str]] = []
    for cols in surface.get("table_columns") or []:
        cols = [col for col in cols if col]
        key = tuple(cols)
        if key and key not in seen:
            seen.add(key)
            out.append(cols)
    return out


def _options_text(item: dict[str, Any]) -> str:
    if item.get("options_omitted"):
        return f"omitted: {item.get('omit_reason')} ({item.get('option_count', 0)} options)"
    labels = [choice.get("label") for choice in item.get("options", []) if choice.get("label")]
    if any("{uuid}" in label for label in labels):
        return f"omitted: row-selection or live-data option set ({len(labels)} options)"
    if not labels:
        return "none"
    return ", ".join(f"`{label}`" for label in labels[:30]) + (f" ... ({len(labels)} options)" if len(labels) > 30 else "")


def render_pages_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# TechDirect Page Catalog",
        "",
        f"- generated_at: `{payload['generated_at']}`",
        f"- pages: `{len(payload['pages'])}`",
        f"- blocked_write_requests: `{len(payload.get('blocked_requests', []))}`",
        "- scope: page types, excluding user-created saved searches and job-seeker list variants",
        "- mode: non-destructive; write-like actions were not clicked",
        "",
        "## Summary",
        "",
        "| Page Type | Category | List Columns | Menus Opened | Detail Opened | API Calls | Blocked Writes |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for item in payload["pages"]:
        lines.append(
            f"| {item['name']} | `{item['category']}` | {sum(len(cols) for cols in _unique_column_sets(item['list']))} | {len(item.get('menus', []))} | {'yes' if item.get('detail') and not item['detail'].get('notes') else 'partial' if item.get('detail') else 'no'} | {len(item['api_calls'])} | {len(item['blocked_requests'])} |"
        )
    for item in payload["pages"]:
        lines += ["", f"## {item['name']}", "", f"- path: `{item['path']}`"]
        list_surface = item["list"]
        cols = _unique_column_sets(list_surface)
        if cols:
            lines.append("- table columns:")
            for colset in cols:
                lines.append("  - " + ", ".join(f"`{col}`" for col in colset))
        if list_surface.get("link_patterns"):
            lines.append("- link patterns:")
            for pattern in list_surface["link_patterns"][:40]:
                lines.append(f"  - `{pattern}`")
        if item["api_calls"]:
            lines.append("- API:")
            for call in item["api_calls"][:40]:
                flag = " write-candidate" if call.get("write_candidate") else ""
                lines.append(f"  - `{call['method']} {call['host']}{call['path']}` status={call.get('status')}{flag}")
    return "\n".join(lines) + "\n"


def render_field_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# TechDirect Field Catalog",
        "",
        f"- generated_at: `{payload['generated_at']}`",
        "- current values are not recorded",
        "- dynamic/live-data option labels are omitted",
        "",
    ]
    for item in payload["pages"]:
        lines += ["", f"## {item['name']}", ""]
        surfaces = [("List", item["list"])]
        surfaces.extend((f"Menu: {surface.get('trigger', '')}", surface) for surface in item.get("menus", []))
        surfaces.append(("Detail", item.get("detail")))
        for title, surface in surfaces:
            if not surface:
                continue
            lines += [f"### {title}", ""]
            labels = [label for label in surface.get("labels", []) if label]
            if labels:
                lines.append("- labels:")
                lines.append("  - " + ", ".join(f"`{label}`" for label in labels[:80]))
            rows = []
            for field_item in surface.get("fields", []):
                flags = ", ".join(name for name in ("required", "disabled", "readonly") if field_item.get(name)) or "-"
                rows.append(
                    f"| {display_label(field_item.get('label') or '-')} | {field_item.get('control')}/{field_item.get('type') or '-'} | `{field_item.get('name') or ''}` | {flags} | {_options_text(field_item)} |"
                )
            for group in surface.get("choice_groups", []):
                rows.append(
                    f"| {display_label(group.get('label') or '-')} | {group.get('control') or '-'} | `{group.get('name') or ''}` | - | {_options_text(group)} |"
                )
            if rows:
                lines += [
                    "",
                    "| Label | Control | Name | Flags | Options |",
                    "|---|---|---|---|---|",
                    *rows,
                    "",
                ]
            else:
                lines.append("- fields: none visible")
    return "\n".join(lines) + "\n"


def render_columns_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# TechDirect Column And Choice Catalog",
        "",
        f"- generated_at: `{payload['generated_at']}`",
        "- scope: page types, excluding user-created saved searches and job-seeker list variants",
        "- table row values and current control values are not recorded",
        "- dynamic/live-data option labels are omitted",
        "",
    ]
    for item in payload["pages"]:
        lines += ["", f"## {item['name']}", "", f"- path: `{item['path']}`"]
        cols = _unique_column_sets(item["list"])
        if cols:
            lines.append("- visible table columns:")
            for colset in cols:
                lines.append("  - " + ", ".join(f"`{col}`" for col in colset))
        else:
            lines.append("- visible table columns: none")

        control_rows: list[str] = []
        surfaces = [("List", item["list"])]
        surfaces.extend((f"Menu: {surface.get('trigger', '')}", surface) for surface in item.get("menus", []))
        for source, surface in surfaces:
            for field_item in surface.get("fields", []):
                options = _options_text(field_item)
                if options == "none" and not field_item.get("name"):
                    continue
                control_rows.append(
                    f"| {source} | {display_label(field_item.get('label') or '-')} | {field_item.get('control')}/{field_item.get('type') or '-'} | `{field_item.get('name') or ''}` | {options} |"
                )
            for group in surface.get("choice_groups", []):
                control_rows.append(
                    f"| {source} | {display_label(group.get('label') or '-')} | {group.get('control') or '-'} | `{group.get('name') or ''}` | {_options_text(group)} |"
                )
        if control_rows:
            lines += [
                "",
                "| Source | Column/Control | Control | Name | Choices |",
                "|---|---|---|---|---|",
                *control_rows,
            ]
        else:
            lines.append("- column/filter choices: none visible")
    return "\n".join(lines) + "\n"


def render_danger_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# TechDirect Danger Actions",
        "",
        f"- generated_at: `{payload['generated_at']}`",
        f"- blocked_write_requests: `{len(payload.get('blocked_requests', []))}`",
        "- final write-like actions and list options were not clicked",
        "",
        "## Summary",
        "",
        "| Page | Surface | Danger Labels | List/Menu Options | Blocked Writes |",
        "|---|---|---|---|---:|",
    ]
    for item in payload["pages"]:
        surfaces = [("list", item.get("list"))]
        surfaces.extend((f"menu:{surface.get('trigger', '')}", surface) for surface in item.get("menus", []))
        surfaces.append(("detail", item.get("detail")))
        for surface_name, surface in surfaces:
            if not surface:
                continue
            dangers = ", ".join(f"`{label}`" for label in surface.get("danger_labels", [])) or "none"
            safe_options = [label for label in surface.get("menu_options", []) if safe_menu_option(clean_text(label))]
            options = ", ".join(f"`{clean_text(label)}`" for label in safe_options) or "none"
            lines.append(f"| {item['name']} | {surface_name} | {dangers} | {options} | {len(item.get('blocked_requests', []))} |")
    lines += [
        "",
        "## Boundaries",
        "",
        "- Menu/dropdown surfaces may be opened for inspection.",
        "- List/label options are never clicked because they may toggle state immediately.",
        "- Message, scout, application, rejection, archive, mute, block, save, and delete actions are not clicked.",
        "- Non-GET TechDirect/Codeal API requests are aborted by route guard.",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", default="/tmp/techdirect-catalog")
    parser.add_argument("--docs-dir", help="Optional docs/techdirect output directory")
    parser.add_argument("--headed", action="store_true")
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    out = ensure_local_output_dir(args.out_dir)
    routes = ROUTES[: args.limit] if args.limit else ROUTES
    blocked: list[dict[str, Any]] = []
    with sync_playwright() as pw:
        browser, context, page = login_with_cache(pw, headless=not args.headed)
        try:
            install_write_guard(page, blocked)
            pages = [probe_route(page, route, blocked) for route in routes]
        finally:
            browser.close()

    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "base_url": BASE_URL,
        "mode": "non_destructive_techdirect_catalog",
        "pages": pages,
        "blocked_requests": blocked,
    }
    (out / "catalog.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    pages_md = render_pages_markdown(payload)
    fields_md = render_field_markdown(payload)
    columns_md = render_columns_markdown(payload)
    danger_md = render_danger_markdown(payload)
    (out / "pages.md").write_text(pages_md, encoding="utf-8")
    (out / "field-catalog.md").write_text(fields_md, encoding="utf-8")
    (out / "column-catalog.md").write_text(columns_md, encoding="utf-8")
    (out / "danger-actions.md").write_text(danger_md, encoding="utf-8")
    if args.docs_dir:
        docs = ensure_local_output_dir(args.docs_dir)
        (docs / "pages.md").write_text(pages_md, encoding="utf-8")
        (docs / "field-catalog.md").write_text(fields_md, encoding="utf-8")
        (docs / "column-catalog.md").write_text(columns_md, encoding="utf-8")
        (docs / "danger-actions.md").write_text(danger_md, encoding="utf-8")
    print(f"json: {out / 'catalog.json'}")
    print(f"pages: {out / 'pages.md'}")
    print(f"field_catalog: {out / 'field-catalog.md'}")
    print(f"column_catalog: {out / 'column-catalog.md'}")
    print(f"danger_actions: {out / 'danger-actions.md'}")
    print(f"blocked_write_requests: {len(blocked)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
