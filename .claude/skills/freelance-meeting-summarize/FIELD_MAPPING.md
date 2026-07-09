# FreelanceBase 書き込みフィールドマッピング（v2）

Phase 0 の実地調査結果。テスト候補者 MJC80315672_TT（内部ID 3292）で全セクションを確認済み。

## URL 構造

- 一覧: `https://freelancebase.jp/enterprise/candidates#view-1`
- 候補者詳細: `https://freelancebase.jp/enterprise/candidates/{internal_id}#outline-tab`
  - `internal_id` は管理用ID（例 MJC80315672_TT）とは別の整数ID
  - 管理用ID → 内部ID の変換: 一覧の「クイック検索」に管理用IDを入れ、行の管理用IDセルをクリック→プレビュードロワーの「詳細を見る」ボタンを新タブで開いた URL から取得

## 編集ドロワー

- 候補者詳細の各セクションに「編集する」ボタン（合計 **8 個**）
- クリックすると右サイドに **ドロワー** が開く
  - セレクタ: `.modal_content.right-modal.right-open`（`right-open` があれば表示状態）
  - 注意: `.modal_content.right-modal.right-open` は **複数マッチし得る**（空のものが混ざる）。タイトルに `○○を編集` を含むドロワーで絞る
- ドロワー下部に「保存する」「キャンセル」ボタン
  - 保存: `button:has-text("保存する")`（クラス: `btn bg-primary size-40`）
  - キャンセル: `button:has-text("キャンセル")`

### 保存後の挙動（確認済み）

- 保存 API: `PUT https://freelancebase.jp/api/enterprise/candidates/update/{internal_id}`
- 成功時レスポンス: 200（約 0.2 秒で返却）
- **ドロワーは自動で閉じない** — 保存後に明示的に閉じる必要あり
- **可視のトーストなし**（標準セレクタでは検出不可）
- 実装方針: `page.expect_response(lambda r: "/api/enterprise/candidates/update/" in r.url and r.request.method == "PUT")` で成功判定

### 連続操作の注意

- `page.goto()` で **リロードすると Vue SPA の状態が壊れて、以降の編集するクリックが常に基本情報を開く不具合** が発生する
- 正しい運用: 1 度だけ遷移して、以降は **ドロワーをキャンセルで閉じる→次の編集するをクリック** を繰り返す

## 各ドロワーのフィールドマッピング

### 基本情報（inputs: 37）

| name | type | 選択肢 / placeholder |
|------|------|---------------------|
| `affiliation_type_id` | radio | 自社 / 他社 |
| `candidate_type_id` | radio | フリーランス / フリーランス(法人) / 正社員 / 契約社員 |
| `gender_id` | radio | 未回答 / 男性 / 女性 |
| `nationality_type_id` | radio | 日本籍 / 外国籍 |
| `station_id` | text (autocomplete) | 駅名を入力し選択 |
| `ekyc` | checkbox | 確認済 |
| `signed_contract` | checkbox | 基本契約書 / NDA |
| 管理用ID | text | ph=AE009878 |
| 氏名（姓/名） | text × 2 | ph=田中 / 太郎 |
| かな（セイ/メイ） | text × 2 | ph=たなか / たろう |
| 屋号名 | text | |
| 法人名 | text | |
| メールアドレス | text (必須) | ph=contact@freelancebase.jp |
| 電話番号 | text | ph=03-1111-1111 |
| 年齢 | number | |
| 郵便番号 | text | ph=1510062 |
| 住所（都道府県） | select | 60 件（地方区分含む） |
| 住所（市区町村） | text | ph=渋谷区元代々木町25-6 |
| ビル名 | text | |
| オンライン登録面談 録画URL | text | |
| 連絡手段 | text | |
| 社内向け情報 | textarea | |
| 緊急連絡先（続柄） | textarea | |

### 営業情報（inputs: 33）

**checkbox / radio 選択肢（value ↔ ラベル）**

- `contract_type_ids` (複数): 1=準委任契約 / 2=業務委託 / 3=派遣 / 4=契約社員 / 5=正社員
- `work_styles_ids` (複数): 1=常駐 / 3=フルリモート / 2=一部リモート可
- `business_day_ids` (複数): 5=週5日 / 4=週4日 / 3=週3日 / 2=週2日 / 1=週1日
- `possession_flg` (radio): 1=あり / 2=なし / 0=未選択

**その他のフィールド**

| ラベル | 型 | 備考 |
|-------|---|------|
| 稼働開始日 | select × 3（年/月/日） | |
| 営業終了日 | date | |
| 提案単価/月 | number | ph=700000 |
| 本人希望単価/月 | text × 2（範囲） | ph=450000 / 700000 |
| 商談可能日程 | text | ph=平日業務後18:00以降 |
| 先出し可否 | select | 0=未選択 / 1=先出しOK / 2=案件確認 |
| 商談可能時間帯 | select | 0=午前中 / 1=お昼~夕方 / 2=業務後 |
| 人材担当コメント | textarea | |

### スキル・経験情報（inputs: 107）

**大量の checkbox / radio**

- `occupation_ids` (複数, **68種類**): フロントエンド / バックエンド / サーバーサイド / アプリ / インフラ / ネットワーク / DB / セキュリティ / PM / PMO / PdM / プランナー / Webディレクター / ITコンサルタント / Webデザイナー / イラストレーター / 情報システム / 社内SE / Webマーケター / 汎用機 / AI / 機械学習 / ブロックチェーン / テクニカルサポート / 組込・制御 / ...（value=1-68）
- `dev_process_ids` (複数, **13種類**): 1=企画 / 2=要件定義 / 3=基本設計 / 4=詳細設計 / 5=実装 / 6=テスト / 7=運用・保守 / 8=デザイン / 9=コンサルティング / 10=ディレクション / 11=マネジメント / 12=データ分析 / 13=その他
- `industry_ids` (複数, **21種類**): 1=通信 / 2=ゲーム / 3=EC / 4=広告 / 5=Saas / 6=流通・小売 / 7=公共・官公庁 / 8=医療・福祉 / 9=SIer・業務系 / 10=銀行 / 11=証券 / 12=保険 / 13=エンタメ / 14=製造・メーカー / 15=toB / 16=toC / 17=WEBサービス / 18=サービス / 19=金融 / 20=人材 / 21=教育
- `searchFilter` (text): 言語・スキルを入力し選択

**テキスト系**

| ラベル | 型 | 備考 |
|-------|---|------|
| ポートフォリオ（URL） | text | ph=https://freelancebase.jp/ |
| Github（URL） | text | ph=https://github.com/ |
| スキル・経験サマリー | textarea | 長文。UI ラベルは「スキル・経験サマリー」（同セクション内の最初の textarea） |
| 保有資格 | textarea | UI ラベルは「保有資格」 |

### 希望条件（inputs: 4）

シンプルに textarea 4 つ:

- 希望の作業場所
- 希望の作業内容
- 希望の作業時間
- その他希望

### 管理情報（inputs: 27）

Phase 0 で取得済み（詳細は `sections_v3/管理情報.json` 参照）。v2 v1 サマリには直接対応する項目が少ないため、書き込み対象としては後回し。

## 実装時の注意まとめ

1. **UA 必須**: ヘッドレス Chromium でも User-Agent を設定しないと Cloudflare で 403 される（`snippets/playwright_freelancebase.py` で対応済み）
2. **リロード禁止**: 1 候補者で複数セクションを編集する場合、`page.goto()` のリロードは禁忌。**キャンセルで閉じる → 次の 編集する** を繰り返す
3. **ドロワー選択**: `.modal_content.right-modal.right-open` は複数マッチするので、`title が "{セクション名}を編集" を含む` で絞る
4. **セクションの特定**: `h6.fs-18` 見出し→ `ancestor::div[contains(@class,'row') and contains(@class,'align-items-center')][1]` を辿って同じ row 内の「編集する」ボタンを押す
5. **スクロール**: `btn.scroll_into_view_if_needed()` + `click(force=True)` で sticky ヘッダー競合を回避

## v1 サマリ → CRM 書き込みマッピング（設計メモ）

v1 サマリ Markdown の各項目を CRM のどのセクション/フィールドに書き込むか：

| v1 サマリ項目 | CRM セクション | CRM フィールド |
|-------------|-------------|-------------|
| 管理用ID | 基本情報 | 管理用ID（text） |
| 稼働形態 | 営業情報 | `work_styles_ids` |
| 性別 | 基本情報 | `gender_id` |
| 年齢 | 基本情報 | 年齢 |
| 国籍 | 基本情報 | `nationality_type_id` |
| 稼働開始日 | 営業情報 | 稼働開始日（select×3） |
| 最寄り駅 | 基本情報 | `station_id` |
| 経験職種 | スキル・経験情報 | `occupation_ids` |
| 担当工程 | スキル・経験情報 | `dev_process_ids` |
| [スキルシート] URL | 基本情報? | ポートフォリオURL？ （再確認必要） |
| [概要] | スキル・経験情報 | 経歴概要（textarea） |
| [経験スキル] | スキル・経験情報 | searchFilter（複数選択）+ 業種 industry_ids? |
| [特記事項] | 営業情報 | 人材担当コメント or 基本情報 社内向け情報 |
| 人材担当コメント | 営業情報 | 人材担当コメント（textarea） |
| 希望の作業場所 | 希望条件 | 希望の作業場所 |
| 希望の作業内容 | 希望条件 | 希望の作業内容 |
| 提案単価 | 営業情報 | 提案単価/月（number） |

## 残課題（Phase 0 完了後）

- [x] 基本情報 / 営業情報 / スキル・経験情報 / 希望条件 / 管理情報 の全ドロワー構造取得
- [ ] 振込先 / 適格請求書 / 支払情報の構造（v2 書き込み対象外なので優先度低）
- [ ] 「保存する」ボタン押下後の挙動（成功トースト・ドロワー自動閉じ・API レスポンス）の確認
- [ ] スキル・経験情報の `searchFilter`（autocomplete）の使い方と送信形式
- [ ] 基本情報の「住所（都道府県）」select のラベル↔value 対応（60件）
