#!/usr/bin/env python3
"""
Skill sheet PDF generator with modern UI design.

Usage:
  Set FONT_DIR, OUTPUT_PATH, DOC_DATE, and fill in personal_info, self_pr,
  tech_summary, projects before running.
  Requires: pip install reportlab
  Fonts: NotoSansJP-Regular.ttf and NotoSansJP-Bold.ttf in FONT_DIR
"""

import sys
import re
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# === CONFIGURATION (set these before running) ===
FONT_DIR = "/tmp"  # Directory containing NotoSansJP-Regular.ttf and NotoSansJP-Bold.ttf
OUTPUT_PATH = "/tmp/output.pdf"
DOC_DATE = "2026年7月"

# === DATA (replace with extracted content) ===
personal_info = {
    "技術者コード": "",
    "所属": "",
    "稼動": "",
    "性別": "",
    "最寄駅": "",
    "年齢": "",
    "資格": "",
    "学歴": "",
}

self_pr = ""

tech_summary = []
# Example:
# {"no": 1, "focus": "言語・OS基盤", "detail": "..."}

projects = []
# Example:
# {
#     "period": "2023年05月 〜 2026年05月（3年1ヶ月）",
#     "company": "プロジェクト名",
#     "content": "業務内容テキスト",
#     "phases": ["詳細設計", "実装", "テスト"],
#     "techs": ["Kotlin", "Android"],
#     "members": "複数名",
#     "role": "開発メンバー",
#     "tasks": ["タスク1", "タスク2"],
#     "extra_sections": [
#         {"heading": "習得スキル・知識", "items": ["スキル1", "スキル2"]},
#         {"heading": "取り組み・実績", "items": ["実績1", "実績2"]},
#     ],
# }

# === END CONFIGURATION ===


def sort_key(proj):
    m = re.search(r'(\d{4})年(\d{2})月', proj['period'])
    if m:
        return int(m.group(1)) * 100 + int(m.group(2))
    return 0


projects.sort(key=sort_key, reverse=True)

pdfmetrics.registerFont(TTFont('NotoSansJP', f'{FONT_DIR}/NotoSansJP-Regular.ttf'))
pdfmetrics.registerFont(TTFont('NotoSansJPBold', f'{FONT_DIR}/NotoSansJP-Bold.ttf'))
F = 'NotoSansJP'
FB = 'NotoSansJPBold'

NAVY = HexColor('#1e3a5f')
NAVY_LIGHT = HexColor('#2563eb')
GRAY_900 = HexColor('#111827')
GRAY_700 = HexColor('#374151')
GRAY_500 = HexColor('#6b7280')
GRAY_300 = HexColor('#d1d5db')
GRAY_200 = HexColor('#e5e7eb')
GRAY_50 = HexColor('#f9fafb')
WHITE = HexColor('#ffffff')
TAG_BG = HexColor('#e5e7eb')
TAG_FG = HexColor('#1f2937')

W, H = A4
ML = 18 * mm
MR = 18 * mm
CW = W - ML - MR
LH = 4.6 * mm
BOTTOM_MARGIN = 20 * mm
MIN_CONTENT_AFTER_HEADING = 30 * mm


def wrap_text(c, text, font, fs, max_w):
    lines = []
    for paragraph in text.split('\n'):
        line = ''
        for ch in paragraph:
            test = line + ch
            if c.stringWidth(test, font, fs) > max_w:
                lines.append(line)
                line = ch
            else:
                line = test
        if line:
            lines.append(line)
    return lines


def pill(c, x, y_center, text, fs=7, bg=TAG_BG, fg=TAG_FG):
    c.setFont(F, fs)
    tw = c.stringWidth(text, F, fs)
    px = 3 * mm
    py = 1.8 * mm
    pw = tw + px * 2
    ph = fs * 0.352 * mm + py * 2
    box_y = y_center - ph / 2
    c.saveState()
    c.setFillColor(bg)
    p = c.beginPath()
    p.roundRect(x, box_y, pw, ph, ph / 2)
    c.drawPath(p, fill=1, stroke=0)
    c.setFillColor(fg)
    text_y = y_center - fs * 0.352 * mm / 2
    c.drawString(x + px, text_y, text)
    c.restoreState()
    return pw + 2 * mm


def pills_wrap(c, x, y_center, tags, max_w, fs=7):
    cx = x
    cy = y_center
    row_h = fs * 0.352 * mm + 3.6 * mm + 2.5 * mm
    for tag in tags:
        c.setFont(F, fs)
        tw = c.stringWidth(tag, F, fs) + 6 * mm + 2 * mm
        if cx + tw > x + max_w and cx > x:
            cy -= row_h
            cx = x
        pill(c, cx, cy, tag, fs)
        cx += tw
    return cy - row_h / 2 - 2 * mm


def draw_footer(c, n, total):
    c.saveState()
    c.setStrokeColor(GRAY_300)
    c.setLineWidth(0.3)
    c.line(ML, 13 * mm, W - MR, 13 * mm)
    c.setFillColor(GRAY_500)
    c.setFont(F, 7)
    c.drawCentredString(W / 2, 8 * mm, f"{n} / {total}")
    c.restoreState()


def new_page(c, page_ref, total):
    c.showPage()
    page_ref[0] += 1
    draw_footer(c, page_ref[0], total)
    return H - 15 * mm


def check_page(c, y, needed, page_ref, total):
    if y - needed < BOTTOM_MARGIN:
        return new_page(c, page_ref, total)
    return y


def draw_header(c, y):
    hh = 22 * mm
    c.saveState()
    c.setFillColor(NAVY)
    c.rect(0, y - hh, W, hh, fill=1, stroke=0)
    c.setFillColor(WHITE)
    c.setFont(FB, 16)
    c.drawString(ML + 2 * mm, y - hh / 2 + 1.5 * mm, "スキルシート")
    c.setFont(F, 9)
    c.drawRightString(W - MR - 2 * mm, y - hh / 2 + 1.5 * mm, f"{DOC_DATE} 現在")
    c.restoreState()
    return y - hh


def draw_section_heading(c, y, title, page_ref, total):
    y = check_page(c, y, MIN_CONTENT_AFTER_HEADING, page_ref, total)
    bar_h = 7.5 * mm
    c.saveState()
    c.setFillColor(NAVY)
    c.rect(ML, y - bar_h, 3, bar_h, fill=1, stroke=0)
    c.setFillColor(GRAY_900)
    c.setFont(FB, 11)
    c.drawString(ML + 7 * mm, y - bar_h / 2 - 1.5 * mm, title)
    c.restoreState()
    return y - bar_h - 4 * mm


def draw_personal_info(c, y, page_ref, total):
    y -= 6 * mm
    y = draw_section_heading(c, y, "基本情報", page_ref, total)
    y -= 2 * mm

    left_items = [
        ("技術者コード", personal_info["技術者コード"]),
        ("稼動", personal_info["稼動"]),
        ("最寄駅", personal_info["最寄駅"]),
        ("資格", personal_info["資格"]),
    ]
    right_items = [
        ("所属", personal_info["所属"]),
        ("性別", personal_info["性別"]),
        ("年齢", personal_info["年齢"]),
        ("学歴", personal_info["学歴"]),
    ]

    row_h = 7.5 * mm
    pad_x = 5 * mm
    pad_y = 3 * mm
    box_h = len(left_items) * row_h + pad_y * 2
    label_w = 26 * mm
    mid_x = ML + CW / 2
    right_label_w = 16 * mm

    c.saveState()
    c.setFillColor(GRAY_50)
    c.setStrokeColor(GRAY_200)
    c.setLineWidth(0.5)
    p = c.beginPath()
    p.roundRect(ML, y - box_h, CW, box_h, 2 * mm)
    c.drawPath(p, fill=1, stroke=1)
    c.restoreState()

    ty = y - pad_y - row_h / 2
    for i in range(len(left_items)):
        lbl_l, val_l = left_items[i]
        lbl_r, val_r = right_items[i]
        text_y = ty - 1.2 * mm

        c.saveState()
        c.setFillColor(GRAY_500)
        c.setFont(FB, 8)
        c.drawString(ML + pad_x, text_y, lbl_l)
        c.setFillColor(GRAY_900)
        c.setFont(F, 9)
        c.drawString(ML + pad_x + label_w, text_y, val_l)

        c.setFillColor(GRAY_500)
        c.setFont(FB, 8)
        c.drawString(mid_x + pad_x, text_y, lbl_r)
        c.setFillColor(GRAY_900)
        c.setFont(F, 9)
        c.drawString(mid_x + pad_x + right_label_w, text_y, val_r)

        if i < len(left_items) - 1:
            div_y = ty - row_h / 2
            c.setStrokeColor(GRAY_200)
            c.setLineWidth(0.3)
            c.line(ML + pad_x, div_y, ML + CW - pad_x, div_y)
        c.restoreState()
        ty -= row_h

    c.saveState()
    c.setStrokeColor(GRAY_200)
    c.setLineWidth(0.3)
    c.line(mid_x, y - pad_y, mid_x, y - box_h + pad_y)
    c.restoreState()

    return y - box_h - 6 * mm


def draw_self_pr(c, y, page_ref, total):
    y = draw_section_heading(c, y, "自己PR・得意技術", page_ref, total)
    y -= 2 * mm

    pad_x = 5 * mm
    pad_y = 4 * mm
    text_w = CW - pad_x * 2
    fs = 8.5
    line_h = 4.5 * mm

    lines = wrap_text(c, self_pr, F, fs, text_w)
    box_h = len(lines) * line_h + pad_y * 2

    y = check_page(c, y, box_h, page_ref, total)

    c.saveState()
    c.setFillColor(GRAY_50)
    c.setStrokeColor(GRAY_200)
    c.setLineWidth(0.5)
    p = c.beginPath()
    p.roundRect(ML, y - box_h, CW, box_h, 2 * mm)
    c.drawPath(p, fill=1, stroke=1)
    c.restoreState()

    ty = y - pad_y - fs * 0.352 * mm
    c.saveState()
    c.setFillColor(GRAY_900)
    c.setFont(F, fs)
    for line in lines:
        c.drawString(ML + pad_x, ty, line)
        ty -= line_h
    c.restoreState()

    return y - box_h - 6 * mm


def draw_tech_summary(c, y, page_ref, total):
    y = draw_section_heading(c, y, "技術サマリー", page_ref, total)
    y -= 2 * mm

    no_w = 12 * mm
    focus_w = 36 * mm
    detail_x_offset = no_w + focus_w
    detail_w = CW - detail_x_offset - 4 * mm
    pad_x = 4 * mm
    pad_y = 3 * mm
    fs = 7.5
    line_h = 3.6 * mm
    header_h = 8 * mm

    y = check_page(c, y, header_h + 20 * mm, page_ref, total)

    c.saveState()
    c.setFillColor(NAVY)
    p = c.beginPath()
    p.roundRect(ML, y - header_h, CW, header_h, 1.5 * mm)
    c.drawPath(p, fill=1, stroke=0)
    c.rect(ML, y - header_h, CW, 2 * mm, fill=1, stroke=0)
    c.setFillColor(WHITE)
    c.setFont(FB, 8)
    text_y = y - header_h / 2 - 1 * mm
    c.drawString(ML + pad_x, text_y, "No")
    c.drawString(ML + no_w + pad_x, text_y, "フォーカス領域")
    c.drawString(ML + detail_x_offset + pad_x, text_y, "該当スキル・実務経験および強み")
    c.restoreState()
    y -= header_h

    for idx, item in enumerate(tech_summary):
        lines = wrap_text(c, item['detail'], F, fs, detail_w)
        row_h = max(len(lines) * line_h + pad_y * 2, 12 * mm)

        y = check_page(c, y, row_h, page_ref, total)

        bg = GRAY_50 if idx % 2 == 1 else WHITE
        c.saveState()
        c.setFillColor(bg)
        c.rect(ML, y - row_h, CW, row_h, fill=1, stroke=0)
        c.setStrokeColor(GRAY_200)
        c.setLineWidth(0.3)
        c.line(ML, y - row_h, ML + CW, y - row_h)
        c.line(ML + no_w, y, ML + no_w, y - row_h)
        c.line(ML + detail_x_offset, y, ML + detail_x_offset, y - row_h)
        c.restoreState()

        c.saveState()
        c.setFillColor(NAVY)
        c.setFont(FB, 9)
        c.drawCentredString(ML + no_w / 2, y - pad_y - 2.5 * mm, str(item['no']))
        c.restoreState()

        c.saveState()
        c.setFillColor(GRAY_900)
        c.setFont(FB, 8)
        c.drawString(ML + no_w + pad_x, y - pad_y - 2.5 * mm, item['focus'])
        c.restoreState()

        c.saveState()
        c.setFillColor(GRAY_700)
        c.setFont(F, fs)
        ty = y - pad_y - fs * 0.352 * mm
        for line in lines:
            c.drawString(ML + detail_x_offset + pad_x, ty, line)
            ty -= line_h
        c.restoreState()

        y -= row_h

    return y - 6 * mm


def draw_career_title(c, y, page_ref, total):
    y = check_page(c, y, 70 * mm, page_ref, total)
    bar_h = 9 * mm
    c.saveState()
    c.setFillColor(NAVY)
    p = c.beginPath()
    p.roundRect(ML, y - bar_h, CW, bar_h, 2 * mm)
    c.drawPath(p, fill=1, stroke=0)
    c.setFillColor(WHITE)
    c.setFont(FB, 12)
    c.drawString(ML + 6 * mm, y - bar_h / 2 - 1.8 * mm, "職務経歴(Android)")
    c.restoreState()
    return y - bar_h - 6 * mm


def draw_divider(c, y):
    c.saveState()
    c.setStrokeColor(GRAY_300)
    c.setLineWidth(0.4)
    c.line(ML, y, W - MR, y)
    c.restoreState()
    return y - 5 * mm


def draw_wrapped_text_block(c, x, y, text, font, fs, max_w, line_h, page_ref, total):
    lines = wrap_text(c, text, font, fs, max_w)
    for line in lines:
        if y < BOTTOM_MARGIN:
            y = new_page(c, page_ref, total)
        c.saveState()
        c.setFillColor(GRAY_900)
        c.setFont(font, fs)
        c.drawString(x, y, line)
        c.restoreState()
        y -= line_h
    return y


def draw_project(c, y, proj, page_ref, total, is_last=False):
    cx = ML + 3 * mm
    content_w = CW - 6 * mm
    indent_x = cx + 6 * mm

    y = check_page(c, y, 50 * mm, page_ref, total)

    c.saveState()
    c.setFillColor(NAVY)
    c.rect(ML, y - 7.5 * mm, 3, 7.5 * mm, fill=1, stroke=0)
    c.setFillColor(NAVY_LIGHT)
    c.setFont(F, 8.5)
    period_text = proj['period']
    c.drawString(ML + 7 * mm, y - 5 * mm, period_text)
    pw = c.stringWidth(period_text, F, 8.5)
    c.setFillColor(GRAY_900)
    c.setFont(FB, 10)
    c.drawString(ML + 7 * mm + pw + 5 * mm, y - 5.2 * mm, proj['company'])
    c.restoreState()
    y -= 11 * mm

    # 業務内容
    c.saveState()
    c.setFillColor(GRAY_500)
    c.setFont(FB, 8)
    c.drawString(cx, y, "業務内容")
    c.restoreState()
    y -= LH
    y = draw_wrapped_text_block(c, indent_x, y, proj['content'], F, 8.5, content_w - 6 * mm, LH, page_ref, total)
    y -= 1.5 * mm

    # 担当フェーズ
    y = check_page(c, y, 12 * mm, page_ref, total)
    c.saveState()
    c.setFillColor(GRAY_500)
    c.setFont(FB, 8)
    c.drawString(cx, y, "担当フェーズ")
    c.restoreState()
    y -= 5 * mm
    y = pills_wrap(c, cx, y, proj['phases'], content_w, fs=7.5)
    y -= 1 * mm

    # 開発環境
    y = check_page(c, y, 12 * mm, page_ref, total)
    c.saveState()
    c.setFillColor(GRAY_500)
    c.setFont(FB, 8)
    c.drawString(cx, y, "開発環境")
    c.restoreState()
    y -= 5 * mm
    y = pills_wrap(c, cx, y, proj['techs'], content_w, fs=7)
    y -= 1 * mm

    # 体制
    c.saveState()
    c.setFillColor(GRAY_500)
    c.setFont(FB, 8)
    c.drawString(cx, y, "体制")
    c.setFillColor(GRAY_900)
    c.setFont(F, 8.5)
    c.drawString(cx + 22 * mm, y, f"{proj['members']}  /  役割: {proj['role']}")
    c.restoreState()
    y -= LH - 0.5 * mm
    y -= 1.5 * mm

    # 担当業務
    y = check_page(c, y, LH * 3, page_ref, total)
    c.saveState()
    c.setFillColor(GRAY_500)
    c.setFont(FB, 8)
    c.drawString(cx, y, "担当業務")
    c.restoreState()
    y -= LH

    for task in proj['tasks']:
        task_lines = wrap_text(c, task, F, 8.5, content_w - 10 * mm)
        for j, line_text in enumerate(task_lines):
            if y < BOTTOM_MARGIN:
                y = new_page(c, page_ref, total)
            c.saveState()
            if j == 0:
                c.setFillColor(GRAY_500)
                c.setFont(F, 8)
                c.drawString(indent_x, y, "-")
            c.setFillColor(GRAY_900)
            c.setFont(F, 8.5)
            c.drawString(indent_x + 4 * mm, y, line_text)
            c.restoreState()
            y -= LH

    # Extra sections (習得スキル・知識, 取り組み・実績, etc.)
    for section in proj.get('extra_sections', []):
        y -= 2 * mm
        y = check_page(c, y, LH * 3, page_ref, total)
        c.saveState()
        c.setFillColor(GRAY_500)
        c.setFont(FB, 8)
        c.drawString(cx, y, section['heading'])
        c.restoreState()
        y -= LH
        for item in section['items']:
            item_lines = wrap_text(c, item, F, 8.5, content_w - 10 * mm)
            for j, line_text in enumerate(item_lines):
                if y < BOTTOM_MARGIN:
                    y = new_page(c, page_ref, total)
                c.saveState()
                if j == 0:
                    c.setFillColor(GRAY_500)
                    c.setFont(F, 8)
                    c.drawString(indent_x, y, "-")
                c.setFillColor(GRAY_900)
                c.setFont(F, 8.5)
                c.drawString(indent_x + 4 * mm, y, line_text)
                c.restoreState()
                y -= LH

    y -= 3 * mm
    if not is_last:
        y = draw_divider(c, y)

    return y, page_ref


def generate():
    if not projects:
        print("Error: No projects data set.", file=sys.stderr)
        sys.exit(1)

    # First pass to count pages
    c = canvas.Canvas("/dev/null", pagesize=A4)
    c.setTitle("スキルシート")
    page_ref = [1]
    y = H - 22 * mm
    y = draw_personal_info(c, y, page_ref, 99)
    y = draw_self_pr(c, y, page_ref, 99)
    y = draw_tech_summary(c, y, page_ref, 99)
    y = draw_career_title(c, y, page_ref, 99)
    for i, proj in enumerate(projects):
        is_last = (i == len(projects) - 1)
        y, page_ref = draw_project(c, y, proj, page_ref, 99, is_last)
    total = page_ref[0]

    # Second pass with correct total
    c = canvas.Canvas(OUTPUT_PATH, pagesize=A4)
    c.setTitle("スキルシート")
    page_ref = [1]
    draw_footer(c, page_ref[0], total)
    y = H
    y = draw_header(c, y)
    y = draw_personal_info(c, y, page_ref, total)
    y = draw_self_pr(c, y, page_ref, total)
    y = draw_tech_summary(c, y, page_ref, total)
    y = draw_career_title(c, y, page_ref, total)
    for i, proj in enumerate(projects):
        is_last = (i == len(projects) - 1)
        y, page_ref = draw_project(c, y, proj, page_ref, total, is_last)
    c.save()
    print(f"Done: {OUTPUT_PATH} ({total} pages)")


if __name__ == '__main__':
    generate()
