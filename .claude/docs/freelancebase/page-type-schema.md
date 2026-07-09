# FreelanceBase Page-Type Schema Catalog

- generated_at: `2026-06-08T03:44:19`
- page_types: `19`
- blocked_write_requests: `0`
- mode: non-destructive Playwright probe; save/post/delete/publish/status-change final actions were not clicked

This catalog is grouped by page type. Concrete record pages are sampled once where needed and normalized to `{id}` patterns.

## Summary

| Page Type | Route | Source | List | List Columns | Create | Detail Fields | Update | Delete UI | Write-like UI | Write API | Omitted Options |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 応募 | `/enterprise/applies` | known | yes | 25 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 合算請求書 | `/enterprise/billing_merges` | known | yes | 9 | 0 | 1 | 0 | 0 | 1 | 0 | 0 |
| 請求・支払 | `/enterprise/billing_payments` | known | yes | 29 | 0 | 2 | 0 | 0 | 1 | 0 | 0 |
| 稼働 | `/enterprise/contract_operations` | known | yes | 18 | 0 | 1 | 0 | 0 | 0 | 0 | 0 |
| 契約 | `/enterprise/contracts` | known | yes | 31 | 1 | 0 | 1 | 0 | 0 | 0 | 3 |
| 人材 | `/enterprise/candidates` | known | yes | 14 | 1 | 0 | 1 | 0 | 0 | 0 | 0 |
| 企業 | `/enterprise/companies` | known | yes | 12 | 1 | 0 | 1 | 0 | 0 | 0 | 2 |
| 企業担当者 | `/enterprise/company_members` | known | yes | 12 | 1 | 0 | 1 | 0 | 0 | 0 | 3 |
| 案件 | `/enterprise/jobs` | known | yes | 11 | 1 | 0 | 1 | 0 | 0 | 0 | 6 |
| 商談 | `/enterprise/opportunities` | known | yes | 14 | 1 | 1 | 1 | 0 | 0 | 0 | 5 |
| 記事 | `/enterprise/articles` | known | yes | 10 | 1 | 7 | 0 | 0 | 0 | 0 | 4 |
| 自動化 | `/enterprise/automation_emails#new-tab` | known | yes | 4 | 1 | 1 | 0 | 0 | 2 | 0 | 2 |
| 配信 | `/enterprise/broadcasts#all-tab` | known | yes | 10 | 1 | 1 | 0 | 0 | 0 | 0 | 0 |
| フォーム | `/enterprise/questionnaire_forms` | known | yes | 10 | 1 | 1 | 0 | 0 | 0 | 0 | 0 |
| 案件サイト | `/enterprise/sites#contents-tab_mainvisual-menu` | known | yes | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 |
| 提案 | `/enterprise/restrictions/proposals` | known | no | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 担当別レポート | `/enterprise/report_billing_payments` | known | yes | 12 | 0 | 2 | 0 | 0 | 0 | 0 | 0 |
| 商談レポート | `/enterprise/report_opportunities` | known | yes | 12 | 0 | 2 | 0 | 0 | 0 | 0 | 0 |
| レポート | `/enterprise/report_summaries/contract` | known | yes | 13 | 0 | 3 | 0 | 0 | 0 | 0 | 0 |

## 応募

- route: `/enterprise/applies`
- navigated: `/enterprise/applies#view-8`
- source: `known` / category: `apply`

### CRUD / API

- create triggers: none
- update triggers: none
- delete triggers: none
- write-like actions: none
- row link patterns: none
- observed API:
  - `POST /api/enterprise/view_settings/index` status=200
  - `POST /api/enterprise/applies/index` status=200

### List

- table columns:
  - `応募ID`, `人材ID`, `新規/既存`, `氏名`, `応募日時`, `応募経路`, `応募案件`, `かな`, `メールアドレス`, `電話番号`, `生年月日`, `年齢`, `都道府県`, `人材タイプ`, `現在の状況`, `職種`, `経験業界`, `スキル`, `稼働形態`, `稼働可能日数`, `稼働開始日`, `本人希望最高単価/月 （単位：円）`, `本人希望最低単価/月 （単位：円）`, `連絡が取りやすい 時間帯`, `希望の作業内容`

| Label | Control | Name | Flags | Options |
|---|---|---|---|---|
| 合計件数 | select | `` | - | `ページあたり10件`, `ページあたり30件`, `ページあたり50件`, `ページあたり100件` |

### Detail

- notes: Error: detail probe failed

- fields: none visible


## 合算請求書

- route: `/enterprise/billing_merges`
- navigated: `/enterprise/billing_merges#view-10`
- source: `known` / category: `contract`
- sampled detail page type: `/enterprise/billing_merges`

### CRUD / API

- create triggers: none
- update triggers: none
- delete triggers: none
- write-like actions: 合算請求候補を抽出
- row link patterns: none
- observed API:
  - `POST /api/enterprise/view_settings/index` status=200
  - `POST /api/enterprise/billing_merges/index` status=200

### List

- table columns:
  - `合算請求書ID`, `合算請求書番号`, `メール送付ステータス (合算請求書)`, `メール送付日時 (合算請求書)`, `請求月`, `請求先`, `合算請求金額`, `合算請求書 発行日`, `支払期限 (売上->自)`

| Label | Control | Name | Flags | Options |
|---|---|---|---|---|
| 合計件数 | select | `` | - | `ページあたり10件`, `ページあたり30件`, `ページあたり50件`, `ページあたり100件` |

### Detail

- table columns:
  - `合算請求書ID`, `合算請求書番号`, `メール送付ステータス (合算請求書)`, `メール送付日時 (合算請求書)`, `請求月`, `請求先`, `合算請求金額`, `合算請求書 発行日`, `支払期限 (売上->自)`

- detail labels:
  - `合算請求書ID`, `合算請求書番号`, `メール送付ステータス (合算請求書)`, `メール送付日時 (合算請求書)`, `請求月`, `請求先`, `合算請求金額`, `合算請求書 発行日`, `支払期限 (売上->自)`

| Label | Control | Name | Flags | Options |
|---|---|---|---|---|
| 合計件数 | select | `` | - | `ページあたり10件`, `ページあたり30件`, `ページあたり50件`, `ページあたり100件` |


## 請求・支払

- route: `/enterprise/billing_payments`
- navigated: `/enterprise/billing_payments#view-7`
- source: `known` / category: `contract`
- sampled detail page type: `/enterprise/billing_payments`

### CRUD / API

- create triggers: none
- update triggers: none
- delete triggers: none
- write-like actions: 合算請求候補を抽出
- row link patterns: none
- observed API:
  - `POST /api/enterprise/view_settings/index` status=200
  - `POST /api/enterprise/billing_payments/index` status=200

### List

- table columns:
  - `請求・支払ID`, `契約ID`, `稼働ID`, `稼働ステータス`, `提出物ステータス`, `請求ステータス`, `支払ステータス`, `計上月`, `稼働開始日`, `稼働終了日`, `請求書番号`, `支払通知書番号`, `契約件名`, `請求先`, `作業者`, `提出物`, `稼働時間`, `請求金額`, `支払期限 (売上→自)`, `自社担当者（請求先）`, `メール送付 ステータス(請求書)`, `メール送付日 (請求書)`, `仕入先タイプ`, `支払先`, `支払金額`, `支払期限 (自→仕入)`, `自社担当者（仕入先）`, `メール送付 ステータス(支払通知書)`, `メール送付日 (支払通知書)`

| Label | Control | Name | Flags | Options |
|---|---|---|---|---|
| 詳細フィルター | input | `` | - | none |
| 合計件数 | select | `` | - | `ページあたり10件`, `ページあたり30件`, `ページあたり50件`, `ページあたり100件` |

### Detail

- table columns:
  - `請求・支払ID`, `契約ID`, `稼働ID`, `稼働ステータス`, `提出物ステータス`, `請求ステータス`, `支払ステータス`, `計上月`, `稼働開始日`, `稼働終了日`, `請求書番号`, `支払通知書番号`, `契約件名`, `請求先`, `作業者`, `提出物`, `稼働時間`, `請求金額`, `支払期限 (売上→自)`, `自社担当者（請求先）`, `メール送付 ステータス(請求書)`, `メール送付日 (請求書)`, `仕入先タイプ`, `支払先`, `支払金額`, `支払期限 (自→仕入)`, `自社担当者（仕入先）`, `メール送付 ステータス(支払通知書)`, `メール送付日 (支払通知書)`

- detail labels:
  - `請求・支払ID`, `契約ID`, `稼働ID`, `稼働ステータス`, `提出物ステータス`, `請求ステータス`, `支払ステータス`, `計上月`, `稼働開始日`, `稼働終了日`, `請求書番号`, `支払通知書番号`, `契約件名`, `請求先`, `作業者`, `提出物`, `稼働時間`, `請求金額`, `支払期限 (売上→自)`, `自社担当者（請求先）`, `メール送付 ステータス(請求書)`, `メール送付日 (請求書)`, `仕入先タイプ`, `支払先`, `支払金額`, `支払期限 (自→仕入)`, `自社担当者（仕入先）`, `メール送付 ステータス(支払通知書)`, `メール送付日 (支払通知書)`

| Label | Control | Name | Flags | Options |
|---|---|---|---|---|
| 詳細フィルター | input | `` | - | none |
| 合計件数 | select | `` | - | `ページあたり10件`, `ページあたり30件`, `ページあたり50件`, `ページあたり100件` |


## 稼働

- route: `/enterprise/contract_operations`
- navigated: `/enterprise/contract_operations#view-6`
- source: `known` / category: `contract`
- sampled detail page type: `/enterprise/contract_operations`

### CRUD / API

- create triggers: none
- update triggers: none
- delete triggers: none
- write-like actions: none
- row link patterns: none
- observed API:
  - `POST /api/enterprise/view_settings/index` status=200
  - `POST /api/enterprise/contract_operations/index` status=200

### List

- table columns:
  - `稼働ID`, `契約ID`, `請求・支払ID`, `稼働ステータス`, `提出物ステータス`, `稼働月`, `稼働開始日`, `稼働終了日`, `契約開始日`, `契約終了日`, `案件参画日`, `稼働時間`, `提出物`, `売上先`, `自社担当者(売上先)`, `仕入先`, `稼働者`, `自社担当者(仕入先)`

| Label | Control | Name | Flags | Options |
|---|---|---|---|---|
| 合計件数 | select | `` | - | `ページあたり10件`, `ページあたり30件`, `ページあたり50件`, `ページあたり100件` |

### Detail

- table columns:
  - `稼働ID`, `契約ID`, `請求・支払ID`, `稼働ステータス`, `提出物ステータス`, `稼働月`, `稼働開始日`, `稼働終了日`, `契約開始日`, `契約終了日`, `案件参画日`, `稼働時間`, `提出物`, `売上先`, `自社担当者(売上先)`, `仕入先`, `稼働者`, `自社担当者(仕入先)`

- detail labels:
  - `稼働ID`, `契約ID`, `請求・支払ID`, `稼働ステータス`, `提出物ステータス`, `稼働月`, `稼働開始日`, `稼働終了日`, `契約開始日`, `契約終了日`, `案件参画日`, `稼働時間`, `提出物`, `売上先`, `自社担当者(売上先)`, `仕入先`, `稼働者`, `自社担当者(仕入先)`

| Label | Control | Name | Flags | Options |
|---|---|---|---|---|
| 合計件数 | select | `` | - | `ページあたり10件`, `ページあたり30件`, `ページあたり50件`, `ページあたり100件` |


## 契約

- route: `/enterprise/contracts`
- navigated: `/enterprise/contracts#view-5`
- source: `known` / category: `contract`
- sampled detail page type: `/enterprise/contracts/{id}`

### CRUD / API

- create triggers: 契約を作成
- update triggers: none
- delete triggers: none
- write-like actions: none
- row link patterns: none
- observed API:
  - `POST /api/enterprise/view_settings/index` status=200
  - `POST /api/enterprise/contracts/index` status=200
  - `POST /api/enterprise/enterprise_members/index` status=200
  - `GET /api/enterprise/enterprise_document_settings/show` status=200
  - `POST /api/enterprise/opportunities/index` status=200
  - `POST /api/enterprise/view_settings/index` status=200
  - `POST /api/enterprise/contracts/index` status=200
  - `POST /api/enterprise/comment_contracts/index` status=200
  - `GET /api/enterprise/candidates/show/{id}` status=200
  - `GET /api/enterprise/file_attachments/index/Contract/{id}` status=200
  - `POST /api/enterprise/contracts/index` status=200
  - `POST /api/enterprise/contract_operations/index` status=200
  - `POST /api/enterprise/billing_payments/index` status=200
  - `GET /api/enterprise/enterprise_document_settings/show` status=200

### List

- table columns:
  - `契約ID`, `契約番号`, `契約ステータス`, `契約件名`, `契約タイプ`, `契約形態`, `契約開始日`, `契約終了日`, `自社担当者(売上先)`, `自社担当者(仕入先)`, `売上先`, `住所(売上先)`, `企業担当者(売上先)`, `所属`, `仕入先`, `人材タイプ`, `作業者`, `住所(仕入先)`, `企業担当者(仕入先)`, `売上単価`, `精算方法(売上先)`, `超過単価(売上先)`, `控除単価(売上先)`, `仕入単価`, `精算方法(仕入先)`, `超過単価(仕入先)`, `控除単価(仕入先)`, `支払いサイト_締め日(売上先)`, `支払いサイト_締め日(仕入先)`, `備考(売上先)`, `備考(仕入先)`

| Label | Control | Name | Flags | Options |
|---|---|---|---|---|
| 詳細フィルター | input | `` | - | none |
| 合計件数 | select | `` | - | `ページあたり10件`, `ページあたり30件`, `ページあたり50件`, `ページあたり100件` |

### Detail

- table columns:
  - `契約件名`
  - `売上先`
  - `企業名`
  - `企業担当者(売上先)`
  - `提出物提出期限`

- detail labels:
  - `契約件名`, `契約形態`, `契約期間`, `作業場所`, `提出物`, `売上先`, `住所(売上先)`, `売上単価`, `精算方法(売上先)`, `超過単価(売上先)`, `控除単価(売上先)`, `支払いサイト_締め日(売上先)`, `備考(売上先)`, `特別精算`, `特記事項(売上先)`, `企業名`, `作業者`, `住所(仕入先)`, `仕入単価`, `精算方法(仕入先)`, `超過単価(仕入先)`, `控除単価(仕入先)`, `支払いサイト_締め日(仕入先)`, `備考(仕入先)`, `特記事項(仕入先)`, `企業担当者(売上先)`, `自社担当者(売上先)`, `企業担当者(仕入先)`, `自社担当者(仕入先)`, `契約終了理由`, `粗利(税別)`, `前日リマインド`, `入場連絡`, `作業報告書フォーマット`, `提出物提出期限`, `提出物提出期限_備考`, `請求書提出期限`, `請求書提出期限_備考`, `支払通知書提出期限`, `支払通知書提出期限_備考`, `支援費`, `支援費備考`, `提出物ファイル名自動変更`, `成果物自動回収`

- fields: none visible

### Create 1: `契約を作成`

| Label | Control | Name | Flags | Options |
|---|---|---|---|---|
| 契約形態 必須 | select | `` | - | `準委任契約` |
| 商談と紐付け | custom-select | `opportunity_id_by_enterprise_id` | - | omitted: dynamic live-data field (50 options) |
| 新規 | radio | `group_id` | - | `新規`, `更新` |

### Update 1: `編集する`

| Label | Control | Name | Flags | Options |
|---|---|---|---|---|
| 企業担当者(売上先) | input | `sales_company_member_id_by_enterprise_id` | - | none |
| 自社担当者(売上先) | select | `` | - | omitted: dynamic live-data field (11 options) |
| 企業担当者(仕入先) | input | `supplier_company_member_id_by_enterprise_id` | - | none |
| 自社担当者(仕入先) | select | `` | - | omitted: dynamic live-data field (11 options) |
| 契約終了理由 | textarea | `` | - | none |
| 円 | input/number | `` | - | none |
| 仕入元パートナー | radio | `report_format` | - | `仕入元パートナー`, `mijica`, `上位会社 or 現場` |


## 人材

- route: `/enterprise/candidates`
- navigated: `/enterprise/candidates#view-1`
- source: `known` / category: `core`
- sampled detail page type: `/enterprise/candidates/{id}`

### CRUD / API

- create triggers: 人材を作成
- update triggers: none
- delete triggers: none
- write-like actions: none
- row link patterns: none
- observed API:
  - `POST /api/enterprise/view_settings/index` status=200
  - `POST /api/enterprise/candidates/index` status=200
  - `POST /api/enterprise/enterprise_members/index` status=200
  - `GET /api/enterprise/candidate_resumes/index/{id}` status=200
  - `POST /api/enterprise/applies/index` status=200
  - `POST /api/enterprise/opportunities/index` status=200
  - `POST /api/enterprise/candidates/shared_info_text_preview` status=200
  - `GET /api/enterprise/comment_candidates/index/{id}` status=200

### List

- table columns:
  - `管理用ID`, `人材ID`, `年齢`, `メールアドレス`, `電話番号`, `スキルタグ`, `作成日時`, `更新日時`, `自社担当者1`, `自社担当者2`, `所属企業`, `集客ステータス`, `営業ステータス`, `メイン振込先`

| Label | Control | Name | Flags | Options |
|---|---|---|---|---|
| 詳細フィルター | input | `` | - | none |
| 合計件数 | select | `` | - | `ページあたり10件`, `ページあたり30件`, `ページあたり50件`, `ページあたり100件` |

### Detail

- table columns:
  - `人材タイプ`
  - `契約形態`
  - `経験職種`
  - `希望の作業場所`
  - `集客ステータス`
  - `メイン振込先`
  - `適格請求書発行事業者 登録番号`
  - `支払通知書メール送付先(Cc)`
  - `緊急連絡先`
  - `OpenSES`

- detail labels:
  - `人材タイプ`, `管理用ID`, `氏名`, `かな`, `屋号名`, `法人名`, `メールアドレス`, `電話番号`, `生年月日`, `年齢`, `性別`, `国籍`, `住所`, `最寄り駅`, `現在の状況`, `社内向け情報`, `連絡手段`, `オンライン登録面談 録画URL`, `締結済み契約書`, `eKYC`, `緊急連絡先（続柄）`, `契約形態`, `稼働形態`, `稼働日数`, `稼働開始日`, `提案単価/月（単位：円）`, `本人希望最高単価/月（単位：円）`, `本人希望最低単価/月（単位：円）`, `営業開始日`, `商談可能日程`, `人材担当コメント`, `独占営業`, `独占営業期間`, `提案方法`, `連絡が取りやすい時間帯`, `営業終了日`, `経験職種`, `担当工程`, `経験業界`, `スキル・経験サマリー`, `スキルタグ`, `保有資格`, `経歴書・スキルシート`, `ポートフォリオ（URL）`, `Github（URL）`, `希望の作業場所`, `希望の作業内容`, `希望の作業時間`, `その他希望`, `集客ステータス`, `営業ステータス`, `掘り起こし`, `人材ランク`, `作成経路`, `自社担当者1`, `自社担当者2`, `営業種別`, `流入経路`, `稼働ステータス`, `メイン振込先`, `適格請求書発行事業者 登録番号`, `支払通知書メール送付先(Cc)`, `緊急連絡先`, `OpenSES`, `掲載URL`, `公開状況`

- fields: none visible

### Create 1: `人材を作成 > 通常作成`

| Label | Control | Name | Flags | Options |
|---|---|---|---|---|
| メールアドレス 必須 | input/text | `` | - | none |
| 氏名 必須 | input/text | `` | - | none |
| 氏名 必須 | input/text | `` | - | none |
| かな | input/text | `` | - | none |
| かな | input/text | `` | - | none |
| 自社 | radio | `affiliation_type_id` | - | `自社`, `他社` |

### Update 1: `編集する`

| Label | Control | Name | Flags | Options |
|---|---|---|---|---|
| 管理用ID | input/text | `` | - | none |
| 氏名 必須 | input/text | `` | - | none |
| 氏名 必須 | input/text | `` | - | none |
| かな | input/text | `` | - | none |
| かな | input/text | `` | - | none |
| 屋号名 | input/text | `` | - | none |
| 法人名 | input/text | `` | - | none |
| メールアドレス 必須 | input/text | `` | - | none |
| 電話番号 | input/text | `` | - | none |
| 生年月日 | select | `` | - | 年 ... 2008年 (60 options) |
| 生年月日 | select | `` | - | `月`, `1月`, `2月`, `3月`, `4月`, `5月`, `6月`, `7月`, `8月`, `9月`, `10月`, `11月`, `12月` |
| 生年月日 | select | `` | - | 日 ... 31日 (32 options) |
| 年齢 | input/number | `` | - | none |
| 住所 | input | `nationality_id` | - | none |
| 郵便番号 | input/text | `` | - | none |
| 都道府県 | select | `` | - | `北海道`, `青森県`, `岩手県`, `宮城県`, `秋田県`, `山形県`, `福島県`, `茨城県`, `栃木県`, `群馬県`, `埼玉県`, `千葉県`, `東京都`, `神奈川県`, `新潟県`, `富山県`, `石川県`, `福井県`, `山梨県`, `長野県`, `岐阜県`, `静岡県`, `愛知県`, `三重県`, `滋賀県`, `京都府`, `大阪府`, `兵庫県`, `奈良県`, `和歌山県` ... (48 options) |
| 住所 | input/text | `` | - | none |
| ビル名 | input/text | `` | - | none |
| 最寄駅 | input | `station_id` | - | none |
| 現在の状況 | select | `` | - | `フリーランス`, `正社員`, `契約社員`, `派遣社員`, `アルバイト`, `無職`, `その他` |
| 社内向け情報 | textarea | `` | - | none |
| 緊急連絡先（続柄） | textarea | `` | - | none |
| オンライン登録面談 録画URL | input/text | `` | - | none |
| 連絡手段 | input/text | `` | - | none |
| 自社 | radio | `affiliation_type_id` | - | `自社`, `他社` |
| フリーランス | radio | `candidate_type_id` | - | `フリーランス`, `フリーランス(法人)`, `正社員`, `契約社員` |
| 未回答 | radio | `gender_id` | - | `未回答`, `男性`, `女性` |
| 日本籍 | radio | `nationality_type_id` | - | `日本籍`, `外国籍` |


## 企業

- route: `/enterprise/companies`
- navigated: `/enterprise/companies#view-2`
- source: `known` / category: `core`
- sampled detail page type: `/enterprise/companies/{id}`

### CRUD / API

- create triggers: 企業を作成
- update triggers: none
- delete triggers: none
- write-like actions: none
- row link patterns: none
- observed API:
  - `POST /api/enterprise/enterprise_members/index` status=200
  - `POST /api/enterprise/view_settings/index` status=200
  - `POST /api/enterprise/companies/index` status=200
  - `POST /api/enterprise/enterprise_members/index` status=200
  - `GET /api/enterprise/file_attachments/index/Company/{id}` status=200
  - `GET /api/enterprise/comment_companies/index/{id}` status=200

### List

- table columns:
  - `企業名`, `企業ID`, `企業タイプ`, `作成日時`, `更新日時`, `自社担当者1`, `自社担当者2`, `企業ランク`, `注力ランク`, `募集中案件数`, `企業ステータス`, `社内向け情報`

| Label | Control | Name | Flags | Options |
|---|---|---|---|---|
| 詳細フィルター | input | `` | - | none |
| 合計件数 | select | `` | - | `ページあたり10件`, `ページあたり30件`, `ページあたり50件`, `ページあたり100件` |

### Detail

- table columns:
  - `企業タイプ`
  - `企業ステータス`
  - `請求書メール送付先(To)`
  - `支払通知書メール送付先(To)`
  - `メイン振込先`
  - `適格請求書発行事業者 登録番号`

- detail labels:
  - `企業タイプ`, `企業名`, `ホームページ`, `お問い合わせ`, `電話番号`, `FAX番号`, `設立`, `代表者名`, `所在地`, `最寄駅`, `事業概要`, `就業時間`, `企業の特徴`, `社内向け情報`, `オンライン打ち合わせ 録画URL`, `締結済み契約書`, `企業ステータス`, `企業ランク`, `注力ランク`, `自社担当者1`, `自社担当者2`, `獲得経路`, `請求書メール送付先(To)`, `請求書メール送付先(Cc)`, `請求書メール件名`, `請求書メール本文`, `支払通知書メール送付先(To)`, `支払通知書メール送付先(Cc)`, `支払通知書メール件名`, `支払通知書メール本文`, `メイン振込先`, `適格請求書発行事業者 登録番号`

- fields: none visible

### Create 1: `企業を作成`

| Label | Control | Name | Flags | Options |
|---|---|---|---|---|
| 企業名 必須 | input/text | `` | - | none |
| ホームページ | input/text | `` | - | none |
| お問い合わせ | input/text | `` | - | none |
| 電話番号 | input/text | `` | - | none |
| FAX番号 | input/text | `` | - | none |
| 設立 | select | `` | - | 年 ... 2026年 (108 options) |
| 設立 | select | `` | - | `月`, `1月`, `2月`, `3月`, `4月`, `5月`, `6月`, `7月`, `8月`, `9月`, `10月`, `11月`, `12月` |
| 設立 | select | `` | - | 日 ... 31日 (32 options) |
| 代表者名 | input/text | `` | - | none |
| 郵便番号 | input/text | `` | - | none |
| 都道府県 | select | `` | - | `北海道`, `青森県`, `岩手県`, `宮城県`, `秋田県`, `山形県`, `福島県`, `茨城県`, `栃木県`, `群馬県`, `埼玉県`, `千葉県`, `東京都`, `神奈川県`, `新潟県`, `富山県`, `石川県`, `福井県`, `山梨県`, `長野県`, `岐阜県`, `静岡県`, `愛知県`, `三重県`, `滋賀県`, `京都府`, `大阪府`, `兵庫県`, `奈良県`, `和歌山県` ... (48 options) |
| 住所 | input/text | `` | - | none |
| ビル名 | input/text | `` | - | none |
| 最寄駅 | input | `station_id` | - | none |
| 事業概要 | textarea | `` | - | none |
| 就業時間 | input/text | `` | - | none |
| 社内向け情報 | textarea | `` | - | none |
| 企業ステータス | select | `` | - | `未選択`, `開拓対象`, `アプローチ中`, `打ち合わせ済`, `提案可能`, `契約書締結`, `取引可能`, `接触NG`, `営業不可`, `取引停止`, `無効` |
| 自社担当者1 | select | `` | - | omitted: dynamic live-data field (11 options) |
| 自社担当者2 | select | `` | - | omitted: dynamic live-data field (11 options) |
| 未選択 | radio | `company_rank_id` | - | `未選択`, `A`, `B`, `C`, `D`, `E` |
| 未選択 | radio | `company_sales_rank_id` | - | `未選択`, `A`, `B`, `C`, `D`, `E` |

### Update 1: `編集する`

| Label | Control | Name | Flags | Options |
|---|---|---|---|---|
| 企業名 必須 | input/text | `` | - | none |
| ホームページ | input/text | `` | - | none |
| お問い合わせ | input/text | `` | - | none |
| 電話番号 | input/text | `` | - | none |
| FAX番号 | input/text | `` | - | none |
| 設立 | select | `` | - | 年 ... 2026年 (108 options) |
| 設立 | select | `` | - | `月`, `1月`, `2月`, `3月`, `4月`, `5月`, `6月`, `7月`, `8月`, `9月`, `10月`, `11月`, `12月` |
| 設立 | select | `` | - | 日 ... 31日 (32 options) |
| 代表者名 | input/text | `` | - | none |
| 郵便番号 | input/text | `` | - | none |
| 都道府県 | select | `` | - | `北海道`, `青森県`, `岩手県`, `宮城県`, `秋田県`, `山形県`, `福島県`, `茨城県`, `栃木県`, `群馬県`, `埼玉県`, `千葉県`, `東京都`, `神奈川県`, `新潟県`, `富山県`, `石川県`, `福井県`, `山梨県`, `長野県`, `岐阜県`, `静岡県`, `愛知県`, `三重県`, `滋賀県`, `京都府`, `大阪府`, `兵庫県`, `奈良県`, `和歌山県` ... (48 options) |
| 住所 | input/text | `` | - | none |
| ビル名 | input/text | `` | - | none |
| 最寄駅 | input | `station_id` | - | none |
| 事業概要 | textarea | `` | - | none |
| 就業時間 | input/text | `` | - | none |
| 社内向け情報 | textarea | `` | - | none |
| オンライン打ち合わせ 録画URL | input/text | `` | - | none |


## 企業担当者

- route: `/enterprise/company_members`
- navigated: `/enterprise/company_members#view-9`
- source: `known` / category: `core`
- sampled detail page type: `/enterprise/company_members/{id}`

### CRUD / API

- create triggers: 企業担当者を作成
- update triggers: none
- delete triggers: none
- write-like actions: none
- row link patterns: none
- observed API:
  - `POST /api/enterprise/enterprise_members/index` status=200
  - `POST /api/enterprise/view_settings/index` status=200
  - `POST /api/enterprise/company_members/index` status=200
  - `POST /api/enterprise/companies/search` status=200
  - `GET /api/enterprise/file_attachments/index/CompanyMember/{id}` status=200

### List

- table columns:
  - `氏名`, `企業担当者ID`, `所属企業`, `担当者ステータス`, `メールアドレス`, `電話番号`, `部署`, `役職`, `自社担当者1`, `自社担当者2`, `作成日`, `更新日`

| Label | Control | Name | Flags | Options |
|---|---|---|---|---|
| 詳細フィルター | input | `` | - | none |
| 合計件数 | select | `` | - | `ページあたり10件`, `ページあたり30件`, `ページあたり50件`, `ページあたり100件` |

### Detail

- table columns:
  - `氏名`
  - `担当者ステータス`

- detail labels:
  - `氏名`, `メールアドレス`, `電話番号`, `所属企業`, `部署`, `役職`, `担当者ステータス`, `自社担当者1`, `自社担当者2`

- fields: none visible

### Create 1: `企業担当者を作成`

| Label | Control | Name | Flags | Options |
|---|---|---|---|---|
| 所属企業 必須 | custom-select | `company_id_by_enterprise_id` | - | omitted: dynamic live-data field (101 options) |
| 氏名 必須 | input/text | `` | - | none |
| 氏名 必須 | input/text | `` | - | none |
| メールアドレス | input/text | `` | - | none |
| 電話番号 | input/text | `` | - | none |
| 部署 | input/text | `` | - | none |
| 役職 | input/text | `` | - | none |
| 自社担当者1 | select | `` | - | omitted: dynamic live-data field (11 options) |
| 自社担当者2 | select | `` | - | omitted: dynamic live-data field (11 options) |
| 有効 | radio | `company_member_status_id` | - | `有効`, `無効` |

### Update 1: `編集する`

| Label | Control | Name | Flags | Options |
|---|---|---|---|---|
| 氏名 必須 | input/text | `` | - | none |
| 氏名 必須 | input/text | `` | - | none |
| メールアドレス | input/text | `` | - | none |
| 電話番号 | input/text | `` | - | none |
| 部署 | input/text | `` | - | none |
| 役職 | input/text | `` | - | none |


## 案件

- route: `/enterprise/jobs`
- navigated: `/enterprise/jobs#view-3`
- source: `known` / category: `core`
- sampled detail page type: `/enterprise/jobs/{id}`

### CRUD / API

- create triggers: 案件を作成
- update triggers: none
- delete triggers: none
- write-like actions: none
- row link patterns: none
- observed API:
  - `POST /api/enterprise/enterprise_members/index` status=200
  - `POST /api/enterprise/view_settings/index` status=200
  - `POST /api/enterprise/jobs/index` status=200
  - `POST /api/enterprise/companies/search` status=200
  - `POST /api/enterprise/company_members/index` status=200
  - `POST /api/enterprise/enterprise_members/index` status=200
  - `GET /api/enterprise/companies/show/{id}` status=200
  - `POST /api/enterprise/jobs/shared_info_text_preview` status=200
  - `POST /api/enterprise/opportunities/index` status=200
  - `GET /api/enterprise/comment_jobs/index/{id}` status=200

### List

- table columns:
  - `案件名`, `管理用ID`, `案件ID`, `案件元企業`, `作成日時`, `更新日時`, `自社担当者1`, `自社担当者2`, `募集状況`, `公開状況`, `案件ランク`

| Label | Control | Name | Flags | Options |
|---|---|---|---|---|
| 詳細フィルター | input | `` | - | none |
| 合計件数 | select | `` | - | `ページあたり10件`, `ページあたり30件`, `ページあたり50件`, `ページあたり100件` |

### Detail

- table columns:
  - `案件元企業`
  - `案件タイプ`
  - `掲載URL`
  - `フリーランスボード`

- detail labels:
  - `案件元企業`, `案件元企業担当者`, `管理用ID`, `案件名`, `URL`, `職種`, `担当工程`, `業界`, `案件の内容`, `募集背景`, `求めるスキル`, `歓迎スキル`, `開発環境`, `スキルタグ`, `稼働日数`, `売最高単価/月（単位：円）`, `売最低単価/月（単位：円）`, `仕入れ最高単価/月（単位：円）`, `仕入れ最低単価/月（単位：円）`, `精算方法`, `支払いサイト_締め日`, `商談`, `開始時期`, `契約期間`, `募集人数`, `チーム規模`, `稼働形態`, `案件の特徴`, `案件担当のコメント`, `都道府県`, `最寄駅`, `作業開始/終了時間の目安`, `平均稼働時間`, `現場の雰囲気`, `商流制限`, `希望する年齢層`, `外国籍`, `PC貸与`, `服装規定`, `社内向け情報`, `案件タイプ`, `案件ランク`, `自社担当者1`, `自社担当者2`, `掲載URL`, `募集状況`, `公開状況`, `フリーランスボード`, `フリーランススタート`, `OpenSES`, `所在地`, `設立`, `代表者名`, `電話番号`, `FAX番号`, `ホームページ`, `お問い合わせ`, `事業概要`, `企業タイプ`, `企業ランク`, `注力ランク`, `企業ステータス`

- fields: none visible

### Create 1: `案件を作成 > 通常作成`

| Label | Control | Name | Flags | Options |
|---|---|---|---|---|
| 案件元企業 必須 社内向け | custom-select | `company_id_by_enterprise_id` | - | omitted: dynamic live-data field (103 options) |
| 案件元企業担当者 社内向け | custom-select | `company_member_id_by_enterprise_id` | - | omitted: dynamic live-data field (154 options) |
| 管理用ID | input/text | `` | - | none |
| 案件名 必須 サイト掲載 | input/text | `` | - | none |
| 案件の内容 必須 サイト掲載 | textarea | `` | - | none |
| 募集背景 サイト掲載 | textarea | `` | - | none |
| 求めるスキル 必須 サイト掲載 | textarea | `` | - | none |
| 歓迎スキル サイト掲載 | textarea | `` | - | none |
| 開発環境 サイト掲載 | textarea | `` | - | none |
| 情報から一括追加 | custom-select | `searchFilter` | - | omitted: large non-static option set (174 options) |
| 商談 必須 サイト掲載 | input/text | `` | - | none |
| ~ | input/price | `` | - | none |
| ~ | input/price | `` | - | none |
| ~ | input/price | `` | - | none |
| ~ | input/price | `` | - | none |
| 精算タイプ | select | `` | - | `上下割`, `上割`, `中割`, `下割` |
| ~ | input/number | `` | - | none |
| ~ | input/number | `` | - | none |
| 精算基準単位 | select | `` | - | `10円未満切り捨て` |
| 支払い | select | `` | - | `当月末締め` |
| 支払い | select | `` | - | `翌月`, `翌々月` |
| 支払い | select | `` | - | `末日`, `5日`, `10日`, `15日`, `25日`, `20日` |
| 商談 必須 サイト掲載 | input/text | `` | - | none |
| 開始時期 サイト掲載 | select | `` | - | `年`, `2021年`, `2022年`, `2023年`, `2024年`, `2025年`, `2026年`, `2027年`, `2028年`, `2029年`, `2030年`, `2031年` |
| 開始時期 サイト掲載 | select | `` | - | `月`, `1月`, `2月`, `3月`, `4月`, `5月`, `6月`, `7月`, `8月`, `9月`, `10月`, `11月`, `12月` |
| 開始時期 サイト掲載 | select | `` | - | 日 ... 31日 (32 options) |
| 契約期間 | input/text | `` | - | none |
| 人 | input/number | `` | - | none |
| 案件担当のコメント サイト掲載 | textarea | `` | - | none |
| 都道府県 サイト掲載 | select | `` | - | `北海道`, `青森県`, `岩手県`, `宮城県`, `秋田県`, `山形県`, `福島県`, `茨城県`, `栃木県`, `群馬県`, `埼玉県`, `千葉県`, `東京都`, `神奈川県`, `新潟県`, `富山県`, `石川県`, `福井県`, `山梨県`, `長野県`, `岐阜県`, `静岡県`, `愛知県`, `三重県`, `滋賀県`, `京都府`, `大阪府`, `兵庫県`, `奈良県`, `和歌山県` ... (48 options) |
| 最寄駅 | custom-select | `station_id` | - | omitted: large non-static option set (174 options) |
| 作業開始/終了時間の目安 サイト掲載 | input/text | `` | - | none |
| 平均稼働時間 サイト掲載 | input/text | `` | - | none |
| 現場の雰囲気 サイト掲載 | textarea | `` | - | none |
| 商談 必須 サイト掲載 | input/text | `` | - | none |
| ~ | input/text | `` | - | none |
| ~ | input/text | `` | - | none |
| 商談 必須 サイト掲載 | input/text | `` | - | none |
| 商談 必須 サイト掲載 | input/text | `` | - | none |
| 商談 必須 サイト掲載 | input/text | `` | - | none |
| 商談 必須 サイト掲載 | input/text | `` | - | none |
| 社内向け情報 社内向け | textarea | `` | - | none |
| 自社担当者1 社内向け | select | `` | - | omitted: dynamic live-data field (11 options) |
| 自社担当者2 社内向け | select | `` | - | omitted: dynamic live-data field (11 options) |
| 時間幅 | radio | `adjustment_flg` | - | `時間幅`, `固定精算` |
| 1回 | radio | `communications_time_id` | - | `1回`, `2回`, `その他` |
| オンライン | radio | `communications_way_id` | - | `オンライン`, `対面` |
| 未選択 | radio | `dev_scale_id` | - | `未選択`, `1名`, `2-5名`, `6-10名`, `11-20名`, `21-30名`, `31名以上` |
| 常駐 | radio | `work_styles_id` | - | `常駐`, `フルリモート`, `一部リモート可` |
| 指定なし | radio | `resale_restriction_type_id` | - | `指定なし`, `自社直`, `1社下まで` |
| 未設定 | radio | `accept_foreigner_type_id` | - | `未設定`, `外国籍OK`, `外国籍NG` |
| 未設定 | radio | `pc_loan_type_id` | - | `未設定`, `あり`, `なし` |
| 未設定 | radio | `dresscode_type_id` | - | `未設定`, `あり`, `なし` |
| エンド | radio | `company_type_id` | - | `エンド`, `元請け`, `パートナー`, `その他` |
| 未選択 | radio | `job_rank_id` | - | `未選択`, `A`, `B`, `C`, `D`, `E` |
| 募集中 | radio | `application_status_flg` | - | `募集中`, `募集停止` |
| 公開中 | radio | `open_status_flg` | - | `公開中`, `非公開` |
| 募集中 | radio | `application_status_fb_flg` | - | `募集中`, `募集停止` |
| 公開中 | radio | `open_status_fb_flg` | - | `公開中`, `非公開` |
| 募集中 | radio | `application_status_fs_flg` | - | `募集中`, `募集停止` |
| 公開中 | radio | `open_status_fs_flg` | - | `公開中`, `非公開` |
| 募集中 | radio | `application_status_os_flg` | - | `募集中`, `募集停止` |
| 公開中 | radio | `open_status_os_flg` | - | `公開中`, `非公開` |

### Update 1: `編集する`

| Label | Control | Name | Flags | Options |
|---|---|---|---|---|
| 案件元企業 必須 社内向け | input | `company_id_by_enterprise_id` | - | none |
| 案件元企業担当者 社内向け | input | `company_member_id_by_enterprise_id` | - | none |
| 管理用ID | input/text | `` | - | none |
| 案件名 必須 サイト掲載 | input/text | `` | - | none |
| 案件の内容 必須 サイト掲載 | textarea | `` | - | none |
| 募集背景 サイト掲載 | textarea | `` | - | none |
| 求めるスキル 必須 サイト掲載 | textarea | `` | - | none |
| 歓迎スキル サイト掲載 | textarea | `` | - | none |
| 開発環境 サイト掲載 | textarea | `` | - | none |
| 情報から一括追加 | input | `searchFilter` | - | none |
| 商談 必須 サイト掲載 | input/text | `` | - | none |
| ~ | input/price | `` | - | none |
| ~ | input/price | `` | - | none |
| ~ | input/price | `` | - | none |
| ~ | input/price | `` | - | none |
| 精算タイプ | select | `` | - | `上下割`, `上割`, `中割`, `下割` |
| ~ | input/number | `` | - | none |
| ~ | input/number | `` | - | none |
| 精算基準単位 | select | `` | - | `10円未満切り捨て` |
| 支払い | select | `` | - | `当月末締め` |
| 支払い | select | `` | - | `翌月`, `翌々月` |
| 支払い | select | `` | - | `末日`, `5日`, `10日`, `15日`, `25日`, `20日` |
| 商談 必須 サイト掲載 | input/text | `` | - | none |
| 開始時期 サイト掲載 | select | `` | - | `年`, `2021年`, `2022年`, `2023年`, `2024年`, `2025年`, `2026年`, `2027年`, `2028年`, `2029年`, `2030年`, `2031年` |
| 開始時期 サイト掲載 | select | `` | - | `月`, `1月`, `2月`, `3月`, `4月`, `5月`, `6月`, `7月`, `8月`, `9月`, `10月`, `11月`, `12月` |
| 開始時期 サイト掲載 | select | `` | - | 日 ... 31日 (32 options) |
| 契約期間 | input/text | `` | - | none |
| 人 | input/number | `` | - | none |
| 案件担当のコメント サイト掲載 | textarea | `` | - | none |
| 都道府県 サイト掲載 | select | `` | - | `北海道`, `青森県`, `岩手県`, `宮城県`, `秋田県`, `山形県`, `福島県`, `茨城県`, `栃木県`, `群馬県`, `埼玉県`, `千葉県`, `東京都`, `神奈川県`, `新潟県`, `富山県`, `石川県`, `福井県`, `山梨県`, `長野県`, `岐阜県`, `静岡県`, `愛知県`, `三重県`, `滋賀県`, `京都府`, `大阪府`, `兵庫県`, `奈良県`, `和歌山県` ... (48 options) |
| 最寄駅 | input | `station_id` | - | none |
| 作業開始/終了時間の目安 サイト掲載 | input/text | `` | - | none |
| 平均稼働時間 サイト掲載 | input/text | `` | - | none |
| 現場の雰囲気 サイト掲載 | textarea | `` | - | none |
| 商談 必須 サイト掲載 | input/text | `` | - | none |
| ~ | input/text | `` | - | none |
| ~ | input/text | `` | - | none |
| 商談 必須 サイト掲載 | input/text | `` | - | none |
| 商談 必須 サイト掲載 | input/text | `` | - | none |
| 商談 必須 サイト掲載 | input/text | `` | - | none |
| 商談 必須 サイト掲載 | input/text | `` | - | none |
| 社内向け情報 社内向け | textarea | `` | - | none |
| 時間幅 | radio | `adjustment_flg` | - | `時間幅`, `固定精算` |
| 1回 | radio | `communications_time_id` | - | `1回`, `2回`, `その他` |
| オンライン | radio | `communications_way_id` | - | `オンライン`, `対面` |
| 未選択 | radio | `dev_scale_id` | - | `未選択`, `1名`, `2-5名`, `6-10名`, `11-20名`, `21-30名`, `31名以上` |
| 常駐 | radio | `work_styles_id` | - | `常駐`, `フルリモート`, `一部リモート可` |
| 指定なし | radio | `resale_restriction_type_id` | - | `指定なし`, `自社直`, `1社下まで` |
| 未設定 | radio | `accept_foreigner_type_id` | - | `未設定`, `外国籍OK`, `外国籍NG` |
| 未設定 | radio | `pc_loan_type_id` | - | `未設定`, `あり`, `なし` |
| 未設定 | radio | `dresscode_type_id` | - | `未設定`, `あり`, `なし` |


## 商談

- route: `/enterprise/opportunities`
- navigated: `/enterprise/opportunities#view-4`
- source: `known` / category: `core`
- sampled detail page type: `/enterprise/opportunities/{id}`

### CRUD / API

- create triggers: 商談を作成
- update triggers: none
- delete triggers: none
- write-like actions: none
- row link patterns: none
- observed API:
  - `GET /api/enterprise/model_settings/show/opportunity` status=200
  - `POST /api/enterprise/view_settings/index` status=200
  - `POST /api/enterprise/opportunities/index` status=200
  - `POST /api/enterprise/companies/search` status=200
  - `POST /api/enterprise/jobs/search` status=200
  - `POST /api/enterprise/candidates/index` status=200
  - `POST /api/enterprise/enterprise_members/index` status=200
  - `GET /api/enterprise/comment_opportunities/index/{id}` status=200
  - `GET /api/enterprise/log_opportunities/index/{id}` status=200

### List

- table columns:
  - `提案先企業`, `案件`, `提案人材`, `商談ID`, `仕入先`, `商談状況`, `商談結果`, `商談確度`, `売り提案単価`, `仕入提案単価`, `自社担当者1`, `自社担当者2`, `作成日時`, `更新日時`

| Label | Control | Name | Flags | Options |
|---|---|---|---|---|
| 詳細フィルター | input | `` | - | none |
| 合計件数 | select | `` | - | `ページあたり10件`, `ページあたり30件`, `ページあたり50件`, `ページあたり100件` |

### Detail

- table columns:
  - `提案先企業`
  - `商談確度`

- detail labels:
  - `提案先企業`, `案件`, `提案人材`, `売り提案単価`, `仕入提案単価`, `商談確度`, `自社担当者1`, `自社担当者2`

| Label | Control | Name | Flags | Options |
|---|---|---|---|---|
| 成約を確定 | select | `` | - | `案件紹介`, `提案`, `1次商談依頼`, `1次商談`, `1次商談結果待ち`, `最終商談依頼`, `最終商談`, `最終商談結果待ち`, `オファー`, `オファー承諾`, `成約` |

### Create 1: `商談を作成`

| Label | Control | Name | Flags | Options |
|---|---|---|---|---|
| 提案先企業 必須 | custom-select | `company_id_by_enterprise_id` | - | omitted: dynamic live-data field (101 options) |
| 案件 | custom-select | `job_id_by_enterprise_id` | - | omitted: dynamic live-data field (102 options) |
| 提案人材 必須 | custom-select | `candidate_id_by_enterprise_id` | - | omitted: dynamic live-data field (199 options) |
| 円 | input/number | `` | - | none |
| 円 | input/number | `` | - | none |
| 商談確度 | select | `` | - | `未選択`, `A`, `B`, `C`, `D`, `E` |
| 自社担当者1 | select | `` | - | omitted: dynamic live-data field (11 options) |
| 自社担当者2 | select | `` | - | omitted: dynamic live-data field (11 options) |
| 自社 | radio | `candidate_affiliation_type_id` | - | `自社`, `他社` |

### Update 1: `編集する`

| Label | Control | Name | Flags | Options |
|---|---|---|---|---|
| 提案先企業 必須 | input | `company_id_by_enterprise_id` | - | none |
| 案件 | input | `job_id_by_enterprise_id` | - | none |
| 提案人材 必須 | input | `candidate_id_by_enterprise_id` | - | none |
| 円 | input/number | `` | - | none |
| 円 | input/number | `` | - | none |
| 自社 | radio | `candidate_affiliation_type_id` | - | `自社`, `他社` |


## 記事

- route: `/enterprise/articles`
- navigated: `/enterprise/articles`
- source: `known` / category: `marketing`
- sampled detail page type: `/enterprise/articles/form#outline`

### CRUD / API

- create triggers: 記事を作成
- update triggers: none
- delete triggers: none
- write-like actions: none
- row link patterns: none
- observed API:
  - `POST /api/enterprise/articles/index` status=200
  - `POST /api/enterprise/articles/index` status=200
  - `GET /api/enterprise/site_setting_drafts/show` status=200
  - `POST /api/enterprise/article_categories/index` status=200
  - `POST /api/enterprise/article_tags/search` status=200
  - `POST /api/enterprise/articles/index` status=200
  - `GET /api/enterprise/site_setting_drafts/show` status=200
  - `GET /api/enterprise/article_drafts/show/{id}` status=200
  - `POST /api/enterprise/article_categories/index` status=200
  - `POST /api/enterprise/article_tags/search` status=200

### List

- table columns:
  - `ID`, `キービジュアル`, `タイトル`, `文字数`, `初回公開日`, `最終公開日時`, `下書き最終更新`, `予約公開日時`, `公開ステータス`, `公開URL`

| Label | Control | Name | Flags | Options |
|---|---|---|---|---|
| 下書き公開中公開予約中公開停止中 | input | `` | - | none |
| 合計件数 | select | `` | - | `ページあたり10件`, `ページあたり30件`, `ページあたり50件`, `ページあたり100件` |

### Detail

| Label | Control | Name | Flags | Options |
|---|---|---|---|---|
| タイトル | input/text | `` | - | none |
| カテゴリ | select | `` | - | `キャリア`, `スキル`, `ノウハウ` |
| タグ | custom-select | `searchFilter` | - | omitted: contains non-catalog text (70 options) |
| メタ ディスクリプション | textarea | `` | - | none |
| メタ キーワード | input/text | `` | - | none |
| 関連する案件カテゴリページ | select | `` | - | `スキル`, `職種` |
| 概要 記事本文 | custom-select | `recommend_jobs_master_id` | - | omitted: dynamic live-data field (77 options) |

### Create 1: `記事を作成`

| Label | Control | Name | Flags | Options |
|---|---|---|---|---|
| タイトル | input/text | `` | - | none |
| カテゴリ | select | `` | - | `キャリア`, `スキル`, `ノウハウ` |
| タグ | custom-select | `searchFilter` | - | omitted: contains non-catalog text (70 options) |
| メタ ディスクリプション | textarea | `` | - | none |
| メタ キーワード | input/text | `` | - | none |
| 関連する案件カテゴリページ | select | `` | - | `スキル`, `職種` |
| 概要 記事本文 | custom-select | `recommend_jobs_master_id` | - | omitted: dynamic live-data field (77 options) |


## 自動化

- route: `/enterprise/automation_emails#new-tab`
- navigated: `/enterprise/automation_emails#new-tab`
- source: `known` / category: `marketing`
- sampled detail page type: `/enterprise/automation_emails#new-tab`

### CRUD / API

- create triggers: 条件を新規作成
- update triggers: none
- delete triggers: none
- write-like actions: 公開する, 処理順を編集
- row link patterns: none
- observed API:
  - `POST /api/enterprise/automation_email_drafts/index` status=200
  - `POST /api/enterprise/enterprise_members/index` status=200
  - `POST /api/enterprise/questionnaire_forms/index` status=200
  - `POST /api/enterprise/enterprise_members/index` status=200
  - `POST /api/enterprise/automation_email_drafts/index` status=200
  - `POST /api/enterprise/automation_email_drafts/index` status=200

### List

- table columns:
  - `処理順`, `管理用タイトル`, `最終編集日時`, `ON/OFF`

| Label | Control | Name | Flags | Options |
|---|---|---|---|---|
| 合計件数 | select | `` | - | `ページあたり10件`, `ページあたり30件`, `ページあたり50件`, `ページあたり100件` |

### Detail

- table columns:
  - `処理順`, `管理用タイトル`, `最終編集日時`, `ON/OFF`

- detail labels:
  - `処理順`, `管理用タイトル`, `最終編集日時`, `ON/OFF`

| Label | Control | Name | Flags | Options |
|---|---|---|---|---|
| 合計件数 | select | `` | - | `ページあたり10件`, `ページあたり30件`, `ページあたり50件`, `ページあたり100件` |

### Create 1: `条件を新規作成`

| Label | Control | Name | Flags | Options |
|---|---|---|---|---|
| ~ | input/number | `` | - | none |
| ~ | input/number | `` | - | none |
| 経験・スキル | custom-select | `searchFilter` | - | omitted: contains non-catalog text (20 options) |
| 配信アドレス 必須 | select | `` | - | omitted: contains non-catalog text (9 options) |
| メール件名 必須 | input/text | `` | - | none |
| フォーム | textarea | `` | - | none |
| 管理用タイトル | input/text | `` | - | none |
| ON | radio | `open_flg` | - | `ON`, `OFF` |


## 配信

- route: `/enterprise/broadcasts#all-tab`
- navigated: `/enterprise/broadcasts#all-tab`
- source: `known` / category: `marketing`
- sampled detail page type: `/enterprise/broadcasts#all-tab`

### CRUD / API

- create triggers: 配信を作成
- update triggers: none
- delete triggers: none
- write-like actions: none
- row link patterns: none
- observed API:
  - `POST /api/enterprise/broadcasts/index` status=200
  - `POST /api/enterprise/custom_properties/index` status=200
  - `POST /api/enterprise/custom_properties/index` status=200
  - `POST /api/enterprise/enterprise_members/index` status=200
  - `POST /api/enterprise/enterprise_members/index` status=200
  - `POST /api/enterprise/questionnaire_forms/index` status=200
  - `POST /api/enterprise/enterprise_members/index` status=200
  - `POST /api/enterprise/view_settings/index` status=200
  - `POST /api/enterprise/view_settings/index` status=200
  - `POST /api/enterprise/jobs/index` status=200
  - `POST /api/enterprise/candidates/index` status=200
  - `POST /api/enterprise/broadcasts/preview` status=200
  - `POST /api/enterprise/broadcasts/index` status=200

### List

- table columns:
  - `配信ID`, `管理用タイトル`, `件名`, `配信対象`, `配信者名`, `配信アドレス`, `作成日`, `配信日`, `配信数`, `開封UU数`

| Label | Control | Name | Flags | Options |
|---|---|---|---|---|
| 合計件数 | select | `` | - | `ページあたり10件`, `ページあたり30件`, `ページあたり50件`, `ページあたり100件` |

### Detail

- table columns:
  - `配信ID`, `管理用タイトル`, `件名`, `配信対象`, `配信者名`, `配信アドレス`, `作成日`, `配信日`, `配信数`, `開封UU数`

- detail labels:
  - `配信ID`, `管理用タイトル`, `件名`, `配信対象`, `配信者名`, `配信アドレス`, `作成日`, `配信日`, `配信数`, `開封UU数`

| Label | Control | Name | Flags | Options |
|---|---|---|---|---|
| 合計件数 | select | `` | - | `ページあたり10件`, `ページあたり30件`, `ページあたり50件`, `ページあたり100件` |

### Create 1: `配信を作成 > 3 配信内容作成`

- table columns:
  - `管理用ID`, `人材ID`, `年齢`, `メールアドレス`, `電話番号`, `スキルタグ`, `作成日時`, `更新日時`, `自社担当者1`, `自社担当者2`, `所属企業`, `集客ステータス`, `営業ステータス`, `メイン振込先`

| Label | Control | Name | Flags | Options |
|---|---|---|---|---|
| 詳細フィルター | input | `` | - | none |
| 合計件数 | select | `` | - | `ページあたり10件`, `ページあたり30件`, `ページあたり50件`, `ページあたり100件` |


## フォーム

- route: `/enterprise/questionnaire_forms`
- navigated: `/enterprise/questionnaire_forms`
- source: `known` / category: `marketing`
- sampled detail page type: `/enterprise/questionnaire_forms`

### CRUD / API

- create triggers: フォームを作成
- update triggers: none
- delete triggers: none
- write-like actions: none
- row link patterns: none
- observed API:
  - `POST /api/enterprise/enterprise_members/index` status=200
  - `POST /api/enterprise/custom_properties/index` status=200

### List

- table columns:
  - `フォームID`, `管理用フォーム名`, `公開用フォーム名`, `有効/無効`, `作成者`, `送信通知アドレス`, `回答数`, `リリース日`, `更新日`, `作成日`

| Label | Control | Name | Flags | Options |
|---|---|---|---|---|
| 合計件数 | select | `` | - | `ページあたり10件`, `ページあたり30件`, `ページあたり50件`, `ページあたり100件` |

### Detail

- table columns:
  - `フォームID`, `管理用フォーム名`, `公開用フォーム名`, `有効/無効`, `作成者`, `送信通知アドレス`, `回答数`, `リリース日`, `更新日`, `作成日`

- detail labels:
  - `フォームID`, `管理用フォーム名`, `公開用フォーム名`, `有効/無効`, `作成者`, `送信通知アドレス`, `回答数`, `リリース日`, `更新日`, `作成日`

| Label | Control | Name | Flags | Options |
|---|---|---|---|---|
| 合計件数 | select | `` | - | `ページあたり10件`, `ページあたり30件`, `ページあたり50件`, `ページあたり100件` |

### Create 1: `フォームを作成`

| Label | Control | Name | Flags | Options |
|---|---|---|---|---|
| フォームを作成 項目 オプション 終了 保存する リリース | input | `` | - | none |


## 案件サイト

- route: `/enterprise/sites#contents-tab_mainvisual-menu`
- navigated: `/enterprise/sites#contents-tab_mainvisual-menu`
- source: `known` / category: `marketing`

### CRUD / API

- create triggers: none
- update triggers: 保存
- delete triggers: none
- write-like actions: 保存, 公開する
- row link patterns: none
- observed API:
  - `POST /api/enterprise/enterprise_images/index` status=200

### List

| Label | Control | Name | Flags | Options |
|---|---|---|---|---|
| 1行目※15文字以内 | input/text | `` | - | none |
| 2行目※15文字以内 | input/text | `` | - | none |
| 3行目※15文字以内 | input/text | `` | - | none |
| 1行目※20文字以内 | input/text | `` | - | none |
| 2行目※20文字以内 | input/text | `` | - | none |
| 3行目※20文字以内 | input/text | `` | - | none |

### Detail

- notes: no row available

- fields: none visible


## 提案

- route: `/enterprise/restrictions/proposals`
- navigated: `/enterprise/restrictions/proposals`
- source: `known` / category: `proposal`

### CRUD / API

- create triggers: none
- update triggers: none
- delete triggers: none
- write-like actions: none
- row link patterns: none
- observed API:
  - none

### List

- fields: none visible

### Detail

- notes: no row available

- fields: none visible


## 担当別レポート

- route: `/enterprise/report_billing_payments`
- navigated: `/enterprise/report_billing_payments`
- source: `known` / category: `report`
- sampled detail page type: `/enterprise/report_billing_payments`

### CRUD / API

- create triggers: none
- update triggers: none
- delete triggers: none
- write-like actions: none
- row link patterns: none
- observed API:
  - `POST /api/enterprise/report_billing_payments/index` status=200
  - `POST /api/enterprise/report_billing_payments/index` status=200

### List

- table columns:
  - `2025-08`, `2025-09`, `2025-10`, `2025-11`, `2025-12`, `2026-01`, `2026-02`, `2026-03`, `2026-04`, `2026-05`, `2026-06`, `2026-07`

| Label | Control | Name | Flags | Options |
|---|---|---|---|---|
| ~ | input/month | `` | - | none |
| ~ | input/month | `` | - | none |

### Detail

- table columns:
  - `2025-08`, `2025-09`, `2025-10`, `2025-11`, `2025-12`, `2026-01`, `2026-02`, `2026-03`, `2026-04`, `2026-05`, `2026-06`, `2026-07`

- detail labels:
  - `2025-08`, `2025-09`, `2025-10`, `2025-11`, `2025-12`, `2026-01`, `2026-02`, `2026-03`, `2026-04`, `2026-05`, `2026-06`, `2026-07`

| Label | Control | Name | Flags | Options |
|---|---|---|---|---|
| ~ | input/month | `` | - | none |
| ~ | input/month | `` | - | none |


## 商談レポート

- route: `/enterprise/report_opportunities`
- navigated: `/enterprise/report_opportunities`
- source: `known` / category: `report`
- sampled detail page type: `/enterprise/report_opportunities`

### CRUD / API

- create triggers: none
- update triggers: none
- delete triggers: none
- write-like actions: none
- row link patterns: none
- observed API:
  - `POST /api/enterprise/report_opportunities/index` status=200
  - `POST /api/enterprise/report_opportunities/index` status=200
  - `POST /api/enterprise/opportunities/index` status=200

### List

- table columns:
  - `2025-12`, `2026-01`, `2026-02`, `2026-03`, `2026-04`, `2026-05`, `2026-06`, `2026-07`, `2026-08`, `2026-09`, `2026-10`, `2026-11`

| Label | Control | Name | Flags | Options |
|---|---|---|---|---|
| ~ | input/month | `` | - | none |
| ~ | input/month | `` | - | none |

### Detail

- table columns:
  - `2025-12`, `2026-01`, `2026-02`, `2026-03`, `2026-04`, `2026-05`, `2026-06`, `2026-07`, `2026-08`, `2026-09`, `2026-10`, `2026-11`

- detail labels:
  - `2025-12`, `2026-01`, `2026-02`, `2026-03`, `2026-04`, `2026-05`, `2026-06`, `2026-07`, `2026-08`, `2026-09`, `2026-10`, `2026-11`

| Label | Control | Name | Flags | Options |
|---|---|---|---|---|
| ~ | input/month | `` | - | none |
| ~ | input/month | `` | - | none |


## レポート

- route: `/enterprise/report_summaries/contract`
- navigated: `/enterprise/report_summaries/contract`
- source: `known` / category: `report`
- sampled detail page type: `/enterprise/report_summaries/contract`

### CRUD / API

- create triggers: none
- update triggers: none
- delete triggers: none
- write-like actions: none
- row link patterns: none
- observed API:
  - `POST /api/enterprise/report_summaries/index` status=200
  - `POST /api/enterprise/report_summaries/index` status=200

### List

- table columns:
  - `2025-09`, `2025-10`, `2025-11`, `2025-12`, `2026-01`, `2026-02`, `2026-03`, `2026-04`, `2026-05`, `2026-06`, `2026-07`, `2026-08`, `2026-09`

| Label | Control | Name | Flags | Options |
|---|---|---|---|---|
| レポート | select | `` | - | `契約`, `稼働`, `請求・支払` |
| ~ | input/month | `` | - | none |
| ~ | input/month | `` | - | none |

### Detail

- table columns:
  - `2025-09`, `2025-10`, `2025-11`, `2025-12`, `2026-01`, `2026-02`, `2026-03`, `2026-04`, `2026-05`, `2026-06`, `2026-07`, `2026-08`, `2026-09`

- detail labels:
  - `2025-09`, `2025-10`, `2025-11`, `2025-12`, `2026-01`, `2026-02`, `2026-03`, `2026-04`, `2026-05`, `2026-06`, `2026-07`, `2026-08`, `2026-09`

| Label | Control | Name | Flags | Options |
|---|---|---|---|---|
| レポート | select | `` | - | `契約`, `稼働`, `請求・支払` |
| ~ | input/month | `` | - | none |
| ~ | input/month | `` | - | none |


## Notes

- Concrete record IDs are normalized to {id}; the probe samples at most one visible row per page type.
- Current field values, raw HTML, screenshots, auth headers, cookies, and API bodies are not stored.
- Static select/radio/checkbox/custom-select choices are recorded. Likely live-data option labels are omitted.
