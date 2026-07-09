#!/usr/bin/env python3
"""Google Drive の Meet 録画フォルダから、管理用IDを含む .mp4 録画をダウンロード.

使い方:
    python3 fetch_recording.py <management_id>
    python3 fetch_recording.py <management_id> --out /path/to/save.mp4

前提:
  - Google カレンダーの会議題名に管理用ID (MJC...) を入れる運用
  - Meet 録画は題名をファイル名のプレフィックスにして Drive に自動保存される

動作:
  - Shared Drive フォルダ (FOLDER_ID) 内を
    `name contains '<management_id>' and mimeType = 'video/mp4'`
    で検索
  - 複数ヒット時は `modifiedTime desc` の先頭を採用
  - OS tmp に DL（またはユーザー指定の --out）
  - 保存先パスを stdout に出力（既存 transcribe.py に渡せる）

注意:
  - Meet 録画は数百 MB〜数 GB になることがある。ダウンロードに時間がかかる点に注意
"""
from __future__ import annotations

import argparse
import io
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, __import__("os").path.expanduser("~/.claude/snippets"))

from googleapiclient.http import MediaIoBaseDownload  # noqa: E402
import google_workspace  # noqa: E402

FOLDER_ID = "1zSKyKBRB0lorObsu2P87Hu4EM81x-32k"
MP4_MIME = "video/mp4"


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("management_id", help="管理用ID (例 MJC90451111_TS)")
    p.add_argument("--out", help="ダウンロード先パス（省略時は OS tmp に自動命名）")
    args = p.parse_args()

    svc = google_workspace.get_drive_service()
    q = (
        f"'{FOLDER_ID}' in parents "
        f"and name contains '{args.management_id}' "
        f"and mimeType = '{MP4_MIME}' "
        f"and trashed = false"
    )
    res = svc.files().list(
        q=q,
        orderBy="modifiedTime desc",
        fields="files(id, name, mimeType, modifiedTime, size)",
        pageSize=10,
        includeItemsFromAllDrives=True,
        supportsAllDrives=True,
        corpora="allDrives",
    ).execute()
    hits = res.get("files", [])
    if not hits:
        print(f"[ERR] 録画 mp4 未ヒット: {args.management_id}", file=sys.stderr)
        return 2

    top = hits[0]
    if len(hits) > 1:
        print(
            f"[INFO] {len(hits)} 件ヒット、最新更新日を採用: "
            f"{top['name']} (modifiedTime={top['modifiedTime']})",
            file=sys.stderr,
        )
    size_bytes = int(top.get("size") or 0)
    print(
        f"[INFO] DL 開始: {top['name']} ({size_bytes / 1024 / 1024:.1f} MB)",
        file=sys.stderr,
    )

    if args.out:
        out_path = Path(args.out)
    else:
        tmp = tempfile.NamedTemporaryFile(
            prefix=f"recording_{args.management_id}_", suffix=".mp4", delete=False
        )
        tmp.close()
        out_path = Path(tmp.name)

    req = svc.files().get_media(fileId=top["id"], supportsAllDrives=True)
    buf = io.BytesIO()
    downloader = MediaIoBaseDownload(buf, req, chunksize=8 * 1024 * 1024)
    done = False
    last_pct = -1
    while not done:
        status, done = downloader.next_chunk()
        if status:
            pct = int(status.progress() * 100)
            if pct >= last_pct + 10 or done:
                print(f"  ... {pct}%", file=sys.stderr)
                last_pct = pct
    out_path.write_bytes(buf.getvalue())
    print(f"[OK] {top['name']} -> {out_path}", file=sys.stderr)
    print(out_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
