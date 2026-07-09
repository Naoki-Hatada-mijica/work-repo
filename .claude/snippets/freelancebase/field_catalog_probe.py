#!/usr/bin/env python3
"""Catalog FreelanceBase detail/create/update fields without writing data.

The probe intentionally does not capture current field values. Static
select/radio/checkbox choices are recorded; dynamic live-data choices such as
candidate/company/user/job lookups are counted but their labels are omitted from
committed output.
"""

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
from freelancebase.api import api_path, is_destructive_candidate, is_enterprise_api  # noqa: E402
from freelancebase.core import BASE_URL, build_url, ensure_local_output_dir  # noqa: E402
from freelancebase.crud_probe import (  # noqa: E402
    ROUTES,
    RouteSpec,
    click_visible_exact,
    close_overlay,
    create_triggers,
    first_row_id,
)


WRITE_LIKE_TEXT_RE = re.compile(
    r"^(保存|保存する|公開する|リリース|下書き保存|本番に公開|"
    r"成約を確定|見送り|辞退|合算請求候補を抽出|コメントを投稿|"
    r"人材を作成|企業を作成|企業担当者を作成|案件を作成|商談を作成|"
    r"削除|公開停止|公開停止中|コピーする|.*を複製)$"
)
DYNAMIC_FIELD_RE = re.compile(
    r"(候補者名|人材名|企業名|会社名|担当者|メンバー|案件名|契約名|商談名|"
    r"請求先|支払先|顧客|取引先|営業担当|ユーザー|"
    r"user|member|candidate|company|job|contract|opportunit|billing|invoice|client|owner)",
    re.IGNORECASE,
)
ID_NAME_RE = re.compile(
    r"(candidate_id|company_id|company_member_id|member_id|user_id|job_id|contract_id|"
    r"opportunity_id|billing_.*id|invoice_.*id|client_id|owner_id)",
    re.IGNORECASE,
)
STATIC_OPTION_HINT_RE = re.compile(
    r"(タイプ|種別|ステータス|状態|ランク|経路|性別|国籍|都道府県|年月日|"
    r"年|月|日|設立|現在の状況|公開状況|掲載状況|稼働形態|契約形態|"
    r"工程|業界|カテゴリ|区分|可否|有無|優先度|頻度|"
    r"type|status|rank|gender|nationality|category|kind|source)",
    re.IGNORECASE,
)
SAFE_OPTION_LABEL_RE = re.compile(
    r"^[\w\sぁ-んァ-ヶー一-龠々・（）()／/,.%:+\-〜~]+$",
    re.UNICODE,
)
YEAR_RE = re.compile(r"^(18|19|20)\d{2}年?$")
NUMBER_UNIT_RE = re.compile(r"^\d+(日|月|年|歳|円|万円|人|件|時間|分|ヶ月|か月|%)?$")


@dataclass
class FieldChoice:
    label: str
    value: str = ""
    disabled: bool = False


@dataclass
class FieldItem:
    label: str
    control: str
    type: str = ""
    name: str = ""
    placeholder: str = ""
    aria_label: str = ""
    required: bool = False
    disabled: bool = False
    readonly: bool = False
    options: list[FieldChoice] = field(default_factory=list)
    option_count: int = 0
    options_omitted: bool = False
    omit_reason: str = ""


@dataclass
class ChoiceGroup:
    label: str
    control: str
    name: str = ""
    options: list[FieldChoice] = field(default_factory=list)
    option_count: int = 0
    options_omitted: bool = False
    omit_reason: str = ""


@dataclass
class SurfaceCatalog:
    kind: str
    trigger: str
    title: str = ""
    table_columns: list[list[str]] = field(default_factory=list)
    detail_labels: list[str] = field(default_factory=list)
    fields: list[FieldItem] = field(default_factory=list)
    choice_groups: list[ChoiceGroup] = field(default_factory=list)
    buttons: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


FIELD_CATALOG_JS = r"""([kind, trigger]) => {
    const visible = el => {
        const r = el.getBoundingClientRect();
        const s = getComputedStyle(el);
        return r.width > 0 && r.height > 0 && s.display !== 'none' && s.visibility !== 'hidden';
    };
    const norm = value => ((value || '') + '').replace(/\s+/g, ' ').trim();
    const short = (value, max = 120) => norm(value).slice(0, max);
    const leafText = el => Array.from(el.childNodes)
        .filter(n => n.nodeType === Node.TEXT_NODE)
        .map(n => n.textContent)
        .join(' ');
    const explicitLabel = el => {
        const id = el.getAttribute('id');
        if (id) {
            const label = Array.from(document.querySelectorAll('label')).find(l => l.htmlFor === id);
            if (label && visible(label)) return short(label.innerText || label.textContent, 120);
        }
        const wrapped = el.closest('label');
        if (wrapped && visible(wrapped)) {
            const own = short(leafText(wrapped), 120);
            if (own) return own;
            return short(wrapped.innerText || wrapped.textContent, 120);
        }
        return '';
    };
    const neighborLabel = el => {
        let cur = el;
        for (let depth = 0; depth < 7 && cur; depth++) {
            const prev = cur.previousElementSibling;
            if (prev && visible(prev) && !prev.querySelector('input, textarea, select')) {
                const text = short(prev.innerText || prev.textContent, 120);
                if (text && text.length <= 80) return text;
            }
            const parent = cur.parentElement;
            if (!parent) break;
            const direct = Array.from(parent.children)
                .filter(child => child !== cur)
                .filter(child => visible(child))
                .filter(child => !child.querySelector('input, textarea, select'))
                .map(child => short(child.innerText || child.textContent, 120))
                .filter(text => text && text.length <= 80);
            if (direct.length) return direct[0];
            cur = parent;
        }
        return '';
    };
    const fieldLabel = el => short(
        explicitLabel(el) ||
        el.getAttribute('aria-label') ||
        neighborLabel(el) ||
        el.getAttribute('placeholder') ||
        el.getAttribute('name') ||
        '',
        120
    );
    const groupLabel = el => {
        const fieldset = el.closest('fieldset');
        if (fieldset) {
            const legend = fieldset.querySelector('legend');
            if (legend && visible(legend)) {
                const text = short(legend.innerText || legend.textContent, 120);
                if (text) return text;
            }
        }
        return short(neighborLabel(el) || fieldLabel(el), 120);
    };
    const optionLabel = input => {
        const label = explicitLabel(input);
        if (label) return label;
        const parent = input.parentElement;
        if (!parent) return '';
        const text = short(parent.innerText || parent.textContent, 120);
        return text || input.getAttribute('value') || '';
    };
    const modalRoots = Array.from(document.querySelectorAll(
        '.modal_content, [role=dialog], .modal, .drawer, .right-modal, .right-open, form'
    )).filter(visible);
    const root = modalRoots.find(r => r.querySelector('input, textarea, select')) ||
        document.querySelector('main') ||
        document.body;
    const fieldRoots = kind === 'detail' ? document.body : root;
    const fields = Array.from(fieldRoots.querySelectorAll('input, textarea, select'))
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
                    label: short(opt.textContent || opt.label || '', 120),
                    value: short(opt.value || '', 80),
                    disabled: !!opt.disabled,
                })).filter(opt => opt.label || opt.value)
                : [];
            return {
                label: fieldLabel(el),
                control: tag,
                type,
                name: el.getAttribute('name') || '',
                placeholder: el.getAttribute('placeholder') || '',
                aria_label: el.getAttribute('aria-label') || '',
                required: !!el.required || el.getAttribute('aria-required') === 'true',
                disabled: !!el.disabled || el.getAttribute('aria-disabled') === 'true',
                readonly: !!el.readOnly || el.getAttribute('readonly') !== null,
                options,
            };
        });
    const grouped = new Map();
    Array.from(fieldRoots.querySelectorAll('input[type=radio], input[type=checkbox]'))
        .filter(visible)
        .forEach(input => {
            const type = (input.getAttribute('type') || '').toLowerCase();
            const name = input.getAttribute('name') || '';
            const key = `${type}:${name || groupLabel(input)}`;
            if (!grouped.has(key)) {
                grouped.set(key, {
                    label: groupLabel(input),
                    control: type,
                    name,
                    options: [],
                });
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
    const labelTexts = Array.from(root.querySelectorAll('label, dt, th'))
        .filter(visible)
        .map(el => short(el.innerText || el.textContent, 80))
        .filter(text => text && text.length <= 80);
    const buttons = Array.from(root.querySelectorAll('button'))
        .filter(visible)
        .map(btn => short(btn.innerText || btn.textContent || btn.getAttribute('aria-label'), 80))
        .filter(Boolean);
    return {
        kind,
        trigger,
        title: Array.from(root.querySelectorAll('h1,h2,h3,h4,h5,h6'))
            .filter(visible)
            .map(el => short(el.innerText || el.textContent, 120))
            .find(Boolean) || '',
        table_columns: tableColumns,
        detail_labels: Array.from(new Set(labelTexts)),
        fields,
        choice_groups: Array.from(grouped.values()),
        buttons,
    };
}"""


def _dedupe_choices(choices: list[FieldChoice]) -> list[FieldChoice]:
    seen: set[tuple[str, str]] = set()
    out: list[FieldChoice] = []
    for choice in choices:
        key = (choice.label, choice.value)
        if key in seen:
            continue
        seen.add(key)
        out.append(choice)
    return out


def _continuous_numeric_or_year_labels(labels: list[str]) -> bool:
    clean = [label for label in labels if label and label not in {"-", "選択してください", "未選択", "年", "月", "日"}]
    if not clean:
        return False
    return all(YEAR_RE.search(label) or NUMBER_UNIT_RE.search(label) for label in clean)


def _is_dynamic_options(label: str, name: str, choices: list[FieldChoice]) -> tuple[bool, str]:
    target = f"{label} {name}"
    static_hint = bool(STATIC_OPTION_HINT_RE.search(target))
    if not static_hint and (DYNAMIC_FIELD_RE.search(target) or ID_NAME_RE.search(name)):
        return True, "dynamic live-data field"
    labels = [choice.label for choice in choices if choice.label]
    values = [choice.value for choice in choices if choice.value]
    if len(labels) > 80 and not _continuous_numeric_or_year_labels(labels):
        return True, "large non-static option set"
    numeric_values = sum(1 for value in values if value.isdigit())
    if numeric_values >= 20 and len(labels) >= 20 and not static_hint and not _continuous_numeric_or_year_labels(labels):
        return True, "numeric id-like option values"
    unsafe_labels = [label for label in labels if not SAFE_OPTION_LABEL_RE.search(label)]
    if unsafe_labels:
        return True, "contains non-catalog text"
    return False, ""


def _sanitize_item(item: FieldItem | ChoiceGroup) -> FieldItem | ChoiceGroup:
    choices = _dedupe_choices(item.options)
    item.option_count = len(choices)
    if not choices:
        item.options = []
        return item
    dynamic, reason = _is_dynamic_options(item.label, item.name, choices)
    if dynamic:
        item.options = []
        item.options_omitted = True
        item.omit_reason = reason
        return item
    item.options = choices
    return item


def _field_item(raw: dict[str, Any]) -> FieldItem:
    choices = [FieldChoice(**choice) for choice in raw.get("options", [])]
    item = FieldItem(
        label=raw.get("label", ""),
        control=raw.get("control", ""),
        type=raw.get("type", ""),
        name=raw.get("name", ""),
        placeholder="",
        aria_label=raw.get("aria_label", ""),
        required=bool(raw.get("required")),
        disabled=bool(raw.get("disabled")),
        readonly=bool(raw.get("readonly")),
        options=choices,
    )
    return _sanitize_item(item)  # type: ignore[return-value]


def _choice_group(raw: dict[str, Any]) -> ChoiceGroup:
    choices = [FieldChoice(**choice) for choice in raw.get("options", [])]
    group = ChoiceGroup(
        label=raw.get("label", ""),
        control=raw.get("control", ""),
        name=raw.get("name", ""),
        options=choices,
    )
    return _sanitize_item(group)  # type: ignore[return-value]


def collect_surface_catalog(page: Any, kind: str, trigger: str) -> SurfaceCatalog:
    raw = page.evaluate(FIELD_CATALOG_JS, [kind, trigger])
    catalog = SurfaceCatalog(
        kind=raw.get("kind", kind),
        trigger=raw.get("trigger", trigger),
        title=raw.get("title", ""),
        table_columns=raw.get("table_columns", []),
        detail_labels=raw.get("detail_labels", []),
        fields=[_field_item(item) for item in raw.get("fields", [])],
        choice_groups=[_choice_group(group) for group in raw.get("choice_groups", [])],
        buttons=[button for button in raw.get("buttons", []) if button],
    )
    return catalog


def install_write_guard(page: Any, blocked: list[dict[str, Any]]) -> None:
    def handler(route: Any, request: Any) -> None:
        if is_enterprise_api(request.url):
            path = api_path(request.url)
            if is_destructive_candidate(request.method, path):
                blocked.append({"method": request.method, "path": path, "reason": "aborted_by_field_catalog_probe"})
                route.abort()
                return
        route.continue_()

    page.route("**/*", handler)


def _open_create_surfaces(page: Any, triggers: list[str]) -> list[SurfaceCatalog]:
    surfaces: list[SurfaceCatalog] = []
    for trigger in triggers:
        if not click_visible_exact(page, trigger, prefer_button=True):
            continue
        page.wait_for_timeout(1000)
        menu_items = page.evaluate(
            """() => Array.from(document.querySelectorAll('.ele-dropdown-body a, .ele-dropdown-body li, [role=menu] *, a, li'))
                .map(el => ((el.innerText || el.textContent || '') + '').replace(/\\s+/g, ' ').trim())
                .filter(Boolean)
                .slice(0, 80)"""
        )
        chosen = None
        for candidate in ("通常作成", "新規作成", "手動作成", "作成"):
            if candidate in menu_items and click_visible_exact(page, candidate):
                chosen = candidate
                page.wait_for_timeout(1500)
                break
        actual_trigger = f"{trigger} > {chosen}" if chosen else trigger
        surfaces.append(collect_surface_catalog(page, "create", actual_trigger))
        close_overlay(page)
        page.wait_for_timeout(700)
    return surfaces


def _open_detail(page: Any, route: RouteSpec) -> tuple[bool, str]:
    if route.detail_path:
        rid = first_row_id(page, route.id_header_candidates)
        if rid:
            page.goto(build_url(route.detail_path.format(id=rid)), wait_until="networkidle", timeout=14_000)
            page.wait_for_timeout(1700)
            return True, "first visible row id direct"
    rows = page.locator("table tbody tr")
    if rows.count() == 0:
        return False, "no row available"
    rows.first.click(force=True)
    page.wait_for_timeout(1300)
    if page.get_by_text("詳細を見る", exact=True).count() > 0:
        page.get_by_text("詳細を見る", exact=True).first.click(force=True)
        try:
            page.wait_for_load_state("networkidle", timeout=10_000)
        except PWTimeoutError:
            pass
        page.wait_for_timeout(1500)
        return True, "row drawer detail link"
    return True, "first visible row surface"


def _open_update_surface(page: Any) -> list[SurfaceCatalog]:
    if click_visible_exact(page, "編集する", prefer_button=True):
        page.wait_for_timeout(1300)
        surface = collect_surface_catalog(page, "update", "編集する")
        close_overlay(page)
        return [surface]
    return []


def probe_route(page: Any, route: RouteSpec, blocked: list[dict[str, Any]]) -> dict[str, Any]:
    before = len(blocked)
    page.goto(build_url(route.path), wait_until="networkidle")
    page.wait_for_timeout(2200)
    list_catalog = collect_surface_catalog(page, "list", "page")
    create_surfaces = _open_create_surfaces(
        page,
        create_triggers(list_catalog.buttons),
    )
    detail_surface: SurfaceCatalog | None = None
    update_surfaces: list[SurfaceCatalog] = []
    detail_note = ""
    try:
        opened, detail_note = _open_detail(page, route)
        if opened:
            detail_surface = collect_surface_catalog(page, "detail", detail_note)
            update_surfaces = _open_update_surface(page)
        else:
            detail_surface = SurfaceCatalog(kind="detail", trigger=detail_note, notes=[detail_note])
    except Exception as exc:
        detail_surface = SurfaceCatalog(kind="detail", trigger="failed", notes=[f"{type(exc).__name__}: detail open failed"])
    return {
        "name": route.name,
        "category": route.category,
        "path": route.path,
        "list": asdict(list_catalog),
        "create_surfaces": [asdict(surface) for surface in create_surfaces],
        "detail_surface": asdict(detail_surface) if detail_surface else None,
        "update_surfaces": [asdict(surface) for surface in update_surfaces],
        "blocked_requests": blocked[before:],
    }


def _compact_options(options: list[dict[str, Any]]) -> str:
    labels = [opt.get("label", "") for opt in options if opt.get("label")]
    if not labels:
        return "none"
    if len(labels) > 24 and _continuous_numeric_or_year_labels(labels):
        return f"{labels[0]} ... {labels[-1]} ({len(labels)} options)"
    if len(labels) > 30:
        return ", ".join(f"`{label}`" for label in labels[:30]) + f" ... ({len(labels)} options)"
    return ", ".join(f"`{label}`" for label in labels)


def _display_label(label: str) -> str:
    return re.sub(r"^合計\s+\d+$", "合計件数", label or "").strip()


def _unique_column_sets(surface: dict[str, Any]) -> list[list[str]]:
    seen: set[tuple[str, ...]] = set()
    out: list[list[str]] = []
    for cols in surface.get("table_columns") or []:
        key = tuple(cols)
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(cols)
    return out


def _field_rows(surface: dict[str, Any]) -> list[str]:
    rows: list[str] = []
    for field_item in surface.get("fields", []):
        options = "none"
        if field_item.get("options_omitted"):
            options = f"omitted: {field_item.get('omit_reason')} ({field_item.get('option_count', 0)} options)"
        elif field_item.get("option_count"):
            options = _compact_options(field_item.get("options", []))
        flags = []
        if field_item.get("required"):
            flags.append("required")
        if field_item.get("disabled"):
            flags.append("disabled")
        if field_item.get("readonly"):
            flags.append("readonly")
        rows.append(
            "| {label} | {control} | `{name}` | {flags} | {options} |".format(
                label=_display_label(
                    field_item.get("label") or field_item.get("aria_label") or field_item.get("placeholder") or "-"
                ),
                control=field_item.get("control") + (f"/{field_item.get('type')}" if field_item.get("type") else ""),
                name=field_item.get("name") or "",
                flags=", ".join(flags) or "-",
                options=options,
            )
        )
    for group in surface.get("choice_groups", []):
        if group.get("options_omitted"):
            options = f"omitted: {group.get('omit_reason')} ({group.get('option_count', 0)} options)"
        else:
            options = _compact_options(group.get("options", []))
        rows.append(
            "| {label} | {control} | `{name}` | - | {options} |".format(
                label=_display_label(group.get("label") or "-"),
                control=group.get("control") or "-",
                name=group.get("name") or "",
                options=options,
            )
        )
    return rows


def _render_surface(surface: dict[str, Any], title: str) -> list[str]:
    lines = [f"### {title}", ""]
    if surface.get("notes"):
        lines.append("- notes: " + "; ".join(surface["notes"]))
        lines.append("")
    columns = _unique_column_sets(surface)
    if columns:
        lines.append("- table columns:")
        for cols in columns:
            lines.append(f"  - {', '.join(f'`{col}`' for col in cols)}")
        lines.append("")
    labels = [_display_label(label) for label in surface.get("detail_labels", []) if label]
    if labels and title.startswith("Detail"):
        lines.append("- detail labels:")
        lines.append("  - " + ", ".join(f"`{label}`" for label in labels[:80]))
        if len(labels) > 80:
            lines.append(f"  - ... ({len(labels)} labels)")
        lines.append("")
    rows = _field_rows(surface)
    if rows:
        lines += [
            "| Label | Control | Name | Flags | Options |",
            "|---|---|---|---|---|",
            *rows,
            "",
        ]
    else:
        lines.append("- fields: none visible")
        lines.append("")
    return lines


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# FreelanceBase Field Catalog",
        "",
        f"- generated_at: `{payload['generated_at']}`",
        f"- pages: `{len(payload['pages'])}`",
        f"- blocked_write_requests: `{len(payload.get('blocked_requests', []))}`",
        "",
        "Generated from a non-destructive Playwright probe. The probe opened list, first-row detail, create, and edit surfaces where available, but did not click save/post/delete/publish/release/status-change final actions.",
        "",
        "Current field values are not recorded. Static select/radio/checkbox choices are recorded. Dynamic live-data choices such as candidate, company, member, job, contract, billing, and user lookups are counted but labels are omitted from git-tracked output.",
        "",
        "## Table of Contents",
        "",
    ]
    for page in payload["pages"]:
        lines.append(f"- [{page['name']}](#{page['name'].lower().replace('・', '').replace(' ', '-')})")
    lines += [
        "",
        "## Summary",
        "",
        "| Page | List Columns | Create Surfaces | Detail Fields | Update Surfaces | Omitted Dynamic Option Groups | Blocked Writes |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for page in payload["pages"]:
        surfaces = [page["list"], *(page.get("create_surfaces") or []), page.get("detail_surface"), *(page.get("update_surfaces") or [])]
        surfaces = [surface for surface in surfaces if surface]
        omitted = 0
        for surface in surfaces:
            omitted += sum(1 for item in surface.get("fields", []) if item.get("options_omitted"))
            omitted += sum(1 for item in surface.get("choice_groups", []) if item.get("options_omitted"))
        detail = page.get("detail_surface") or {}
        detail_fields = len(detail.get("fields", [])) + len(detail.get("choice_groups", []))
        lines.append(
            "| {name} | {cols} | {create} | {detail} | {update} | {omitted} | {blocked} |".format(
                name=page["name"],
                cols=sum(len(cols) for cols in _unique_column_sets(page["list"])),
                create=len(page.get("create_surfaces") or []),
                detail=detail_fields,
                update=len(page.get("update_surfaces") or []),
                omitted=omitted,
                blocked=len(page.get("blocked_requests") or []),
            )
        )
    for page in payload["pages"]:
        lines += [
            "",
            f"## {page['name']}",
            "",
            f"- path: `{page['path']}`",
            f"- category: `{page['category']}`",
            "",
        ]
        lines += _render_surface(page["list"], "List")
        detail_surface = page.get("detail_surface")
        if detail_surface:
            lines += _render_surface(detail_surface, "Detail")
        for idx, surface in enumerate(page.get("create_surfaces") or [], start=1):
            lines += _render_surface(surface, f"Create {idx}: `{surface.get('trigger', '')}`")
        for idx, surface in enumerate(page.get("update_surfaces") or [], start=1):
            lines += _render_surface(surface, f"Update {idx}: `{surface.get('trigger', '')}`")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", default="/tmp/freelancebase-field-catalog")
    parser.add_argument("--docs-out", help="Optional git-tracked sanitized markdown path")
    parser.add_argument("--headed", action="store_true")
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    out = ensure_local_output_dir(args.out_dir)
    routes = ROUTES[: args.limit] if args.limit else ROUTES
    blocked: list[dict[str, Any]] = []
    with sync_playwright() as pw:
        browser, context, page = fb.login(pw, headless=not args.headed)
        try:
            install_write_guard(page, blocked)
            pages = [probe_route(page, route, blocked) for route in routes]
        finally:
            browser.close()

    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "base_url": BASE_URL,
        "mode": "non_destructive_field_catalog",
        "pages": pages,
        "blocked_requests": blocked,
    }
    json_path = out / "field-catalog.json"
    md_path = out / "field-catalog.md"
    markdown = render_markdown(payload)
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(markdown, encoding="utf-8")
    if args.docs_out:
        Path(args.docs_out).write_text(markdown, encoding="utf-8")
        print(f"docs: {args.docs_out}")
    print(f"json: {json_path}")
    print(f"markdown: {md_path}")
    print(f"blocked_write_requests: {len(blocked)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
