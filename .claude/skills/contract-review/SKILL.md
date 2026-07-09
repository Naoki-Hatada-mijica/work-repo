---
name: contract-review
description: SES業務委託基本契約書をレビューし、コメント・変更履歴付きWordファイルとMarkdownレビュー結果を出力する。契約書レビュー、業務委託契約、SES契約の確認を行う場合に使用する。
---

## ワークフロー進捗

このチェックリストをコピーして進捗を追跡する:

```
- [ ] ステップ1: 入力確認
- [ ] ステップ2: 弊社ひな形の読み込み
- [ ] ステップ3: レビュー実行
- [ ] ステップ4: レビュー結果の確認
- [ ] ステップ5: 指摘の整理とJSON出力
- [ ] ステップ6: Markdownレビュー結果の出力
- [ ] ステップ7: 文書への適用
- [ ] ステップ8: 結果サマリの表示
```

## 前提

- 株式会社mijicaはSES（準委任契約）を前提としたITフリーランスエージェント業を営んでいる
- 基本的にmijica側（乙）は責任を負いたくない立場にある
- 損害賠償もできるだけ負いたくない
- 弊社ひな形: `docs/contracts/業務委託基本契約書_雛形.md`

### 依存パッケージ

- Word文書操作: `pip3 install python-docx`
- Google Docs操作: `pip3 install google-api-python-client google-auth-httplib2 google-auth-oauthlib`

## 手順

### ステップ1: 入力確認

以下の優先順位で入力を判定する:

1. **PLAN.md を読む** — Google DocsのURL（`https://docs.google.com/document/d/...`）が記載されていればそちらを使用
2. **input/ フォルダを確認** — .docx ファイルがあればそちらを使用
3. **どちらもない場合** — ユーザーにURLまたはファイルの提供を依頼する

---

**A. Word文書（.docx）の場合:**
1. タスクフォルダの `input/` 内にある先方の契約書（.docx）を特定する
2. 複数ある場合はユーザーに確認する
3. 先方の契約書をpython3で読み取る（docxをテキスト抽出）:

```bash
python3 -c "
import zipfile, xml.etree.ElementTree as ET, sys
z = zipfile.ZipFile(sys.argv[1])
tree = ET.parse(z.open('word/document.xml'))
ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
for p in tree.findall('.//w:p', ns):
    texts = [t.text for t in p.findall('.//w:t', ns) if t.text]
    if texts:
        print(''.join(texts))
" "input/先方の契約書.docx"
```

**B. Google Docs URLの場合（PLAN.mdまたはユーザーから取得）:**
1. URLからドキュメントIDを抽出する
2. テキスト読み取り:

```bash
python3 .claude/skills/review-contract/apply_review_gdocs.py read "https://docs.google.com/document/d/{ID}/edit"
```

3. 出力されたテキストをレビューに使用する

**初回セットアップ（Google Docs利用時）:**
- Google Cloud ConsoleでOAuthクライアントID（デスクトップアプリ）を作成
- JSONを `~/.config/claude-gdocs-credentials.json` に配置
- 初回実行時にブラウザ認証が必要（トークンは `~/.config/claude-gdocs-token.json` に保存）

### ステップ2: 弊社ひな形の読み込み

`docs/contracts/業務委託基本契約書_雛形.md` を読み込む。

### ステップ3: レビュー実行

[REVIEW_CRITERIA.md](REVIEW_CRITERIA.md) の観点1〜6を**条番号の順番に**適用し、指摘事項を洗い出す。

### ステップ4: レビュー結果の確認（フィードバックループ）

review_items の内容をユーザーに提示し、以下を確認する:
- 指摘の妥当性
- リスクレベルの適切さ
- 不要な指摘の削除

修正があれば反映してからステップ5に進む。

### ステップ5: 指摘の整理とJSON出力

各指摘を以下のJSON形式でファイル出力する。ファイル名: `review_items.json`（タスクフォルダ直下）

```json
{
  "review_items": [
    {
      "article": "第○条",
      "article_title": "条文タイトル",
      "risk_level": "高 | 中 | 低",
      "category": "カテゴリ名",
      "original_text": "先方契約書の該当テキスト（段落内で部分一致検索できる程度の長さ。短すぎると誤マッチするため、前後の文脈を含めて20〜60文字程度）",
      "proposed_text": "変更後のテキスト（comment_onlyの場合は空文字列）",
      "comment": "先方に送るコメント（丁寧な表現で、変更理由を具体的に説明）",
      "issue_type": "modification | missing_clause | comment_only"
    }
  ]
}
```

**issue_typeの使い分け:**
- `modification`: 既存テキストを変更する場合（Track Changes + コメント）
- `missing_clause`: 先方に存在しない条項を追加提案する場合（文書末尾に挿入）
- `comment_only`: テキスト変更は不要だが注意喚起したい場合（コメントのみ）

**commentの書き方:**
- 先方の担当者が読むことを想定し、丁寧語で記載する
- **`comment` には `【高】`/`【中】` 等のリスクレベルや `第○条` などの機械的ラベルを含めない。**
  Word/Docs に挿入されるコメントは `comment` の文面そのままなので、ラベルが付くと「AIレビュー感」が出て不自然になる。
  リスクレベル（risk_level）・条番号（article）は JSON のフィールドとして持ち、Markdownレビュー結果の整理にのみ使う。
- 変更理由を法的根拠や商慣習に基づいて説明する
- 例: 「準委任契約においては成果物の完成義務は生じないため、本条項の「完成責任」という表現は契約の性質と齟齬が生じます。「善管注意義務をもって業務を遂行する」旨の表現への変更をお願いできれば幸いです。」

### ステップ6: Markdownレビュー結果の出力

`output/{ディレクトリ名}_レビュー結果.md` を作成する（例: `output/20260416-契約書レビュー_A社業務委託_レビュー結果.md`）。以下の形式:

```markdown
# 契約書レビュー結果

- 対象: {先方企業名 or ファイル名}
- レビュー日: {日付}
- レビュー元: 株式会社mijica 業務委託基本契約書ひな形

## サマリ

| リスク | 件数 |
|--------|------|
| 高 | X件 |
| 中 | X件 |
| 低 | X件 |

## 指摘事項

### 【高】第○条（条文タイトル）— カテゴリ

**現状:**
> 先方の該当テキスト

**変更案:**
> 変更後のテキスト

**先方へのコメント:**
コメント内容

---
（以下、条番号順に繰り返し）

## 不足条項

（弊社ひな形に存在し、先方に存在しない条項の一覧と追加提案）
```

### ステップ7: 文書への適用

入力形式に応じて適切なスクリプトを使用する:

**A. Word文書の場合:**

```bash
python3 .claude/skills/review-contract/apply_review.py \
  "input/{先方契約書ファイル名}.docx" \
  review_items.json \
  "output/{先方契約書ファイル名}_レビュー済.docx"
```

**注意:**
- Track Changesの適用はベストエフォート。Word内部でテキストが複数runに分割されている場合、一部適用できない可能性がある
- 適用できなかった指摘はログに表示される。Markdownのレビュー結果には全件含まれるため、そちらを正とする

**B. Google Docsの場合:**

```bash
python3 .claude/skills/review-contract/apply_review_gdocs.py apply \
  "https://docs.google.com/document/d/{ID}/edit" \
  review_items.json
```

**処理内容:**
- 元のドキュメントを同一フォルダ内に複製
- 複製したドキュメントのタイトル末尾に「YYYY/MM/DD 修正」を追加
- テキスト変更（modification）を直接適用し、コメントで変更理由を付記
- 不足条項（missing_clause）を文書末尾に挿入
- 全指摘にコメントを追加
- 修正済みドキュメントのURLを表示

**注意:**
- 初回実行時はブラウザ認証が必要
- Google Docs APIの制約上、Word文書のTrack Changesとは異なり直接編集＋コメントの形式で反映される

### ステップ8: 結果サマリの表示

レビュー結果のサマリをユーザーに表示する:
- リスク高の指摘件数と主要な指摘事項
- 不足条項の有無
- Word文書の生成結果（成功/一部失敗/スキップ）
- `output/` 内の生成ファイル一覧