"""UI-level helpers for FreelanceBase Vue pages."""

from __future__ import annotations

import re
from typing import Any

DRAWER_SEL = ".modal_content.right-modal.right-open"


def click_counted_tab(page: Any, label: str) -> bool:
    """Click a tab whose text may be formatted as `label(N件)`."""
    return bool(
        page.evaluate(
            """([label]) => {
                const all = Array.from(document.querySelectorAll('button, a, li, span, div'));
                const exact = all.find(e => (e.innerText || '').trim() === label);
                if (exact) { exact.click(); return true; }
                const re = new RegExp('^' + label.replace(/[.*+?^${}()|[\\]\\\\]/g, '\\\\$&') + '\\\\(\\\\d+件\\\\)$');
                const candidates = all.filter(e => re.test((e.innerText || '').trim()));
                candidates.sort((a, b) => a.children.length - b.children.length);
                if (candidates[0]) { candidates[0].click(); return true; }
                return false;
            }""",
            [label],
        )
    )


def click_text(page: Any, text: str, *, exact: bool = True, max_len: int = 80) -> bool:
    """Click the first visible-ish element matching text via DOM JS."""
    return bool(
        page.evaluate(
            """([text, exact, maxLen]) => {
                const els = Array.from(document.querySelectorAll('button, a, li, span, div'));
                const target = els.find(e => {
                    const t = (e.innerText || '').trim();
                    if (!t || t.length > maxLen) return false;
                    return exact ? t === text : t.includes(text);
                });
                if (target) { target.click(); return true; }
                return false;
            }""",
            [text, exact, max_len],
        )
    )


def close_drawer(page: Any) -> None:
    if page.locator(DRAWER_SEL).count() == 0:
        return
    cancel = page.locator(f"{DRAWER_SEL} button").filter(has_text="キャンセル").first
    if cancel.count():
        cancel.click(force=True)
        page.wait_for_timeout(1000)
        return
    page.keyboard.press("Escape")
    page.wait_for_timeout(500)


def set_text_input(locator: Any, value: str) -> None:
    """Set a text input while dispatching events for Vue v-model."""
    locator.scroll_into_view_if_needed()
    locator.click()
    locator.fill("")
    locator.evaluate(
        """(el, v) => {
            el.focus();
            el.value = v;
            el.dispatchEvent(new Event('input', {bubbles:true}));
            el.dispatchEvent(new Event('change', {bubbles:true}));
            el.dispatchEvent(new Event('blur', {bubbles:true}));
        }""",
        value,
    )


def set_select_near_label(page: Any, label: str, option_text: str) -> str:
    """Set the nearest select around a label by visible option text."""
    return page.evaluate(
        """([labelText, optionText]) => {
            const all = Array.from(document.querySelectorAll('*'));
            const label = all.find(e =>
                (e.innerText || '').trim() === labelText &&
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
            const opt = Array.from(select.options).find(o => o.text.trim() === optionText);
            if (!opt) return 'option_not_found';
            select.value = opt.value;
            select.dispatchEvent(new Event('change', {bubbles: true}));
            select.dispatchEvent(new Event('input', {bubbles: true}));
            return 'ok';
        }""",
        [label, option_text],
    )


def extract_id_from_url(url: str, resource: str) -> int | None:
    match = re.search(rf"/enterprise/{re.escape(resource)}/(\d+)", url)
    return int(match.group(1)) if match else None

