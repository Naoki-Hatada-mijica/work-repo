---
name: seo-article-check
description: SEO記事のチェックリスト（構成案／執筆後）を、カテゴリごとに別サブエージェントが分担チェックして漏れを防ぐスキル。Google Docs のURLとメインKWを渡すと、全チェック項目の判定マトリクスと修正案(before/after)をHTMLレポートに出力し、承認後に元Docsへ提案モード（またはコメント）で修正案を記入する。「SEO記事チェック」「記事のチェックリスト」「この記事レビューして」「構成案チェック」「seo-article-check」などのリクエストに使用する。
---

## 概要

ライターのSEO記事が社内チェックリストを厳密に守れていない問題に対し、**チェックリストの
全項目を機械的に検証する**スキル。1エージェントで全項目を見ると必ず漏れが出るため、
**カテゴリごとに別サブエージェントを並列で走らせ、各エージェントは担当カテゴリの全項目に
必ず verdict を返す**構成にしている（漏れ防止が本スキルの核）。

- 入力: 記事の Google Docs URL ＋ メインKW（サブKW・共起語は任意）
- 出力:
  1. HTMLレポート（`output/` に保存し `open`）— 全項目×verdict マトリクス／修正案／Docs記入結果
  2. 元 Docs への修正案記入（**提案モード**優先、不可なら原文引用つきコメント）
- チェック正本: `references/checklist.md`（元Docsのスナップショット。ID付き）

## 2つのチェックモード（最初に必ず確認）

記事は「構成案の段階」か「執筆後の原稿」かでチェック項目が異なる。**実行の最初に必ず
どちらのモードかを確認する**。

| モード | 対象 | カテゴリ（サブエージェント） |
|--------|------|------------------------------|
| **構成チェック** | 構成案・ロジックツリー | S1 見出し表現 / S2 構成ロジック（2並列） |
| **本稿チェック** | 執筆後の完成記事 | A タイトル / B リード文 / C 構成・見出し / D 本文執筆ルール / E 最終原チェック（5並列） |

判定手順:
1. `fetch_article.py` の出力（本文の量・見出し配下に本文段落があるか）からモードを推定する
   - 見出しはあるが各見出し配下の本文段落がほぼ無い → 構成チェックの可能性が高い
   - 見出し配下に本文段落が続く → 本稿チェックの可能性が高い
2. 推定をデフォルト候補にして **AskUserQuestion で確認**してから進む（勝手に決めない）

## 対象外（判定しない）

`references/checklist.md` 末尾の「対象外」に従う。リサーチ工程（競合調査・サジェスト・
共起語・SERP分析）、コピペチェック、入稿時Xリンク、入稿後の順位取得は記事テキストから
検証できないため**レポート冒頭に「対象外」として明示**し、担当者が別途担保する前提とする。

---

## 依存関係

- Python パッケージ: `google-api-python-client` / `google-auth`（Docs・Drive API）、`playwright`
  （提案モード。`playwright install chromium` 済みが前提）
- 認証: `~/.claude/snippets/google_workspace.py` の OAuth トークンを流用
  （scopes に documents / drive を含む）。各スクリプトが import path に自動追加する。
- サブエージェント: `general-purpose`（Task tool）。WebFetch 不可を前提に記事はメイン側で取得。

## 実行手順

### ステップ1: 入力の受付

- Docs URL を受け取る。**メインKW**が未指定なら質問する（サブKW・共起語は任意、あれば受ける）。
  - KW はチェックの根拠になるため、メインKW無しでは進めない（未指定のまま進めない）。
- 作業用の一時ディレクトリを用意（`tmp/seo-check/` など gitignore 済みの場所）。

### ステップ2: 記事の取得

```bash
python3 .claude/skills/seo-article-check/scripts/fetch_article.py "<DOC_URL>" --out tmp/seo-check/article.json
```

出力 `article.json` に title / headings / paragraphs（各 char_count 付き）/ full_text が入る。

### ステップ3: モード確認

article.json の内容からモードを推定 → AskUserQuestion で「構成チェック / 本稿チェック」を確認。

### ステップ4: 機械判定

```bash
# 本稿チェックの例
python3 .claude/skills/seo-article-check/scripts/mechanical_checks.py \
  --article tmp/seo-check/article.json \
  --main "<メインKW>" --sub "<サブKW,カンマ区切り>" --cooc "<共起語>" \
  --mode article --out tmp/seo-check/mechanical.json
# 構成チェックなら --mode structure
```

文字数系・KW出現率はここで数値が確定する。**サブエージェントにこの数値を渡し、
LLM には数えさせない**。

### ステップ5: サブエージェントを並列 fan-out

モードに応じたカテゴリ数だけ **general-purpose サブエージェントを1メッセージで並列起動**する
（構成=2体 / 本稿=5体）。各サブエージェントへ渡すもの:

- `article.json` のパス（Read させる。full_text と headings/paragraphs を使う）
- `mechanical.json` のパス（担当カテゴリの数値判定）
- `references/checklist.md` のパス＋**担当カテゴリのID範囲**（例: 「カテゴリ D の D-1〜D-8 を担当」）
- メインKW／サブKW／共起語

各サブエージェントへの指示（プロンプトに必ず含める）:

> あなたは SEO 記事チェックの「カテゴリ〈X〉」担当です。`references/checklist.md` の
> 〈カテゴリXの全ID〉について、**1つも飛ばさず**それぞれ verdict を返してください。
> - `article.json` を Read して記事本文・見出し・段落を把握する
> - `mechanical.json` の該当カテゴリの数値を**そのまま根拠に使う**（自分で字数やKW率を数え直さない）
> - type=mechanical の項目は mechanical.json の測定値を根拠に OK/NG を確定する
> - type=judgement の項目は記事本文を読んで判断する
> - NG/BORDERLINE の項目には、必ず**原文の完全一致引用**と**修正案(before/after)**を付ける
>   （before は記事本文に一字一句一致する文字列。after は修正後の文。文意判断のみで
>    自動置換に馴染まない項目は before/after を空にし comment に理由を書く）
> - 出力は次の JSON 配列のみ（前置き・後書きなし）:
> ```json
> [{"id":"D-2","item":"1文の長さは60字程度","verdict":"NG",
>   "quote":"原文の完全一致文字列","issue":"何が問題か","severity":"high|mid|low",
>   "before":"置換対象（原文一致）","after":"修正後","comment":"補足"}]
> ```
> verdict は "OK" / "NG" / "BORDERLINE" / "判定不能" のいずれか。全IDを網羅すること。

### ステップ6: 集約と検証（メイン側）

- 全サブエージェントの JSON を統合。**各カテゴリの全IDが揃っているか検証**し、欠けていれば
  そのサブエージェントを再実行する（漏れを絶対に残さない）。
- `before`（＝置換対象）が `article.json` の full_text に**完全一致で存在するか**を検証する。
  一致しない before は自動置換に使えないため、その修正案は「手動確認」に降格し、
  Docs 記入時は comment 方式に回す（誤置換防止）。
- 重複指摘（同一箇所への複数カテゴリからの指摘）はマージする。

### ステップ7: HTMLレポート生成

ステップ6で集約・検証した結果を `findings.json` にまとめ、`render_report.py` で HTML 化する。

```bash
python3 .claude/skills/seo-article-check/scripts/render_report.py \
  --findings tmp/seo-check/findings.json \
  --out "02_task/<タスクフォルダ名>/output/<タスクフォルダ名>_SEO記事チェック結果.html"
open "02_task/<タスクフォルダ名>/output/<タスクフォルダ名>_SEO記事チェック結果.html"
```

`findings.json` のスキーマ（render_report.py 冒頭のドキュメント参照）:
```json
{"mode":"article|structure","doc_url":"...","title":"...","generated_at":"YYYY-MM-DD HH:MM",
 "kw":{"main":"...","sub":[...],"cooccurrence":[...]},
 "categories":{"<カテゴリ名>":[{"id","item","verdict","measured","issue","before","after","comment"}]},
 "apply_result":[{"id","method","status","detail"}]}
```
レポートは 実行モード / 対象外項目 / 判定サマリ / 全項目マトリクス / 修正案(before/after) /
Docs記入結果（`apply_result` があれば）を1枚に描画する。`apply_result` はステップ8実行後に
findings.json へ追記して再生成すると、記入内訳（suggest/comment）まで反映される。

### ステップ8: Docs へ記入（承認必須）

**外部ドキュメントへの書き込みのため、修正案一覧をユーザーに提示し承認を得てから実行する。**

```bash
# 提案モード優先（失敗項目は自動でコメントにフォールバック）
python3 .claude/skills/seo-article-check/scripts/apply_suggestions.py \
  --doc "<DOC_URL>" --suggestions tmp/seo-check/suggestions.json \
  --out tmp/seo-check/apply-result.json
```

- `suggestions.json` は before/after/comment を持つ修正案配列（ステップ6で検証済みのもの）。
- 提案モードは Google の canvas 描画により壊れやすい。**初回のみ手動ログインが必要**:
  `python3 apply_suggestions.py --login`（ブラウザが開くので Google ログイン→Enter）。
  以降はプロファイルにセッションが残る。ログインが切れている/切替に失敗した項目は
  自動で原文引用つきコメントにフォールバックするため、スキルは必ず完走する。
- 提案モードを使わず確実にコメントだけで記入したい場合は `--comments-only` を付ける。
- 実行後 `apply-result.json` を読み、各修正案が suggest / comment のどちらで入ったかを
  HTMLレポート（ステップ7の6節）に追記する。

---

## 出力前セルフチェック

- [ ] **モード確認を飛ばしていないか**（構成/本稿をユーザーに確認したか）
- [ ] メインKW未指定のまま進めていないか
- [ ] **全カテゴリの全IDに verdict があるか**（欠けたカテゴリのサブエージェントを再実行したか）
- [ ] NG/BORDERLINE 項目に原文引用と修正案(before/after)が付いているか
- [ ] before が記事本文に完全一致するか検証したか（不一致は comment 方式へ降格）
- [ ] 機械判定できる項目で、LLM に数えさせず mechanical.json の数値を根拠にしたか
- [ ] レポート冒頭に「対象外項目」を明示したか
- [ ] Docs 記入前にユーザーの承認を得たか
- [ ] Docs 記入後、apply-result の suggest/comment 内訳をレポートに追記したか

## 元Docs（チェックリスト）更新時の再同期

`references/checklist.md` は元 Docs のスナップショット。元 Docs が更新されたら:

```bash
python3 .claude/skills/seo-article-check/scripts/fetch_article.py \
  "https://docs.google.com/document/d/1hDgkku4rOhnElaD4cLrd1E9Fuv2ZAfAP9SYdxubwi6w/edit" \
  --out tmp/checklist-latest.json
```

を取得して checklist.md との差分を確認し、追加/変更された項目に ID を振って反映する。

## 補足・ハマりどころ

- サブエージェント（general-purpose）は WebFetch できない場合がある。記事取得は必ず
  メイン側で `fetch_article.py` を実行し、テキスト（article.json）をパスで渡すこと。
- 記事本文はクライアント公開前コンテンツ。処理はローカル＋本人の Google アカウント内で
  完結させる（外部SaaSに本文を渡さない）。
- 検証時は本物の記事を汚さないよう、Drive API でコピーした使い捨て Doc で試すこと。
