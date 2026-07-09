#!/usr/bin/env python3
"""Google Docs 本文取得ユーティリティ.

使い方:
    python3 fetch_doc.py <Google Docs URL or ID>

stdout に本文テキストを出力する。
"""

from __future__ import annotations

import sys
from pathlib import Path

SNIPPETS_DIR = Path.home() / ".claude" / "snippets"
if SNIPPETS_DIR.exists():
    sys.path.insert(0, str(SNIPPETS_DIR.parent))


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__, file=sys.stderr)
        return 1

    try:
        from snippets.google_workspace import get_doc_text
    except ImportError as e:
        print(
            "!! google_workspace ユーティリティの import に失敗しました。"
            f"\n   {SNIPPETS_DIR}/google_workspace.py を確認してください。\n   {e}",
            file=sys.stderr,
        )
        return 2

    try:
        text = get_doc_text(argv[0])
    except Exception as e:
        print(f"!! Google Docs 取得失敗: {e}", file=sys.stderr)
        return 3

    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
