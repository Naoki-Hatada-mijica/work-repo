#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Excelスキルシートの見た目（罫線・列幅・結合セル・配置・塗り・縦書き）を
保ったまま、読みやすいA4縦PDF用のHTMLに変換する汎用スクリプト。
中身は変えない。フォーマットが違うスキルシートでも動くよう自動判定する。

使い方: python3 xlsx_to_html.py <入力.xlsx> [シート名] [出力.html]
"""
import sys, html
import openpyxl
from openpyxl.utils import get_column_letter, range_boundaries
from openpyxl.utils.datetime import from_excel

SRC = sys.argv[1]
SHEET = sys.argv[2] if len(sys.argv) > 2 and sys.argv[2] else None
OUT = sys.argv[3] if len(sys.argv) > 3 else 'grid.html'

wb = openpyxl.load_workbook(SRC, data_only=True)
ws = wb[SHEET] if (SHEET and SHEET in wb.sheetnames) else wb.worksheets[0]

FONT = ('"Meiryo","メイリオ","游ゴシック","Yu Gothic",'
        '"Hiragino Kaku Gothic ProN","Hiragino Sans",sans-serif')
KEEP_TOGETHER = True   # 案件をページ途中で分割しない（ページに収まらない案件は次ページへ）
ROW_SCALE = 0.9        # 行の高さの余白を少し詰める（文字サイズは変えない）

# ===== 1. 印刷範囲を自動検出（印刷範囲指定→なければ内容＋罫線＋塗りの範囲）=====
def content_bounds():
    maxr = maxc = 1
    for row in ws.iter_rows():
        for c in row:
            has = c.value not in (None, '')
            if not has:
                b = c.border
                has = any(s and s.style for s in (b.top, b.bottom, b.left, b.right))
            if not has:
                fl = c.fill
                has = getattr(fl, 'patternType', None) == 'solid'
            if has:
                if c.row > maxr: maxr = c.row
                if c.column > maxc: maxc = c.column
    for rng in ws.merged_cells.ranges:
        maxr = max(maxr, rng.max_row); maxc = max(maxc, rng.max_col)
    return maxr, maxc

pa = ws.print_area
if pa:
    pa = pa[0] if isinstance(pa, (list, tuple)) else pa
    pa = pa.split('!')[-1].replace('$', '')
    MINC, MINR, MAXC, MAXR = range_boundaries(pa)  # 印刷範囲がA1始まりでない場合に対応
else:
    MINR, MINC = 1, 1
    MAXR, MAXC = content_bounds()

# 隠れ行・隠れ列（Excelで非表示のもの）は高さ／幅0にして畳む
HIDDEN_ROWS = {r for r, d in ws.row_dimensions.items() if d.hidden}
HIDDEN_COLS = set()
for c, d in ws.column_dimensions.items():
    if d.hidden:
        for ci in range(d.min, (d.max or d.min) + 1):
            HIDDEN_COLS.add(ci)

CORRECTIONS = {}  # 誤字補正はファイル固有なので既定では行わない

# ===== 本文フォントサイズの統一 =====
# 折り返し（本文）セルの中で最も多いサイズを「標準」とし、そこから極端に離れて
# いない本文セルは標準に合わせる（例：一部の案件だけ11ptなのを10ptに統一）。
# タイトルや大見出しなど大きく離れたサイズはそのまま維持する。
import collections as _collections
_body = _collections.Counter()
for _row in ws.iter_rows(min_row=MINR, max_row=MAXR, min_col=MINC, max_col=MAXC):
    for _c in _row:
        if (_c.alignment and _c.alignment.wrap_text and isinstance(_c.value, str)
                and len(_c.value) > 25 and _c.font and _c.font.sz):
            _body[_c.font.sz] += 1
BODY_SIZE = _body.most_common(1)[0][0] if _body else None

def norm_size(cell):
    """本文セルのフォントサイズを標準に寄せる。それ以外は元のサイズ。"""
    sz = cell.font.sz if (cell.font and cell.font.sz) else None
    if sz is None or BODY_SIZE is None:
        return sz
    al = cell.alignment
    if not (al and al.wrap_text):
        return sz
    v = cell.value
    # 長い本文（折り返しセル）は、サイズが大きく外れていても標準に統一する
    # （例：ある案件だけ業務内容が20pt→10ptへ）。短いセル（見出し等）は範囲内のみ。
    if isinstance(v, str) and len(v) > 30:
        return BODY_SIZE
    if 0.6 * BODY_SIZE <= sz <= 1.5 * BODY_SIZE:
        return BODY_SIZE
    return sz

# ===== 2. 案件（まとまり）の区切りを自動検出 =====
def is_idx(v):
    return isinstance(v, int) or (isinstance(v, str) and v.strip().isdigit())

def idx_rows(col):
    out = []
    for r in range(MINR, MAXR + 1):
        if r in HIDDEN_ROWS:
            continue
        v = ws.cell(r, col).value
        if is_idx(v) and 1 <= int(str(v).strip()) <= 99:
            out.append(r)
    return out

# スキル評価セクション（「■…スキル…」で始まる行）を先に検出
skill_start = None
for r in range(MINR, MAXR + 1):
    if any(isinstance(ws.cell(r, c).value, str) and '■' in ws.cell(r, c).value
           and 'スキル' in ws.cell(r, c).value for c in range(MINC, MINC + 3)):
        skill_start = r
        break

# (a) 案件番号ベース：先頭列／次列に 1〜99 の番号が並ぶ形式
a_rows = idx_rows(MINC)
num_starts = a_rows if len(a_rows) >= 2 else idx_rows(MINC + 1)

# (b) 見出しベース：業務内容タイトル（3列以上の結合セルで「■」始まり）。
#     番号のない案件（個人開発など）もこれで拾える。ヘッダやスキル欄は除外。
first_ref = min(num_starts) if num_starts else MINR
title_starts = []
for rng in ws.merged_cells.ranges:
    r0 = rng.min_row
    if (rng.max_col - rng.min_col + 1) >= 3 and MINR <= r0 <= MAXR and r0 >= first_ref \
            and not (skill_start and r0 >= skill_start):
        v = ws.cell(r0, rng.min_col).value
        if isinstance(v, str) and v.strip().startswith('■'):
            title_starts.append(r0)

# (a)(b) を統合し、ごく近接（2行以内＝番号行と見出し行の重複）だけ1つにまとめる
proj_starts = []
for r in sorted(set(num_starts) | set(title_starts)):
    if not proj_starts or r - proj_starts[-1] > 2:
        proj_starts.append(r)

# ブロック生成（先頭＝見出し等／各案件＝分割禁止／スキル評価＝分割可）
BLOCKS = []
if proj_starts:
    first = proj_starts[0]
    if first > MINR:
        BLOCKS.append((MINR, first - 1, False))
    end_proj = (skill_start - 1) if skill_start else MAXR
    for i, s in enumerate(proj_starts):
        e = proj_starts[i + 1] - 1 if i + 1 < len(proj_starts) else end_proj
        BLOCKS.append((s, e, True))
    if skill_start:
        BLOCKS.append((skill_start, MAXR, False))
else:
    BLOCKS = [(MINR, MAXR, False)]

# ===== 3. 列幅・行高 =====
DEFAULT_W = ws.sheet_format.defaultColWidth or 8.43
width_map = {}
for cd in ws.column_dimensions.values():
    if cd.width is None:
        continue
    for ci in range(cd.min, min(cd.max, MAXC) + 1):
        width_map[ci] = cd.width
def col_px(c):
    if c in HIDDEN_COLS:
        return 0
    return round(width_map.get(c, DEFAULT_W) * 7 + 5)
colw = [col_px(c) for c in range(MINC, MAXC + 1)]
table_w = sum(colw)

def row_px(r):
    if r in HIDDEN_ROWS:
        return 0
    rd = ws.row_dimensions.get(r)
    h = rd.height if (rd and rd.height) else 13.5
    return round(h * 96 / 72 * ROW_SCALE, 1)

# ===== 4. 結合セル =====
anchor, covered = {}, set()
for rng in ws.merged_cells.ranges:
    r1, c1, r2, c2 = rng.min_row, rng.min_col, rng.max_row, rng.max_col
    if r1 > MAXR or c1 > MAXC or r2 < MINR or c2 < MINC:
        continue
    r1, c1 = max(r1, MINR), max(c1, MINC)
    r2, c2 = min(r2, MAXR), min(c2, MAXC)
    anchor[(r1, c1)] = (r2 - r1 + 1, c2 - c1 + 1)
    for rr in range(r1, r2 + 1):
        for cc in range(c1, c2 + 1):
            if (rr, cc) != (r1, c1):
                covered.add((rr, cc))

# ===== 5. セルのスタイル =====
BSTYLE = {'thin': '1px solid', 'hair': '0.5px solid', 'medium': '1.5px solid',
          'thick': '2.5px solid', 'double': '3px double', 'dotted': '1px dotted',
          'dashed': '1px dashed', 'dashDot': '1px dashed', 'mediumDashed': '1.5px dashed',
          'slantDashDot': '1px dashed'}

def argb(color):
    rgb = getattr(color, 'rgb', None)
    if isinstance(rgb, str) and len(rgb) == 8:
        return '#' + rgb[2:]
    return None

def border_css(side):
    if not side or not side.style:
        return '0'
    return f'{BSTYLE.get(side.style, "1px solid")} {argb(side.color) or "#000"}'

def cell_style(cell):
    s = []
    b = cell.border
    s.append(f'border-top:{border_css(b.top)}')
    s.append(f'border-bottom:{border_css(b.bottom)}')
    s.append(f'border-left:{border_css(b.left)}')
    s.append(f'border-right:{border_css(b.right)}')
    f = cell.font
    if f:
        sz = norm_size(cell)  # 本文サイズを標準に統一
        if sz:
            s.append(f'font-size:{round(sz * 96 / 72)}px')  # pt→px
        if f.bold:
            s.append('font-weight:700')
        fc = argb(f.color)
        if fc and fc != '#000000':
            s.append(f'color:{fc}')
    fl = cell.fill
    if fl and getattr(fl, 'patternType', None) == 'solid':
        bg = argb(fl.fgColor)
        if bg:
            s.append(f'background:{bg}')
    al = cell.alignment
    s.append('vertical-align:middle')
    if al and al.textRotation == 255:  # 縦書き
        s.append('writing-mode:vertical-rl; text-orientation:upright; white-space:nowrap')
        s.append('text-align:center')
        return ';'.join(s)
    h = (al.horizontal if al else None) or \
        ('right' if isinstance(cell.value, (int, float)) else 'left')
    s.append(f'text-align:{h}')
    if al and al.wrap_text:
        s.append('white-space:pre-wrap; word-break:break-word')
    else:
        s.append('white-space:nowrap')
    return ';'.join(s)

def cell_text(r, c, cell):
    val = CORRECTIONS.get((r, c), cell.value)
    if val is None:
        return ''
    # 日付シリアル値の対応：
    #  ・日付書式が付いている数値、または
    #  ・2000〜2049年相当（36526〜54789）の裸の数値（＝書式漏れの日付とみなす）
    # のみ日付へ変換する。それ以外の数値はそのまま。
    nf = cell.number_format or ''
    if isinstance(val, (int, float)) and not isinstance(val, bool):
        is_date_fmt = any(t in nf for t in ('y', 'm', 'd', '年', '月', '日'))
        if (is_date_fmt and val > 59) or (36526 <= val <= 54789):
            try:
                val = from_excel(val)
            except Exception:
                pass
    if hasattr(val, 'strftime'):
        return val.strftime('%Y年%-m月')
    return html.escape(str(val)).replace('\n', '<br>')

# ===== 6. HTML生成 =====
COLGROUP = '<colgroup>' + ''.join(f'<col style="width:{w}px">' for w in colw) + '</colgroup>'

def render_rows(r0, r1):
    out = []
    for r in range(r0, r1 + 1):
        out.append(f'<tr style="height:{row_px(r)}px">')
        for c in range(MINC, MAXC + 1):
            if (r, c) in covered:
                continue
            cell = ws.cell(r, c)
            span = anchor.get((r, c), (1, 1))
            attrs = ''
            if span[0] > 1:
                attrs += f' rowspan="{span[0]}"'
            if span[1] > 1:
                attrs += f' colspan="{span[1]}"'
            style = cell_style(cell)
            # セルが占める行がすべて非表示なら中身を畳む（高さを持たせない）
            if sum(row_px(rr) for rr in range(r, r + span[0])) == 0:
                style += ';font-size:0;line-height:0;padding:0'
                txt = ''
            else:
                txt = cell_text(r, c, cell)
            out.append(f'<td{attrs} style="{style}">{txt}</td>')
        out.append('</tr>')
    return '\n'.join(out)

# 印刷可能幅（A4縦 210mm − 左右0.25in）に合わせて縮小（狭い表は等倍まで）
PRINT_W = round((210 - 6.35 * 2) * 96 / 25.4)
PRINT_H = round((297 - 6.35 * 2) * 96 / 25.4)
zoom = round(min(PRINT_W / table_w, 1.0) * 0.99, 4)

# 大きすぎる案件ブロックは分割禁止を解除する。
# ・小さい案件は分割禁止のまま（＝途中で切れない）
# ・1ページの MAX_KEEP_FRACTION を超える案件は分割許可（＝大きな余白を作らない／はみ出さない）
MAX_KEEP_FRACTION = 0.65
def block_h(r0, r1):
    return sum(row_px(r) for r in range(r0, r1 + 1))
BLOCKS = [(r0, r1, keep and block_h(r0, r1) * zoom < PRINT_H * MAX_KEEP_FRACTION)
          for (r0, r1, keep) in BLOCKS]

css = f"""<meta charset="utf-8"><style>
@page {{ size: A4 portrait; margin: 0.25in; }}
* {{ box-sizing: border-box; }}
html, body {{ margin: 0; padding: 0; }}
body {{ font-family: {FONT}; -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
.sheet {{ zoom: {zoom}; width: {table_w}px; margin: 0 auto; }}
table {{ border-collapse: collapse; table-layout: fixed; }}
tbody.keep {{ break-inside: avoid; page-break-inside: avoid; }}
td {{ padding: 0 1px; line-height: 1.12; font-family: {FONT}; overflow: hidden; }}
</style>"""

parts = [css, f'<div class="sheet"><table>{COLGROUP}']
for (r0, r1, keep) in BLOCKS:
    cls = ' class="keep"' if (keep and KEEP_TOGETHER) else ''
    parts.append(f'<tbody{cls}>{render_rows(r0, r1)}</tbody>')
parts.append('</table></div>')

open(OUT, 'w', encoding='utf-8').write('\n'.join(parts))
print(f'sheet={ws.title!r} range=A1:{get_column_letter(MAXC)}{MAXR} '
      f'table_w={table_w} zoom={zoom} projects={len(proj_starts)} blocks={len(BLOCKS)}')
