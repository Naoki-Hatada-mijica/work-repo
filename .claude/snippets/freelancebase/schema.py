"""Unified page-type schema probe for FreelanceBase.

The probe is intentionally non-destructive. It catalogs route/page types,
visible list/detail/create/update surfaces, CRUD affordances, observed API
shapes, fields, and static choices. Numeric record pages are sampled at most
once per route and are normalized to `{id}` page-type patterns.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .api import ApiRecorder, is_destructive_candidate
from .core import BASE_URL, build_url, ensure_local_output_dir
from .crud_probe import (
    ROUTES,
    RouteSpec,
    collect_row_affordances,
    create_triggers,
    delete_triggers,
    normalize_row_affordances,
    update_triggers,
    write_like_actions,
)
from .field_catalog_probe import (
    FieldChoice,
    FieldItem,
    SurfaceCatalog,
    _continuous_numeric_or_year_labels,
    _display_label,
    _open_detail,
    _open_update_surface,
    _render_surface,
    _sanitize_item,
    click_visible_exact,
    close_overlay,
    collect_surface_catalog,
    install_write_guard,
)


VIEW_FRAGMENT_RE = re.compile(r"^view-\d+$")
NUMERIC_SEGMENT_RE = re.compile(r"^\d+$")
NUMERIC_PATH_RE = re.compile(r"/\d+(?=/?(?:#|\?|$))")
SKIP_ROUTE_RE = re.compile(
    r"^/enterprise/(signin|signout|logout|notifications|password|two_factor|help)(?:/|$)"
)
STATIC_CUSTOM_FIELD_HINT_RE = re.compile(
    r"(タイプ|種別|ステータス|状態|ランク|経路|性別|国籍|都道府県|"
    r"現在の状況|公開状況|掲載状況|稼働形態|契約形態|工程|業界|"
    r"カテゴリ|区分|可否|有無|優先度|頻度|年|月|日|"
    r"type|status|rank|gender|nationality|category|kind|source)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class PageTypeSpec:
    name: str
    path: str
    page_type: str
    category: str = "discovered"
    source: str = "discovered"
    detail_path: str | None = None
    id_header_candidates: tuple[str, ...] = ()


def normalize_page_type(path_or_url: str, *, keep_semantic_hash: bool = True) -> str:
    """Normalize a FreelanceBase URL/path to a page-type identifier.

    Concrete numeric record IDs are replaced with `{id}`. Saved-view fragments
    such as `#view-1` are dropped because they identify a view instance rather
    than a page type. Semantic fragments such as `#all-tab` are kept.
    """
    url = build_url(path_or_url)
    parsed = urlparse(url)
    path = re.sub(r"/+", "/", parsed.path.rstrip("/") or "/")
    parts = ["{id}" if NUMERIC_SEGMENT_RE.match(part) else part for part in path.split("/")]
    normalized = "/".join(parts) or "/"
    if keep_semantic_hash and parsed.fragment and not VIEW_FRAGMENT_RE.match(parsed.fragment):
        normalized += f"#{parsed.fragment}"
    return normalized


def route_path_without_view(path_or_url: str) -> str:
    """Return a navigable route path while removing saved-view fragments."""
    url = build_url(path_or_url)
    parsed = urlparse(url)
    path = parsed.path.rstrip("/") or "/"
    if parsed.fragment and not VIEW_FRAGMENT_RE.match(parsed.fragment):
        return f"{path}#{parsed.fragment}"
    return path


def goto_probe_page(page: Any, path_or_url: str, *, timeout: int = 22_000) -> str:
    """Navigate for probing, falling back when pages keep network connections open."""
    url = build_url(path_or_url)
    try:
        page.goto(url, wait_until="networkidle", timeout=timeout)
    except Exception:
        page.goto(url, wait_until="domcontentloaded", timeout=timeout)
        page.wait_for_timeout(2500)
    return page.url


def is_record_route(path_or_url: str) -> bool:
    parsed = urlparse(build_url(path_or_url))
    return any(NUMERIC_SEGMENT_RE.match(part) for part in parsed.path.split("/"))


def is_probeable_enterprise_route(path_or_url: str) -> bool:
    parsed = urlparse(build_url(path_or_url))
    if not parsed.path.startswith("/enterprise/"):
        return False
    if SKIP_ROUTE_RE.search(parsed.path):
        return False
    return not is_record_route(path_or_url)


def normalize_dynamic_path(path_or_url: str) -> str:
    """Replace concrete numeric path segments with `{id}`."""
    return NUMERIC_PATH_RE.sub("/{id}", path_or_url)


def sanitize_api_call(call: dict[str, Any]) -> dict[str, Any]:
    """Remove concrete record URLs/IDs from an API summary."""
    out = dict(call)
    if out.get("path"):
        out["path"] = normalize_dynamic_path(str(out["path"]))
    if out.get("url"):
        parsed = urlparse(str(out["url"]))
        path = parsed.path or str(out["url"])
        out["url"] = normalize_dynamic_path(path)
    return out


def _known_route_specs() -> dict[str, PageTypeSpec]:
    out: dict[str, PageTypeSpec] = {}
    for route in ROUTES:
        page_type = normalize_page_type(route.path)
        out[page_type] = PageTypeSpec(
            name=route.name,
            path=route.path,
            page_type=page_type,
            category=route.category,
            source="known",
            detail_path=route.detail_path,
            id_header_candidates=route.id_header_candidates,
        )
    return out


def _fallback_name(path_or_url: str) -> str:
    page_type = normalize_page_type(path_or_url)
    leaf = page_type.split("#", 1)[0].rstrip("/").rsplit("/", 1)[-1]
    return leaf.replace("_", " ").replace("-", " ") or page_type


def collect_navigation_routes(page: Any, *, limit: int = 200) -> list[dict[str, str]]:
    """Collect non-record enterprise links from visible and hidden navigation."""
    return page.evaluate(
        """({baseUrl, limit}) => {
            const norm = value => ((value || '') + '').replace(/\\s+/g, ' ').trim();
            const visible = el => {
                const r = el.getBoundingClientRect();
                const s = getComputedStyle(el);
                return r.width > 0 && r.height > 0 && s.display !== 'none' && s.visibility !== 'hidden';
            };
            const out = [];
            const seen = new Set();
            for (const a of Array.from(document.querySelectorAll('a[href]'))) {
                const raw = a.getAttribute('href') || '';
                let url = '';
                try {
                    url = raw.startsWith('http') ? raw : new URL(raw, baseUrl).href;
                } catch (e) {
                    continue;
                }
                if (!url.startsWith(baseUrl + '/enterprise/')) continue;
                const key = url.split('?')[0];
                if (seen.has(key)) continue;
                seen.add(key);
                const label = norm(a.innerText || a.textContent || a.getAttribute('aria-label'));
                out.push({url: key, label, visible: visible(a) ? 'true' : 'false'});
                if (out.length >= limit) break;
            }
            return out;
        }""",
        {"baseUrl": BASE_URL, "limit": limit},
    )


def discover_page_types(
    page: Any,
    *,
    starts: list[str] | None = None,
    include_known: bool = True,
    limit: int = 200,
) -> list[PageTypeSpec]:
    """Discover route/page types from navigation and merge known core routes."""
    specs: dict[str, PageTypeSpec] = _known_route_specs() if include_known else {}
    start_paths = starts or ["/enterprise/candidates"]
    for start in start_paths:
        try:
            goto_probe_page(page, start, timeout=20_000)
            page.wait_for_timeout(1800)
        except Exception:
            continue
        for link in collect_navigation_routes(page, limit=limit):
            url = link.get("url", "")
            if not is_probeable_enterprise_route(url):
                continue
            page_type = normalize_page_type(url)
            if page_type in specs:
                continue
            specs[page_type] = PageTypeSpec(
                name=link.get("label") or _fallback_name(url),
                path=route_path_without_view(url),
                page_type=page_type,
                category="discovered",
                source="navigation",
            )
    return sorted(specs.values(), key=lambda spec: (spec.category, spec.page_type))


CUSTOM_SELECT_JS = r"""() => {
    const visible = el => {
        const r = el.getBoundingClientRect();
        const s = getComputedStyle(el);
        return r.width > 0 && r.height > 0 && s.display !== 'none' && s.visibility !== 'hidden';
    };
    const norm = value => ((value || '') + '').replace(/\s+/g, ' ').trim();
    const text = el => norm(el.innerText || el.textContent || el.getAttribute('aria-label') || el.getAttribute('placeholder') || '');
    const explicitLabel = el => {
        const id = el.getAttribute('id');
        if (id) {
            const label = Array.from(document.querySelectorAll('label')).find(l => l.htmlFor === id);
            if (label && visible(label)) return text(label).slice(0, 120);
        }
        const wrapped = el.closest('label');
        if (wrapped && visible(wrapped)) return text(wrapped).slice(0, 120);
        return '';
    };
    const neighborLabel = el => {
        let cur = el;
        for (let depth = 0; depth < 6 && cur; depth++) {
            const prev = cur.previousElementSibling;
            if (prev && visible(prev) && !prev.querySelector('input, textarea, select')) {
                const value = text(prev).slice(0, 120);
                if (value && value.length <= 80) return value;
            }
            cur = cur.parentElement;
        }
        return '';
    };
    const roots = Array.from(document.querySelectorAll(
        '.el-select, .ele-select, .v-select, .vue-treeselect, .multiselect, [role=combobox]'
    )).filter(visible);
    return roots.map((root, index) => {
        const input = root.querySelector('input, textarea, [role=combobox]') || root;
        const label = explicitLabel(input) || explicitLabel(root) || neighborLabel(root) || input.getAttribute('aria-label') || input.getAttribute('placeholder') || '';
        return {
            index,
            label: norm(label).slice(0, 120),
            name: input.getAttribute('name') || root.getAttribute('name') || '',
            placeholder: input.getAttribute('placeholder') || root.getAttribute('placeholder') || '',
            aria_label: input.getAttribute('aria-label') || root.getAttribute('aria-label') || '',
            text: text(root).slice(0, 120),
        };
    }).filter(item => item.label || item.name || item.placeholder || item.aria_label || item.text);
}"""


def _click_custom_select(page: Any, index: int) -> bool:
    return bool(
        page.evaluate(
            """(index) => {
                const visible = el => {
                    const r = el.getBoundingClientRect();
                    const s = getComputedStyle(el);
                    return r.width > 0 && r.height > 0 && s.display !== 'none' && s.visibility !== 'hidden';
                };
                const roots = Array.from(document.querySelectorAll(
                    '.el-select, .ele-select, .v-select, .vue-treeselect, .multiselect, [role=combobox]'
                )).filter(visible);
                const root = roots[index];
                if (!root) return false;
                const target = root.querySelector('input, [role=combobox], button') || root;
                target.scrollIntoView({block: 'center', inline: 'nearest'});
                target.click();
                return true;
            }""",
            index,
        )
    )


def _visible_dropdown_choices(page: Any) -> list[FieldChoice]:
    rows = page.evaluate(
        """() => {
            const visible = el => {
                const r = el.getBoundingClientRect();
                const s = getComputedStyle(el);
                return r.width > 0 && r.height > 0 && s.display !== 'none' && s.visibility !== 'hidden';
            };
            const norm = value => ((value || '') + '').replace(/\\s+/g, ' ').trim();
            const selectors = [
                '[role=option]',
                '.el-select-dropdown__item',
                '.ele-dropdown-body li',
                '.dropdown-menu li',
                '.multiselect__element',
                '.vue-treeselect__option',
                '.v-list-item'
            ];
            const seen = new Set();
            const out = [];
            for (const el of Array.from(document.querySelectorAll(selectors.join(','))).filter(visible)) {
                const label = norm(el.innerText || el.textContent || el.getAttribute('aria-label')).slice(0, 120);
                const value = norm(el.getAttribute('data-value') || el.getAttribute('value') || '').slice(0, 80);
                if (!label && !value) continue;
                const key = `${label}\\u0000${value}`;
                if (seen.has(key)) continue;
                seen.add(key);
                out.push({label, value, disabled: el.getAttribute('aria-disabled') === 'true' || el.classList.contains('disabled')});
            }
            return out.slice(0, 200);
        }"""
    )
    return [FieldChoice(**row) for row in rows]


def _sanitize_custom_item(item: FieldItem) -> FieldItem:
    sanitized = _sanitize_item(item)
    if sanitized.options_omitted or not sanitized.option_count:
        return sanitized  # type: ignore[return-value]
    labels = [choice.label for choice in sanitized.options if choice.label]
    target = f"{sanitized.label} {sanitized.name} {sanitized.placeholder} {sanitized.aria_label}"
    if not STATIC_CUSTOM_FIELD_HINT_RE.search(target) and not _continuous_numeric_or_year_labels(labels):
        sanitized.options = []
        sanitized.options_omitted = True
        sanitized.omit_reason = "custom select without static catalog hint"
    return sanitized  # type: ignore[return-value]


def enrich_custom_select_choices(page: Any, catalog: SurfaceCatalog, *, max_controls: int = 80) -> None:
    """Add static custom-dropdown choices to a surface catalog.

    Labels for likely live-data dropdowns are omitted. The browser remains on the
    same surface; only select-like controls are clicked and Escape is pressed
    after each collection.
    """
    try:
        controls = page.evaluate(CUSTOM_SELECT_JS)
    except Exception:
        catalog.notes.append("custom select probe failed")
        return
    existing_keys = {
        (
            (field.label or field.aria_label or field.placeholder).strip(),
            (field.name or "").strip(),
        )
        for field in catalog.fields
    }
    added = 0
    for control in controls[:max_controls]:
        if not _click_custom_select(page, int(control["index"])):
            continue
        page.wait_for_timeout(450)
        choices = _visible_dropdown_choices(page)
        page.keyboard.press("Escape")
        page.wait_for_timeout(120)
        if not choices:
            continue
        item = FieldItem(
            label=control.get("label") or control.get("aria_label") or control.get("placeholder") or control.get("text") or "",
            control="custom-select",
            name=control.get("name", ""),
            placeholder=control.get("placeholder", ""),
            aria_label=control.get("aria_label", ""),
            options=choices,
        )
        item = _sanitize_custom_item(item)
        key = ((item.label or item.aria_label or item.placeholder).strip(), (item.name or "").strip())
        matched = False
        for field in catalog.fields:
            field_key = (
                (field.label or field.aria_label or field.placeholder).strip(),
                (field.name or "").strip(),
            )
            if field_key == key and field.option_count == 0:
                field.control = item.control
                field.options = item.options
                field.option_count = item.option_count
                field.options_omitted = item.options_omitted
                field.omit_reason = item.omit_reason
                matched = True
                break
        if not matched and key not in existing_keys:
            catalog.fields.append(item)
            existing_keys.add(key)
            added += 1
    if added:
        catalog.notes.append(f"custom select choices probed: {added}")


def collect_enriched_surface_catalog(page: Any, kind: str, trigger: str) -> SurfaceCatalog:
    catalog = collect_surface_catalog(page, kind, trigger)
    # Page/detail titles can contain tenant names or record names. They are not
    # needed for the page-type schema and should not be persisted.
    catalog.title = ""
    enrich_custom_select_choices(page, catalog)
    return catalog


def _create_menu_items(page: Any) -> list[str]:
    return page.evaluate(
        """() => Array.from(document.querySelectorAll('.ele-dropdown-body a, .ele-dropdown-body li, [role=menu] *, a, li'))
            .map(el => ((el.innerText || el.textContent || '') + '').replace(/\\s+/g, ' ').trim())
            .filter(Boolean)
            .filter(text => text.length <= 80)
            .slice(0, 120)"""
    )


def _create_variant_labels(menu_items: list[str]) -> list[str | None]:
    preferred = ["通常作成", "新規作成", "手動作成", "作成"]
    variants: list[str | None] = []
    for label in preferred:
        if label in menu_items and label not in variants:
            variants.append(label)
    for label in menu_items:
        if label in variants:
            continue
        if re.search(r"(作成|追加)$", label) and "インポート" not in label:
            variants.append(label)
    return variants[:8] or [None]


def open_create_surfaces_all(page: Any, route: PageTypeSpec, triggers: list[str]) -> list[SurfaceCatalog]:
    surfaces: list[SurfaceCatalog] = []
    for trigger in triggers[:6]:
        try:
            goto_probe_page(page, route.path, timeout=18_000)
            page.wait_for_timeout(900)
            if not click_visible_exact(page, trigger, prefer_button=True):
                continue
            page.wait_for_timeout(900)
            variants = _create_variant_labels(_create_menu_items(page))
            for idx, variant in enumerate(variants):
                if idx > 0:
                    goto_probe_page(page, route.path, timeout=18_000)
                    page.wait_for_timeout(900)
                    if not click_visible_exact(page, trigger, prefer_button=True):
                        continue
                    page.wait_for_timeout(600)
                actual_trigger = trigger
                if variant:
                    if not click_visible_exact(page, variant):
                        close_overlay(page)
                        continue
                    actual_trigger = f"{trigger} > {variant}"
                    page.wait_for_timeout(1200)
                else:
                    page.wait_for_timeout(1200)
                surfaces.append(collect_enriched_surface_catalog(page, "create", actual_trigger))
                close_overlay(page)
                page.wait_for_timeout(400)
        except Exception as exc:
            surfaces.append(
                SurfaceCatalog(
                    kind="create",
                    trigger=trigger,
                    notes=[f"{type(exc).__name__}: create surface probe failed"],
                )
            )
    return surfaces


def collect_tab_list_surfaces(page: Any, route: PageTypeSpec, *, max_tabs: int = 16) -> list[SurfaceCatalog]:
    """Collect additional list catalogs for semantic tabs on the list page."""
    tabs = page.evaluate(
        """() => {
            const visible = el => {
                const r = el.getBoundingClientRect();
                const s = getComputedStyle(el);
                return r.width > 0 && r.height > 0 && s.display !== 'none' && s.visibility !== 'hidden';
            };
            const norm = value => ((value || '') + '').replace(/\\s+/g, ' ').trim();
            return Array.from(document.querySelectorAll('a[href^="#"], [role=tab]'))
                .filter(visible)
                .map((el, index) => ({
                    index,
                    text: norm(el.innerText || el.textContent || el.getAttribute('aria-label')).slice(0, 80),
                    href: el.getAttribute('href') || '',
                    role: el.getAttribute('role') || '',
                }))
                .filter(item => item.text || item.href)
                .slice(0, 40);
        }"""
    )
    out: list[SurfaceCatalog] = []
    seen: set[str] = set()
    for tab in tabs[:max_tabs]:
        label = tab.get("text") or tab.get("href") or ""
        if not label or label in seen:
            continue
        seen.add(label)
        try:
            clicked = page.evaluate(
                """(index) => {
                    const visible = el => {
                        const r = el.getBoundingClientRect();
                        const s = getComputedStyle(el);
                        return r.width > 0 && r.height > 0 && s.display !== 'none' && s.visibility !== 'hidden';
                    };
                    const tabs = Array.from(document.querySelectorAll('a[href^="#"], [role=tab]')).filter(visible);
                    const el = tabs[index];
                    if (!el) return false;
                    el.scrollIntoView({block: 'center', inline: 'nearest'});
                    el.click();
                    return true;
                }""",
                int(tab["index"]),
            )
            if not clicked:
                continue
            page.wait_for_timeout(1000)
            out.append(collect_enriched_surface_catalog(page, "list-tab", f"tab:{label}"))
        except Exception:
            continue
    return out


def _route_for_legacy_helpers(route: PageTypeSpec) -> RouteSpec:
    return RouteSpec(
        route.name,
        route.path,
        route.category,
        route.detail_path,
        route.id_header_candidates,
    )


def probe_page_type(
    page: Any,
    route: PageTypeSpec,
    blocked: list[dict[str, Any]],
    *,
    include_detail: bool = True,
    include_tabs: bool = False,
) -> dict[str, Any]:
    before_blocked = len(blocked)
    with ApiRecorder(page) as recorder:
        goto_probe_page(page, route.path, timeout=22_000)
        page.wait_for_timeout(1800)
        list_catalog = collect_enriched_surface_catalog(page, "list", "page")
        row_affordances = normalize_row_affordances(collect_row_affordances(page))
        tab_surfaces = collect_tab_list_surfaces(page, route) if include_tabs else []
        buttons = list_catalog.buttons
        create_surfaces = open_create_surfaces_all(page, route, create_triggers(buttons))

        detail_surface: SurfaceCatalog | None = None
        update_surfaces: list[SurfaceCatalog] = []
        detail_page_type = ""
        if include_detail:
            try:
                goto_probe_page(page, route.path, timeout=18_000)
                page.wait_for_timeout(1000)
                opened, detail_note = _open_detail(page, _route_for_legacy_helpers(route))
                detail_page_type = normalize_page_type(page.url) if opened else ""
                if opened:
                    detail_surface = collect_enriched_surface_catalog(page, "detail", detail_note)
                    update_surfaces = _open_update_surface(page)
                    for surface in update_surfaces:
                        enrich_custom_select_choices(page, surface)
                else:
                    detail_surface = SurfaceCatalog(kind="detail", trigger=detail_note, notes=[detail_note])
            except Exception as exc:
                detail_surface = SurfaceCatalog(kind="detail", trigger="failed", notes=[f"{type(exc).__name__}: detail probe failed"])

    api_calls = [sanitize_api_call(call) for call in recorder.to_dicts()]
    all_surfaces = [list_catalog, *tab_surfaces, *create_surfaces]
    if detail_surface:
        all_surfaces.append(detail_surface)
    all_surfaces.extend(update_surfaces)
    surface_dicts = [asdict(surface) for surface in all_surfaces]
    omitted_options = 0
    for surface in surface_dicts:
        omitted_options += sum(1 for item in surface.get("fields", []) if item.get("options_omitted"))
        omitted_options += sum(1 for item in surface.get("choice_groups", []) if item.get("options_omitted"))

    return {
        "name": route.name or list_catalog.title or _fallback_name(route.path),
        "category": route.category,
        "source": route.source,
        "path": route.path,
        "page_type": route.page_type,
        "final_page_type": normalize_page_type(page.url),
        "detail_page_type": detail_page_type,
        "list": asdict(list_catalog),
        "list_tab_surfaces": [asdict(surface) for surface in tab_surfaces],
        "create_surfaces": [asdict(surface) for surface in create_surfaces],
        "detail_surface": asdict(detail_surface) if detail_surface else None,
        "update_surfaces": [asdict(surface) for surface in update_surfaces],
        "crud": {
            "list": bool(list_catalog.table_columns) or any("/index" in c.get("path", "") for c in api_calls),
            "row_affordances": row_affordances,
            "create_triggers": create_triggers(buttons),
            "update_triggers": update_triggers(buttons),
            "delete_triggers": delete_triggers(buttons),
            "write_like_actions": write_like_actions(buttons),
            "api_calls": api_calls,
            "write_api_candidates": [
                c for c in api_calls if is_destructive_candidate(c.get("method", ""), c.get("path", ""))
            ],
            "blocked_requests": blocked[before_blocked:],
        },
        "stats": {
            "surfaces": len(surface_dicts),
            "table_column_groups": sum(len(surface.get("table_columns") or []) for surface in surface_dicts),
            "fields": sum(len(surface.get("fields") or []) for surface in surface_dicts),
            "choice_groups": sum(len(surface.get("choice_groups") or []) for surface in surface_dicts),
            "omitted_dynamic_option_groups": omitted_options,
        },
    }


def probe_freelancebase_schema(
    page: Any,
    *,
    starts: list[str] | None = None,
    include_known: bool = True,
    include_detail: bool = True,
    include_tabs: bool = False,
    route_limit: int = 0,
) -> dict[str, Any]:
    blocked: list[dict[str, Any]] = []
    install_write_guard(page, blocked)
    routes = discover_page_types(page, starts=starts, include_known=include_known)
    if route_limit:
        routes = routes[:route_limit]
    pages: list[dict[str, Any]] = []
    for route in routes:
        try:
            pages.append(
                probe_page_type(
                    page,
                    route,
                    blocked,
                    include_detail=include_detail,
                    include_tabs=include_tabs,
                )
            )
        except Exception as exc:
            pages.append(
                {
                    "name": route.name,
                    "category": route.category,
                    "source": route.source,
                    "path": route.path,
                    "page_type": route.page_type,
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )
    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "base_url": BASE_URL,
        "mode": "non_destructive_page_type_schema",
        "route_count": len(routes),
        "pages": pages,
        "blocked_requests": blocked,
        "notes": [
            "Concrete record IDs are normalized to {id}; the probe samples at most one visible row per page type.",
            "Current field values, raw HTML, screenshots, auth headers, cookies, and API bodies are not stored.",
            "Static select/radio/checkbox/custom-select choices are recorded. Likely live-data option labels are omitted.",
        ],
    }


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


def render_schema_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# FreelanceBase Page-Type Schema Catalog",
        "",
        f"- generated_at: `{payload.get('generated_at')}`",
        f"- page_types: `{len(payload.get('pages', []))}`",
        f"- blocked_write_requests: `{len(payload.get('blocked_requests', []))}`",
        "- mode: non-destructive Playwright probe; save/post/delete/publish/status-change final actions were not clicked",
        "",
        "This catalog is grouped by page type. Concrete record pages are sampled once where needed and normalized to `{id}` patterns.",
        "",
        "## Summary",
        "",
        "| Page Type | Route | Source | List | List Columns | Create | Detail Fields | Update | Delete UI | Write-like UI | Write API | Omitted Options |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for page in payload.get("pages", []):
        if page.get("error"):
            lines.append(
                f"| {page.get('name')} | `{page.get('page_type')}` | {page.get('source')} | error | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |"
            )
            continue
        crud = page.get("crud", {})
        stats = page.get("stats", {})
        detail = page.get("detail_surface") or {}
        detail_fields = len(detail.get("fields", [])) + len(detail.get("choice_groups", []))
        list_columns = sum(len(cols) for cols in _unique_column_sets(page.get("list") or {}))
        lines.append(
            "| {name} | `{route}` | {source} | {list_} | {cols} | {create} | {detail} | {update} | {delete} | {write_like} | {write_api} | {omitted} |".format(
                name=page.get("name", ""),
                route=page.get("page_type", ""),
                source=page.get("source", ""),
                list_="yes" if crud.get("list") else "no",
                cols=list_columns,
                create=len(page.get("create_surfaces") or []),
                detail=detail_fields,
                update=len(page.get("update_surfaces") or []),
                delete=len(crud.get("delete_triggers") or []),
                write_like=len(crud.get("write_like_actions") or []),
                write_api=len(crud.get("write_api_candidates") or []),
                omitted=stats.get("omitted_dynamic_option_groups", 0),
            )
        )
    for page in payload.get("pages", []):
        lines += ["", f"## {page.get('name')}", ""]
        lines.append(f"- route: `{page.get('page_type')}`")
        lines.append(f"- navigated: `{page.get('path')}`")
        lines.append(f"- source: `{page.get('source')}` / category: `{page.get('category')}`")
        if page.get("detail_page_type"):
            lines.append(f"- sampled detail page type: `{page.get('detail_page_type')}`")
        if page.get("error"):
            lines.append(f"- error: `{page.get('error')}`")
            continue
        crud = page.get("crud", {})
        lines += [
            "",
            "### CRUD / API",
            "",
            f"- create triggers: {', '.join(crud.get('create_triggers') or []) or 'none'}",
            f"- update triggers: {', '.join(crud.get('update_triggers') or []) or 'none'}",
            f"- delete triggers: {', '.join(crud.get('delete_triggers') or []) or 'none'}",
            f"- write-like actions: {', '.join(crud.get('write_like_actions') or []) or 'none'}",
            f"- row link patterns: {', '.join(crud.get('row_affordances', {}).get('linkHrefs', [])) or 'none'}",
            "- observed API:",
        ]
        for call in crud.get("api_calls") or []:
            flag = " write-candidate" if call.get("destructive_candidate") else ""
            lines.append(f"  - `{call.get('method')} {call.get('path')}` status={call.get('status')}{flag}")
        if not crud.get("api_calls"):
            lines.append("  - none")
        for title, surface in [("List", page.get("list")), *[
            (f"List Tab {idx}: `{surface.get('trigger', '')}`", surface)
            for idx, surface in enumerate(page.get("list_tab_surfaces") or [], start=1)
        ]]:
            if surface:
                lines += ["", *(_render_surface(surface, title))]
        if page.get("detail_surface"):
            lines += _render_surface(page["detail_surface"], "Detail")
        for idx, surface in enumerate(page.get("create_surfaces") or [], start=1):
            lines += _render_surface(surface, f"Create {idx}: `{surface.get('trigger', '')}`")
        for idx, surface in enumerate(page.get("update_surfaces") or [], start=1):
            lines += _render_surface(surface, f"Update {idx}: `{surface.get('trigger', '')}`")
    lines += ["", "## Notes", ""]
    lines += [f"- {note}" for note in payload.get("notes", [])]
    return "\n".join(lines) + "\n"


def write_schema_outputs(
    payload: dict[str, Any],
    out_dir: str | Path,
    *,
    docs_out: str | Path | None = None,
) -> dict[str, Path]:
    out = ensure_local_output_dir(out_dir)
    json_path = out / "page-type-schema.json"
    md_path = out / "page-type-schema.md"
    markdown = render_schema_markdown(payload)
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(markdown, encoding="utf-8")
    outputs = {"json": json_path, "markdown": md_path}
    if docs_out:
        docs_path = Path(docs_out).expanduser()
        docs_path.parent.mkdir(parents=True, exist_ok=True)
        docs_path.write_text(markdown, encoding="utf-8")
        outputs["docs"] = docs_path
    return outputs
