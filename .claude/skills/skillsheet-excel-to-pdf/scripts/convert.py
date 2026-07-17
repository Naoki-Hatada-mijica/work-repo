#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Excelスキルシート → 読みやすいA4縦PDF に一発変換するラッパー。
  1. xlsx_to_html.py でExcelの見た目を保ったHTMLを生成
  2. ヘッドレスChromeでPDF化
  3. 出力フォルダとダウンロードフォルダの両方に保存
  4. PDFを開く

使い方: python3 convert.py <入力.xlsx> [出力フォルダ] [シート名]
  出力フォルダ省略時は入力と同じ場所。
"""
import sys, os, subprocess, shutil

HERE = os.path.dirname(os.path.abspath(__file__))
CHROME_CANDIDATES = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
]


def find_chrome():
    for c in CHROME_CANDIDATES:
        if os.path.exists(c):
            return c
    raise SystemExit("Google Chrome（またはChromium/Edge）が見つかりません。")


def main():
    if len(sys.argv) < 2:
        raise SystemExit("使い方: python3 convert.py <入力.xlsx> [出力フォルダ] [シート名]")
    src = sys.argv[1]
    out_dir = sys.argv[2] if len(sys.argv) > 2 else os.path.dirname(os.path.abspath(src))
    sheet = sys.argv[3] if len(sys.argv) > 3 else ""
    base = os.path.splitext(os.path.basename(src))[0]
    os.makedirs(out_dir, exist_ok=True)
    html = os.path.join(out_dir, base + ".html")
    pdf = os.path.join(out_dir, base + "_技術経歴書.pdf")

    # 1. Excel → HTML
    subprocess.run([sys.executable, os.path.join(HERE, "xlsx_to_html.py"), src, sheet, html],
                   check=True)
    # 2. HTML → PDF（ヘッドレスChrome）
    chrome = find_chrome()
    subprocess.run([chrome, "--headless", "--disable-gpu", "--no-pdf-header-footer",
                    f"--print-to-pdf={pdf}", html],
                   check=True, stderr=subprocess.DEVNULL)
    if not os.path.exists(pdf):
        raise SystemExit("PDFの生成に失敗しました。")

    # 3. ダウンロードフォルダにもコピー
    downloads = os.path.expanduser("~/Downloads")
    dl_copy = None
    if os.path.isdir(downloads):
        dl_copy = os.path.join(downloads, os.path.basename(pdf))
        shutil.copy(pdf, dl_copy)

    # 4. 開く
    subprocess.run(["open", pdf])

    print("PDF:", pdf)
    if dl_copy:
        print("ダウンロードにもコピー:", dl_copy)


if __name__ == "__main__":
    main()
