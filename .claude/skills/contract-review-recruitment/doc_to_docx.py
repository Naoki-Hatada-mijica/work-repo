#!/usr/bin/env python3
"""
旧 .doc（application/msword）を高忠実度で .docx に変換するヘルパー。

textutil の .docx 変換は条文の番号書式（numPr）・インデント・フォント指定を大きく失い、
Google Docs で開くとレイアウトが崩れる。本スクリプトは忠実度の高い順に変換手段を試す:

  1. LibreOffice（soffice --headless --convert-to docx）— 入っていれば最良・最速
  2. Google Drive ネイティブ変換（.doc → Google ドキュメント → .docx エクスポート）
     LibreOffice 不在の Mac でも高忠実度。中間 Google Doc は使用後に削除する。
  3. textutil -convert docx — 最終手段（レイアウト劣化あり。警告を出す）

使い方:
    python3 doc_to_docx.py <input.doc> <output.docx>

備考:
- Google ルートは ~/.config/claude-gdocs-token.json（documents + drive スコープ）を使う。
  `~/.claude/snippets/google_workspace.py` の get_drive_service() を流用。
- 変換忠実度の検証は KNOWLEDGE.md「.doc→.docx 変換のレイアウト忠実度」を参照。
"""

import io
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def convert_with_libreoffice(src: Path, dst: Path) -> bool:
    """LibreOffice があれば .docx へ変換する。成功で True。"""
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if not soffice:
        mac = Path("/Applications/LibreOffice.app/Contents/MacOS/soffice")
        if mac.exists():
            soffice = str(mac)
    if not soffice:
        return False
    with tempfile.TemporaryDirectory() as td:
        subprocess.run(
            [soffice, "--headless", "--convert-to", "docx", "--outdir", td, str(src)],
            check=True,
            capture_output=True,
        )
        produced = Path(td) / (src.stem + ".docx")
        if not produced.exists():
            return False
        shutil.copy(produced, dst)
    print(f"[変換] LibreOffice で {dst.name} を生成")
    return True


def convert_with_google_drive(src: Path, dst: Path) -> bool:
    """Drive のネイティブ変換（.doc→Googleドキュメント→.docx）。成功で True。"""
    try:
        snippets = Path.home() / ".claude" / "snippets"
        sys.path.insert(0, str(snippets))
        from google_workspace import get_drive_service  # noqa: E402
        from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload  # noqa: E402
    except Exception as e:
        print(f"[skip] Google Drive ルート利用不可: {e}")
        return False

    svc = get_drive_service()
    gid = None
    try:
        # 1. .doc をアップロードしつつ Google ドキュメントへ変換
        media = MediaFileUpload(str(src), mimetype="application/msword", resumable=True)
        gdoc = svc.files().create(
            body={"name": "__tmp_doc_to_docx", "mimeType": "application/vnd.google-apps.document"},
            media_body=media,
            fields="id",
            supportsAllDrives=True,
        ).execute()
        gid = gdoc["id"]

        # 2. Google ドキュメント → .docx エクスポート
        req = svc.files().export_media(
            fileId=gid,
            mimeType="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
        buf = io.BytesIO()
        dl = MediaIoBaseDownload(buf, req)
        done = False
        while not done:
            _, done = dl.next_chunk()
        dst.write_bytes(buf.getvalue())
        print(f"[変換] Google Drive ネイティブ変換で {dst.name} を生成（{len(buf.getvalue())} bytes）")
        return True
    except Exception as e:
        print(f"[skip] Google Drive 変換失敗: {e}")
        return False
    finally:
        # 3. 中間 Google Doc を撤去
        if gid:
            try:
                svc.files().delete(fileId=gid, supportsAllDrives=True).execute()
            except Exception:
                pass


def convert_with_textutil(src: Path, dst: Path) -> bool:
    """macOS textutil。最終手段（レイアウト劣化あり）。成功で True。"""
    if not shutil.which("textutil"):
        return False
    subprocess.run(
        ["textutil", "-convert", "docx", "-output", str(dst), str(src)],
        check=True,
        capture_output=True,
    )
    print(f"[変換] textutil で {dst.name} を生成 "
          f"（警告: 番号書式・インデントが失われる可能性。Google Docs で要レイアウト確認）")
    return True


def doc_to_docx(src_path: str, dst_path: str) -> str:
    src, dst = Path(src_path), Path(dst_path)
    if not src.exists():
        print(f"エラー: 入力ファイルが見つかりません: {src}")
        sys.exit(1)
    dst.parent.mkdir(parents=True, exist_ok=True)

    for fn in (convert_with_libreoffice, convert_with_google_drive, convert_with_textutil):
        try:
            if fn(src, dst):
                return str(dst)
        except Exception as e:
            print(f"[skip] {fn.__name__} 失敗: {e}")

    print("エラー: 変換手段がすべて失敗しました（LibreOffice / Google Drive / textutil）。")
    sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <input.doc> <output.docx>")
        sys.exit(1)
    out = doc_to_docx(sys.argv[1], sys.argv[2])
    print(f"完了: {out}")
