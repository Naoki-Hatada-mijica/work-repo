#!/usr/bin/env python3
"""CLI for probing a FreelanceBase page specification.

Raw HTML, screenshots, auth headers, and API bodies are not saved by this tool.
Still, output may contain visible UI labels, so keep generated files local unless
you have reviewed them.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SNIPPETS_DIR = Path(__file__).resolve().parents[1]
if str(SNIPPETS_DIR) not in sys.path:
    sys.path.insert(0, str(SNIPPETS_DIR))

from playwright.sync_api import sync_playwright  # noqa: E402

import playwright_freelancebase as fb  # noqa: E402
from freelancebase.probe import probe_page, write_probe_outputs  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("url", help="FreelanceBase path or absolute URL")
    parser.add_argument("--out-dir", default="/tmp/freelancebase-spec", help="Local output directory")
    parser.add_argument("--stem", default="freelancebase-page-spec", help="Output filename stem")
    parser.add_argument("--headed", action="store_true", help="Run headed instead of headless")
    parser.add_argument("--wait-ms", type=int, default=2500)
    args = parser.parse_args()

    with sync_playwright() as pw:
        browser, context, page = fb.login(pw, headless=not args.headed)
        try:
            spec = probe_page(page, args.url, wait_ms=args.wait_ms)
            outputs = write_probe_outputs(spec, args.out_dir, stem=args.stem)
        finally:
            browser.close()

    for key, path in outputs.items():
        print(f"{key}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

