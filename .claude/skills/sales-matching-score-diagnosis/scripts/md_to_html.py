#!/usr/bin/env python3
"""マッチング診断レポート (Markdown) を HTML に変換する。

使い方:
    python3 md_to_html.py <input.md>

同じディレクトリに同名 .html を書き出して、書き出したパスを標準出力に1行で出す。
"""
import sys
from pathlib import Path

import markdown


CSS = """
* { box-sizing: border-box; }
body {
  font-family: -apple-system, BlinkMacSystemFont, "Hiragino Sans", "Noto Sans JP", sans-serif;
  line-height: 1.7;
  color: #1f2937;
  max-width: 920px;
  margin: 40px auto;
  padding: 0 24px;
  background: #fafafa;
}
h1 { font-size: 1.7rem; border-bottom: 3px solid #2563eb; padding-bottom: 6px; margin-top: 2.2rem; }
h2 { font-size: 1.35rem; border-left: 5px solid #2563eb; padding-left: 10px; margin-top: 2rem; color: #111827; }
h3 { font-size: 1.15rem; background: #eef2ff; padding: 8px 12px; border-radius: 6px; margin-top: 1.8rem; }
hr { border: none; border-top: 1px dashed #cbd5e1; margin: 2rem 0; }
table { border-collapse: collapse; width: 100%; margin: 1rem 0; background: #fff; }
th, td { border: 1px solid #e5e7eb; padding: 8px 12px; text-align: left; }
th { background: #f1f5f9; }
strong { color: #0f172a; }
code { background: #f1f5f9; padding: 2px 6px; border-radius: 4px; font-size: 0.92em; }
blockquote { border-left: 4px solid #94a3b8; margin: 0; padding: 4px 12px; color: #475569; background: #f8fafc; }
ul, ol { padding-left: 1.4rem; }
li { margin: 0.2rem 0; }
"""


def convert(md_path: Path) -> Path:
    html_path = md_path.with_suffix(".html")
    md_text = md_path.read_text(encoding="utf-8")
    body = markdown.markdown(md_text, extensions=["tables", "fenced_code", "toc"])
    title = md_path.stem
    html = (
        "<!DOCTYPE html>\n"
        "<html lang=\"ja\">\n<head>\n"
        "<meta charset=\"UTF-8\">\n"
        f"<title>{title}</title>\n"
        f"<style>{CSS}</style>\n"
        "</head>\n<body>\n"
        f"{body}\n"
        "</body>\n</html>\n"
    )
    html_path.write_text(html, encoding="utf-8")
    return html_path


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: md_to_html.py <input.md>", file=sys.stderr)
        return 2
    md_path = Path(sys.argv[1])
    if not md_path.exists():
        print(f"Not found: {md_path}", file=sys.stderr)
        return 1
    out = convert(md_path)
    print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
