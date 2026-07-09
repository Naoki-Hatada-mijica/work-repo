---
name: skillsheet-redesign
description: |
  PDFの職務経歴書・スキルシートを添付し、UIデザインを改善したPDFを自動生成するスキル。
  ユーザーがPDFファイルを添付して「スキルシートを整形」「UIを改善」「きれいにして」
  「リデザイン」「見やすくして」「書き換えて」などと言った場合にこのスキルを使う。
  職務経歴書、経歴書、スキルシート、履歴書に関するPDF整形リクエストには必ずこのスキルを使うこと。
---

# スキルシート リデザイン

PDFの職務経歴書（スキルシート）を読み取り、内容はそのままでモダンなUIデザインに書き換えたPDFを生成する。

## ワークフロー

### Step 1: PDFの読み取り

添付されたPDFを Read ツールで読み取り、以下の構造でデータを抽出する:

- 日付（例: 2026年7月）
- 基本情報（`personal_info` dict）:
  - `技術者コード`, `所属`, `稼動`, `性別`, `最寄駅`, `年齢`, `資格`, `学歴`
- 自己PR（`self_pr` string）: 改行は `\n` で区切る
- 技術サマリー（`tech_summary` list）:
  - `no`: 番号
  - `focus`: フォーカス領域
  - `detail`: 詳細テキスト
- プロジェクト一覧（各プロジェクトごとに以下を抽出）:
  - `period`: 期間（例: "2025年06月 〜 2026年05月（1年）"）
  - `company`: プロジェクト名
  - `content`: 業務内容
  - `phases`: 担当フェーズの配列
  - `techs`: 開発環境・技術スタックの配列
  - `members`: メンバー構成
  - `role`: 役割
  - `tasks`: 担当業務の配列
  - `extra_sections`: 可変セクションのリスト（なければ空配列）
    - `heading`: セクション見出し（例: "習得スキル・知識", "取り組み・実績（技術的な挑戦と成長）"）
    - `items`: 項目の配列

**重要**: テキストは元PDFから一言一句変更しないこと。UIの整形のみ行う。

### Step 2: フォントの準備

Google Fonts API から NotoSansJP の Regular / Bold をダウンロードする。
すでにスクラッチディレクトリにある場合はスキップ。

```bash
# Regular (weight 400)
curl -sL "https://fonts.gstatic.com/s/notosansjp/v56/-F6jfjtqLzI2JPCgQBnw7HFyzSD-AsregP8VFBEj75s.ttf" -o "$SCRATCH/NotoSansJP-Regular.ttf"
# Bold (weight 700)
curl -sL "https://fonts.gstatic.com/s/notosansjp/v56/-F6jfjtqLzI2JPCgQBnw7HFyzSD-AsregP8VFPYk75s.ttf" -o "$SCRATCH/NotoSansJP-Bold.ttf"
```

### Step 3: PDF生成スクリプトの実行

`scripts/generate_skillsheet.py` を使ってPDFを生成する。

スクリプトの使い方:
1. スクリプトを読み込む（Read ツールでこのスキルの `scripts/generate_skillsheet.py` を読む）
2. Step 1 で抽出したデータを Python のリテラルとしてスクリプト内の変数に埋め込む:
   - `personal_info`, `self_pr`, `tech_summary`, `projects`, `DOC_DATE`
3. 出力パスを設定（元PDFのパスに `_redesigned.pdf` を付けたもの）
4. `FONT_DIR` をフォントのあるディレクトリに設定
5. スクラッチディレクトリにスクリプトを書き出して `python3` で実行

プロジェクトは自動的に新しい順（開始日の降順）にソートされる。

### Step 4: 結果の確認

生成されたPDFを Read ツールで確認し、ユーザーに完了を報告する。
出力先のパスを伝えること。

## デザイン仕様

スクリプトに実装済みだが、概要は以下の通り:

- **配色**: ネイビー(#1e3a5f) + グレー系のみ。シンプルで落ち着いた印象
- **フォント**: NotoSansJP-Regular（本文）+ NotoSansJP-Bold（見出し・ラベル）
- **ヘッダー**: ネイビー背景に白文字「スキルシート」、右側に日付
- **セクション構成**: 基本情報 → 自己PR → 技術サマリー → 職務経歴
- **プロジェクト区切り**: グレーの水平線、各プロジェクト見出しに左ネイビーバー
- **担当フェーズ/開発環境**: pill型タグ（角丸背景 #e5e7eb、文字 #1f2937）
- **業務内容**: ラベルと本文を別行に、本文はインデント表示
- **担当業務/実績/習得スキル**: 「- 」付きリスト形式で統一
- **ラベル**: Bold 8pt、色 #6b7280
- **本文**: Regular 8.5-9pt、色 #111827
- **フッター**: ページ番号（N / 総数）、2パスで正確な総ページ数を算出
- **改ページ制御**: セクション見出しが孤立しないよう、見出し後に最低30mm以上のコンテンツ余裕を確保。職務経歴タイトルバーは最低70mm確保。
- **ソート**: プロジェクトは新しい順（開始日降順）に自動ソート
