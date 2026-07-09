---
name: contract-review-recruitment
description: 人材紹介契約書をレビューし、コメント・変更履歴付きWordファイルとMarkdownレビュー結果を出力する。人材紹介契約・有料職業紹介契約・紹介手数料契約の確認／レビューを行う場合に使用する。SES業務委託契約のレビューは contract-review スキルを使う。
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
- [ ] ステップ9: Google Drive へのアップロード（依頼があれば）
```

## 前提

- 株式会社mijicaは人材紹介（有料職業紹介）事業を営んでおり、**人材紹介契約では mijica は「乙＝紹介会社（成功報酬を受け取る側）」**の立場にある。
  - SES（準委任）の業務委託契約とは観点が異なる。SES契約のレビューは `contract-review` スキルを使う。
- 基本スタンス:
  - 成功報酬（手数料）を確実に確保したい（オーナーシップ／非循環条項、バックドア採用への手数料発生）。
  - 返金義務はできるだけ軽く・短く（自己都合退職に限定、解雇・会社都合は除外、返金期間/率を抑える）。
  - 損害賠償は上限（受領手数料額）を設定し、特別損害・間接損害・逸失利益は除外したい。
  - 過度な保証義務（労働条件の認識齟齬の保証等）は負いたくない。
  - 反社・秘密保持・個人情報・権利義務譲渡は双務（片務化を避ける）。
  - 合意管轄は東京。
- 弊社ひな形:
  - 基本契約書: `docs/contracts/人材紹介基本契約書_雛形.md`
  - 個別契約書（発注票）: `docs/contracts/人材紹介個別契約書_雛形.md`

### 依存パッケージ

- Word文書操作: `pip3 install python-docx lxml`
- Google Docs操作: `pip3 install google-api-python-client google-auth-httplib2 google-auth-oauthlib`

## 手順

### ステップ1: 入力確認

以下の優先順位で入力を判定する:

1. **PLAN.md を読む** — Google DocsのURL（`https://docs.google.com/document/d/...`）が記載されていればそちらを使用
2. **input/ フォルダを確認** — .docx / .doc ファイルがあればそちらを使用
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

**A'. 旧Word文書（.doc / application/msword）の場合:**
- 人材紹介契約書は旧 `.doc` 形式で渡されることがある。テキスト抽出と Track Changes 適用のため、まず `.docx` へ変換する。
- **`.docx` 変換は必ず `doc_to_docx.py` を使う（textutil 直叩き禁止）。**
  - textutil の .docx 変換は**条文の番号書式（numPr）・インデント・フォント指定を大きく失い**、
    Google Docs で開くとレイアウトが崩れる（実測: 番号書式 0 段落）。
  - `doc_to_docx.py` は忠実度の高い順に **LibreOffice → Google Drive ネイティブ変換 → textutil（最終手段）**
    を自動で試す。LibreOffice 不在の Mac でも Google 変換で番号書式・インデントが保持される（実測: 番号書式 46 段落）。

```bash
# テキスト抽出（レビュー分析用）— txt はレイアウト不問なので textutil で可
textutil -convert txt -output "input/先方の契約書.txt" "input/先方の契約書.doc"

# .docx へ高忠実度変換（Track Changes 適用用。apply_review.py は .docx が前提）
python3 .claude/skills/contract-review-recruitment/doc_to_docx.py \
  "input/先方の契約書.doc" "input/先方の契約書.docx"
```

- Google Drive 上の Office ファイル（.doc/.docx）は Docs API では読めない（`must not be an Office file` エラー）。
  Drive API の `files().get_media(fileId=..., supportsAllDrives=True)` でバイナリをダウンロードしてから上記で処理する
  （`~/.claude/snippets/google_workspace.py` の `get_drive_service()` を利用）。

**B. Google Docs URLの場合（PLAN.mdまたはユーザーから取得）:**
1. URLからドキュメントIDを抽出する
2. テキスト読み取り（ネイティブGoogleドキュメントの場合）:

```bash
python3 .claude/skills/contract-review-recruitment/apply_review_gdocs.py read "https://docs.google.com/document/d/{ID}/edit"
```

3. 出力されたテキストをレビューに使用する

**初回セットアップ（Google Docs利用時）:**
- Google Cloud ConsoleでOAuthクライアントID（デスクトップアプリ）を作成
- JSONを `~/.config/claude-gdocs-credentials.json` に配置
- 初回実行時にブラウザ認証が必要（トークンは `~/.config/claude-gdocs-token.json` に保存）

### ステップ2: 弊社ひな形の読み込み

`docs/contracts/人材紹介基本契約書_雛形.md` と `docs/contracts/人材紹介個別契約書_雛形.md` を読み込む。
冒頭の「要点サマリ」で基準値（料率40%・返金90日50%・賠償上限あり等）を把握する。

### ステップ3: レビュー実行

[REVIEW_CRITERIA.md](REVIEW_CRITERIA.md) の観点1〜9を**条番号の順番に**適用し、指摘事項を洗い出す。

### ステップ4: レビュー結果の確認（フィードバックループ）

review_items の内容をユーザーに提示し、以下を確認する:
- 指摘の妥当性
- リスクレベルの適切さ
- 不要な指摘の削除（料率など商談判断に委ねる事項は「指摘」ではなく「参考情報」に留めるか確認）

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
- `missing_clause`: 先方に存在しない条項を追加提案する場合（文書末尾／署名ブロック前に挿入）
- `comment_only`: テキスト変更は不要だが注意喚起したい場合（コメントのみ）
- `direct_fill`: **提案モードではない確定記入**（Track Changes なし・コメントなし）。
  自社（乙＝株式会社mijica）の当事者名・署名欄を埋めるのに使う。詳細は後述「自社情報の記入（direct_fill）」。

### 自社情報の記入（direct_fill）

人材紹介契約では mijica が「乙」になる。先方書式は乙の当事者名・署名欄が空欄のことが多いので、
**提案（変更履歴）ではなく確定記入**で自社情報を埋める（自社情報は交渉対象ではないため）。
`issue_type: "direct_fill"` を使う。Track Changes もコメントも付かず、本文を直接書き換える。
`proposed_text` に改行（`\n`）を含めると、1行目は該当箇所へ直接置換、2行目以降は書式を引き継いだ段落として直後に挿入する（署名欄の社名・代表者行に対応）。

**mijica の固定情報:**
- 当事者名: `株式会社mijica`
- 署名欄:
  ```
  東京都渋谷区代官山町8-7 Daiwa代官山ビル
  株式会社mijica
  代表取締役社長　赤木　宏志
  ```

**標準の direct_fill 項目（先方書式に合わせて original_text を調整する）:**
```json
{
  "article": "甲乙の表示",
  "category": "当事者",
  "original_text": "（以下、「乙」という。）",
  "proposed_text": "株式会社mijica（以下、「乙」という。）",
  "comment": "",
  "issue_type": "direct_fill"
},
{
  "article": "署名欄（乙）",
  "category": "署名",
  "original_text": "乙：",
  "proposed_text": "乙：東京都渋谷区代官山町8-7 Daiwa代官山ビル\n\t\t\t\t\t株式会社mijica\n\t\t\t\t\t代表取締役社長　赤木　宏志",
  "comment": "",
  "issue_type": "direct_fill"
}
```
- `original_text` は先方書式の実テキストから一意にマッチするものを選ぶ（乙の社名直後の `（以下、「乙」という。）`、署名欄の `乙：` など）。
- 署名欄の社名・代表者行のインデントは、甲側の署名行に合わせてタブ（例 `\t\t\t\t\t`）を調整する。

**commentの書き方:**
- 先方の担当者が読むことを想定し、丁寧語で記載する
- **`comment` には `【高】`/`【中】` 等のリスクレベルや `第○条` などの機械的ラベルを含めない。**
  Word/Docs に挿入されるコメントは `comment` の文面そのままなので、ラベルが付くと「AIレビュー感」が出て不自然になる。
  リスクレベル（risk_level）・条番号（article）は JSON のフィールドとして持ち、Markdownレビュー結果の整理にのみ使う。
- 変更理由を法的根拠や商慣習に基づいて説明する
- 例（返金規定）: 「人材紹介の商慣習上、貴社都合による解雇については返金の対象外とすることが一般的です。解雇は弊社の役務（紹介）の瑕疵に起因するものではないため、返金事由を『自己都合退職』に限定いただけますと幸いです。」
- 例（賠償上限）: 「弊社の責に帰すべき事由による損害については誠実に対応いたしますが、予測可能性の観点から、損害賠償の総額を本件成功報酬額を上限とする旨を明記させていただけますと幸いです（故意・重過失の場合を除く）。」

### ステップ6: Markdownレビュー結果の出力

`output/{ディレクトリ名}_レビュー結果.md` を作成する。以下の形式:

```markdown
# 人材紹介契約書レビュー結果

- 対象: {先方企業名 or ファイル名}
- レビュー日: {日付}
- レビュー元: 株式会社mijica 人材紹介基本契約書ひな形（mijica＝乙＝紹介会社）

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

## 参考情報（商談判断に委ねる事項）

（料率水準など、修正指摘ではなく商談で判断すべき事項）
```

### ステップ7: 文書への適用

入力形式に応じて適切なスクリプトを使用する:

**A. Word文書の場合:**

```bash
python3 .claude/skills/contract-review-recruitment/apply_review.py \
  "input/{先方契約書ファイル名}.docx" \
  review_items.json \
  "output/{先方契約書ファイル名}_レビュー済.docx"
```

**注意:**
- `.doc` の場合はステップ1のA'で `doc_to_docx.py` を使って `.docx` に変換してから適用する
  （textutil 直変換だとレイアウトが崩れる）
- Track Changesの適用はベストエフォート。Word内部でテキストが複数runに分割されている場合、一部適用できない可能性がある
- 適用できなかった指摘はログに表示される。Markdownのレビュー結果には全件含まれるため、そちらを正とする

**B. Google Docsの場合:**

```bash
python3 .claude/skills/contract-review-recruitment/apply_review_gdocs.py apply \
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

### ステップ8: 結果サマリの表示

レビュー結果のサマリをユーザーに表示する:
- リスク高の指摘件数と主要な指摘事項
- 不足条項の有無
- Word文書の生成結果（成功/一部失敗/スキップ）
- `output/` 内の生成ファイル一覧

### ステップ9: Google Drive へのアップロード（依頼があれば）

レビュー済み `.docx` を**元の契約書と同じ Drive フォルダ**へアップロードする運用がある。

- アップロードは `.docx` のまま行う（Google ドキュメントへ変換しない）。Google Docs の Office 互換モードで
  変更履歴・コメントがそのまま表示・編集できる。
- アップロード先フォルダは、元契約書ファイルの `parents` から取得する。
- 差し替え時は旧アップロードを `files().delete(fileId=..., supportsAllDrives=True)` で削除する。

```python
import sys; sys.path.insert(0, "~/.claude/snippets".replace("~", __import__("os").path.expanduser("~")))
from google_workspace import get_drive_service
from googleapiclient.http import MediaFileUpload

svc = get_drive_service()
folder_id = "<元契約書の parents から取得したフォルダID>"
src = "output/{先方契約書ファイル名}_レビュー済.docx"
meta = {"name": "【mijicaレビュー済】...（変更履歴・コメント入り）.docx", "parents": [folder_id]}
media = MediaFileUpload(src, mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document", resumable=True)
f = svc.files().create(body=meta, media_body=media, fields="id,webViewLink", supportsAllDrives=True).execute()
print(f["webViewLink"])
```
