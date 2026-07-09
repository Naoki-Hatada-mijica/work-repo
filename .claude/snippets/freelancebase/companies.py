"""Company read helpers for FreelanceBase."""

from __future__ import annotations

import re
from typing import Any

from .core import COMPANIES_URL, company_detail_url
from .pages import click_counted_tab


def search_company_id_from_table(page: Any, name: str) -> str | None:
    """Search the visible companies table and return the first numeric company ID."""
    page.goto(COMPANIES_URL, wait_until="networkidle")
    page.wait_for_timeout(2000)
    search = page.locator("input[placeholder='クイック検索']").first
    search.fill(name)
    page.keyboard.press("Enter")
    page.wait_for_timeout(2500)
    return page.evaluate(
        """(name) => {
            const rows = Array.from(document.querySelectorAll('table tbody tr'));
            for (const row of rows) {
                const cells = Array.from(row.querySelectorAll('td'));
                if (!cells.some(c => (c.innerText || '').trim() === name)) continue;
                for (const cell of cells) {
                    const text = (cell.innerText || '').trim();
                    if (/^[0-9]+$/.test(text)) return text;
                }
            }
            return null;
        }""",
        name,
    )


def open_company_detail(page: Any, company_id_value: int | str) -> str:
    url = company_detail_url(company_id_value)
    page.goto(url, wait_until="networkidle")
    return page.url


def search_and_open_company(page: Any, name: str) -> str | None:
    company_id = search_company_id_from_table(page, name)
    if not company_id:
        return None
    return open_company_detail(page, company_id)


def parse_company_id_from_url(url: str) -> int | None:
    match = re.search(r"/enterprise/companies/(\d+)", url)
    return int(match.group(1)) if match else None


def open_company_comments(page: Any) -> bool:
    clicked = click_counted_tab(page, "コメント")
    if clicked:
        page.wait_for_timeout(1200)
    return clicked


def list_visible_company_contacts(page: Any, limit: int = 50) -> list[dict[str, str]]:
    """Return visible contact rows from the current company detail page."""
    tab = page.get_by_role("tab", name="企業担当者").first
    if tab.count() == 0:
        tab = page.locator("a, button").filter(has_text="企業担当者").first
    tab.click()
    page.wait_for_timeout(2000)
    contacts: list[dict[str, str]] = []
    for row in page.locator("table tbody tr").all()[:limit]:
        try:
            cells = row.locator("td").all()
            if len(cells) >= 3:
                contacts.append(
                    {
                        "name": cells[1].inner_text().strip(),
                        "email": cells[3].inner_text().strip() if len(cells) > 3 else "",
                    }
                )
        except Exception:
            continue
    return contacts

