"""Comment helpers shared across FreelanceBase resources."""

from __future__ import annotations

import re
from typing import Any

from .pages import click_counted_tab


def open_comments_tab(page: Any) -> bool:
    clicked = click_counted_tab(page, "コメント")
    if clicked:
        page.wait_for_timeout(1200)
    return clicked


def latest_candidate_comment(page: Any) -> dict[str, str] | None:
    """Read the latest visible candidate comment card on the current detail page."""
    if not open_comments_tab(page):
        return None
    cards = page.locator("div.comment-card").all()
    if not cards:
        return None
    top = cards[0]
    read_more = top.locator("div.read-more:not(.d-none)").first
    if read_more.count():
        button = read_more.locator("p.textc-dodger-blue").first
        if button.count():
            button.scroll_into_view_if_needed()
            button.click(force=True)
            page.wait_for_timeout(500)
    info = top.evaluate(
        """el => {
            const bodyEl = el.querySelector('.comment-body');
            let body = '';
            if (bodyEl) {
                const rows = Array.from(bodyEl.querySelectorAll(':scope > div.row'));
                const visible = rows.filter(r => !r.classList.contains('d-none') && !r.classList.contains('read-more'));
                body = visible.map(r => (r.innerText || '').trim()).filter(Boolean).join('\\n\\n');
            }
            return {body: body.trim(), full: (el.innerText || '').trim()};
        }"""
    )
    full = info.get("full", "")
    match = re.search(r"(\d{4}/\d{1,2}/\d{1,2})\s+(\d{1,2}:\d{2})", full)
    timestamp = f"{match.group(1)} {match.group(2)}" if match else ""
    author = ""
    head_match = re.search(r"コメント[：:]\s*(.+?)\s+\d{4}/\d{1,2}/\d{1,2}", full)
    if head_match:
        author = head_match.group(1).strip()
    return {"author": author, "timestamp": timestamp, "body": info.get("body", "")}

