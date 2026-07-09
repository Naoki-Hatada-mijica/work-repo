"""Page specification probe for FreelanceBase screens."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from .api import ApiRecorder
from .core import BASE_URL, build_url, ensure_local_output_dir, short_text


def collect_dom_spec(page: Any, *, max_items: int = 80) -> dict[str, Any]:
    """Collect a PII-minimized DOM summary from the current page."""
    return page.evaluate(
        """({maxItems}) => {
            const text = (el) => ((el.innerText || el.value || el.placeholder || el.getAttribute('aria-label') || '') + '').replace(/\\s+/g, ' ').trim();
            const attr = (el, name) => el.getAttribute(name) || '';
            const take = (selector, mapper) => Array.from(document.querySelectorAll(selector)).slice(0, maxItems).map(mapper).filter(Boolean);
            const inputs = take('input, textarea, select', el => ({
                tag: el.tagName.toLowerCase(),
                type: attr(el, 'type'),
                name: attr(el, 'name'),
                placeholder: attr(el, 'placeholder'),
                ariaLabel: attr(el, 'aria-label'),
                optionCount: el.tagName === 'SELECT' ? el.options.length : undefined
            }));
            const tables = take('table', table => {
                const headers = Array.from(table.querySelectorAll('thead th')).map(th => text(th)).filter(Boolean);
                const rowCount = table.querySelectorAll('tbody tr').length;
                const firstRowCellCount = table.querySelector('tbody tr') ? table.querySelector('tbody tr').querySelectorAll('td').length : 0;
                return {headers, rowCount, firstRowCellCount};
            });
            return {
                url: location.href,
                title: document.title,
                headings: take('h1,h2,h3,h4,h5,h6', el => text(el)).filter(t => t && t.length < 120),
                buttons: take('button', el => ({text: text(el), ariaLabel: attr(el, 'aria-label'), disabled: el.disabled})).filter(x => x.text || x.ariaLabel),
                links: take('a[href]', el => ({text: text(el), href: attr(el, 'href')})).filter(x => x.text || x.href),
                tabs: take('[role=tab], a[href^="#"]', el => ({text: text(el), href: attr(el, 'href'), role: attr(el, 'role')})).filter(x => x.text || x.href),
                inputs,
                tables,
                drawers: document.querySelectorAll('.modal_content.right-modal.right-open').length,
                modals: document.querySelectorAll('[role=dialog], .modal, .modal_content').length
            };
        }""",
        {"maxItems": max_items},
    )


def sanitize_dom_spec(spec: dict[str, Any]) -> dict[str, Any]:
    """Trim long UI labels while keeping structural value."""
    out = dict(spec)
    for key in ("headings",):
        out[key] = [short_text(v, 120) for v in out.get(key, [])]
    for key in ("buttons", "links", "tabs"):
        rows = []
        for item in out.get(key, []):
            row = dict(item)
            if "text" in row:
                row["text"] = short_text(row["text"], 120)
            rows.append(row)
        out[key] = rows
    return out


def probe_page(page: Any, path_or_url: str, *, wait_ms: int = 2500, max_items: int = 80) -> dict[str, Any]:
    """Navigate to a page and return DOM + API summaries."""
    url = build_url(path_or_url)
    with ApiRecorder(page) as recorder:
        page.goto(url, wait_until="networkidle")
        page.wait_for_timeout(wait_ms)
        dom = collect_dom_spec(page, max_items=max_items)
    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "page": sanitize_dom_spec(dom),
        "api_calls": recorder.to_dicts(),
        "notes": [
            "Table cell values are intentionally omitted to reduce PII exposure.",
            "API bodies and auth headers are intentionally omitted.",
        ],
    }


def render_markdown(spec: dict[str, Any]) -> str:
    page = spec.get("page", {})
    lines = [
        f"# FreelanceBase Page Spec: {page.get('title') or page.get('url')}",
        "",
        f"- URL: `{page.get('url', '')}`",
        f"- Generated: `{spec.get('generated_at', '')}`",
        f"- Drawers: `{page.get('drawers', 0)}`",
        f"- Modals: `{page.get('modals', 0)}`",
        "",
        "## Headings",
        "",
    ]
    lines += [f"- {h}" for h in page.get("headings", [])[:40]] or ["- none"]
    lines += ["", "## Buttons", ""]
    lines += [
        f"- {b.get('text') or b.get('ariaLabel') or '(unnamed)'}"
        for b in page.get("buttons", [])[:80]
    ] or ["- none"]
    lines += ["", "## Tabs", ""]
    lines += [
        f"- {t.get('text') or t.get('href') or '(unnamed)'}"
        for t in page.get("tabs", [])[:80]
    ] or ["- none"]
    lines += ["", "## Forms", ""]
    for item in page.get("inputs", [])[:80]:
        desc = ", ".join(
            f"{k}={v!r}"
            for k, v in item.items()
            if v not in ("", None)
        )
        lines.append(f"- {desc}")
    if not page.get("inputs"):
        lines.append("- none")
    lines += ["", "## Tables", ""]
    for table in page.get("tables", []):
        lines.append(
            f"- headers={table.get('headers', [])}, rows={table.get('rowCount', 0)}, first_row_cells={table.get('firstRowCellCount', 0)}"
        )
    if not page.get("tables"):
        lines.append("- none")
    lines += ["", "## API Calls", ""]
    for call in spec.get("api_calls", []):
        flag = " destructive-candidate" if call.get("destructive_candidate") else ""
        lines.append(
            f"- `{call.get('method')} {call.get('path')}` status={call.get('status')} keys={call.get('request_keys') or []}{flag}"
        )
    if not spec.get("api_calls"):
        lines.append("- none")
    lines += ["", "## Notes", ""]
    lines += [f"- {note}" for note in spec.get("notes", [])]
    return "\n".join(lines) + "\n"


def write_probe_outputs(spec: dict[str, Any], out_dir: str | Path, stem: str = "freelancebase-page-spec") -> dict[str, Path]:
    out = ensure_local_output_dir(out_dir)
    json_path = out / f"{stem}.json"
    md_path = out / f"{stem}.md"
    json_path.write_text(json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(render_markdown(spec), encoding="utf-8")
    return {"json": json_path, "markdown": md_path}


def collect_enterprise_links(page: Any, *, include_details: bool = False, max_links: int = 200) -> list[str]:
    """Collect internal `/enterprise/` links from the current page.

    Detail pages with numeric IDs are skipped by default to avoid broad PII
    crawling. Pass `include_details=True` only for a specific approved task.
    """
    links = page.evaluate(
        """({baseUrl}) => {
            const out = new Set();
            for (const a of Array.from(document.querySelectorAll('a[href]'))) {
                const href = a.getAttribute('href') || '';
                const url = href.startsWith('http') ? href : new URL(href, baseUrl).href;
                if (url.startsWith(baseUrl + '/enterprise/')) out.add(url);
            }
            return Array.from(out);
        }""",
        {"baseUrl": BASE_URL},
    )
    filtered: list[str] = []
    for url in sorted(links):
        path = url.split(BASE_URL, 1)[-1]
        if not include_details and any(part.isdigit() for part in path.split("/")):
            continue
        filtered.append(url)
    return filtered[:max_links]


def probe_link_set(
    page: Any,
    start_path_or_url: str = "/enterprise/candidates",
    *,
    out_dir: str | Path,
    limit: int = 20,
) -> dict[str, Path]:
    """Probe navigation-linked enterprise pages from one starting page."""
    start_url = build_url(start_path_or_url)
    page.goto(start_url, wait_until="networkidle")
    page.wait_for_timeout(2000)
    links = [start_url]
    for link in collect_enterprise_links(page, include_details=False, max_links=limit):
        if link not in links:
            links.append(link)
    links = links[:limit]
    out = ensure_local_output_dir(out_dir)
    index: list[dict[str, str]] = []
    for i, url in enumerate(links, start=1):
        spec = probe_page(page, url, wait_ms=1200)
        stem = f"{i:02d}-" + (
            url.split("/enterprise/", 1)[-1]
            .replace("/", "-")
            .replace("#", "-")
            .strip("-")
            or "enterprise"
        )
        paths = write_probe_outputs(spec, out, stem=stem)
        index.append({"url": url, "json": str(paths["json"]), "markdown": str(paths["markdown"])})
    index_path = out / "index.json"
    index_path.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"index": index_path}
