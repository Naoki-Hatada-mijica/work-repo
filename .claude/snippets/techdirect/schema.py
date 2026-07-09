"""Unified page-type schema probe for TechDirect.

The probe is non-destructive and page-type focused. It merges known TechDirect
routes with navigation-discovered route types, samples at most one representative
detail page per route type, and normalizes concrete org IDs, user UUIDs, and
record IDs to placeholders.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from .api import ApiRecorder, install_write_guard
from .catalog_probe import (
    Surface,
    _options_text,
    _unique_column_sets,
    clean_text,
    collect_surface,
    display_label,
    first_detail_url,
    normalize_href,
    open_list_menu,
    open_menu_surfaces,
    safe_label,
)
from .core import BASE_URL, build_url, ensure_local_output_dir
from .routes import ROUTES, RouteSpec


VIEW_STATE_RE = re.compile(r"(savedSearchId|listId|statusId|recruitmentStatusId|page|sort|order)")
UUID_SEGMENT_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f-]{27,36}$", re.IGNORECASE)
NUMERIC_SEGMENT_RE = re.compile(r"^\d+$")
MAX_PAGE_TYPES = 120
RECORD_PATTERNS = (
    re.compile(r"^/users/\{uuid\}(?:/|$)"),
    re.compile(r"^/jobs/\{id\}(?:/|$)"),
    re.compile(r"^/orgs/\{id\}/portal/applications/\{id\}(?:/|$)"),
    re.compile(
        r"^/orgs/\{id\}/portal/"
        r"(job-seeker-lists|recruitment-statuses|message-templates|scout-templates|recruiters)/\{id\}(?:/|$)"
    ),
    re.compile(r"^/user/(applications|bookmarks|saved_job_searches)/\{id\}(?:/|$)"),
)
SKIP_PATH_RE = re.compile(
    r"^/(login|logout|signup|password|notifications|terms|privacy|media|assets|packs|rails|uploads|images|api)(?:/|$)"
)
PAGE_LINK_RE = re.compile(r"^/(jobs|orgs|user|company|helps|inquiry)(?:/|$)")
STATIC_ASSET_RE = re.compile(
    r"\.(?:pdf|png|jpe?g|gif|svg|webp|zip|docx?|xlsx?|csv|json|ico)(?:$|\?)",
    re.IGNORECASE,
)
COUNT_LABEL_RE = re.compile(r"^(メッセージ|スカウト|応募|採用実績一覧|求職者一覧|案件一覧|担当者一覧|求職者リスト)\s+[0-9,]+$")


@dataclass(frozen=True)
class PageTypeSpec:
    name: str
    path: str
    page_type: str
    category: str = "discovered"
    source: str = "discovered"
    detail_kind: str = ""
    menu_triggers: tuple[str, ...] = ()


def normalize_page_type(path_or_url: str) -> str:
    """Normalize a TechDirect URL/path to a page-type route."""
    url = build_url(path_or_url)
    parsed = urlsplit(url)
    path = parsed.path.rstrip("/") or "/"
    normalized_parts: list[str] = []
    for part in path.split("/"):
        if UUID_SEGMENT_RE.match(part):
            normalized_parts.append("{uuid}")
        elif NUMERIC_SEGMENT_RE.match(part):
            normalized_parts.append("{id}")
        else:
            normalized_parts.append(part)
    return re.sub(r"/+", "/", "/".join(normalized_parts))


def is_record_page_type(page_type: str) -> bool:
    return any(pattern.match(page_type) for pattern in RECORD_PATTERNS)


def is_probeable_route(path_or_url: str) -> bool:
    page_type = normalize_page_type(path_or_url)
    if SKIP_PATH_RE.search(page_type):
        return False
    if is_record_page_type(page_type):
        return False
    return not VIEW_STATE_RE.search(urlsplit(build_url(path_or_url)).query)


def normalize_link_pattern(path_or_url: str) -> str:
    """Normalize a discovered link to a page-type pattern."""
    pattern = normalize_href(path_or_url)
    if pattern.startswith("/"):
        pattern = normalize_page_type(pattern)
    return pattern


def is_page_link_pattern(pattern: str) -> bool:
    if not pattern.startswith("/"):
        return False
    if STATIC_ASSET_RE.search(pattern):
        return False
    if SKIP_PATH_RE.search(pattern):
        return False
    if not PAGE_LINK_RE.search(pattern):
        return False
    return not is_record_page_type(pattern)


def goto_probe_page(page: Any, path_or_url: str, *, timeout: int = 24_000) -> str:
    """Navigate to a page, falling back when long-polling prevents networkidle."""
    url = build_url(path_or_url)
    try:
        page.goto(url, wait_until="networkidle", timeout=timeout)
    except Exception:
        page.goto(url, wait_until="domcontentloaded", timeout=timeout)
        page.wait_for_timeout(2500)
    return page.url


def known_page_types() -> dict[str, PageTypeSpec]:
    out: dict[str, PageTypeSpec] = {}
    for route in ROUTES:
        page_type = normalize_page_type(route.path)
        out[page_type] = PageTypeSpec(
            name=route.name,
            path=route.path,
            page_type=page_type,
            category=route.category,
            source="known",
            detail_kind=route.detail_kind,
            menu_triggers=route.menu_triggers,
        )
    return out


def fallback_name(path_or_url: str) -> str:
    page_type = normalize_page_type(path_or_url)
    parts = [part for part in page_type.strip("/").split("/") if part]
    leaf = parts[-1] if parts else page_type
    if leaf in {"{id}", "{uuid}"} and len(parts) >= 2:
        leaf = f"{parts[-2]} detail"
    if leaf in {"", "portal"}:
        leaf = page_type.rstrip("/").rsplit("/", 2)[-1]
    return leaf.replace("-", " ").replace("_", " ") or page_type


def collect_navigation_routes(page: Any, *, limit: int = 250) -> list[dict[str, str]]:
    return page.evaluate(
        """({baseUrl, limit}) => {
            const norm = value => ((value || '') + '').replace(/\\s+/g, ' ').trim();
            const visible = el => {
                const r = el.getBoundingClientRect();
                const s = getComputedStyle(el);
                return r.width > 0 && r.height > 0 && s.display !== 'none' && s.visibility !== 'hidden';
            };
            const rows = [];
            const seen = new Set();
            for (const a of Array.from(document.querySelectorAll('a[href]'))) {
                const raw = a.getAttribute('href') || '';
                let url = '';
                try {
                    url = raw.startsWith('http') ? raw : new URL(raw, baseUrl).href;
                } catch (e) {
                    continue;
                }
                const parsed = new URL(url);
                if (parsed.host !== 'techdirect.jp') continue;
                const key = parsed.origin + parsed.pathname;
                if (seen.has(key)) continue;
                seen.add(key);
                rows.push({
                    url: key,
                    label: norm(a.innerText || a.textContent || a.getAttribute('aria-label')).slice(0, 80),
                    visible: visible(a) ? 'true' : 'false',
                });
                if (rows.length >= limit) break;
            }
            return rows;
        }""",
        {"baseUrl": BASE_URL, "limit": limit},
    )


def discover_page_types(
    page: Any,
    *,
    starts: list[str] | None = None,
    include_known: bool = True,
) -> list[PageTypeSpec]:
    specs = known_page_types() if include_known else {}
    for start in starts or ["/jobs", "/orgs/39336/portal/"]:
        try:
            goto_probe_page(page, start)
            page.wait_for_timeout(1200)
        except Exception:
            continue
        for link in collect_navigation_routes(page):
            url = link.get("url", "")
            if not is_probeable_route(url):
                continue
            page_type = normalize_page_type(url)
            if page_type in specs:
                continue
            specs[page_type] = PageTypeSpec(
                name=link.get("label") or fallback_name(url),
                path=page_type,
                page_type=page_type,
                category="discovered",
                source="navigation",
            )
    return sorted(specs.values(), key=lambda spec: (spec.category, spec.page_type))


def page_type_from_link(pattern: str) -> PageTypeSpec | None:
    page_type = normalize_page_type(pattern)
    if not is_probeable_route(page_type):
        return None
    if not is_page_link_pattern(page_type):
        return None
    return PageTypeSpec(
        name=fallback_name(page_type),
        path=page_type,
        page_type=page_type,
        category="discovered",
        source="surface-link",
    )


def sanitize_surface(surface: Surface) -> Surface:
    """Drop page titles and keep only page-type structure."""
    surface.title = ""
    normalized_links: list[str] = []
    seen_links: set[str] = set()
    for raw_pattern in surface.link_patterns:
        pattern = normalize_link_pattern(raw_pattern)
        if not is_page_link_pattern(pattern) or pattern in seen_links:
            continue
        seen_links.add(pattern)
        normalized_links.append(pattern)
    surface.link_patterns = normalized_links[:80]
    surface.labels = sanitize_labels(surface.labels)
    surface.buttons = sanitize_labels(surface.buttons)
    surface.danger_labels = sanitize_labels(surface.danger_labels)
    surface.menu_options = sanitize_labels(surface.menu_options)
    return surface


def sanitize_label(label: str) -> str:
    label = clean_text(label)
    return COUNT_LABEL_RE.sub(r"\1件数", label)


def sanitize_labels(labels: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for raw_label in labels:
        label = sanitize_label(raw_label)
        if safe_label(label) and label not in seen:
            seen.add(label)
            out.append(label)
    return out


def sanitize_api_calls(calls: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for call in calls:
        row = dict(call)
        row["path"] = normalize_page_type(normalize_href(row.get("path", "")))
        out.append(row)
    return out


def collect_route_schema(page: Any, route: PageTypeSpec, blocked: list[dict[str, Any]]) -> dict[str, Any]:
    before = len(blocked)
    with ApiRecorder(page) as recorder:
        goto_probe_page(page, route.path)
        page.wait_for_timeout(2200)
        list_surface = sanitize_surface(collect_surface(page, "list", route.name))
        menu_surfaces = [
            asdict(sanitize_surface(Surface(**surface)))
            for surface in open_menu_surfaces(page, route.menu_triggers)
        ]

        detail_surface: Surface | None = None
        detail_page_type = ""
        if route.detail_kind:
            detail_url = first_detail_url(page, route.detail_kind)
            if detail_url:
                goto_probe_page(page, detail_url)
                page.wait_for_timeout(1800)
                detail_page_type = normalize_page_type(page.url)
                detail_surface = sanitize_surface(
                    collect_surface(page, "detail", f"first visible {route.detail_kind}")
                )
                menu_options, notes = open_list_menu(page)
                detail_surface.menu_options = sanitize_labels(menu_options)
                detail_surface.notes.extend(notes)
            else:
                detail_surface = Surface(
                    kind="detail",
                    trigger="no detail opened",
                    notes=[f"no visible {route.detail_kind} detail link"],
                )

    api_calls = sanitize_api_calls(recorder.to_dicts())
    surfaces = [asdict(list_surface), *menu_surfaces]
    if detail_surface:
        surfaces.append(asdict(detail_surface))
    return {
        "name": clean_text(route.name),
        "category": route.category,
        "source": route.source,
        "path": normalize_page_type(route.path),
        "page_type": route.page_type,
        "detail_page_type": detail_page_type,
        "list": asdict(list_surface),
        "menus": menu_surfaces,
        "detail": asdict(detail_surface) if detail_surface else None,
        "api_calls": api_calls,
        "blocked_requests": blocked[before:],
        "stats": {
            "surfaces": len(surfaces),
            "table_column_groups": sum(len(surface.get("table_columns") or []) for surface in surfaces),
            "fields": sum(len(surface.get("fields") or []) for surface in surfaces),
            "choice_groups": sum(len(surface.get("choice_groups") or []) for surface in surfaces),
            "omitted_dynamic_option_groups": sum(
                sum(1 for item in surface.get("fields", []) if item.get("options_omitted"))
                + sum(1 for item in surface.get("choice_groups", []) if item.get("options_omitted"))
                for surface in surfaces
            ),
        },
    }


def linked_page_types(page_schema: dict[str, Any]) -> list[PageTypeSpec]:
    out: list[PageTypeSpec] = []
    seen: set[str] = set()
    surfaces = [page_schema.get("list"), *(page_schema.get("menus") or [])]
    if page_schema.get("detail"):
        surfaces.append(page_schema["detail"])
    for surface in surfaces:
        if not surface:
            continue
        for pattern in surface.get("link_patterns") or []:
            spec = page_type_from_link(pattern)
            if spec and spec.page_type not in seen:
                seen.add(spec.page_type)
                out.append(spec)
    return out


def probe_techdirect_schema(
    page: Any,
    *,
    starts: list[str] | None = None,
    include_known: bool = True,
    route_limit: int = 0,
) -> dict[str, Any]:
    blocked: list[dict[str, Any]] = []
    install_write_guard(page, blocked)
    routes = discover_page_types(page, starts=starts, include_known=include_known)
    if route_limit:
        routes = routes[:route_limit]
    pages: list[dict[str, Any]] = []
    known_route_types = {route.page_type for route in routes}
    route_index = 0
    while route_index < len(routes):
        route = routes[route_index]
        try:
            page_schema = collect_route_schema(page, route, blocked)
            pages.append(page_schema)
            if not route_limit:
                for linked in linked_page_types(page_schema):
                    if linked.page_type in known_route_types:
                        continue
                    known_route_types.add(linked.page_type)
                    routes.append(linked)
                    if len(routes) >= MAX_PAGE_TYPES:
                        break
        except Exception as exc:
            pages.append(
                {
                    "name": clean_text(route.name),
                    "category": route.category,
                    "source": route.source,
                    "path": normalize_page_type(route.path),
                    "page_type": route.page_type,
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )
        route_index += 1
        if len(routes) >= MAX_PAGE_TYPES and route_index >= len(routes):
            break
    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "base_url": BASE_URL,
        "mode": "non_destructive_page_type_schema",
        "page_types": len(routes),
        "pages": pages,
        "blocked_requests": blocked,
        "notes": [
            "Concrete org IDs, user UUIDs, job IDs, application IDs, and API record IDs are normalized.",
            "User-created saved searches, list filter variants, and per-record pages are excluded from route discovery.",
            "Detail pages are sampled only as representative page types from the first visible link.",
            "Current field values, request/response bodies, cookies, auth headers, emails, phones, and UUIDs are not stored.",
        ],
    }


def render_surface(surface: dict[str, Any], title: str) -> list[str]:
    lines = [f"### {title}", ""]
    if surface.get("notes"):
        lines.append("- notes: " + "; ".join(surface["notes"]))
        lines.append("")
    column_sets = _unique_column_sets(surface)
    if column_sets:
        lines.append("- table columns:")
        for columns in column_sets:
            lines.append("  - " + ", ".join(f"`{column}`" for column in columns))
        lines.append("")
    labels = [display_label(label) for label in surface.get("labels", []) if label]
    if labels and title == "Detail":
        lines.append("- labels:")
        lines.append("  - " + ", ".join(f"`{label}`" for label in labels[:80]))
        if len(labels) > 80:
            lines.append(f"  - ... ({len(labels)} labels)")
        lines.append("")
    rows: list[str] = []
    for field_item in surface.get("fields", []):
        flags = ", ".join(name for name in ("required", "disabled", "readonly") if field_item.get(name)) or "-"
        rows.append(
            "| {label} | {control} | `{name}` | {flags} | {options} |".format(
                label=display_label(field_item.get("label") or "-"),
                control=f"{field_item.get('control')}/{field_item.get('type') or '-'}",
                name=field_item.get("name") or "",
                flags=flags,
                options=_options_text(field_item),
            )
        )
    for group in surface.get("choice_groups", []):
        rows.append(
            "| {label} | {control} | `{name}` | - | {options} |".format(
                label=display_label(group.get("label") or "-"),
                control=group.get("control") or "-",
                name=group.get("name") or "",
                options=_options_text(group),
            )
        )
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
    if surface.get("danger_labels"):
        lines.append("- write-like labels: " + ", ".join(f"`{label}`" for label in surface["danger_labels"]))
        lines.append("")
    if surface.get("menu_options"):
        lines.append("- menu/list options:")
        lines.append("  - " + ", ".join(f"`{label}`" for label in surface["menu_options"][:60]))
        lines.append("")
    return lines


def render_schema_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# TechDirect Page-Type Schema Catalog",
        "",
        f"- generated_at: `{payload['generated_at']}`",
        f"- page_types: `{len(payload['pages'])}`",
        f"- blocked_write_requests: `{len(payload.get('blocked_requests', []))}`",
        "- mode: non-destructive; write-like actions were not clicked and non-GET TechDirect/Codeal API requests are aborted",
        "",
        "## Summary",
        "",
        "| Page Type | Route | Source | List Columns | Menus | Detail | Fields | Write-like Labels | API Calls | Blocked Writes | Omitted Options |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for page in payload["pages"]:
        if page.get("error"):
            lines.append(
                f"| {page['name']} | `{page['page_type']}` | {page['source']} | error | 0 | 0 | 0 | 0 | 0 | 0 | 0 |"
            )
            continue
        surfaces = [page["list"], *(page.get("menus") or [])]
        if page.get("detail"):
            surfaces.append(page["detail"])
        list_cols = sum(len(cols) for cols in _unique_column_sets(page["list"]))
        write_labels = sum(len(surface.get("danger_labels") or []) for surface in surfaces)
        stats = page.get("stats") or {}
        lines.append(
            "| {name} | `{route}` | {source} | {cols} | {menus} | {detail} | {fields} | {write_labels} | {api} | {blocked} | {omitted} |".format(
                name=page["name"],
                route=page["page_type"],
                source=page["source"],
                cols=list_cols,
                menus=len(page.get("menus") or []),
                detail="yes" if page.get("detail") and not page["detail"].get("notes") else "partial" if page.get("detail") else "no",
                fields=stats.get("fields", 0) + stats.get("choice_groups", 0),
                write_labels=write_labels,
                api=len(page.get("api_calls") or []),
                blocked=len(page.get("blocked_requests") or []),
                omitted=stats.get("omitted_dynamic_option_groups", 0),
            )
        )
    for page in payload["pages"]:
        lines += ["", f"## {page['name']}", ""]
        lines.append(f"- route: `{page['page_type']}`")
        lines.append(f"- source: `{page['source']}` / category: `{page['category']}`")
        if page.get("detail_page_type"):
            lines.append(f"- sampled detail page type: `{page['detail_page_type']}`")
        if page.get("error"):
            lines.append(f"- error: `{page['error']}`")
            continue
        if page.get("api_calls"):
            lines += ["", "### API", ""]
            for call in page["api_calls"][:60]:
                flag = " write-candidate" if call.get("write_candidate") else ""
                lines.append(
                    f"- `{call['method']} {call['host']}{call['path']}` status={call.get('status')}{flag}"
                )
        lines += ["", *render_surface(page["list"], "List")]
        for idx, menu in enumerate(page.get("menus") or [], start=1):
            lines += render_surface(menu, f"Menu {idx}: `{menu.get('trigger', '')}`")
        if page.get("detail"):
            lines += render_surface(page["detail"], "Detail")
    lines += ["", "## Notes", ""]
    lines += [f"- {note}" for note in payload.get("notes", [])]
    return "\n".join(lines) + "\n"


def write_schema_outputs(payload: dict[str, Any], out_dir: str | Path, *, docs_out: str | Path | None = None) -> dict[str, Path]:
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
