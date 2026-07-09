#!/usr/bin/env python3
"""Probe multiple navigation-linked FreelanceBase enterprise pages."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SNIPPETS_DIR = Path(__file__).resolve().parents[1]
if str(SNIPPETS_DIR) not in sys.path:
    sys.path.insert(0, str(SNIPPETS_DIR))

from playwright.sync_api import sync_playwright  # noqa: E402

import playwright_freelancebase as fb  # noqa: E402
from freelancebase.probe import probe_link_set  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", default="/enterprise/candidates", help="Starting page")
    parser.add_argument("--out-dir", default="/tmp/freelancebase-site-spec")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--headed", action="store_true")
    args = parser.parse_args()

    with sync_playwright() as pw:
        browser, context, page = fb.login(pw, headless=not args.headed)
        try:
            outputs = probe_link_set(page, args.start, out_dir=args.out_dir, limit=args.limit)
        finally:
            browser.close()

    for key, path in outputs.items():
        print(f"{key}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

