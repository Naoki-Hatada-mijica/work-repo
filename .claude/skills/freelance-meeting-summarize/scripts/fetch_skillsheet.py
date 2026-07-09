#!/usr/bin/env python3
"""Google Drive の指定フォルダ内から、管理用ID を含むスキルシートを検索・ダウンロード.

使い方:
    python3 fetch_skillsheet.py <management_id>
    python3 fetch_skillsheet.py <management_id> --out /path/to/save.xlsx
    python3 fetch_skillsheet.py <management_id> --with-url
    python3 fetch_skillsheet.py <management_id> --no-share  # 共有権限を変更しない
    python3 fetch_skillsheet.py <management_id> --name "佐伯 英良"  # 未ヒット時に氏名で救済

動作:
  - フォルダ (FOLDER_ID) 内 で name contains '<management_id>' を検索
  - 複数ヒット時は modifiedTime desc で最新を 1 件採用
  - **管理用ID で未ヒットかつ `--name <氏名>` 指定時はフォールバック**:
    氏名（姓のみでも可）でフォルダ内を検索し、現物が見つかれば
    ファイル名を `<management_id>_<元の名前>` にリネームしてから採用する。
    これにより、運営が管理用ID無しの名前で置いたスキルシートを次回以降 ID で引けるようにする。
  - Google Sheets なら xlsx にエクスポート、通常ファイルならそのままダウンロード
  - **既定で** 対象ファイルに「リンクを知っている全員 = 閲覧者」権限を付与（CRM 共有用途）
    `--no-share` で権限変更をスキップ可能
  - ダウンロード先パスを stdout に出力（--with-url 指定時は 1行目=path, 2行目=webViewLink）
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

# スキルシート保管フォルダ（要件で指定）
FOLDER_ID = "1xBLxRqRnnMVi8IYy1tbDQ9CD1BP4BftT"

# Google ネイティブ mime → export する mime と拡張子
EXPORT_MAP = {
    "application/vnd.google-apps.spreadsheet": (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".xlsx",
    ),
    "application/vnd.google-apps.document": (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".docx",
    ),
    "application/vnd.google-apps.presentation": (
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        ".pptx",
    ),
}


def _list(svc, keyword: str) -> list[dict]:
    """フォルダ内を name contains '<keyword>' で検索（最新更新順）."""
    q = (
        f"'{FOLDER_ID}' in parents "
        f"and name contains '{keyword}' "
        f"and trashed = false"
    )
    res = svc.files().list(
        q=q,
        orderBy="modifiedTime desc",
        fields="files(id, name, mimeType, modifiedTime, webViewLink)",
        pageSize=10,
        # FOLDER_ID が Shared Drive 配下にあるため以下が必須
        includeItemsFromAllDrives=True,
        supportsAllDrives=True,
        corpora="allDrives",
    ).execute()
    return res.get("files", [])


def search(svc, management_id: str) -> list[dict]:
    return _list(svc, management_id)


def search_by_name(svc, name: str) -> list[dict]:
    """氏名（フルネーム→姓）でフォールバック検索する.

    "佐伯 英良" のような空白入りはまずフルネーム連結（佐伯英良）で引き、
    無ければ姓のみ（佐伯）で引く。運営がスキルシートに付ける表記ゆれを吸収する。
    """
    norm = (name or "").replace(" ", "").replace("　", "").strip()
    hits = _list(svc, norm) if norm else []
    if not hits:
        last = (name or "").replace("　", " ").strip().split(" ")[0]
        if last and last != norm:
            hits = _list(svc, last)
    return hits


def rename_with_management_id(svc, file: dict, management_id: str) -> dict:
    """ファイル名を `<management_id>_<元の名前>` にリネームし、更新後の file dict を返す.

    既に名前に management_id を含む場合はリネームしない（冪等）。
    """
    name = file.get("name", "")
    if management_id in name:
        return file
    new_name = f"{management_id}_{name}"
    updated = svc.files().update(
        fileId=file["id"],
        body={"name": new_name},
        fields="id, name, mimeType, modifiedTime, webViewLink",
        supportsAllDrives=True,
    ).execute()
    return updated


def ensure_anyone_reader(svc, file_id: str) -> str:
    """対象ファイルに「リンクを知っている全員 = 閲覧者」権限を付与（既存があればスキップ）.

    戻り値: "granted" / "already" / "error: ..."
    """
    try:
        existing = svc.permissions().list(
            fileId=file_id,
            fields="permissions(id, type, role)",
            supportsAllDrives=True,
        ).execute()
        for perm in existing.get("permissions", []):
            if perm.get("type") == "anyone":
                return "already"
        svc.permissions().create(
            fileId=file_id,
            body={"type": "anyone", "role": "reader"},
            supportsAllDrives=True,
            sendNotificationEmail=False,
        ).execute()
        return "granted"
    except Exception as e:  # noqa: BLE001
        return f"error: {e}"


def download(svc, file: dict, out_path: Path) -> Path:
    mime = file["mimeType"]
    file_id = file["id"]
    if mime in EXPORT_MAP:
        export_mime, ext = EXPORT_MAP[mime]
        if out_path.suffix.lower() != ext:
            out_path = out_path.with_suffix(ext)
        req = svc.files().export_media(fileId=file_id, mimeType=export_mime)
    else:
        req = svc.files().get_media(fileId=file_id, supportsAllDrives=True)
    buf = io.BytesIO()
    downloader = MediaIoBaseDownload(buf, req)
    done = False
    while not done:
        _status, done = downloader.next_chunk()
    out_path.write_bytes(buf.getvalue())
    return out_path


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("management_id", help="管理用ID (例 MJC90451111_TS)")
    p.add_argument("--out", help="ダウンロード先パス（省略時は OS tmp に自動命名）")
    p.add_argument(
        "--with-url",
        action="store_true",
        help="stdout を 1行目=保存先パス, 2行目=webViewLink の2行出力にする",
    )
    p.add_argument(
        "--no-share",
        action="store_true",
        help="リンクを知っている全員 = 閲覧者の共有権限付与をスキップ（既定は付与）",
    )
    p.add_argument(
        "--name",
        help="管理用ID で未ヒット時に氏名で救済検索する（例 '佐伯 英良'）。"
        "見つかればファイル名を <管理用ID>_ にリネームしてから採用する",
    )
    args = p.parse_args()

    svc = google_workspace.get_drive_service()
    hits = search(svc, args.management_id)

    if not hits and args.name:
        # フォールバック: 氏名で現物を探し、見つかれば管理用IDにリネームして採用
        name_hits = search_by_name(svc, args.name)
        if name_hits:
            top = name_hits[0]
            if len(name_hits) > 1:
                print(
                    f"[WARN] 氏名 '{args.name}' で {len(name_hits)} 件ヒット、"
                    f"最新更新日を採用: {top['name']}（取り違えに注意）",
                    file=sys.stderr,
                )
            renamed = rename_with_management_id(svc, top, args.management_id)
            if renamed.get("name") != top.get("name"):
                print(
                    f"[RENAME] {top['name']} -> {renamed['name']}（管理用ID付与）",
                    file=sys.stderr,
                )
            hits = [renamed]

    if not hits:
        print(f"[ERR] Drive 未ヒット: {args.management_id}", file=sys.stderr)
        return 2

    top = hits[0]
    if len(hits) > 1:
        print(
            f"[INFO] {len(hits)} 件ヒット、最新更新日を採用: "
            f"{top['name']} (modifiedTime={top['modifiedTime']})",
            file=sys.stderr,
        )

    if args.out:
        out = Path(args.out)
    else:
        suffix = Path(top["name"]).suffix or ".bin"
        tmp = tempfile.NamedTemporaryFile(
            prefix=f"skillsheet_{args.management_id}_", suffix=suffix, delete=False
        )
        tmp.close()
        out = Path(tmp.name)

    out = download(svc, top, out)
    web_view_link = top.get("webViewLink", "")
    # ファイル名（Drive 上の元名 + 保存先パス + URL）を stderr に出力
    print(f"[OK] {top['name']} -> {out}", file=sys.stderr)
    print(f"[URL] {web_view_link}", file=sys.stderr)

    if not args.no_share:
        share_status = ensure_anyone_reader(svc, top["id"])
        print(f"[SHARE] anyone-reader: {share_status}", file=sys.stderr)

    print(out)
    if args.with_url:
        print(web_view_link)
    return 0


if __name__ == "__main__":
    sys.exit(main())
