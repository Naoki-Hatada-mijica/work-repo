"""Google Workspace API ユーティリティ.

Google Docs / Sheets / Drive / Gmail にアクセスするための共通認証・取得関数。
OAuth2トークン（~/.config/claude-gdocs-token.json）を使用する。

使い方:
    from snippets.google_workspace import (
        get_doc_text,
        get_sheet_values,
        get_drive_service,
        get_gmail_service,
        search_gmail_threads,
        get_gmail_thread,
        download_gmail_attachments,
    )

トークン再発行（スコープ追加時）:
    python3 ~/.claude/snippets/reauth_google.py
"""

from __future__ import annotations

import base64
import json
import os
from pathlib import Path

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

TOKEN_PATH = Path.home() / ".config" / "claude-gdocs-token.json"

SCOPES = [
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/gmail.readonly",
]


def _get_credentials() -> Credentials:
    """OAuth2トークンファイルから認証情報を取得する."""
    with open(TOKEN_PATH) as f:
        token_data = json.load(f)
    return Credentials(
        token=token_data["token"],
        refresh_token=token_data["refresh_token"],
        token_uri=token_data["token_uri"],
        client_id=token_data["client_id"],
        client_secret=token_data["client_secret"],
        scopes=token_data["scopes"],
    )


def extract_doc_id(url: str) -> str:
    """Google Docs/Sheets/Drive URLからドキュメントIDを抽出する."""
    # https://docs.google.com/document/d/{ID}/edit
    # https://docs.google.com/spreadsheets/d/{ID}/edit
    parts = url.rstrip("/").split("/")
    for i, part in enumerate(parts):
        if part == "d" and i + 1 < len(parts):
            return parts[i + 1].split("?")[0].split("#")[0]
    return url  # IDそのものが渡された場合


def get_doc_text(doc_id_or_url: str) -> str:
    """Google Docsの全テキストを取得する."""
    doc_id = extract_doc_id(doc_id_or_url)
    service = build("docs", "v1", credentials=_get_credentials())
    doc = service.documents().get(documentId=doc_id).execute()

    text = ""
    for elem in doc.get("body", {}).get("content", []):
        if "paragraph" in elem:
            for run in elem["paragraph"].get("elements", []):
                if "textRun" in run:
                    text += run["textRun"]["content"]
    return text


def get_sheet_values(sheet_id_or_url: str, range_notation: str = "A:Z") -> list:
    """Google Sheetsの値を二次元リストで取得する."""
    sheet_id = extract_doc_id(sheet_id_or_url)
    service = build("sheets", "v4", credentials=_get_credentials())
    result = (
        service.spreadsheets()
        .values()
        .get(spreadsheetId=sheet_id, range=range_notation)
        .execute()
    )
    return result.get("values", [])


def get_drive_service():
    """Google Drive APIサービスオブジェクトを返す."""
    return build("drive", "v3", credentials=_get_credentials())


def get_gmail_service():
    """Gmail APIサービスオブジェクトを返す."""
    return build("gmail", "v1", credentials=_get_credentials())


def search_gmail_threads(query: str, max_results: int = 20) -> list:
    """Gmailスレッドを検索する。Gmail検索構文（from:, has:attachment等）が使える."""
    service = get_gmail_service()
    result = (
        service.users()
        .threads()
        .list(userId="me", q=query, maxResults=max_results)
        .execute()
    )
    return result.get("threads", [])


def get_gmail_thread(thread_id: str) -> dict:
    """Gmailスレッドを取得する（messages配下に全メッセージのfull payload）."""
    service = get_gmail_service()
    return (
        service.users()
        .threads()
        .get(userId="me", id=thread_id, format="full")
        .execute()
    )


def _iter_parts(payload: dict):
    """payloadを再帰的にたどり、全partをyieldする."""
    yield payload
    for part in payload.get("parts", []) or []:
        yield from _iter_parts(part)


def download_gmail_attachments(thread_id: str, out_dir: str | Path) -> list[Path]:
    """スレッド内の全メッセージから添付ファイルをout_dirにダウンロードする.

    Returns: 保存したファイルパスのリスト。
    """
    service = get_gmail_service()
    thread = (
        service.users()
        .threads()
        .get(userId="me", id=thread_id, format="full")
        .execute()
    )
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    saved: list[Path] = []
    for msg in thread.get("messages", []):
        msg_id = msg["id"]
        for part in _iter_parts(msg.get("payload", {})):
            filename = part.get("filename")
            body = part.get("body", {})
            att_id = body.get("attachmentId")
            if not filename or not att_id:
                continue
            att = (
                service.users()
                .messages()
                .attachments()
                .get(userId="me", messageId=msg_id, id=att_id)
                .execute()
            )
            data = base64.urlsafe_b64decode(att["data"])
            path = out_dir / filename
            # 同名ファイルがあれば連番を付与
            i = 1
            while path.exists():
                path = out_dir / f"{path.stem}__{i}{path.suffix}"
                i += 1
            path.write_bytes(data)
            saved.append(path)
    return saved
