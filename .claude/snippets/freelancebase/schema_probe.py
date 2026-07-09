#!/usr/bin/env python3
"""Unified non-destructive FreelanceBase page-type schema probe."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SNIPPETS_DIR = Path(__file__).resolve().parents[1]
if str(SNIPPETS_DIR) not in sys.path:
    sys.path.insert(0, str(SNIPPETS_DIR))

from playwright.sync_api import sync_playwright  # noqa: E402

import playwright_freelancebase as fb  # noqa: E402
from freelancebase.schema import probe_freelancebase_schema, write_schema_outputs  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", default="/tmp/freelancebase-page-type-schema")
    parser.add_argument(
        "--docs-out",
        help="Optional sanitized markdown path to update under git-managed docs.",
    )
    parser.add_argument(
        "--start",
        action="append",
        help="Navigation start path. Can be repeated. Defaults to /enterprise/candidates.",
    )
    parser.add_argument("--headed", action="store_true")
    parser.add_argument("--limit", type=int, default=0, help="Limit discovered routes for smoke tests")
    parser.add_argument("--no-known", action="store_true", help="Do not merge the curated known route list")
    parser.add_argument("--no-detail", action="store_true", help="Skip first-row detail sampling")
    parser.add_argument("--include-tabs", action="store_true", help="Also sample visible list tab variants")
    args = parser.parse_args()

    with sync_playwright() as pw:
        browser, context, page = fb.login(pw, headless=not args.headed)
        try:
            payload = probe_freelancebase_schema(
                page,
                starts=args.start,
                include_known=not args.no_known,
                include_detail=not args.no_detail,
                include_tabs=args.include_tabs,
                route_limit=args.limit,
            )
        finally:
            browser.close()

    outputs = write_schema_outputs(payload, args.out_dir, docs_out=args.docs_out)
    for key, path in outputs.items():
        print(f"{key}: {path}")
    print(f"page_types: {len(payload.get('pages', []))}")
    print(f"blocked_write_requests: {len(payload.get('blocked_requests', []))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
