"""SEO記事チェック: 機械判定（文字数・KW出現率）を行い JSON を返す.

LLM に数値を数えさせると誤るため、文字数系・KW 出現率など「数えれば決まる」項目は
本スクリプトで先に判定し、その結果をサブエージェントへ渡す。サブエージェントは
この数値を根拠に verdict を書く（自分では数えない）。

入力:
  --article article.json   fetch_article.py の出力
  --kw kw.json             {"main": "...", "sub": [...], "cooccurrence": [...]}
                           （--main / --sub / --cooc でも可）
  --mode {structure,article}  構成チェック / 本稿チェック

出力（stdout, JSON）:
  {
    "mode": "...",
    "kw": {...},
    "checks": {
      "<category>": [ {item, measured, threshold, verdict, detail}, ... ]
    }
  }
  verdict は "OK" / "NG" / "BORDERLINE"（閾値近傍）/ "INFO"（材料提供のみ）。

判定はあくまで機械的な下限保証。文意を伴う項目（見出しだけで内容が分かる等）は
INFO 材料のみ提供し、最終 verdict はサブエージェントに委ねる。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# 閾値の許容幅（BORDERLINE 判定）: 各項目の閾値に対する ±のりしろ。
# チェックリストの数値は「程度」「目安」表現が多く、僅かな超過を即NGにすると
# ノイズが増えるため、閾値近傍を BORDERLINE（要確認）に落とす帯を設けている。

# 日本語の文末想定（。！？と全角/半角）
SENTENCE_SPLIT = re.compile(r"(?<=[。！？!?])")


def _split_sentences(text: str) -> list[str]:
    return [s.strip() for s in SENTENCE_SPLIT.split(text) if s.strip()]


def _count_kw(text: str, kws: list[str]) -> list[str]:
    """text に含まれる KW を返す（部分一致・大文字小文字無視）."""
    low = text.lower()
    return [kw for kw in kws if kw and kw.lower() in low]


def _verdict(ok: bool, borderline: bool = False) -> str:
    if borderline:
        return "BORDERLINE"
    return "OK" if ok else "NG"


def check_title(article: dict, kw: dict) -> list[dict]:
    title = article.get("title", "")
    n = len(title)
    main = kw.get("main", "")
    subs = kw.get("sub", [])
    checks = [
        {
            "item": "タイトルは原則35文字以内",
            "measured": f"{n}字",
            "threshold": "35字以内",
            "verdict": _verdict(n <= 35, borderline=36 <= n <= 38),
            "detail": f"タイトル: 「{title}」",
        },
        {
            "item": "タイトルにメインKWを自然に含む",
            "measured": "含む" if _count_kw(title, [main]) else "含まない",
            "threshold": f"メインKW『{main}』を含む",
            "verdict": _verdict(bool(_count_kw(title, [main]))) if main else "INFO",
            "detail": "メインKW未指定" if not main else "",
        },
        {
            "item": "タイトルにサブKWを自然に含む",
            "measured": f"含むサブKW: {_count_kw(title, subs) or 'なし'}",
            "threshold": "サブKWをできるだけ含む",
            "verdict": "INFO",
            "detail": "サブKWは必須ではないため材料提供のみ",
        },
        {
            "item": "タイトルに具体的な数値を使う",
            "measured": "数字あり" if re.search(r"[0-9０-９]", title) else "数字なし",
            "threshold": "具体的な数値を推奨",
            "verdict": "INFO",
            "detail": "数値の妥当性はサブエージェント判定",
        },
    ]
    return checks


def _lead_block(article: dict) -> str:
    """最初の見出しより前の段落（=リード文）を連結して返す."""
    paras = article.get("paragraphs", [])
    lead = []
    for p in paras:
        if p.get("is_heading"):
            break
        # タイトル段落（先頭 TITLE/最初の1行）はリードに含めない
        if p["order"] == 0 and p.get("text") == article.get("title"):
            continue
        lead.append(p["text"])
    return "\n".join(lead)


def check_lead(article: dict, kw: dict) -> list[dict]:
    lead = _lead_block(article)
    n = len(lead.replace("\n", ""))
    main = kw.get("main", "")
    subs = kw.get("sub", [])
    coocs = kw.get("cooccurrence", [])
    found_main = _count_kw(lead, [main]) if main else []
    return [
        {
            "item": "リード文は150〜300字",
            "measured": f"{n}字",
            "threshold": "150〜300字",
            "verdict": _verdict(150 <= n <= 300, borderline=(130 <= n < 150 or 300 < n <= 330)),
            "detail": "リード文=最初の見出し前の本文" + ("（本文検出できず）" if n == 0 else ""),
        },
        {
            "item": "リード文にメインKWを盛り込む",
            "measured": "含む" if found_main else "含まない",
            "threshold": f"メインKW『{main}』",
            "verdict": _verdict(bool(found_main)) if main else "INFO",
            "detail": "",
        },
        {
            "item": "リード文にサブKW・共起語を盛り込む",
            "measured": f"サブKW: {_count_kw(lead, subs) or 'なし'} / 共起語: {_count_kw(lead, coocs) or 'なし'}",
            "threshold": "自然に盛り込む",
            "verdict": "INFO",
            "detail": "自然さはサブエージェント判定",
        },
    ]


def check_headings(article: dict, kw: dict) -> list[dict]:
    headings = article.get("headings", [])
    # タイトル(level0)は除外、記事内の見出し(level>=1)のみ
    body_headings = [h for h in headings if h["level"] >= 1]
    main = kw.get("main", "")
    subs = kw.get("sub", [])
    kw_all = [main] + subs if main else subs

    # 各見出しの字数
    over = [h for h in body_headings if len(h["text"]) > 25]
    under = [h for h in body_headings if len(h["text"]) < 13]
    # KW 出現率
    with_kw = [h for h in body_headings if _count_kw(h["text"], kw_all)]
    rate = (len(with_kw) / len(body_headings)) if body_headings else 0.0

    detail_lengths = "; ".join(f"「{h['text']}」={len(h['text'])}字" for h in body_headings[:20])

    checks = [
        {
            "item": "見出しは20〜25字程度",
            "measured": f"25字超: {len(over)}件 / 13字未満: {len(under)}件 / 全{len(body_headings)}見出し",
            "threshold": "20〜25字程度",
            "verdict": _verdict(not over, borderline=bool(over) and len(over) <= max(1, len(body_headings) // 5)),
            "detail": detail_lengths,
        },
        {
            "item": "見出しにKWを7〜8割入れる（サブKW・サジェスト含む）",
            "measured": f"KW含有 {len(with_kw)}/{len(body_headings)}見出し = {rate*100:.0f}%",
            "threshold": "70〜80%以上",
            "verdict": (
                "INFO" if not kw_all else _verdict(rate >= 0.7, borderline=0.6 <= rate < 0.7)
            ),
            "detail": "KW未指定" if not kw_all else "サジェスト/共起語は別途サブエージェントが加味",
        },
        {
            "item": "見出しの階層構造が適切",
            "measured": f"レベル分布: {_level_dist(body_headings)}",
            "threshold": "H2>H3 の入れ子が自然",
            "verdict": "INFO",
            "detail": "飛び級（H2→H4等）の有無はサブエージェント判定",
        },
    ]
    return checks


def _level_dist(headings: list[dict]) -> str:
    dist: dict[int, int] = {}
    for h in headings:
        dist[h["level"]] = dist.get(h["level"], 0) + 1
    return ", ".join(f"H{lvl}:{cnt}" for lvl, cnt in sorted(dist.items()))


def check_body(article: dict, kw: dict) -> list[dict]:
    paras = article.get("paragraphs", [])
    body_paras = [p for p in paras if not p.get("is_heading") and not p.get("is_list_item")]
    # 本文段落から、タイトル・リード相当も含め全体の1文長を見る
    long_sentences = []
    for p in body_paras:
        for s in _split_sentences(p["text"]):
            if len(s) > 80:
                long_sentences.append(s)
    # 段落（改行）長: 120字超
    long_paras = [p for p in body_paras if p["char_count"] > 120]

    main = kw.get("main", "")
    subs = kw.get("sub", [])
    kw_all = [main] + subs if main else subs
    # 段落ごとの対策KW: KWを1つも含まない本文段落
    if kw_all:
        no_kw_paras = [p for p in body_paras if not _count_kw(p["text"], kw_all)]
        kw_para_rate = 1 - (len(no_kw_paras) / len(body_paras)) if body_paras else 0
    else:
        no_kw_paras = []
        kw_para_rate = 0

    return [
        {
            "item": "1文の長さは60字程度",
            "measured": f"80字超の文: {len(long_sentences)}件",
            "threshold": "60字程度（80字を明確な超過ラインとする）",
            "verdict": _verdict(not long_sentences, borderline=0 < len(long_sentences) <= 3),
            "detail": "; ".join(f"「{s[:40]}…」={len(s)}字" for s in long_sentences[:10]),
        },
        {
            "item": "80〜120字で改行する",
            "measured": f"120字超の段落: {len(long_paras)}件 / 全{len(body_paras)}段落",
            "threshold": "1段落120字以内目安",
            "verdict": _verdict(not long_paras, borderline=0 < len(long_paras) <= 3),
            "detail": "; ".join(f"{p['char_count']}字" for p in long_paras[:10]),
        },
        {
            "item": "対策キーワードを段落ごとに入れる",
            "measured": (
                f"KW無し段落: {len(no_kw_paras)}/{len(body_paras)} "
                f"(含有率{kw_para_rate*100:.0f}%)" if kw_all else "KW未指定"
            ),
            "threshold": "各段落に対策KWを意識",
            "verdict": "INFO" if not kw_all else _verdict(kw_para_rate >= 0.6),
            "detail": "厳密な必須ではないため参考。過剰詰め込みは逆効果",
        },
    ]


def run(article: dict, kw: dict, mode: str) -> dict:
    checks: dict[str, list[dict]] = {}
    if mode == "structure":
        # 構成チェック: 見出し表現のみ機械判定（構成ロジックは非機械）
        checks["見出し表現"] = check_headings(article, kw)
    else:
        checks["タイトル"] = check_title(article, kw)
        checks["リード文"] = check_lead(article, kw)
        checks["構成・見出し"] = check_headings(article, kw)
        checks["本文執筆ルール"] = check_body(article, kw)
    return {"mode": mode, "kw": kw, "checks": checks}


def _load_kw(args) -> dict:
    if args.kw:
        kw = json.loads(Path(args.kw).read_text(encoding="utf-8"))
    else:
        kw = {}
    if args.main:
        kw["main"] = args.main
    if args.sub:
        kw["sub"] = [s.strip() for s in args.sub.split(",") if s.strip()]
    if args.cooc:
        kw["cooccurrence"] = [s.strip() for s in args.cooc.split(",") if s.strip()]
    kw.setdefault("main", "")
    kw.setdefault("sub", [])
    kw.setdefault("cooccurrence", [])
    return kw


def main() -> None:
    ap = argparse.ArgumentParser(description="SEO記事の機械判定")
    ap.add_argument("--article", required=True, help="fetch_article.py の出力 JSON")
    ap.add_argument("--kw", help="KW定義 JSON {main, sub[], cooccurrence[]}")
    ap.add_argument("--main", help="メインKW")
    ap.add_argument("--sub", help="サブKW（カンマ区切り）")
    ap.add_argument("--cooc", help="共起語（カンマ区切り）")
    ap.add_argument("--mode", choices=["structure", "article"], default="article")
    ap.add_argument("--out", help="出力先（省略時 stdout）")
    args = ap.parse_args()

    article = json.loads(Path(args.article).read_text(encoding="utf-8"))
    kw = _load_kw(args)
    result = run(article, kw, args.mode)
    payload = json.dumps(result, ensure_ascii=False, indent=2)
    if args.out:
        Path(args.out).write_text(payload, encoding="utf-8")
        print(f"[mechanical_checks] wrote {args.out}", file=sys.stderr)
    else:
        print(payload)


if __name__ == "__main__":
    main()
