# TechDirect Page Catalog

- generated_at: `2026-06-02T02:30:08`
- pages: `22`
- blocked_write_requests: `2`
- scope: page types, excluding user-created saved searches and job-seeker list variants
- mode: non-destructive; write-like actions were not clicked

## Summary

| Page Type | Category | List Columns | Menus Opened | Detail Opened | API Calls | Blocked Writes |
|---|---|---:|---:|---:|---:|---:|
| 公開案件検索 | `public_jobs` | 0 | 0 | yes | 5 | 0 |
| 公開会社案件一覧 | `public_org_jobs` | 0 | 0 | yes | 3 | 0 |
| 採用管理ダッシュボード | `dashboard` | 0 | 0 | no | 4 | 0 |
| 旧ダッシュボード | `legacy_dashboard` | 0 | 0 | no | 6 | 0 |
| 旧統計ダッシュボード | `legacy_dashboard` | 0 | 0 | no | 4 | 0 |
| 統計一覧 | `analytics` | 7 | 0 | no | 2 | 0 |
| メッセージ/応募一覧 | `applications` | 0 | 0 | yes | 12 | 0 |
| 採用実績一覧 | `accepted_users` | 8 | 0 | yes | 4 | 1 |
| 案件管理一覧 | `portal_jobs` | 10 | 0 | yes | 4 | 0 |
| 案件新規作成 | `job_form` | 0 | 0 | no | 3 | 0 |
| スカウト候補者一覧 | `candidates` | 9 | 3 | yes | 5 | 1 |
| 求職者リスト管理 | `job_seeker_lists` | 0 | 1 | no | 3 | 0 |
| 求職者リスト新規作成 | `job_seeker_list_form` | 0 | 0 | no | 2 | 0 |
| 採用ステータス一覧 | `recruitment_statuses` | 0 | 1 | no | 4 | 0 |
| 採用ステータス新規作成 | `recruitment_status_form` | 0 | 0 | no | 2 | 0 |
| メッセージ定型文一覧 | `message_templates` | 0 | 1 | no | 4 | 0 |
| メッセージ定型文新規作成 | `message_template_form` | 0 | 0 | no | 2 | 0 |
| スカウト定型文一覧 | `scout_templates` | 0 | 1 | no | 3 | 0 |
| スカウト定型文新規作成 | `scout_template_form` | 0 | 0 | no | 2 | 0 |
| 担当者一覧 | `recruiters` | 0 | 0 | no | 2 | 0 |
| 会社情報編集 | `org_edit` | 0 | 0 | no | 4 | 0 |
| プラン情報 | `plan` | 0 | 0 | no | 2 | 0 |

## 公開案件検索

- path: `/jobs`
- link patterns:
  - `/jobs`
  - `/jobs/{id}`
  - `/orgs/{id}/jobs`
  - `/user/saved_job_searches`
  - `blog.techdirect.jp/archives/{id}`
- API:
  - `GET api.codeal.work/v1/user/applications/unread_ids` status=200
  - `GET api.codeal.work/v1/user/saved_job_searches` status=200
  - `GET api.codeal.work/v1/user/saved_job_searches` status=200
  - `GET api.codeal.work/v1/user/applications/unread_ids` status=200
  - `GET api.codeal.work/v1/jobs` status=200

## 公開会社案件一覧

- path: `/orgs/{id}/jobs`
- link patterns:
  - `/jobs/{id}`
  - `/orgs/{id}/jobs`
  - `blog.techdirect.jp/archives/{id}`
  - `www.mijica.co.jp/`
- API:
  - `GET api.codeal.work/v1/user/applications/unread_ids` status=200
  - `GET api.codeal.work/v1/user/applications/unread_ids` status=200
  - `GET api.codeal.work/v1/jobs` status=200

## 採用管理ダッシュボード

- path: `/orgs/{id}/portal/`
- link patterns:
  - `/orgs/{id}/portal/`
  - `/orgs/{id}/portal/accepted-users`
  - `/orgs/{id}/portal/analysis`
  - `/orgs/{id}/portal/applications/`
  - `/orgs/{id}/portal/edit`
  - `/orgs/{id}/portal/job-seeker-lists`
  - `/orgs/{id}/portal/job-seekers-tabular`
  - `/orgs/{id}/portal/jobs`
  - `/orgs/{id}/portal/message-templates`
  - `/orgs/{id}/portal/old-dashboard`
  - `/orgs/{id}/portal/plan`
  - `/orgs/{id}/portal/recruiters`
  - `/orgs/{id}/portal/recruitment-statuses`
  - `/orgs/{id}/portal/scout-templates`
  - `blog.techdirect.jp/archives/category/news/`
  - `blog.techdirect.jp/archives/{id}`
  - `crowdworks-product.my.salesforce.com/sfc/p/{id}/a/{id}/{id}`
  - `drive.google.com/file/d/{id}/view`
  - `info.techdirect.jp/l/{id}/2024-06-23/2cztvy4`
- API:
  - `GET api.codeal.work/v1/orgs/{id}/stats/dashboard_dates` status=200
  - `GET api.codeal.work/v1/orgs/{id}/stats/dashboard` status=200
  - `GET api.codeal.work/v1/user/applications/unread_ids` status=200
  - `GET api.codeal.work/v1/orgs/{id}/contracts` status=200

## 旧ダッシュボード

- path: `/orgs/{id}/portal/old-dashboard`
- link patterns:
  - `/jobs/{id}`
  - `/orgs/{id}/portal/`
  - `/orgs/{id}/portal/accepted-users`
  - `/orgs/{id}/portal/analysis`
  - `/orgs/{id}/portal/applications/`
  - `/orgs/{id}/portal/dashboard`
  - `/orgs/{id}/portal/edit`
  - `/orgs/{id}/portal/job-seeker-lists`
  - `/orgs/{id}/portal/job-seekers-tabular`
  - `/orgs/{id}/portal/jobs`
  - `/orgs/{id}/portal/message-templates`
  - `/orgs/{id}/portal/plan`
  - `/orgs/{id}/portal/recruiters`
  - `/orgs/{id}/portal/recruitment-statuses`
  - `/orgs/{id}/portal/scout-templates`
  - `blog.techdirect.jp/archives/category/news/`
  - `blog.techdirect.jp/archives/{id}`
  - `crowdworks-product.my.salesforce.com/sfc/p/{id}/a/{id}/{id}`
  - `drive.google.com/file/d/{id}/view`
  - `info.techdirect.jp/l/{id}/2024-06-23/2cztvy4`
- API:
  - `GET api.codeal.work/v1/user/applications/unread_ids` status=200
  - `GET api.codeal.work/v1/orgs/{id}/contracts` status=200
  - `GET api.codeal.work/v1/orgs/{id}/recruitment_statuses/stats` status=200
  - `GET api.codeal.work/v1/orgs/{id}/applications` status=200
  - `GET api.codeal.work/v1/orgs/{id}/stats/jobs` status=200
  - `GET api.codeal.work/v1/orgs/{id}/stats/summary` status=200

## 旧統計ダッシュボード

- path: `/orgs/{id}/portal/dashboard`
- link patterns:
  - `/orgs/{id}/portal/`
  - `/orgs/{id}/portal/accepted-users`
  - `/orgs/{id}/portal/analysis`
  - `/orgs/{id}/portal/applications/`
  - `/orgs/{id}/portal/edit`
  - `/orgs/{id}/portal/job-seeker-lists`
  - `/orgs/{id}/portal/job-seekers-tabular`
  - `/orgs/{id}/portal/jobs`
  - `/orgs/{id}/portal/message-templates`
  - `/orgs/{id}/portal/old-dashboard`
  - `/orgs/{id}/portal/plan`
  - `/orgs/{id}/portal/recruiters`
  - `/orgs/{id}/portal/recruitment-statuses`
  - `/orgs/{id}/portal/scout-templates`
  - `blog.techdirect.jp/archives/category/news/`
  - `blog.techdirect.jp/archives/{id}`
  - `crowdworks-product.my.salesforce.com/sfc/p/{id}/a/{id}/{id}`
  - `drive.google.com/file/d/{id}/view`
  - `info.techdirect.jp/l/{id}/2024-06-23/2cztvy4`
- API:
  - `GET api.codeal.work/v1/orgs/{id}/stats/dashboard_dates` status=200
  - `GET api.codeal.work/v1/orgs/{id}/stats/dashboard` status=200
  - `GET api.codeal.work/v1/user/applications/unread_ids` status=200
  - `GET api.codeal.work/v1/orgs/{id}/contracts` status=200

## 統計一覧

- path: `/orgs/{id}/portal/analysis`
- table columns:
  - `項目名`, `12月1日`, `1月1日`, `2月1日`, `3月1日`, `4月1日`, `5月1日`
- link patterns:
  - `/orgs/{id}/portal/`
  - `/orgs/{id}/portal/accepted-users`
  - `/orgs/{id}/portal/analysis`
  - `/orgs/{id}/portal/applications/`
  - `/orgs/{id}/portal/dashboard`
  - `/orgs/{id}/portal/edit`
  - `/orgs/{id}/portal/job-seeker-lists`
  - `/orgs/{id}/portal/job-seekers-tabular`
  - `/orgs/{id}/portal/jobs`
  - `/orgs/{id}/portal/message-templates`
  - `/orgs/{id}/portal/plan`
  - `/orgs/{id}/portal/recruiters`
  - `/orgs/{id}/portal/recruitment-statuses`
  - `/orgs/{id}/portal/scout-templates`
- API:
  - `GET api.codeal.work/v1/user/applications/unread_ids` status=200
  - `GET api.codeal.work/v1/orgs/{id}/contracts` status=200

## メッセージ/応募一覧

- path: `/orgs/{id}/portal/applications/`
- link patterns:
  - `/orgs/{id}/portal/`
  - `/orgs/{id}/portal/accepted-users`
  - `/orgs/{id}/portal/analysis`
  - `/orgs/{id}/portal/applications/`
  - `/orgs/{id}/portal/applications/{id}`
  - `/orgs/{id}/portal/edit`
  - `/orgs/{id}/portal/job-seeker-lists`
  - `/orgs/{id}/portal/job-seekers-tabular`
  - `/orgs/{id}/portal/jobs`
  - `/orgs/{id}/portal/message-templates`
  - `/orgs/{id}/portal/plan`
  - `/orgs/{id}/portal/recruiters`
  - `/orgs/{id}/portal/recruitment-statuses`
  - `/orgs/{id}/portal/scout-templates`
- API:
  - `GET api.codeal.work/v1/user/applications/unread_ids` status=200
  - `GET api.codeal.work/v1/orgs/{id}/contracts` status=200
  - `GET api.codeal.work/v1/orgs/{id}/muted_user_ids` status=200
  - `GET api.codeal.work/v1/orgs/{id}/applications` status=200
  - `GET api.codeal.work/v1/user/applications/unread_ids` status=200
  - `GET api.codeal.work/v1/orgs/{id}/contracts` status=200
  - `GET api.codeal.work/v1/jobs/{id}` status=200
  - `GET api.codeal.work/v1/orgs/{id}/users/{uuid}/job_actions` status=200
  - `GET api.codeal.work/v1/messages` status=200
  - `GET api.codeal.work/v1/recruiter_memos` status=200
  - `GET api.codeal.work/v1/orgs/{id}/muted_user_ids` status=200
  - `GET api.codeal.work/v1/orgs/{id}/applications` status=200

## 採用実績一覧

- path: `/orgs/{id}/portal/accepted-users`
- table columns:
  - `編集`, `ニックネーム`, `氏名`, `メッセージ`, `職種`, `はたらく場所`, `ステータス変更日`, `時間単価`
- link patterns:
  - `/orgs/{id}/portal/`
  - `/orgs/{id}/portal/accepted-users`
  - `/orgs/{id}/portal/analysis`
  - `/orgs/{id}/portal/applications/`
  - `/orgs/{id}/portal/applications/{id}`
  - `/orgs/{id}/portal/edit`
  - `/orgs/{id}/portal/job-seeker-lists`
  - `/orgs/{id}/portal/job-seekers-tabular`
  - `/orgs/{id}/portal/jobs`
  - `/orgs/{id}/portal/message-templates`
  - `/orgs/{id}/portal/plan`
  - `/orgs/{id}/portal/recruiters`
  - `/orgs/{id}/portal/recruitment-statuses`
  - `/orgs/{id}/portal/scout-templates`
  - `/users/{uuid}`
- API:
  - `GET api.codeal.work/v1/user/applications/unread_ids` status=200
  - `GET api.codeal.work/v1/orgs/{id}/contracts` status=200
  - `GET api.codeal.work/v1/user/applications/unread_ids` status=200
  - `POST api.codeal.work/v1/users/{uuid}/orgs/{id}/viewed` status=None write-candidate

## 案件管理一覧

- path: `/orgs/{id}/portal/jobs`
- table columns:
  - `編集`, `ステータス`, `案件詳細`, `作成/編集`, `PV`, `気になる`, `応募`, `スカウト`, `スカウト 返信`, `スカウト 返信率`
- link patterns:
  - `/jobs/{id}`
  - `/orgs/{id}/portal/`
  - `/orgs/{id}/portal/accepted-users`
  - `/orgs/{id}/portal/analysis`
  - `/orgs/{id}/portal/applications/`
  - `/orgs/{id}/portal/edit`
  - `/orgs/{id}/portal/job-seeker-lists`
  - `/orgs/{id}/portal/job-seekers-tabular`
  - `/orgs/{id}/portal/jobs`
  - `/orgs/{id}/portal/jobs/new`
  - `/orgs/{id}/portal/message-templates`
  - `/orgs/{id}/portal/plan`
  - `/orgs/{id}/portal/recruiters`
  - `/orgs/{id}/portal/recruitment-statuses`
  - `/orgs/{id}/portal/scout-templates`
- API:
  - `GET api.codeal.work/v1/user/applications/unread_ids` status=200
  - `GET api.codeal.work/v1/orgs/{id}/contracts` status=200
  - `GET api.codeal.work/v1/user/applications/unread_ids` status=200
  - `GET api.codeal.work/v1/jobs` status=200

## 案件新規作成

- path: `/orgs/{id}/portal/jobs/new`
- link patterns:
  - `/orgs/{id}/portal/`
  - `/orgs/{id}/portal/accepted-users`
  - `/orgs/{id}/portal/analysis`
  - `/orgs/{id}/portal/applications/`
  - `/orgs/{id}/portal/edit`
  - `/orgs/{id}/portal/job-seeker-lists`
  - `/orgs/{id}/portal/job-seekers-tabular`
  - `/orgs/{id}/portal/jobs`
  - `/orgs/{id}/portal/jobs/new`
  - `/orgs/{id}/portal/message-templates`
  - `/orgs/{id}/portal/plan`
  - `/orgs/{id}/portal/recruiters`
  - `/orgs/{id}/portal/recruitment-statuses`
  - `/orgs/{id}/portal/scout-templates`
- API:
  - `GET api.codeal.work/v1/job_skills` status=200
  - `GET api.codeal.work/v1/user/applications/unread_ids` status=200
  - `GET api.codeal.work/v1/orgs/{id}/contracts` status=200

## スカウト候補者一覧

- path: `/orgs/{id}/portal/job-seekers-tabular`
- table columns:
  - `ニックネーム`, `気になる履歴`, `メッセージ`, `リスト`, `職種`, `業務経験スキル`, `希望する業務開始時期`, `稼働可能日数`, `最低時間単価`
- link patterns:
  - `/orgs/{id}/portal/`
  - `/orgs/{id}/portal/accepted-users`
  - `/orgs/{id}/portal/analysis`
  - `/orgs/{id}/portal/applications/`
  - `/orgs/{id}/portal/applications/{id}`
  - `/orgs/{id}/portal/edit`
  - `/orgs/{id}/portal/job-seeker-lists`
  - `/orgs/{id}/portal/job-seekers-tabular`
  - `/orgs/{id}/portal/jobs`
  - `/orgs/{id}/portal/message-templates`
  - `/orgs/{id}/portal/plan`
  - `/orgs/{id}/portal/recruiters`
  - `/orgs/{id}/portal/recruitment-statuses`
  - `/orgs/{id}/portal/scout-templates`
  - `/users/{uuid}`
- API:
  - `GET api.codeal.work/v1/user/applications/unread_ids` status=200
  - `GET api.codeal.work/v1/orgs/{id}/contracts` status=200
  - `GET api.codeal.work/v1/orgs/{id}/jobs` status=200
  - `GET api.codeal.work/v1/user/applications/unread_ids` status=200
  - `POST api.codeal.work/v1/users/{uuid}/orgs/{id}/viewed` status=None write-candidate

## 求職者リスト管理

- path: `/orgs/{id}/portal/job-seeker-lists`
- link patterns:
  - `/orgs/{id}/portal/`
  - `/orgs/{id}/portal/accepted-users`
  - `/orgs/{id}/portal/analysis`
  - `/orgs/{id}/portal/applications/`
  - `/orgs/{id}/portal/edit`
  - `/orgs/{id}/portal/job-seeker-lists`
  - `/orgs/{id}/portal/job-seeker-lists/new`
  - `/orgs/{id}/portal/job-seekers-tabular`
  - `/orgs/{id}/portal/jobs`
  - `/orgs/{id}/portal/message-templates`
  - `/orgs/{id}/portal/plan`
  - `/orgs/{id}/portal/recruiters`
  - `/orgs/{id}/portal/recruitment-statuses`
  - `/orgs/{id}/portal/scout-templates`
- API:
  - `GET api.codeal.work/v1/orgs/{id}/job_seeker_lists` status=200
  - `GET api.codeal.work/v1/user/applications/unread_ids` status=200
  - `GET api.codeal.work/v1/orgs/{id}/contracts` status=200

## 求職者リスト新規作成

- path: `/orgs/{id}/portal/job-seeker-lists/new`
- link patterns:
  - `/orgs/{id}/portal/`
  - `/orgs/{id}/portal/accepted-users`
  - `/orgs/{id}/portal/analysis`
  - `/orgs/{id}/portal/applications/`
  - `/orgs/{id}/portal/edit`
  - `/orgs/{id}/portal/job-seeker-lists`
  - `/orgs/{id}/portal/job-seekers-tabular`
  - `/orgs/{id}/portal/jobs`
  - `/orgs/{id}/portal/message-templates`
  - `/orgs/{id}/portal/plan`
  - `/orgs/{id}/portal/recruiters`
  - `/orgs/{id}/portal/recruitment-statuses`
  - `/orgs/{id}/portal/scout-templates`
- API:
  - `GET api.codeal.work/v1/user/applications/unread_ids` status=200
  - `GET api.codeal.work/v1/orgs/{id}/contracts` status=200

## 採用ステータス一覧

- path: `/orgs/{id}/portal/recruitment-statuses`
- link patterns:
  - `/orgs/{id}/portal/`
  - `/orgs/{id}/portal/accepted-users`
  - `/orgs/{id}/portal/analysis`
  - `/orgs/{id}/portal/applications/`
  - `/orgs/{id}/portal/edit`
  - `/orgs/{id}/portal/job-seeker-lists`
  - `/orgs/{id}/portal/job-seekers-tabular`
  - `/orgs/{id}/portal/jobs`
  - `/orgs/{id}/portal/message-templates`
  - `/orgs/{id}/portal/plan`
  - `/orgs/{id}/portal/recruiters`
  - `/orgs/{id}/portal/recruitment-statuses`
  - `/orgs/{id}/portal/recruitment-statuses/new`
  - `/orgs/{id}/portal/scout-templates`
- API:
  - `GET api.codeal.work/v1/orgs/{id}/recruitment_statuses/stats` status=200
  - `GET api.codeal.work/v1/user/applications/unread_ids` status=200
  - `GET api.codeal.work/v1/orgs/{id}/contracts` status=200
  - `GET api.codeal.work/v1/orgs/{id}/recruitment_statuses/stats` status=200

## 採用ステータス新規作成

- path: `/orgs/{id}/portal/recruitment-statuses/new`
- link patterns:
  - `/orgs/{id}/portal/`
  - `/orgs/{id}/portal/accepted-users`
  - `/orgs/{id}/portal/analysis`
  - `/orgs/{id}/portal/applications/`
  - `/orgs/{id}/portal/edit`
  - `/orgs/{id}/portal/job-seeker-lists`
  - `/orgs/{id}/portal/job-seekers-tabular`
  - `/orgs/{id}/portal/jobs`
  - `/orgs/{id}/portal/message-templates`
  - `/orgs/{id}/portal/plan`
  - `/orgs/{id}/portal/recruiters`
  - `/orgs/{id}/portal/recruitment-statuses`
  - `/orgs/{id}/portal/scout-templates`
- API:
  - `GET api.codeal.work/v1/user/applications/unread_ids` status=200
  - `GET api.codeal.work/v1/orgs/{id}/contracts` status=200

## メッセージ定型文一覧

- path: `/orgs/{id}/portal/message-templates`
- link patterns:
  - `/orgs/{id}/portal/`
  - `/orgs/{id}/portal/accepted-users`
  - `/orgs/{id}/portal/analysis`
  - `/orgs/{id}/portal/applications/`
  - `/orgs/{id}/portal/edit`
  - `/orgs/{id}/portal/job-seeker-lists`
  - `/orgs/{id}/portal/job-seekers-tabular`
  - `/orgs/{id}/portal/jobs`
  - `/orgs/{id}/portal/message-templates`
  - `/orgs/{id}/portal/message-templates/new`
  - `/orgs/{id}/portal/plan`
  - `/orgs/{id}/portal/recruiters`
  - `/orgs/{id}/portal/recruitment-statuses`
  - `/orgs/{id}/portal/scout-templates`
- API:
  - `GET api.codeal.work/v1/orgs/{id}/message_templates` status=200
  - `GET api.codeal.work/v1/user/applications/unread_ids` status=200
  - `GET api.codeal.work/v1/orgs/{id}/contracts` status=200
  - `GET api.codeal.work/v1/orgs/{id}/special_message_templates/schedule_adjustment_request` status=200

## メッセージ定型文新規作成

- path: `/orgs/{id}/portal/message-templates/new`
- link patterns:
  - `/orgs/{id}/portal/`
  - `/orgs/{id}/portal/accepted-users`
  - `/orgs/{id}/portal/analysis`
  - `/orgs/{id}/portal/applications/`
  - `/orgs/{id}/portal/edit`
  - `/orgs/{id}/portal/job-seeker-lists`
  - `/orgs/{id}/portal/job-seekers-tabular`
  - `/orgs/{id}/portal/jobs`
  - `/orgs/{id}/portal/message-templates`
  - `/orgs/{id}/portal/plan`
  - `/orgs/{id}/portal/recruiters`
  - `/orgs/{id}/portal/recruitment-statuses`
  - `/orgs/{id}/portal/scout-templates`
- API:
  - `GET api.codeal.work/v1/user/applications/unread_ids` status=200
  - `GET api.codeal.work/v1/orgs/{id}/contracts` status=200

## スカウト定型文一覧

- path: `/orgs/{id}/portal/scout-templates`
- link patterns:
  - `/orgs/{id}/portal/`
  - `/orgs/{id}/portal/accepted-users`
  - `/orgs/{id}/portal/analysis`
  - `/orgs/{id}/portal/applications/`
  - `/orgs/{id}/portal/edit`
  - `/orgs/{id}/portal/job-seeker-lists`
  - `/orgs/{id}/portal/job-seekers-tabular`
  - `/orgs/{id}/portal/jobs`
  - `/orgs/{id}/portal/message-templates`
  - `/orgs/{id}/portal/plan`
  - `/orgs/{id}/portal/recruiters`
  - `/orgs/{id}/portal/recruitment-statuses`
  - `/orgs/{id}/portal/scout-templates`
  - `/orgs/{id}/portal/scout-templates/new`
- API:
  - `GET api.codeal.work/v1/orgs/{id}/scout_templates` status=200
  - `GET api.codeal.work/v1/user/applications/unread_ids` status=200
  - `GET api.codeal.work/v1/orgs/{id}/contracts` status=200

## スカウト定型文新規作成

- path: `/orgs/{id}/portal/scout-templates/new`
- link patterns:
  - `/orgs/{id}/portal/`
  - `/orgs/{id}/portal/accepted-users`
  - `/orgs/{id}/portal/analysis`
  - `/orgs/{id}/portal/applications/`
  - `/orgs/{id}/portal/edit`
  - `/orgs/{id}/portal/job-seeker-lists`
  - `/orgs/{id}/portal/job-seekers-tabular`
  - `/orgs/{id}/portal/jobs`
  - `/orgs/{id}/portal/message-templates`
  - `/orgs/{id}/portal/plan`
  - `/orgs/{id}/portal/recruiters`
  - `/orgs/{id}/portal/recruitment-statuses`
  - `/orgs/{id}/portal/scout-templates`
- API:
  - `GET api.codeal.work/v1/user/applications/unread_ids` status=200
  - `GET api.codeal.work/v1/orgs/{id}/contracts` status=200

## 担当者一覧

- path: `/orgs/{id}/portal/recruiters`
- link patterns:
  - `/orgs/{id}/portal/`
  - `/orgs/{id}/portal/accepted-users`
  - `/orgs/{id}/portal/analysis`
  - `/orgs/{id}/portal/applications/`
  - `/orgs/{id}/portal/edit`
  - `/orgs/{id}/portal/job-seeker-lists`
  - `/orgs/{id}/portal/job-seekers-tabular`
  - `/orgs/{id}/portal/jobs`
  - `/orgs/{id}/portal/message-templates`
  - `/orgs/{id}/portal/plan`
  - `/orgs/{id}/portal/recruiters`
  - `/orgs/{id}/portal/recruitment-statuses`
  - `/orgs/{id}/portal/scout-templates`
- API:
  - `GET api.codeal.work/v1/user/applications/unread_ids` status=200
  - `GET api.codeal.work/v1/orgs/{id}/contracts` status=200

## 会社情報編集

- path: `/orgs/{id}/portal/edit`
- link patterns:
  - `/orgs/{id}/portal/`
  - `/orgs/{id}/portal/accepted-users`
  - `/orgs/{id}/portal/analysis`
  - `/orgs/{id}/portal/applications/`
  - `/orgs/{id}/portal/edit`
  - `/orgs/{id}/portal/job-seeker-lists`
  - `/orgs/{id}/portal/job-seekers-tabular`
  - `/orgs/{id}/portal/jobs`
  - `/orgs/{id}/portal/message-templates`
  - `/orgs/{id}/portal/plan`
  - `/orgs/{id}/portal/recruiters`
  - `/orgs/{id}/portal/recruitment-statuses`
  - `/orgs/{id}/portal/scout-templates`
- API:
  - `GET api.codeal.work/v1/user/applications/unread_ids` status=200
  - `GET api.codeal.work/v1/orgs/{id}/contracts` status=200
  - `GET api.codeal.work/v1/regions` status=200
  - `GET api.codeal.work/v1/countries` status=200

## プラン情報

- path: `/orgs/{id}/portal/plan`
- link patterns:
  - `/orgs/{id}/portal/`
  - `/orgs/{id}/portal/accepted-users`
  - `/orgs/{id}/portal/analysis`
  - `/orgs/{id}/portal/applications/`
  - `/orgs/{id}/portal/edit`
  - `/orgs/{id}/portal/job-seeker-lists`
  - `/orgs/{id}/portal/job-seekers-tabular`
  - `/orgs/{id}/portal/jobs`
  - `/orgs/{id}/portal/message-templates`
  - `/orgs/{id}/portal/plan`
  - `/orgs/{id}/portal/recruiters`
  - `/orgs/{id}/portal/recruitment-statuses`
  - `/orgs/{id}/portal/scout-templates`
  - `info.techdirect.jp/l/{id}/2024-06-23/2cztvy4`
- API:
  - `GET api.codeal.work/v1/user/applications/unread_ids` status=200
  - `GET api.codeal.work/v1/orgs/{id}/contracts` status=200
