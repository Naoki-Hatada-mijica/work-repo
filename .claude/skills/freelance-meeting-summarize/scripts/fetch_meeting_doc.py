#!/usr/bin/env python3
"""Google Drive の Meet 録画フォルダから、管理用IDを含む Gemini メモ (Google Docs) を検索.

使い方:
    python3 fetch_meeting_doc.py <management_id>

前提:
  - Google カレンダーの会議題名に管理用ID (MJC...) を入れる運用
  - Gemini のメモは題名をファイル名のプレフィックスにして Drive に自動保存される

動作:
  - Shared Drive フォルダ (FOLDER_ID) 内を
    `name contains '<management_id>' and mimeType = 'application/vnd.google-apps.document'`
    で検索
  - 複数ヒット時は `modifiedTime desc` の先頭を採用
  - 該当 Doc の URL (https://docs.google.com/document/d/<id>/edit) を stdout に出力
  - 既存の `fetch_doc.py` に渡して議事録本文を抽出できる
"""
from __future__ import annotations

import argparse
import sys

sys.path.insert(0, __import__("os").path.expanduser("~/.claude/snippets"))

import google_workspace  # noqa: E402

# Meet 録画・議事録保管フォルダ
FOLDER_ID = "1zSKyKBRB0lorObsu2P87Hu4EM81x-32k"
GDOC_MIME = "application/vnd.google-apps.document"


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("management_id", help="管理用ID (例 MJC90451111_TS)")
    args = p.parse_args()

    svc = google_workspace.get_drive_service()
    q = (
        f"'{FOLDER_ID}' in parents "
        f"and name contains '{args.management_id}' "
        f"and mimeType = '{GDOC_MIME}' "
        f"and trashed = false"
    )
    res = svc.files().list(
        q=q,
        orderBy="modifiedTime desc",
        fields="files(id, name, mimeType, modifiedTime)",
        pageSize=10,
        includeItemsFromAllDrives=True,
        supportsAllDrives=True,
        corpora="allDrives",
    ).execute()
    hits = res.get("files", [])
    if not hits:
        print(f"[ERR] 議事録 Doc 未ヒット: {args.management_id}", file=sys.stderr)
        return 2

    top = hits[0]
    if len(hits) > 1:
        print(
            f"[INFO] {len(hits)} 件ヒット、最新更新日を採用: "
            f"{top['name']} (modifiedTime={top['modifiedTime']})",
            file=sys.stderr,
        )
    url = f"https://docs.google.com/document/d/{top['id']}/edit"
    print(f"[OK] {top['name']} -> {url}", file=sys.stderr)
    print(url)
    return 0


if __name__ == "__main__":
    sys.exit(main())
