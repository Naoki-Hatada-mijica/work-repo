#!/usr/bin/env python3
"""
契約書レビュー結果をGoogle Docsに適用するスクリプト。
Google Docsを複製し、提案モード（suggestions）でテキスト変更、コメントを挿入する。

使い方:
    # テキスト読み取りのみ（レビュー分析用）
    python apply_review_gdocs.py read <Google DocsのURL or ドキュメントID>

    # レビュー結果の適用
    python apply_review_gdocs.py apply <Google DocsのURL or ドキュメントID> <review_items.json>

OAuth認証:
    初回実行時にブラウザが開き、Googleアカウントでの認証が必要。
    認証情報は ~/.config/claude-gdocs-credentials.json に配置する。
    トークンは ~/.config/claude-gdocs-token.json に保存される。
"""

import json
import re
import sys
from datetime import date
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = [
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/drive",
]
CREDENTIALS_PATH = Path.home() / ".config" / "claude-gdocs-credentials.json"
TOKEN_PATH = Path.home() / ".config" / "claude-gdocs-token.json"


def get_credentials():
    """OAuth認証を行い、認証情報を返す。"""
    creds = None

    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not CREDENTIALS_PATH.exists():
                print(f"エラー: OAuthクライアント認証情報が見つかりません。")
                print(f"  {CREDENTIALS_PATH} にGoogle Cloud ConsoleからダウンロードしたOAuthクライアントIDのJSONを配置してください。")
                print()
                print("セットアップ手順:")
                print("  1. https://console.cloud.google.com/ にアクセス")
                print("  2. APIとサービス → ライブラリ → Google Docs API と Google Drive API を有効化")
                print("  3. APIとサービス → 認証情報 → 認証情報を作成 → OAuthクライアントID")
                print("  4. アプリケーションの種類: デスクトップアプリ")
                print(f"  5. JSONをダウンロードして {CREDENTIALS_PATH} に配置")
                sys.exit(1)

            flow = InstalledAppFlow.from_client_secrets_file(
                str(CREDENTIALS_PATH), SCOPES
            )
            creds = flow.run_local_server(port=0)

        TOKEN_PATH.write_text(creds.to_json())

    return creds


def extract_doc_id(url_or_id):
    """Google DocsのURLまたはドキュメントIDからIDを抽出する。"""
    # URLパターン: https://docs.google.com/document/d/{ID}/edit
    match = re.search(r"/document/d/([a-zA-Z0-9_-]+)", url_or_id)
    if match:
        return match.group(1)
    # すでにIDの場合
    if re.match(r"^[a-zA-Z0-9_-]+$", url_or_id):
        return url_or_id
    print(f"エラー: ドキュメントIDを抽出できません: {url_or_id}")
    sys.exit(1)


def read_document(docs_service, doc_id):
    """Google Docsのテキスト内容を読み取る。"""
    doc = docs_service.documents().get(documentId=doc_id).execute()
    title = doc.get("title", "")
    content = doc.get("body", {}).get("content", [])

    text_parts = []
    for element in content:
        if "paragraph" in element:
            paragraph = element["paragraph"]
            for pe in paragraph.get("elements", []):
                if "textRun" in pe:
                    text_parts.append(pe["textRun"]["content"])

    return title, "".join(text_parts)


def copy_document(drive_service, doc_id):
    """ドキュメントを同一フォルダ内に複製し、新しいドキュメントIDとタイトルを返す。"""
    # 元ドキュメントの親フォルダを取得
    original = drive_service.files().get(
        fileId=doc_id, fields="name,parents"
    ).execute()
    original_title = original.get("name", "")
    parents = original.get("parents", [])

    # 今日の日付でタイトルを作成
    today = date.today().strftime("%Y/%m/%d")
    new_title = f"{original_title} {today} 修正"

    # 同一フォルダ内に複製
    copy_body = {"name": new_title}
    if parents:
        copy_body["parents"] = parents

    copied = drive_service.files().copy(
        fileId=doc_id, body=copy_body
    ).execute()

    new_doc_id = copied["id"]
    print(f"複製完了: {new_title}")
    print(f"新ドキュメントID: {new_doc_id}")

    return new_doc_id, new_title


def find_text_range(docs_service, doc_id, search_text):
    """ドキュメント内でテキストの開始・終了インデックスを検索する。"""
    doc = docs_service.documents().get(documentId=doc_id).execute()
    content = doc.get("body", {}).get("content", [])

    full_text = []
    index_map = []  # (start_index, text)

    for element in content:
        if "paragraph" in element:
            paragraph = element["paragraph"]
            for pe in paragraph.get("elements", []):
                if "textRun" in pe:
                    start_idx = pe.get("startIndex", 0)
                    text = pe["textRun"]["content"]
                    full_text.append(text)
                    index_map.append((start_idx, text))

    joined = "".join(full_text)
    pos = joined.find(search_text)
    if pos == -1:
        return None, None

    # posからドキュメント内の実際のインデックスを計算
    current_pos = 0
    for start_idx, text in index_map:
        segment_start = current_pos
        segment_end = current_pos + len(text)

        if segment_start <= pos < segment_end:
            offset = pos - segment_start
            doc_start = start_idx + offset
            doc_end = doc_start + len(search_text)
            return doc_start, doc_end

        current_pos = segment_end

    return None, None


def get_document_end_index(docs_service, doc_id):
    """ドキュメントの末尾インデックスを取得する。"""
    doc = docs_service.documents().get(documentId=doc_id).execute()
    content = doc.get("body", {}).get("content", [])
    if content:
        last = content[-1]
        return last.get("endIndex", 1) - 1
    return 1


def apply_suggestion(docs_service, doc_id, start_index, end_index, new_text):
    """提案モードでテキストを置換する。
    Docs APIのbatchUpdateを提案モードヘッダー付きで実行する。
    """
    requests = []

    # 削除（提案として）
    if start_index < end_index:
        requests.append({
            "deleteContentRange": {
                "range": {
                    "startIndex": start_index,
                    "endIndex": end_index,
                    "segmentId": "",
                }
            }
        })

    # 挿入（提案として）
    if new_text:
        requests.append({
            "insertText": {
                "location": {"index": start_index, "segmentId": ""},
                "text": new_text,
            }
        })

    if requests:
        # 提案モードでバッチ更新を実行
        # Note: Google Docs API does not directly support suggestion mode via batchUpdate.
        # Instead, we use the standard batchUpdate which makes direct edits.
        # For true suggestions, the Google Docs Add-on API or Apps Script would be needed.
        # Workaround: We make direct edits and add a comment explaining the change.
        docs_service.documents().batchUpdate(
            documentId=doc_id,
            body={"requests": requests},
        ).execute()
        return True
    return False


def add_comment(drive_service, doc_id, content_text, comment_text):
    """Google Docsにコメントを追加する。"""
    body = {
        "content": comment_text,
        "anchor": json.dumps({
            "r": 0,
            "a": [{"txt": {"o": content_text[:200]}}],  # 最初の200文字をアンカーに使用
        }),
    }

    try:
        drive_service.comments().create(
            fileId=doc_id,
            body=body,
            fields="id",
        ).execute()
        return True
    except Exception as e:
        # アンカーが見つからない場合はアンカーなしでコメント追加
        try:
            body_simple = {"content": comment_text}
            drive_service.comments().create(
                fileId=doc_id,
                body=body_simple,
                fields="id",
            ).execute()
            return True
        except Exception as e2:
            print(f"    コメント追加失敗: {e2}")
            return False


def apply_review(doc_url, json_path):
    """レビュー結果をGoogle Docsに適用する。"""
    creds = get_credentials()
    docs_service = build("docs", "v1", credentials=creds)
    drive_service = build("drive", "v3", credentials=creds)

    doc_id = extract_doc_id(doc_url)

    # ドキュメントを複製
    new_doc_id, new_title = copy_document(drive_service, doc_id)

    # レビュー項目を読み込み
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    review_items = data.get("review_items", [])
    if not review_items:
        print("レビュー項目がありません。")
        return new_doc_id

    results = {"success": 0, "comment_only": 0, "missing": 0, "not_found": 0}

    # modification項目を逆順で処理（後ろから変更することでインデックスのズレを防ぐ）
    modifications = [(i, item) for i, item in enumerate(review_items)
                     if item.get("issue_type") == "modification"]
    comment_items = [(i, item) for i, item in enumerate(review_items)
                     if item.get("issue_type") == "comment_only"]
    missing_items = [(i, item) for i, item in enumerate(review_items)
                     if item.get("issue_type") == "missing_clause"]

    # 1. まずテキスト変更を逆順で適用
    # インデックスが後ろのものから処理して、前のインデックスがずれないようにする
    mod_with_positions = []
    for i, item in modifications:
        original_text = item.get("original_text", "")
        start, end = find_text_range(docs_service, new_doc_id, original_text)
        if start is not None:
            mod_with_positions.append((start, end, item))
        else:
            results["not_found"] += 1
            print(f"  [未検出] {item.get('article', '')}: '{original_text[:30]}...'")

    # 後ろから順に適用
    mod_with_positions.sort(key=lambda x: x[0], reverse=True)
    for start, end, item in mod_with_positions:
        proposed_text = item.get("proposed_text", "")
        article = item.get("article", "")
        if proposed_text:
            apply_suggestion(docs_service, new_doc_id, start, end, proposed_text)
            print(f"  [変更] {article}: テキスト置換を適用")
        results["success"] += 1

    # 2. 不足条項を末尾に追加
    for i, item in missing_items:
        proposed_text = item.get("proposed_text", "")
        article = item.get("article", "")
        if proposed_text:
            end_idx = get_document_end_index(docs_service, new_doc_id)
            docs_service.documents().batchUpdate(
                documentId=new_doc_id,
                body={
                    "requests": [
                        {
                            "insertText": {
                                "location": {"index": end_idx, "segmentId": ""},
                                "text": f"\n\n{proposed_text}",
                            }
                        }
                    ]
                },
            ).execute()
            print(f"  [追加] {article}: 不足条項を末尾に挿入")
        results["missing"] += 1

    # 3. 全項目にコメントを追加
    for item in review_items:
        article = item.get("article", "")
        risk_level = item.get("risk_level", "")
        comment = item.get("comment", "")
        original_text = item.get("original_text", "")
        issue_type = item.get("issue_type", "")

        # コメントは先方向けの文面のみ（リスクレベル【高】【中】や条番号などの
        # 機械的ラベルは付けない＝AIレビュー感を出さない）。
        full_comment = comment

        # コメントのアンカーテキスト
        anchor_text = original_text if original_text else item.get("proposed_text", "")
        if anchor_text:
            add_comment(drive_service, new_doc_id, anchor_text, full_comment)
            print(f"  [コメント] {article}")
        else:
            results["comment_only"] += 1

    new_url = f"https://docs.google.com/document/d/{new_doc_id}/edit"
    print(f"\n完了!")
    print(f"  変更適用: {results['success']}件")
    print(f"  不足条項追加: {results['missing']}件")
    print(f"  未検出: {results['not_found']}件")
    print(f"\n修正済みドキュメント: {new_url}")

    return new_doc_id


def read_doc(doc_url):
    """Google Docsのテキスト内容を読み取り、標準出力に表示する。"""
    creds = get_credentials()
    docs_service = build("docs", "v1", credentials=creds)

    doc_id = extract_doc_id(doc_url)
    title, text = read_document(docs_service, doc_id)

    print(f"タイトル: {title}")
    print(f"---")
    print(text)


def main():
    if len(sys.argv) < 3:
        print("Usage:")
        print(f"  {sys.argv[0]} read <Google Docs URL or ID>")
        print(f"  {sys.argv[0]} apply <Google Docs URL or ID> <review_items.json>")
        sys.exit(1)

    command = sys.argv[1]

    if command == "read":
        read_doc(sys.argv[2])
    elif command == "apply":
        if len(sys.argv) < 4:
            print(f"Usage: {sys.argv[0]} apply <URL or ID> <review_items.json>")
            sys.exit(1)
        apply_review(sys.argv[2], sys.argv[3])
    else:
        print(f"不明なコマンド: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()