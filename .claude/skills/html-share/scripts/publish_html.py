#!/usr/bin/env python3
"""Publish an HTML file to the html_share GAS Web App."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
from pathlib import Path


CONFIG_PATH = Path.home() / ".config" / "html_share" / "config.json"
VALID_VISIBILITIES = {"company", "link", "external"}


def load_config() -> dict[str, str]:
    web_app_url = os.environ.get("HTML_SHARE_WEB_APP_URL", "").strip()
    admin_token = os.environ.get("HTML_SHARE_ADMIN_TOKEN", "").strip()

    if web_app_url and admin_token:
        return {"webAppUrl": web_app_url, "adminToken": admin_token}

    if CONFIG_PATH.exists():
        data = json.loads(CONFIG_PATH.read_text())
        web_app_url = web_app_url or str(data.get("webAppUrl", "")).strip()
        admin_token = admin_token or str(data.get("adminToken", "")).strip()

    if not web_app_url:
        raise SystemExit("HTML Share config missing: webAppUrl")
    if not admin_token:
        raise SystemExit("HTML Share config missing: adminToken")

    return {"webAppUrl": web_app_url, "adminToken": admin_token}


def post_json(url: str, payload: dict) -> dict:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


def default_title(path: Path) -> str:
    return path.stem[:120] or "HTML Report"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Publish an HTML file to HTML Share.")
    parser.add_argument("html_file", type=Path, help="Path to .html or .htm file")
    parser.add_argument("--title", help="Share title. Defaults to filename without extension.")
    parser.add_argument("--description", default="", help="Share description.")
    parser.add_argument(
        "--visibility",
        choices=sorted(VALID_VISIBILITIES),
        default="company",
        help="Share visibility. Default: company.",
    )
    parser.add_argument("--expires-at", default="", help="ISO datetime or datetime-local value accepted by GAS.")
    parser.add_argument("--password", default="", help="Optional share password.")
    parser.add_argument("--no-embed", action="store_true", help="Disable iframe embed URL.")
    parser.add_argument("--json", action="store_true", help="Print full JSON response.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    html_file = args.html_file.expanduser().resolve()
    if not html_file.exists() or not html_file.is_file():
        raise SystemExit(f"HTML file not found: {html_file}")
    if html_file.suffix.lower() not in {".html", ".htm"}:
        raise SystemExit("Input must be a .html or .htm file")

    html = html_file.read_text(encoding="utf-8")
    config = load_config()
    payload = {
        "action": "createShare",
        "token": config["adminToken"],
        "payload": {
            "title": args.title or default_title(html_file),
            "description": args.description,
            "html": html,
            "visibility": args.visibility,
            "expiresAt": args.expires_at,
            "password": args.password,
            "allowEmbed": not args.no_embed,
        },
    }

    response = post_json(config["webAppUrl"], payload)
    if not response.get("ok"):
        raise SystemExit(response.get("error") or json.dumps(response, ensure_ascii=False))

    share = response["share"]
    if args.json:
        print(json.dumps(share, ensure_ascii=False, indent=2))
    else:
        print(share["assets"]["shareUrl"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
