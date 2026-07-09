"""SEO記事チェック: 集約済み findings を HTMLレポートへ描画する.

サブエージェントの verdict を集約した findings.json を受け取り、
判定マトリクス・修正案・Docs記入結果を1枚の HTML にする。
メインエージェントが手書きするより再現性が高く、抜けが出にくい。

入力（--findings findings.json）:
  {
    "mode": "article" | "structure",
    "doc_url": "...", "title": "...", "generated_at": "YYYY-MM-DD HH:MM",
    "kw": {"main": "...", "sub": [...], "cooccurrence": [...]},
    "categories": {
      "<カテゴリ名>": [
        {"id","item","verdict","measured","issue","before","after","comment"}, ...
      ]
    },
    "apply_result": [ {"id","method","status","detail"} ]   # 任意（ステップ8後）
  }

出力: --out 指定の HTML パス（省略時 stdout）。
"""

from __future__ import annotations

import argparse
import html
import json
from pathlib import Path

VERDICT_STYLE = {
    "OK": ("#1a7f37", "#e6f4ea", "OK"),
    "NG": ("#b42318", "#fce8e6", "NG"),
    "BORDERLINE": ("#9a6700", "#fff8e1", "要確認"),
    "判定不能": ("#57606a", "#eef1f4", "判定不能"),
    "INFO": ("#57606a", "#eef1f4", "参考"),
}

OUT_OF_SCOPE = [
    "リサーチ工程（競合調査・サジェスト・共起語・SERP分析のシート転記）",
    "コピペチェック（外部ツール）",
    "入稿時：「赤木 宏志 | mijica CEO から一言」へのXリンク付与",
    "入稿後：ラッコキーワードでの順位取得・履歴反映",
]


def esc(s) -> str:
    return html.escape(str(s or ""))


def _badge(verdict: str) -> str:
    fg, bg, label = VERDICT_STYLE.get(verdict, VERDICT_STYLE["判定不能"])
    return f'<span class="badge" style="color:{fg};background:{bg}">{esc(label)}</span>'


def _summary(categories: dict) -> dict:
    counts = {"OK": 0, "NG": 0, "BORDERLINE": 0, "判定不能": 0}
    for items in categories.values():
        for it in items:
            v = it.get("verdict", "判定不能")
            counts[v] = counts.get(v, 0) + 1
    return counts


def render(data: dict) -> str:
    mode = data.get("mode", "article")
    mode_label = "構成チェック" if mode == "structure" else "本稿チェック"
    kw = data.get("kw", {})
    cats = data.get("categories", {})
    counts = _summary(cats)
    total = sum(counts.values())

    apply_result = {r["id"]: r for r in data.get("apply_result", [])}

    rows = []
    proposals = []
    for cat, items in cats.items():
        rows.append(f'<tr class="cat"><td colspan="4">{esc(cat)}</td></tr>')
        for it in items:
            measured = esc(it.get("measured"))
            issue = esc(it.get("issue"))
            detail = measured
            if issue:
                detail += (" / " if measured else "") + issue
            rows.append(
                f'<tr><td class="id">{esc(it.get("id"))}</td>'
                f'<td>{esc(it.get("item"))}</td>'
                f'<td class="v">{_badge(it.get("verdict","判定不能"))}</td>'
                f'<td class="d">{detail}</td></tr>'
            )
            if it.get("verdict") in ("NG", "BORDERLINE"):
                proposals.append((cat, it))

    prop_html = []
    for cat, it in proposals:
        applied = apply_result.get(it.get("id"))
        applied_html = ""
        if applied:
            m = "提案モード" if applied["method"] == "suggest" else "コメント"
            applied_html = f'<div class="applied">Docs記入: {esc(m)}（{esc(applied.get("status"))}）</div>'
        ba = ""
        if it.get("before") or it.get("after"):
            ba = (
                f'<div class="ba"><div class="before"><span>修正前</span>'
                f'<pre>{esc(it.get("before"))}</pre></div>'
                f'<div class="after"><span>修正後</span>'
                f'<pre>{esc(it.get("after"))}</pre></div></div>'
            )
        else:
            ba = '<div class="note">※ 文意判断のため自動置換なし（コメントで指摘）</div>'
        prop_html.append(
            f'<div class="prop {it.get("verdict","")}">'
            f'<div class="phead">{_badge(it.get("verdict"))}'
            f'<span class="pid">{esc(it.get("id"))}</span>'
            f'<span class="pcat">{esc(cat)}</span>'
            f'<span class="pitem">{esc(it.get("item"))}</span></div>'
            f'<div class="issue">{esc(it.get("issue"))}</div>'
            f'{ba}'
            f'<div class="cmt">{esc(it.get("comment"))}</div>'
            f'{applied_html}</div>'
        )

    oos = "".join(f"<li>{esc(x)}</li>" for x in OUT_OF_SCOPE)
    kw_line = f'メインKW: <b>{esc(kw.get("main"))}</b>'
    if kw.get("sub"):
        kw_line += f' / サブKW: {esc("、".join(kw["sub"]))}'
    if kw.get("cooccurrence"):
        kw_line += f' / 共起語: {esc("、".join(kw["cooccurrence"]))}'

    return f"""<!doctype html>
<html lang="ja"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>SEO記事チェック結果 — {esc(data.get('title'))}</title>
<style>
:root{{--bd:#d0d7de;--mut:#57606a;}}
*{{box-sizing:border-box}}
body{{font-family:-apple-system,"Hiragino Sans","Noto Sans JP",sans-serif;margin:0;color:#1f2328;background:#f6f8fa;line-height:1.7}}
.wrap{{max-width:960px;margin:0 auto;padding:32px 20px}}
h1{{font-size:22px;margin:0 0 4px}}
h2{{font-size:17px;margin:32px 0 12px;padding-bottom:6px;border-bottom:2px solid var(--bd)}}
.meta{{color:var(--mut);font-size:13px}}
.meta a{{color:#0969da}}
.modechip{{display:inline-block;background:#0969da;color:#fff;border-radius:12px;padding:2px 12px;font-size:13px;font-weight:600;margin-right:8px}}
.cards{{display:flex;gap:10px;margin:16px 0;flex-wrap:wrap}}
.card{{flex:1;min-width:110px;background:#fff;border:1px solid var(--bd);border-radius:10px;padding:12px 14px;text-align:center}}
.card .n{{font-size:26px;font-weight:700}}
.card .l{{font-size:12px;color:var(--mut)}}
.oos{{background:#fff;border:1px solid var(--bd);border-left:4px solid #9a6700;border-radius:8px;padding:12px 16px;font-size:13px}}
.oos ul{{margin:6px 0 0;padding-left:20px}}
table{{width:100%;border-collapse:collapse;background:#fff;border:1px solid var(--bd);border-radius:8px;overflow:hidden;font-size:14px}}
td{{padding:8px 12px;border-bottom:1px solid #eaeef2;vertical-align:top}}
tr.cat td{{background:#f0f3f6;font-weight:700;font-size:13px}}
td.id{{color:var(--mut);font-variant-numeric:tabular-nums;white-space:nowrap;width:52px}}
td.v{{width:64px}}
td.d{{color:var(--mut);font-size:13px}}
.badge{{display:inline-block;border-radius:10px;padding:1px 10px;font-size:12px;font-weight:700}}
.prop{{background:#fff;border:1px solid var(--bd);border-radius:10px;padding:14px 16px;margin:12px 0}}
.prop.NG{{border-left:4px solid #b42318}}
.prop.BORDERLINE{{border-left:4px solid #9a6700}}
.phead{{display:flex;align-items:center;gap:8px;flex-wrap:wrap}}
.pid{{color:var(--mut);font-size:12px}}
.pcat{{color:var(--mut);font-size:12px}}
.pitem{{font-weight:600}}
.issue{{margin:8px 0;font-size:14px}}
.ba{{display:flex;gap:10px;margin:8px 0;flex-wrap:wrap}}
.ba>div{{flex:1;min-width:240px}}
.ba span{{font-size:11px;font-weight:700;color:var(--mut)}}
.ba pre{{white-space:pre-wrap;word-break:break-word;margin:2px 0 0;padding:8px 10px;border-radius:6px;font-size:13px;font-family:inherit}}
.before pre{{background:#fce8e6}}
.after pre{{background:#e6f4ea}}
.note{{font-size:12px;color:var(--mut);margin:6px 0}}
.cmt{{font-size:13px;color:#3a4149;margin-top:6px}}
.applied{{font-size:12px;color:#0969da;margin-top:8px}}
.empty{{color:var(--mut);font-size:14px}}
</style></head>
<body><div class="wrap">
<h1>SEO記事チェック結果</h1>
<div class="meta">
<div><span class="modechip">{esc(mode_label)}</span><b>{esc(data.get('title'))}</b></div>
<div>{kw_line}</div>
<div><a href="{esc(data.get('doc_url'))}">{esc(data.get('doc_url'))}</a></div>
<div>実行: {esc(data.get('generated_at'))}</div>
</div>

<div class="cards">
<div class="card"><div class="n">{total}</div><div class="l">チェック項目</div></div>
<div class="card"><div class="n" style="color:#1a7f37">{counts.get('OK',0)}</div><div class="l">OK</div></div>
<div class="card"><div class="n" style="color:#b42318">{counts.get('NG',0)}</div><div class="l">NG</div></div>
<div class="card"><div class="n" style="color:#9a6700">{counts.get('BORDERLINE',0)}</div><div class="l">要確認</div></div>
<div class="card"><div class="n" style="color:#57606a">{counts.get('判定不能',0)}</div><div class="l">判定不能</div></div>
</div>

<h2>対象外（本スキルでは判定しない）</h2>
<div class="oos">記事テキストから検証できないため、以下はライター／入稿担当が別途担保する前提です。
<ul>{oos}</ul></div>

<h2>全項目マトリクス</h2>
<table><tbody>{''.join(rows)}</tbody></table>

<h2>修正案（NG・要確認）</h2>
{''.join(prop_html) if prop_html else '<p class="empty">NG・要確認の項目はありませんでした。</p>'}

</div></body></html>"""


def main() -> None:
    ap = argparse.ArgumentParser(description="SEO記事チェック HTMLレポート生成")
    ap.add_argument("--findings", required=True, help="集約済み findings JSON")
    ap.add_argument("--out", help="出力 HTML パス（省略時 stdout）")
    args = ap.parse_args()
    data = json.loads(Path(args.findings).read_text(encoding="utf-8"))
    out_html = render(data)
    if args.out:
        Path(args.out).write_text(out_html, encoding="utf-8")
        print(f"[render_report] wrote {args.out}")
    else:
        print(out_html)


if __name__ == "__main__":
    main()
