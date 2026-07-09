"""SEO記事チェック: Google Docs から記事テキストと構造を抽出する.

Google Docs URL（または ID）を受け取り、以下を JSON で標準出力へ吐く:
  - title:      文書タイトル（TITLE スタイル段落 → なければ最初の見出し → なければ文書名）
  - headings:   [{level, text, order}] 見出し一覧（HEADING_1..6 と TITLE）
  - paragraphs: [{order, style, is_heading, heading_level, text}] 全段落
  - full_text:  改行区切りの全文
  - list_items: 箇条書き段落の text（構成案がリストで書かれるケース対応）

設計意図:
  - チェックのサブエージェントに「構造つきの記事」を渡すための土台。
  - 見出しレベル・段落境界を保持することで、「20〜25字」「階層構造」「見出しだけで
    内容が分かる」等の構成チェックを機械/LLM 双方が判定できるようにする。
  - LLM に数えさせない方針のため、文字数系の材料（各段落 text）を正確に渡す。

認証:
  ~/.claude/snippets/google_workspace.py の OAuth トークンを流用する。
  scopes に documents / drive を含む。

使い方:
  python3 fetch_article.py <DOC_URL_OR_ID> [--out article.json]
  引数を省略すると標準入力の1行目を URL として読む。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# 共通 Google Workspace ユーティリティを import path に追加
SNIPPETS_DIR = Path.home() / ".claude" / "snippets"
sys.path.insert(0, str(SNIPPETS_DIR))

from google_workspace import extract_doc_id, _get_credentials  # noqa: E402
from googleapiclient.discovery import build  # noqa: E402

# namedStyleType → 見出しレベル（TITLE=0, HEADING_1=1 ...）
HEADING_LEVELS = {
    "TITLE": 0,
    "HEADING_1": 1,
    "HEADING_2": 2,
    "HEADING_3": 3,
    "HEADING_4": 4,
    "HEADING_5": 5,
    "HEADING_6": 6,
}


def _paragraph_text(paragraph: dict) -> str:
    """paragraph 要素配下の textRun を連結して1段落のテキストを返す."""
    buf = []
    for el in paragraph.get("elements", []):
        run = el.get("textRun")
        if run and "content" in run:
            buf.append(run["content"])
    # 末尾改行を落として1段落=1行に正規化
    return "".join(buf).replace("\n", "").replace("\x0b", " ").strip()


def parse_document(doc: dict) -> dict:
    """Docs API の document オブジェクトを構造化 dict に変換する."""
    paragraphs: list[dict] = []
    headings: list[dict] = []
    list_items: list[str] = []
    title_from_style: str | None = None

    order = 0
    for elem in doc.get("body", {}).get("content", []):
        para = elem.get("paragraph")
        if not para:
            continue  # table / sectionBreak 等はスキップ
        text = _paragraph_text(para)
        style = para.get("paragraphStyle", {}).get("namedStyleType", "NORMAL_TEXT")
        is_list = "bullet" in para
        # 空段落は構造ノイズになるので保持しない（ただし本文の改行検証は full_text で担保）
        if not text:
            continue

        heading_level = HEADING_LEVELS.get(style)
        is_heading = heading_level is not None and heading_level >= 1
        if style == "TITLE" and title_from_style is None:
            title_from_style = text

        record = {
            "order": order,
            "style": style,
            "is_heading": is_heading,
            "heading_level": heading_level if is_heading else None,
            "is_list_item": is_list,
            "char_count": len(text),
            "text": text,
        }
        paragraphs.append(record)
        if is_heading:
            headings.append({"level": heading_level, "text": text, "order": order})
        if is_list:
            list_items.append(text)
        order += 1

    # タイトル決定: TITLE スタイル → 最初の HEADING_1 → Docs のファイル名
    if title_from_style:
        title = title_from_style
    elif headings:
        title = headings[0]["text"]
    else:
        title = doc.get("title", "")

    full_text = "\n".join(p["text"] for p in paragraphs)

    return {
        "doc_id": doc.get("documentId", ""),
        "doc_name": doc.get("title", ""),
        "title": title,
        "headings": headings,
        "paragraphs": paragraphs,
        "list_items": list_items,
        "full_text": full_text,
        "stats": {
            "paragraph_count": len(paragraphs),
            "heading_count": len(headings),
            "total_chars": len(full_text),
        },
    }


def fetch(doc_id_or_url: str) -> dict:
    doc_id = extract_doc_id(doc_id_or_url)
    service = build("docs", "v1", credentials=_get_credentials())
    doc = service.documents().get(documentId=doc_id).execute()
    return parse_document(doc)


def main() -> None:
    ap = argparse.ArgumentParser(description="Google Docs から記事構造を抽出")
    ap.add_argument("doc", nargs="?", help="Docs URL または ID（省略時は stdin）")
    ap.add_argument("--out", help="出力先 JSON パス（省略時は stdout）")
    args = ap.parse_args()

    doc_ref = args.doc
    if not doc_ref:
        doc_ref = sys.stdin.readline().strip()
    if not doc_ref:
        ap.error("Docs URL/ID を引数か標準入力で渡してください")

    result = fetch(doc_ref)
    payload = json.dumps(result, ensure_ascii=False, indent=2)
    if args.out:
        Path(args.out).write_text(payload, encoding="utf-8")
        print(f"[fetch_article] wrote {args.out} "
              f"({result['stats']['paragraph_count']} paragraphs, "
              f"{result['stats']['heading_count']} headings)", file=sys.stderr)
    else:
        print(payload)


if __name__ == "__main__":
    main()
