#!/usr/bin/env python3
"""Probe dangerous FreelanceBase actions up to the final-click boundary.

This probe does not click final write-like actions such as save, publish,
release, status-change, or extraction buttons. It opens safe setup surfaces
such as create drawers and action menus, records final button labels, and blocks
write-like `/api/enterprise/...` requests as an extra guard.
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

from playwright.sync_api import sync_playwright  # noqa: E402

import playwright_freelancebase as fb  # noqa: E402
from freelancebase.api import api_path, is_destructive_candidate, is_enterprise_api  # noqa: E402
from freelancebase.core import BASE_URL, build_url, ensure_local_output_dir  # noqa: E402
from freelancebase.crud_probe import (  # noqa: E402
    RouteSpec,
    click_visible_exact,
    close_overlay,
    collect_overlay,
    first_row_id,
)


FINAL_ACTION_RE = re.compile(
    r"^(保存|保存する|公開する|リリース|下書き保存|本番に公開|"
    r"成約を確定|見送り|辞退|合算請求候補を抽出|コメントを投稿|"
    r"人材を作成|企業を作成|企業担当者を作成|案件を作成|商談を作成|"
    r"削除|公開停止|公開停止中|コピーする|.*を複製)$"
)
ACTION_LABEL_RE = re.compile(
    r"(保存|公開|リリース|下書き|本番|成約|見送り|辞退|抽出|投稿|作成|"
    r"削除|停止|複製|コピー|編集|処理順|次へ)"
)


@dataclass(frozen=True)
class DangerStep:
    name: str
    route: RouteSpec
    mode: str
    opener: str | None = None
    menu_candidate: str | None = None
    final_labels: tuple[str, ...] = ()


@dataclass
class ProbeResult:
    page: str
    mode: str
    stop_point: str
    visible_final_actions: list[str] = field(default_factory=list)
    setup_buttons: list[str] = field(default_factory=list)
    inputs: list[dict[str, Any]] = field(default_factory=list)
    blocked_requests: list[dict[str, Any]] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


STEPS: list[DangerStep] = [
    DangerStep(
        "人材 detail action menu",
        RouteSpec("人材", "/enterprise/candidates#view-1", "core", "/enterprise/candidates/{id}", ("人材ID",)),
        "detail-menu",
        opener="アクション",
    ),
    DangerStep(
        "企業 detail action menu",
        RouteSpec("企業", "/enterprise/companies#view-2", "core", "/enterprise/companies/{id}", ("企業ID",)),
        "detail-menu",
        opener="アクション",
    ),
    DangerStep(
        "案件 detail action menu",
        RouteSpec("案件", "/enterprise/jobs#view-3", "core", "/enterprise/jobs/{id}", ("案件ID",)),
        "detail-menu",
        opener="アクション",
    ),
    DangerStep(
        "商談 status actions",
        RouteSpec("商談", "/enterprise/opportunities#view-4", "core", "/enterprise/opportunities/{id}", ("商談ID",)),
        "detail-final-visible",
        final_labels=("成約を確定", "見送り", "辞退"),
    ),
    DangerStep(
        "契約 create wizard",
        RouteSpec("契約", "/enterprise/contracts#view-5", "contract"),
        "create-surface",
        opener="契約を作成",
    ),
    DangerStep(
        "請求・支払 aggregation",
        RouteSpec("請求・支払", "/enterprise/billing_payments#view-7", "contract"),
        "list-final-visible",
        final_labels=("合算請求候補を抽出",),
    ),
    DangerStep(
        "合算請求書 aggregation",
        RouteSpec("合算請求書", "/enterprise/billing_merges#view-10", "contract"),
        "list-final-visible",
        final_labels=("合算請求候補を抽出",),
    ),
    DangerStep(
        "自動化 publish",
        RouteSpec("自動化", "/enterprise/automation_emails#new-tab", "marketing"),
        "list-final-visible",
        final_labels=("処理順を編集", "公開する"),
    ),
    DangerStep(
        "自動化 create condition",
        RouteSpec("自動化", "/enterprise/automation_emails#new-tab", "marketing"),
        "create-surface",
        opener="条件を新規作成",
    ),
    DangerStep(
        "フォーム create/release",
        RouteSpec("フォーム", "/enterprise/questionnaire_forms", "marketing"),
        "create-surface",
        opener="フォームを作成",
    ),
    DangerStep(
        "配信 create wizard",
        RouteSpec("配信", "/enterprise/broadcasts#all-tab", "marketing"),
        "create-surface",
        opener="配信を作成",
    ),
    DangerStep(
        "案件サイト save/publish",
        RouteSpec("案件サイト", "/enterprise/sites#contents-tab_mainvisual-menu", "marketing"),
        "list-final-visible",
        final_labels=("保存", "公開する"),
    ),
    DangerStep(
        "記事 create/publish",
        RouteSpec("記事", "/enterprise/articles", "marketing"),
        "create-surface",
        opener="記事を作成",
    ),
]


def visible_labels(page: Any, selector: str = "button, a, [role=button], li", limit: int = 120) -> list[str]:
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
                .filter(t => t.length <= 80)
                .slice(0, limit);
        }""",
        {"selector": selector, "limit": limit},
    )


def final_actions(labels: list[str], expected: tuple[str, ...] = ()) -> list[str]:
    expected_set = set(expected)
    out = []
    for label in labels:
        if label in expected_set or FINAL_ACTION_RE.search(label):
            if label not in out:
                out.append(label)
    return out


def action_labels(labels: list[str]) -> list[str]:
    out = []
    for label in labels:
        if ACTION_LABEL_RE.search(label) and label not in out:
            out.append(label)
    return out


def open_first_detail(page: Any, route: RouteSpec) -> str:
    page.goto(build_url(route.path), wait_until="networkidle")
    page.wait_for_timeout(2200)
    if route.detail_path:
        rid = first_row_id(page, route.id_header_candidates)
        if rid:
            page.goto(build_url(route.detail_path.format(id=rid)), wait_until="networkidle")
            page.wait_for_timeout(1800)
            return "detail page opened by first row id"
    rows = page.locator("table tbody tr")
    if rows.count() == 0:
        return "no row available"
    rows.first.click(force=True)
    page.wait_for_timeout(1200)
    if page.get_by_text("詳細を見る", exact=True).count() > 0:
        page.get_by_text("詳細を見る", exact=True).first.click(force=True)
        page.wait_for_timeout(1500)
        return "detail opened from row drawer"
    return "row surface opened"


def install_write_guard(page: Any, blocked: list[dict[str, Any]]) -> None:
    def handler(route: Any, request: Any) -> None:
        if is_enterprise_api(request.url):
            path = api_path(request.url)
            if is_destructive_candidate(request.method, path):
                blocked.append({"method": request.method, "path": path, "reason": "aborted_by_danger_probe"})
                route.abort()
                return
        route.continue_()

    page.route("**/*", handler)


def probe_step(page: Any, step: DangerStep, blocked: list[dict[str, Any]]) -> ProbeResult:
    before = len(blocked)
    result = ProbeResult(page=step.name, mode=step.mode, stop_point="")
    if step.mode.startswith("detail"):
        result.stop_point = open_first_detail(page, step.route)
    else:
        page.goto(build_url(step.route.path), wait_until="networkidle")
        page.wait_for_timeout(2200)
        result.stop_point = "list/page opened"

    if step.mode == "detail-menu":
        if step.opener and click_visible_exact(page, step.opener, prefer_button=True):
            page.wait_for_timeout(800)
            labels = visible_labels(page)
            result.setup_buttons = action_labels(labels)
            result.visible_final_actions = final_actions(labels, step.final_labels)
            result.stop_point = f"opened setup menu `{step.opener}`; final menu item not clicked"
            close_overlay(page)
        else:
            result.notes.append(f"opener not found: {step.opener}")
            labels = visible_labels(page)
            result.visible_final_actions = final_actions(labels, step.final_labels)
    elif step.mode == "create-surface":
        if step.opener and click_visible_exact(page, step.opener, prefer_button=True):
            page.wait_for_timeout(1000)
            menu_labels = visible_labels(page)
            chosen = None
            for candidate in ("通常作成", "新規作成", "手動作成", "作成"):
                if candidate in menu_labels and click_visible_exact(page, candidate):
                    chosen = candidate
                    page.wait_for_timeout(1200)
                    break
            surface = collect_overlay(page, "danger-create", step.opener)
            result.setup_buttons = action_labels(surface.buttons)
            result.inputs = surface.inputs
            result.visible_final_actions = final_actions(surface.buttons, step.final_labels)
            suffix = f" > {chosen}" if chosen else ""
            result.stop_point = f"opened setup surface `{step.opener}{suffix}`; final action not clicked"
            close_overlay(page)
        else:
            result.notes.append(f"opener not found: {step.opener}")
    else:
        labels = visible_labels(page)
        result.setup_buttons = action_labels(labels)
        result.visible_final_actions = final_actions(labels, step.final_labels)
        result.stop_point = "final action visible on page; not clicked"

    result.blocked_requests = blocked[before:]
    return result


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# FreelanceBase Danger Action Probe",
        "",
        f"- generated_at: `{payload['generated_at']}`",
        "- mode: non-destructive; final write-like action buttons were not clicked",
        "- guard: write-like `/api/enterprise/...` requests are aborted if triggered",
        "",
        "## Summary",
        "",
        "| Step | Stop Point | Final Actions Visible | Inputs | Blocked Requests |",
        "|---|---|---|---:|---:|",
    ]
    for item in payload["results"]:
        lines.append(
            "| {page} | {stop} | {actions} | {inputs} | {blocked} |".format(
                page=item["page"],
                stop=item["stop_point"],
                actions=", ".join(item["visible_final_actions"]) or "none",
                inputs=len(item["inputs"]),
                blocked=len(item["blocked_requests"]),
            )
        )
    for item in payload["results"]:
        lines += [
            "",
            f"## {item['page']}",
            "",
            f"- mode: `{item['mode']}`",
            f"- stop_point: {item['stop_point']}",
            f"- visible_final_actions: {', '.join(item['visible_final_actions']) or 'none'}",
            f"- setup_buttons: {', '.join(item['setup_buttons'][:20]) or 'none'}",
            f"- input_count: `{len(item['inputs'])}`",
        ]
        if item["blocked_requests"]:
            lines.append("- blocked_requests:")
            for req in item["blocked_requests"]:
                lines.append(f"  - `{req['method']} {req['path']}`")
        if item["notes"]:
            lines.append("- notes:")
            for note in item["notes"]:
                lines.append(f"  - {note}")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", default="/tmp/freelancebase-danger-probe")
    parser.add_argument("--headed", action="store_true")
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    out = ensure_local_output_dir(args.out_dir)
    steps = STEPS[: args.limit] if args.limit else STEPS
    blocked: list[dict[str, Any]] = []
    with sync_playwright() as pw:
        browser, context, page = fb.login(pw, headless=not args.headed)
        try:
            install_write_guard(page, blocked)
            results = [asdict(probe_step(page, step, blocked)) for step in steps]
        finally:
            browser.close()

    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "base_url": BASE_URL,
        "mode": "non_destructive_final_click_boundary",
        "results": results,
        "blocked_requests": blocked,
    }
    json_path = out / "danger-probe.json"
    md_path = out / "danger-probe.md"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(render_markdown(payload), encoding="utf-8")
    print(f"json: {json_path}")
    print(f"markdown: {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
