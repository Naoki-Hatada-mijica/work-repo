# FreelanceBase All Pages CRUD Matrix

Generated from a non-destructive probe on 2026-06-01. Save/post/delete buttons were not clicked. Detail pages were opened for the first visible row only where a stable detail URL could be inferred; concrete record IDs are omitted here.

## Contents

- [Summary](#summary)
- [Write-Like Actions](#write-like-actions)
- [Page Details](#page-details)
- [Safety Notes](#safety-notes)

## Summary

| Page | Route | List | Create UI | Update UI | Delete UI |
|---|---|---:|---:|---:|---:|
| 人材 | `/enterprise/candidates#view-1` | yes | yes | yes | no |
| 企業 | `/enterprise/companies#view-2` | yes | yes | yes | no |
| 企業担当者 | `/enterprise/company_members#view-9` | yes | yes | yes | no |
| 案件 | `/enterprise/jobs#view-3` | yes | yes | yes | no |
| 商談 | `/enterprise/opportunities#view-4` | yes | yes | yes | no |
| 契約 | `/enterprise/contracts#view-5` | yes | yes | not confirmed | no |
| 稼働 | `/enterprise/contract_operations#view-6` | yes | no | not confirmed | no |
| 請求・支払 | `/enterprise/billing_payments#view-7` | yes | no | not confirmed | no |
| 合算請求書 | `/enterprise/billing_merges#view-10` | yes | no | not confirmed | no |
| 自動化 | `/enterprise/automation_emails#new-tab` | yes | yes | not confirmed | no |
| フォーム | `/enterprise/questionnaire_forms` | yes | yes | not confirmed | no |
| 配信 | `/enterprise/broadcasts#all-tab` | yes | yes | not confirmed | no |
| 案件サイト | `/enterprise/sites#contents-tab_mainvisual-menu` | partial | no | yes | no |
| 記事 | `/enterprise/articles` | yes | yes | not confirmed | no |
| 提案 | `/enterprise/restrictions/proposals` | restricted | no | no | no |
| 応募 | `/enterprise/applies#view-8` | yes | no | not confirmed | no |
| レポート | `/enterprise/report_summaries/contract` | yes | no | no | no |
| 担当別レポート | `/enterprise/report_billing_payments` | yes | no | no | no |
| 商談レポート | `/enterprise/report_opportunities` | yes | no | no | no |

## Write-Like Actions

These actions are not simple create/update/delete buttons, but they may change status, publication, output, or aggregation state. They were observed but not clicked.

| Page | Actions |
|---|---|
| 商談 | `成約を確定`, `見送り`, `辞退` |
| 請求・支払 | `合算請求候補を抽出` |
| 合算請求書 | `合算請求候補を抽出` |
| 自動化 | `処理順を編集`, `公開する` |
| フォーム | `リリース` |
| 案件サイト | `保存`, `公開する` |
| 記事 | `下書き保存`, `本番に公開` |

## Page Details

### 人材

- Create UI: `人材を作成 > 通常作成` with 7 inputs.
- Update UI: first detail page exposes `編集する` with 34 inputs and `保存する` / `キャンセル`.
- APIs observed:
  - `POST /api/enterprise/candidates/index`
  - `POST /api/enterprise/enterprise_members/index`
  - `GET /api/enterprise/candidate_resumes/index/{id}`
  - `POST /api/enterprise/applies/index`
  - `POST /api/enterprise/candidates/shared_info_text_preview`
  - `POST /api/enterprise/opportunities/index`
  - `GET /api/enterprise/comment_candidates/index/{id}`

### 企業

- Create UI: `企業を作成` with 32 inputs.
- Update UI: first detail page exposes `編集する` with 18 inputs and `保存する` / `キャンセル`.
- APIs observed:
  - `POST /api/enterprise/enterprise_members/index`
  - `POST /api/enterprise/view_settings/index`
  - `POST /api/enterprise/companies/index`
  - `GET /api/enterprise/file_attachments/index/Company/{id}`
  - `GET /api/enterprise/comment_companies/index/{id}`

### 企業担当者

- Create UI: `企業担当者を作成` with 11 inputs.
- Update UI: first detail page exposes `編集する` with 6 inputs and `保存する` / `キャンセル`.
- APIs observed:
  - `POST /api/enterprise/enterprise_members/index`
  - `POST /api/enterprise/view_settings/index`
  - `POST /api/enterprise/company_members/index`
  - `GET /api/enterprise/file_attachments/index/CompanyMember/{id}`

### 案件

- Create UI: `案件を作成 > 通常作成` with 99 inputs.
- Update UI: first detail page exposes `編集する` with 71 inputs and `保存する` / `キャンセル`.
- APIs observed:
  - `POST /api/enterprise/enterprise_members/index`
  - `POST /api/enterprise/view_settings/index`
  - `POST /api/enterprise/jobs/index`
  - `GET /api/enterprise/companies/show/{id}`
  - `POST /api/enterprise/jobs/shared_info_text_preview`
  - `POST /api/enterprise/opportunities/index`
  - `GET /api/enterprise/comment_jobs/index/{id}`

### 商談

- Create UI: `商談を作成` with 10 inputs.
- Update UI: first detail page exposes `編集する` with 7 inputs and `保存する` / `キャンセル`.
- State actions observed on detail: `成約を確定` / `見送り` / `辞退`. These were not clicked.
- APIs observed:
  - `GET /api/enterprise/model_settings/show/opportunity`
  - `POST /api/enterprise/view_settings/index`
  - `POST /api/enterprise/opportunities/index`
  - `POST /api/enterprise/enterprise_members/index`
  - `GET /api/enterprise/comment_opportunities/index/{id}`
  - `GET /api/enterprise/log_opportunities/index/{id}`

### 契約

- Create UI: `契約を作成` opens a wizard with 4 inputs and document-type buttons.
- Update UI: not confirmed by this non-destructive probe.
- APIs observed:
  - `POST /api/enterprise/view_settings/index`
  - `POST /api/enterprise/contracts/index`
  - `POST /api/enterprise/enterprise_members/index`
  - `GET /api/enterprise/enterprise_document_settings/show`

### 稼働

- Create UI: none observed.
- Update UI: not confirmed by this non-destructive probe.
- APIs observed:
  - `POST /api/enterprise/view_settings/index`
  - `POST /api/enterprise/contract_operations/index`

### 請求・支払

- Create UI: none observed.
- Update UI: not confirmed by this non-destructive probe.
- Write-like action observed: `合算請求候補を抽出`. It was not clicked.
- APIs observed:
  - `POST /api/enterprise/view_settings/index`
  - `POST /api/enterprise/billing_payments/index`

### 合算請求書

- Create UI: none observed.
- Update UI: not confirmed by this non-destructive probe.
- Write-like action observed: `合算請求候補を抽出`. It was not clicked.
- APIs observed:
  - `POST /api/enterprise/view_settings/index`
  - `POST /api/enterprise/billing_merges/index`

### 自動化

- Create UI: `条件を新規作成` with 9 inputs.
- Update UI: not confirmed by this non-destructive probe.
- Write-like actions observed: `処理順を編集` / `公開する`. They were not clicked.
- APIs observed:
  - `POST /api/enterprise/automation_email_drafts/index`
  - `POST /api/enterprise/enterprise_members/index`
  - `POST /api/enterprise/questionnaire_forms/index`

### フォーム

- Create UI: `フォームを作成` with 1 initial input and `保存する` / `リリース`.
- Update UI: not confirmed by this non-destructive probe.
- `リリース` is a publish action inside the create surface and was not clicked.
- APIs observed:
  - `POST /api/enterprise/enterprise_members/index`
  - `POST /api/enterprise/custom_properties/index`

### 配信

- Create UI: `配信を作成` with an initial wizard and `次へ`.
- Update UI: not confirmed by this non-destructive probe.
- APIs observed:
  - `POST /api/enterprise/broadcasts/index`
  - `POST /api/enterprise/custom_properties/index`
  - `POST /api/enterprise/enterprise_members/index`
  - `POST /api/enterprise/questionnaire_forms/index`
  - `POST /api/enterprise/view_settings/index`
  - `POST /api/enterprise/jobs/index`
  - `POST /api/enterprise/candidates/index`
  - `POST /api/enterprise/broadcasts/preview`

### 案件サイト

- Create UI: none observed.
- Update UI: page-level `保存` button observed.
- Publish action: `公開する` observed. It was not clicked.
- APIs observed:
  - `POST /api/enterprise/enterprise_images/index`

### 記事

- Create UI: `記事を作成` with 7 inputs and `下書き保存` / `本番に公開` / `アップロード`.
- Publish actions inside create surface: `下書き保存` / `本番に公開`. They were not clicked.
- APIs observed:
  - `POST /api/enterprise/articles/index`
  - `GET /api/enterprise/site_setting_drafts/show`
  - `POST /api/enterprise/article_categories/index`

### 提案

- Route is restricted by current plan: `/enterprise/restrictions/proposals`.
- No CRUD surface observed.

### 応募

- Create UI: none observed.
- Update UI: not confirmed by this non-destructive probe.
- APIs observed:
  - `POST /api/enterprise/view_settings/index`
  - `POST /api/enterprise/applies/index`

### レポート

- Read-only report surface.
- APIs observed:
  - `POST /api/enterprise/report_summaries/index`

### 担当別レポート

- Read-only report surface.
- APIs observed:
  - `POST /api/enterprise/report_billing_payments/index`

### 商談レポート

- Read-only report surface.
- APIs observed:
  - `POST /api/enterprise/report_opportunities/index`
  - `POST /api/enterprise/opportunities/index`

## Safety Notes

- This matrix intentionally does not include raw record values, auth headers, request bodies, response bodies, screenshots, or HTML dumps.
- `*_preview`, `/preview`, and `/index` POST endpoints are treated as non-write APIs.
- Actual create/update/delete endpoints should be captured only inside task-specific write flows after `OperationPreview` output and explicit approval.
- State-change, publish, extraction, and release actions are tracked separately from CRUD and must be treated as write-like even when they are not create/update/delete.
- Delete helpers are intentionally not provided in the common library.
