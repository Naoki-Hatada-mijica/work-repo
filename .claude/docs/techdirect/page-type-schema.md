# TechDirect Page-Type Schema Catalog

- generated_at: `2026-06-08T14:01:15`
- page_types: `37`
- blocked_write_requests: `2`
- mode: non-destructive; write-like actions were not clicked and non-GET TechDirect/Codeal API requests are aborted

## Summary

| Page Type | Route | Source | List Columns | Menus | Detail | Fields | Write-like Labels | API Calls | Blocked Writes | Omitted Options |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 採用実績一覧 | `/orgs/{id}/portal/accepted-users` | known | 8 | 0 | yes | 2 | 1 | 4 | 1 | 1 |
| 統計一覧 | `/orgs/{id}/portal/analysis` | known | 7 | 0 | no | 2 | 0 | 2 | 0 | 0 |
| メッセージ/応募一覧 | `/orgs/{id}/portal/applications` | known | 0 | 0 | yes | 11 | 4 | 11 | 0 | 3 |
| スカウト候補者一覧 | `/orgs/{id}/portal/job-seekers-tabular` | known | 9 | 3 | yes | 63 | 27 | 5 | 1 | 5 |
| 採用管理ダッシュボード | `/orgs/{id}/portal` | known | 0 | 0 | no | 2 | 0 | 4 | 0 | 0 |
| / | `/` | navigation | 0 | 0 | no | 8 | 1 | 3 | 0 | 0 |
| 会社概要 | `/company` | navigation | 1 | 0 | no | 0 | 0 | 0 | 0 | 0 |
| よくある質問 | `/helps` | navigation | 0 | 0 | no | 0 | 0 | 1 | 0 | 0 |
| お問い合わせ | `/inquiry` | navigation | 0 | 0 | no | 0 | 0 | 1 | 0 | 0 |
| メッセージ | `/user/applications` | navigation | 0 | 0 | no | 2 | 0 | 1 | 0 | 0 |
| 気になるした案件一覧 | `/user/bookmarks` | navigation | 0 | 0 | no | 0 | 0 | 1 | 0 | 0 |
| profile | `/user/edit/profile` | navigation | 0 | 0 | no | 5 | 0 | 4 | 0 | 0 |
| 保存した検索条件 | `/user/saved_job_searches` | navigation | 0 | 0 | no | 0 | 0 | 1 | 0 | 0 |
| 案件新規作成 | `/orgs/{id}/portal/jobs/new` | known | 0 | 0 | no | 11 | 1 | 3 | 0 | 0 |
| 求職者リスト新規作成 | `/orgs/{id}/portal/job-seeker-lists/new` | known | 0 | 0 | no | 2 | 1 | 2 | 0 | 0 |
| 求職者リスト管理 | `/orgs/{id}/portal/job-seeker-lists` | known | 0 | 1 | no | 0 | 1 | 3 | 0 | 0 |
| 旧統計ダッシュボード | `/orgs/{id}/portal/dashboard` | known | 0 | 0 | no | 2 | 0 | 4 | 0 | 0 |
| 旧ダッシュボード | `/orgs/{id}/portal/old-dashboard` | known | 0 | 0 | no | 1 | 0 | 7 | 0 | 0 |
| メッセージ定型文新規作成 | `/orgs/{id}/portal/message-templates/new` | known | 0 | 0 | no | 2 | 1 | 2 | 0 | 0 |
| メッセージ定型文一覧 | `/orgs/{id}/portal/message-templates` | known | 0 | 1 | no | 0 | 0 | 8 | 0 | 0 |
| 会社情報編集 | `/orgs/{id}/portal/edit` | known | 0 | 0 | no | 6 | 1 | 4 | 0 | 0 |
| プラン情報 | `/orgs/{id}/portal/plan` | known | 0 | 0 | no | 0 | 0 | 2 | 0 | 0 |
| 案件管理一覧 | `/orgs/{id}/portal/jobs` | known | 10 | 0 | yes | 6 | 1 | 4 | 0 | 0 |
| 公開案件検索 | `/jobs` | known | 0 | 0 | yes | 8 | 2 | 5 | 0 | 0 |
| 公開会社案件一覧 | `/orgs/{id}/jobs` | known | 0 | 0 | yes | 0 | 1 | 3 | 0 | 0 |
| 担当者一覧 | `/orgs/{id}/portal/recruiters` | known | 0 | 0 | no | 7 | 1 | 2 | 0 | 0 |
| 採用ステータス新規作成 | `/orgs/{id}/portal/recruitment-statuses/new` | known | 0 | 0 | no | 3 | 1 | 2 | 0 | 0 |
| 採用ステータス一覧 | `/orgs/{id}/portal/recruitment-statuses` | known | 0 | 1 | no | 2 | 1 | 4 | 0 | 0 |
| スカウト定型文新規作成 | `/orgs/{id}/portal/scout-templates/new` | known | 0 | 0 | no | 2 | 1 | 2 | 0 | 0 |
| スカウト定型文一覧 | `/orgs/{id}/portal/scout-templates` | known | 0 | 1 | no | 0 | 1 | 3 | 0 | 0 |
| helps detail | `/helps/{id}` | surface-link | 0 | 0 | no | 0 | 0 | 0 | 0 | 0 |
| user | `/user` | surface-link | 0 | 0 | no | 1 | 0 | 1 | 0 | 1 |
| portfolio | `/user/edit/portfolio` | surface-link | 0 | 0 | no | 8 | 4 | 2 | 0 | 0 |
| request | `/user/edit/request` | surface-link | 0 | 0 | no | 6 | 0 | 1 | 0 | 0 |
| setting | `/user/edit/setting` | surface-link | 0 | 0 | no | 6 | 0 | 1 | 0 | 4 |
| schedule adjustment request | `/orgs/{id}/portal/message-templates/special/schedule_adjustment_request` | surface-link | 0 | 0 | no | 0 | 0 | 0 | 0 | 0 |
| create | `/user/totp/create` | surface-link | 0 | 0 | no | 1 | 1 | 1 | 0 | 0 |

## 採用実績一覧

- route: `/orgs/{id}/portal/accepted-users`
- source: `known` / category: `accepted_users`
- sampled detail page type: `/users/{uuid}`

### API

- `GET api.codeal.work/v1/user/applications/unread_ids` status=200
- `GET api.codeal.work/v1/orgs/{id}/contracts` status=200
- `GET api.codeal.work/v1/user/applications/unread_ids` status=200
- `POST api.codeal.work/v1/users/{uuid}/orgs/{id}/viewed` status=None write-candidate

### List

- table columns:
  - `編集`, `ニックネーム`, `氏名`, `メッセージ`, `職種`, `はたらく場所`, `ステータス変更日`, `時間単価`

- fields: none visible

### Detail

- labels:
  - `誕生年`, `都道府県`, `氏名`, `住所`, `電話番号`, `職種`, `稼働可能日数`, `オフィス出社頻度`, `稼働時間目安`, `最低時間単価`, `雇用形態`, `業務内容`, `業務対象の種類`, `正社員経験`, `期間`, `役職`, `スキル`, `年収`

| Label | Control | Name | Flags | Options |
|---|---|---|---|---|
| リスト編集 | checkbox | `` | - | `営業対象外`, `他媒体から営業中・対応済み`, `🌟再スカウト（稼働条件）`, `🌟再スカウト（時期）`, `🌟再スカウト（スキル）`, `🌟再スカウト（情報不足）`, `案件が見つけられるか不明`, `対応保留中`, `再スカウト送付済み（2026.1~）`, `NW`, `Base登録済/営業対象外` |
| select-org | radio | `select-org` | - | omitted: dynamic or live-data option set (1 options) |

- write-like labels: `リスト編集`

- menu/list options:
  - `営業対象外`, `他媒体から営業中・対応済み`, `🌟再スカウト（稼働条件）`, `🌟再スカウト（時期）`, `🌟再スカウト（スキル）`, `🌟再スカウト（情報不足）`, `案件が見つけられるか不明`, `対応保留中`, `再スカウト送付済み（2026.1~）`, `NW`, `Base登録済/営業対象外`, `リストを追加・編集`


## 統計一覧

- route: `/orgs/{id}/portal/analysis`
- source: `known` / category: `analytics`

### API

- `GET api.codeal.work/v1/user/applications/unread_ids` status=200
- `GET api.codeal.work/v1/orgs/{id}/contracts` status=200

### List

- table columns:
  - `項目名`, `1月1日`, `2月1日`, `3月1日`, `4月1日`, `5月1日`, `6月1日`

| Label | Control | Name | Flags | Options |
|---|---|---|---|---|
| 今月 | input/- | `` | readonly | none |
| 月次 | radio | `__cid__87` | - | `月次`, `週次`, `日次` |


## メッセージ/応募一覧

- route: `/orgs/{id}/portal/applications`
- source: `known` / category: `applications`
- sampled detail page type: `/orgs/{id}/portal/applications/{id}`

### API

- `GET api.codeal.work/v1/user/applications/unread_ids` status=200
- `GET api.codeal.work/v1/orgs/{id}/contracts` status=200
- `GET api.codeal.work/v1/orgs/{id}/muted_user_ids` status=200
- `GET api.codeal.work/v1/orgs/{id}/applications` status=200
- `GET api.codeal.work/v1/user/applications/unread_ids` status=200
- `GET api.codeal.work/v1/orgs/{id}/contracts` status=200
- `GET api.codeal.work/v1/orgs/{id}/users/{uuid}/job_actions` status=200
- `GET api.codeal.work/v1/messages` status=200
- `GET api.codeal.work/v1/recruiter_memos` status=200
- `GET api.codeal.work/v1/orgs/{id}/muted_user_ids` status=200
- `GET api.codeal.work/v1/orgs/{id}/applications` status=200

### List

| Label | Control | Name | Flags | Options |
|---|---|---|---|---|
| アーカイブ・ミュートを含む | checkbox | `` | - | `アーカイブ・ミュートを含む` |
| 反応待を除外 | checkbox | `` | - | `反応待を除外` |

- write-like labels: `条件追加`

### Detail

- labels:
  - `アーカイブ・ミュートを含む`, `反応待を除外`, `氏名`, `住所`, `電話番号`, `稼働開始時期`, `稼働可能日数`, `稼働時間目安`, `最低時間単価`, `オフィス出社頻度`

| Label | Control | Name | Flags | Options |
|---|---|---|---|---|
| アーカイブ・ミュートを含む | checkbox | `` | - | `アーカイブ・ミュートを含む` |
| 反応待を除外 | checkbox | `` | - | `反応待を除外` |
| 時給 | radio | `__cid__235` | - | `時給`, `月額` |
| 案件の業務内容が希望と合わなかったため | radio | `__cid__260` | - | omitted: dynamic or live-data option set (8 options) |
| 氏名（本名） | checkbox | `` | - | omitted: dynamic or live-data option set (1 options) |
| 住所 | checkbox | `` | - | `住所` |
| 電話番号 | checkbox | `` | - | omitted: dynamic or live-data option set (1 options) |
| リスト編集 | checkbox | `` | - | `営業対象外`, `他媒体から営業中・対応済み`, `🌟再スカウト（稼働条件）`, `🌟再スカウト（時期）`, `🌟再スカウト（スキル）`, `🌟再スカウト（情報不足）`, `案件が見つけられるか不明`, `対応保留中`, `再スカウト送付済み（2026.1~）`, `NW`, `Base登録済/営業対象外` |
| 時給 | radio | `__cid__432` | - | `時給`, `月額` |

- write-like labels: `リスト編集`, `条件追加`, `送信`

- menu/list options:
  - `アーカイブ・ミュートを含む`, `反応待を除外`, `営業対象外`, `他媒体から営業中・対応済み`, `🌟再スカウト（稼働条件）`, `🌟再スカウト（時期）`, `🌟再スカウト（スキル）`, `🌟再スカウト（情報不足）`, `案件が見つけられるか不明`, `対応保留中`, `再スカウト送付済み（2026.1~）`, `NW`, `Base登録済/営業対象外`, `リストを追加・編集`


## スカウト候補者一覧

- route: `/orgs/{id}/portal/job-seekers-tabular`
- source: `known` / category: `candidates`
- sampled detail page type: `/users/{uuid}`

### API

- `GET api.codeal.work/v1/user/applications/unread_ids` status=200
- `GET api.codeal.work/v1/orgs/{id}/contracts` status=200
- `GET api.codeal.work/v1/orgs/{id}/jobs` status=200
- `GET api.codeal.work/v1/user/applications/unread_ids` status=200
- `POST api.codeal.work/v1/users/{uuid}/orgs/{id}/viewed` status=None write-candidate

### List

- table columns:
  - `ニックネーム`, `気になる履歴`, `メッセージ`, `リスト`, `職種`, `業務経験スキル`, `希望する業務開始時期`, `稼働可能日数`, `最低時間単価`

| Label | Control | Name | Flags | Options |
|---|---|---|---|---|
| 気になる!可のみ表示 | checkbox | `` | - | `気になる!可のみ表示` |
| スカウト可のみ表示 | checkbox | `` | - | `スカウト可のみ表示` |
| メッセージ可のみ表示 | checkbox | `` | - | `メッセージ可のみ表示` |
| 求職者一覧件数 | checkbox | `` | - | `true` |
| リスト追加 | checkbox | `` | - | `営業対象外`, `他媒体から営業中・対応済み`, `🌟再スカウト（稼働条件）`, `🌟再スカウト（時期）`, `🌟再スカウト（スキル）`, `🌟再スカウト（情報不足）`, `案件が見つけられるか不明`, `対応保留中`, `再スカウト送付済み（2026.1~）`, `NW`, `Base登録済/営業対象外` |
| 編集 | checkbox | `` | - | `気になる履歴`, `メッセージ`, `リスト`, `職種`, `業務経験スキル`, `添付ファイル`, `稼働可能日数`, `最低時間単価`, `備考`, `最新の雇用形態`, `最新の年収`, `登録日`, `最終活動日`, `プロフィール更新日`, `年齢`, `都道府県` |
| ニックネーム 気になる履歴 メッセージ リスト 職種 業務経験スキル 希望する業務開始時期 稼働可能日数 最低時間単価 | checkbox | `` | - | omitted: row-selection or live-data option set (1 options) |

- write-like labels: `リスト追加`, `一括スカウト`, `削除`, `条件追加`

### Menu 1: `条件追加`

- table columns:
  - `ニックネーム`, `気になる履歴`, `メッセージ`, `リスト`, `職種`, `業務経験スキル`, `希望する業務開始時期`, `稼働可能日数`, `最低時間単価`

| Label | Control | Name | Flags | Options |
|---|---|---|---|---|
| 条件追加 | input/text | `` | - | none |
| 気になる!可のみ表示 | checkbox | `` | - | `気になる!可のみ表示` |
| スカウト可のみ表示 | checkbox | `` | - | `スカウト可のみ表示` |
| メッセージ可のみ表示 | checkbox | `` | - | `メッセージ可のみ表示` |
| 求職者一覧件数 | checkbox | `` | - | `true` |
| リスト追加 | checkbox | `` | - | `営業対象外`, `他媒体から営業中・対応済み`, `🌟再スカウト（稼働条件）`, `🌟再スカウト（時期）`, `🌟再スカウト（スキル）`, `🌟再スカウト（情報不足）`, `案件が見つけられるか不明`, `対応保留中`, `再スカウト送付済み（2026.1~）`, `NW`, `Base登録済/営業対象外` |
| 編集 | checkbox | `` | - | `気になる履歴`, `メッセージ`, `リスト`, `職種`, `業務経験スキル`, `添付ファイル`, `稼働可能日数`, `最低時間単価`, `備考`, `最新の雇用形態`, `最新の年収`, `登録日`, `最終活動日`, `プロフィール更新日`, `年齢`, `都道府県` |
| ニックネーム 気になる履歴 メッセージ リスト 職種 業務経験スキル 希望する業務開始時期 稼働可能日数 最低時間単価 | checkbox | `` | - | omitted: row-selection or live-data option set (1 options) |

- write-like labels: `リスト追加`, `一括スカウト`, `削除`, `採用ステータス`, `条件追加`, `気になる!送信状況`, `求職者リスト`

- menu/list options:
  - `メッセージ件数`, `メッセージ定型文`, `採用ステータス`, `案件一覧`, `スカウト`, `スカウト定型文`, `求職者リスト`, `採用実績一覧`, `担当者一覧`, `会社情報編集`, `削除`, `編集`, `検索条件をリセット`, `条件追加`, `検索`, `職種`, `活動拠点（地域）`, `活動拠点（都道府県）`, `稼働開始時期(求職状況)`, `稼働開始時期(年月)`, `稼働可能日数`, `最新経歴の職種`, `最新経歴の雇用形態`, `最新経歴の年収`, `希望する雇用形態`, `平日コアタイム稼働可能`, `スキル経験`, `最低時間単価`, `年齢`, `担当者`, `最新経歴の詳細`, `ファイル添付`, `プロフィール更新日`, `ニックネーム`, `URL`, `正社員経験`, `スカウト可のみ表示`, `メッセージ可のみ表示`, `リスト追加`, `一括メッセージ`, `一括スカウト`

### Menu 2: `編集`

- table columns:
  - `ニックネーム`, `気になる履歴`, `メッセージ`, `リスト`, `職種`, `業務経験スキル`, `希望する業務開始時期`, `稼働可能日数`, `最低時間単価`

| Label | Control | Name | Flags | Options |
|---|---|---|---|---|
| 条件追加 | input/text | `` | - | none |
| 気になる!可のみ表示 | checkbox | `` | - | `気になる!可のみ表示` |
| スカウト可のみ表示 | checkbox | `` | - | `スカウト可のみ表示` |
| メッセージ可のみ表示 | checkbox | `` | - | `メッセージ可のみ表示` |
| 求職者一覧件数 | checkbox | `` | - | `true` |
| リスト追加 | checkbox | `` | - | `営業対象外`, `他媒体から営業中・対応済み`, `🌟再スカウト（稼働条件）`, `🌟再スカウト（時期）`, `🌟再スカウト（スキル）`, `🌟再スカウト（情報不足）`, `案件が見つけられるか不明`, `対応保留中`, `再スカウト送付済み（2026.1~）`, `NW`, `Base登録済/営業対象外` |
| 気になる履歴 | checkbox | `` | - | `気になる履歴` |
| メッセージ | checkbox | `` | - | `メッセージ` |
| リスト | checkbox | `` | - | `リスト` |
| 職種 | checkbox | `` | - | `職種` |
| 業務経験スキル | checkbox | `` | - | `業務経験スキル` |
| 添付ファイル | checkbox | `` | - | `添付ファイル` |
| 稼働可能日数 | checkbox | `` | - | `稼働可能日数` |
| 最低時間単価 | checkbox | `` | - | `最低時間単価` |
| 備考 | checkbox | `` | - | `備考` |
| 最新の雇用形態 | checkbox | `` | - | `最新の雇用形態` |
| 最新の年収 | checkbox | `` | - | `最新の年収` |
| 登録日 | checkbox | `` | - | `登録日` |
| 最終活動日 | checkbox | `` | - | `最終活動日` |
| プロフィール更新日 | checkbox | `` | - | `プロフィール更新日` |
| 年齢 | checkbox | `` | - | `年齢` |
| 都道府県 | checkbox | `` | - | `都道府県` |
| ニックネーム 気になる履歴 メッセージ リスト 職種 業務経験スキル 希望する業務開始時期 稼働可能日数 最低時間単価 | checkbox | `` | - | omitted: row-selection or live-data option set (1 options) |

- write-like labels: `リスト追加`, `一括スカウト`, `削除`, `採用ステータス`, `条件追加`, `気になる!送信状況`, `求職者リスト`

- menu/list options:
  - `メッセージ件数`, `メッセージ定型文`, `採用ステータス`, `案件一覧`, `スカウト`, `スカウト定型文`, `求職者リスト`, `採用実績一覧`, `担当者一覧`, `会社情報編集`, `削除`, `編集`, `検索条件をリセット`, `条件追加`, `検索`, `職種`, `活動拠点（地域）`, `活動拠点（都道府県）`, `稼働開始時期(求職状況)`, `稼働開始時期(年月)`, `稼働可能日数`, `最新経歴の職種`, `最新経歴の雇用形態`, `最新経歴の年収`, `希望する雇用形態`, `平日コアタイム稼働可能`, `スキル経験`, `最低時間単価`, `年齢`, `担当者`, `最新経歴の詳細`, `ファイル添付`, `プロフィール更新日`, `ニックネーム`, `URL`, `正社員経験`, `スカウト可のみ表示`, `メッセージ可のみ表示`, `リスト追加`, `一括メッセージ`, `一括スカウト`, `リセット`, `メッセージ`, `リスト`, `業務経験スキル`, `添付ファイル`, `最新の雇用形態`, `最新の年収`, `都道府県`

### Menu 3: `リスト追加`

- table columns:
  - `ニックネーム`, `気になる履歴`, `メッセージ`, `リスト`, `職種`, `業務経験スキル`, `希望する業務開始時期`, `稼働可能日数`, `最低時間単価`

| Label | Control | Name | Flags | Options |
|---|---|---|---|---|
| 条件追加 | input/text | `` | - | none |
| 気になる!可のみ表示 | checkbox | `` | - | `気になる!可のみ表示` |
| スカウト可のみ表示 | checkbox | `` | - | `スカウト可のみ表示` |
| メッセージ可のみ表示 | checkbox | `` | - | `メッセージ可のみ表示` |
| 求職者一覧件数 | checkbox | `` | - | `true` |
| リスト追加 | checkbox | `` | - | `営業対象外`, `他媒体から営業中・対応済み`, `🌟再スカウト（稼働条件）`, `🌟再スカウト（時期）`, `🌟再スカウト（スキル）`, `🌟再スカウト（情報不足）`, `案件が見つけられるか不明`, `対応保留中`, `再スカウト送付済み（2026.1~）`, `NW`, `Base登録済/営業対象外` |
| 気になる履歴 | checkbox | `` | - | `気になる履歴` |
| メッセージ | checkbox | `` | - | `メッセージ` |
| リスト | checkbox | `` | - | `リスト` |
| 職種 | checkbox | `` | - | `職種` |
| 業務経験スキル | checkbox | `` | - | `業務経験スキル` |
| 添付ファイル | checkbox | `` | - | `添付ファイル` |
| 稼働可能日数 | checkbox | `` | - | `稼働可能日数` |
| 最低時間単価 | checkbox | `` | - | `最低時間単価` |
| 備考 | checkbox | `` | - | `備考` |
| 最新の雇用形態 | checkbox | `` | - | `最新の雇用形態` |
| 最新の年収 | checkbox | `` | - | `最新の年収` |
| 登録日 | checkbox | `` | - | `登録日` |
| 最終活動日 | checkbox | `` | - | `最終活動日` |
| プロフィール更新日 | checkbox | `` | - | `プロフィール更新日` |
| 年齢 | checkbox | `` | - | `年齢` |
| 都道府県 | checkbox | `` | - | `都道府県` |
| ニックネーム 気になる履歴 メッセージ リスト 職種 業務経験スキル 希望する業務開始時期 稼働可能日数 最低時間単価 | checkbox | `` | - | omitted: row-selection or live-data option set (1 options) |

- write-like labels: `リスト追加`, `一括スカウト`, `削除`, `採用ステータス`, `条件追加`, `気になる!送信状況`, `求職者リスト`

- menu/list options:
  - `メッセージ件数`, `メッセージ定型文`, `採用ステータス`, `案件一覧`, `スカウト`, `スカウト定型文`, `求職者リスト`, `採用実績一覧`, `担当者一覧`, `会社情報編集`, `削除`, `編集`, `検索条件をリセット`, `条件追加`, `検索`, `職種`, `活動拠点（地域）`, `活動拠点（都道府県）`, `稼働開始時期(求職状況)`, `稼働開始時期(年月)`, `稼働可能日数`, `最新経歴の職種`, `最新経歴の雇用形態`, `最新経歴の年収`, `希望する雇用形態`, `平日コアタイム稼働可能`, `スキル経験`, `最低時間単価`, `年齢`, `担当者`, `最新経歴の詳細`, `ファイル添付`, `プロフィール更新日`, `ニックネーム`, `URL`, `正社員経験`, `スカウト可のみ表示`, `メッセージ可のみ表示`, `リスト追加`, `一括メッセージ`, `一括スカウト`, `リセット`, `メッセージ`, `リスト`, `業務経験スキル`, `添付ファイル`, `最新の雇用形態`, `最新の年収`, `都道府県`

### Detail

- labels:
  - `誕生年`, `都道府県`, `氏名`, `住所`, `電話番号`, `職種`, `稼働開始時期`, `稼働可能日数`, `オフィス出社頻度`, `稼働時間目安`, `最低時間単価`, `雇用形態`, `業務内容`, `業務対象の種類`, `正社員経験`, `期間`, `役職`, `スキル`

| Label | Control | Name | Flags | Options |
|---|---|---|---|---|
| リスト編集 | checkbox | `` | - | `営業対象外`, `他媒体から営業中・対応済み`, `🌟再スカウト（稼働条件）`, `🌟再スカウト（時期）`, `🌟再スカウト（スキル）`, `🌟再スカウト（情報不足）`, `案件が見つけられるか不明`, `対応保留中`, `再スカウト送付済み（2026.1~）`, `NW`, `Base登録済/営業対象外` |
| select-org | radio | `select-org` | - | omitted: dynamic or live-data option set (1 options) |

- write-like labels: `スカウト`, `リスト編集`

- menu/list options:
  - `営業対象外`, `他媒体から営業中・対応済み`, `🌟再スカウト（稼働条件）`, `🌟再スカウト（時期）`, `🌟再スカウト（スキル）`, `🌟再スカウト（情報不足）`, `案件が見つけられるか不明`, `対応保留中`, `再スカウト送付済み（2026.1~）`, `NW`, `Base登録済/営業対象外`, `リストを追加・編集`


## 採用管理ダッシュボード

- route: `/orgs/{id}/portal`
- source: `known` / category: `dashboard`

### API

- `GET api.codeal.work/v1/orgs/{id}/stats/dashboard_dates` status=200
- `GET api.codeal.work/v1/orgs/{id}/stats/dashboard` status=200
- `GET api.codeal.work/v1/user/applications/unread_ids` status=200
- `GET api.codeal.work/v1/orgs/{id}/contracts` status=200

### List

| Label | Control | Name | Flags | Options |
|---|---|---|---|---|
| 統計一覧 今月 | input/- | `` | readonly | none |
| 現在 | radio | `__cid__143` | - | `現在`, `期間` |


## /

- route: `/`
- source: `navigation` / category: `discovered`

### API

- `GET api.codeal.work/v1/user/applications/unread_ids` status=200
- `GET api.codeal.work/v1/user/saved_job_searches` status=200
- `GET api.codeal.work/v1/user/saved_job_searches` status=200

### List

| Label | Control | Name | Flags | Options |
|---|---|---|---|---|
| 検索条件 検索条件をリセット | input/text | `` | - | none |
| スキル | input/- | `` | - | none |
| 職種 | radio | `__cid__167_job-search-pc-category` | - | `指定しない`, `エンジニア`, `PM・ディレクション`, `デザイナー`, `マーケッター`, `コンサルタント`, `セールス`, `経営・事業企画`, `広報・PR`, `ライター`, `カスタマーサクセス`, `人事・労務・総務`, `財務・経理`, `その他` |
| 業務対象の種類 | checkbox | `` | - | `自社サービス`, `受託`, `請負`, `SES` |
| 稼働時間目安 | checkbox | `` | - | `週5日`, `週4日`, `週3日`, `週2日`, `週1日` |
| はたらく場所 | checkbox | `` | - | `フルリモート可`, `北海道`, `東北`, `関東`, `中部`, `近畿`, `中国`, `四国`, `九州・沖縄`, `海外` |
| 募集状況 | checkbox | `` | - | `現在募集中の案件のみを表示する` |
| 平日コアタイム稼働可能 | checkbox | `` | - | `平日コアタイム稼働可能` |

- write-like labels: `検索条件を保存`


## 会社概要

- route: `/company`
- source: `navigation` / category: `discovered`

### List

- table columns:
  - `所在地`

- fields: none visible


## よくある質問

- route: `/helps`
- source: `navigation` / category: `discovered`

### API

- `GET api.codeal.work/v1/user/applications/unread_ids` status=200

### List

- fields: none visible


## お問い合わせ

- route: `/inquiry`
- source: `navigation` / category: `discovered`

### API

- `GET api.codeal.work/v1/user/applications/unread_ids` status=200

### List

- fields: none visible


## メッセージ

- route: `/user/applications`
- source: `navigation` / category: `discovered`

### API

- `GET api.codeal.work/v1/user/applications/unread_ids` status=200

### List

| Label | Control | Name | Flags | Options |
|---|---|---|---|---|
| メッセージを検索 | input/text | `` | - | none |
| アーカイブを含める | checkbox | `` | - | `アーカイブを含める` |


## 気になるした案件一覧

- route: `/user/bookmarks`
- source: `navigation` / category: `discovered`

### API

- `GET api.codeal.work/v1/user/applications/unread_ids` status=200

### List

- fields: none visible


## profile

- route: `/user/edit/profile`
- source: `navigation` / category: `discovered`

### API

- `GET api.codeal.work/v1/regions` status=200
- `GET api.codeal.work/v1/user/applications/unread_ids` status=200
- `GET api.codeal.work/v1/regions` status=200
- `GET api.codeal.work/v1/countries` status=200

### List

| Label | Control | Name | Flags | Options |
|---|---|---|---|---|
| ニックネーム * | input/text | `` | required | none |
| 氏名（本名）* | input/text | `` | - | none |
| 電話番号 * | input/tel | `` | - | none |
| 住所をリセット | input/- | `` | - | none |
| 住所 | input/- | `` | - | none |


## 保存した検索条件

- route: `/user/saved_job_searches`
- source: `navigation` / category: `discovered`

### API

- `GET api.codeal.work/v1/user/applications/unread_ids` status=200

### List

- fields: none visible


## 案件新規作成

- route: `/orgs/{id}/portal/jobs/new`
- source: `known` / category: `job_form`

### API

- `GET api.codeal.work/v1/job_skills` status=200
- `GET api.codeal.work/v1/user/applications/unread_ids` status=200
- `GET api.codeal.work/v1/orgs/{id}/contracts` status=200

### List

| Label | Control | Name | Flags | Options |
|---|---|---|---|---|
| 報酬例 * | input/text | `` | - | none |
| ～ | input/text | `` | - | none |
| 報酬備考 | textarea/- | `` | - | none |
| はたらく場所備考 | textarea/- | `` | - | none |
| タイトル * | textarea/- | `` | required | none |
| スキル * | input/- | `` | - | none |
| テキスト入力 プレビュー | textarea/- | `` | - | none |
| 業務対象の種類 *1つ以上選択必須、複数指定可 | checkbox | `` | - | `自社サービス`, `受託`, `請負`, `SES` |
| 契約の特徴 | checkbox | `` | - | `社員転向あり` |
| 稼働時間目安 * | checkbox | `` | - | `週1日`, `週2日`, `週3日`, `週4日`, `週5日` |
| はたらく場所 * | radio | `__cid__153` | - | `フルリモート`, `リモート併用`, `リモート不可（常駐）` |

- write-like labels: `下書き保存`


## 求職者リスト新規作成

- route: `/orgs/{id}/portal/job-seeker-lists/new`
- source: `known` / category: `job_seeker_list_form`

### API

- `GET api.codeal.work/v1/user/applications/unread_ids` status=200
- `GET api.codeal.work/v1/orgs/{id}/contracts` status=200

### List

| Label | Control | Name | Flags | Options |
|---|---|---|---|---|
| タイトル * | input/text | `` | required | none |
| 詳細 | textarea/- | `` | - | none |

- write-like labels: `追加`


## 求職者リスト管理

- route: `/orgs/{id}/portal/job-seeker-lists`
- source: `known` / category: `job_seeker_lists`

### API

- `GET api.codeal.work/v1/orgs/{id}/job_seeker_lists` status=200
- `GET api.codeal.work/v1/user/applications/unread_ids` status=200
- `GET api.codeal.work/v1/orgs/{id}/contracts` status=200

### List

- fields: none visible

### Menu 1: `メニューを開く`

- fields: none visible

- write-like labels: `削除`

- menu/list options:
  - `メッセージ件数`, `メッセージ定型文`, `採用ステータス`, `案件一覧`, `スカウト`, `スカウト定型文`, `求職者リスト`, `採用実績一覧`, `担当者一覧`, `会社情報編集`, `戻る`, `求職者リスト追加`, `↑`, `↓`, `編集`, `削除`


## 旧統計ダッシュボード

- route: `/orgs/{id}/portal/dashboard`
- source: `known` / category: `legacy_dashboard`

### API

- `GET api.codeal.work/v1/orgs/{id}/stats/dashboard_dates` status=200
- `GET api.codeal.work/v1/orgs/{id}/stats/dashboard` status=200
- `GET api.codeal.work/v1/user/applications/unread_ids` status=200
- `GET api.codeal.work/v1/orgs/{id}/contracts` status=200

### List

| Label | Control | Name | Flags | Options |
|---|---|---|---|---|
| 統計一覧 今月 | input/- | `` | readonly | none |
| 現在 | radio | `__cid__143` | - | `現在`, `期間` |


## 旧ダッシュボード

- route: `/orgs/{id}/portal/old-dashboard`
- source: `known` / category: `legacy_dashboard`

### API

- `GET api.codeal.work/v1/user/applications/unread_ids` status=200
- `GET api.codeal.work/v1/orgs/{id}/contracts` status=200
- `GET api.codeal.work/v1/orgs/{id}/recruitment_statuses/stats` status=200
- `GET api.codeal.work/v1/orgs/{id}/applications` status=200
- `GET api.codeal.work/v1/orgs/{id}/stats/jobs` status=200
- `GET api.codeal.work/v1/orgs/{id}/stats/summary` status=None
- `GET api.codeal.work/v1/orgs/{id}/stats/summary` status=None

### List

| Label | Control | Name | Flags | Options |
|---|---|---|---|---|
| 期間選択 | input/- | `` | readonly | none |


## メッセージ定型文新規作成

- route: `/orgs/{id}/portal/message-templates/new`
- source: `known` / category: `message_template_form`

### API

- `GET api.codeal.work/v1/user/applications/unread_ids` status=200
- `GET api.codeal.work/v1/orgs/{id}/contracts` status=200

### List

| Label | Control | Name | Flags | Options |
|---|---|---|---|---|
| 定型文タイトル * | input/text | `` | required | none |
| ${name}タグを使うことで、求職者の氏名を入力することができます。 | textarea/- | `` | - | none |

- write-like labels: `追加`


## メッセージ定型文一覧

- route: `/orgs/{id}/portal/message-templates`
- source: `known` / category: `message_templates`

### API

- `GET api.codeal.work/v1/orgs/{id}/message_templates` status=200
- `GET api.codeal.work/v1/user/applications/unread_ids` status=200
- `GET api.codeal.work/v1/orgs/{id}/contracts` status=200
- `GET api.codeal.work/v1/orgs/{id}/special_message_templates/schedule_adjustment_request` status=200
- `GET api.codeal.work/v1/orgs/{id}/message_templates` status=200
- `GET api.codeal.work/v1/user/applications/unread_ids` status=200
- `GET api.codeal.work/v1/orgs/{id}/contracts` status=200
- `GET api.codeal.work/v1/orgs/{id}/special_message_templates/schedule_adjustment_request` status=200

### List

- fields: none visible

### Menu 1: `メニューを開く`

- fields: none visible

- menu/list options:
  - `メッセージ件数`, `メッセージ定型文`, `採用ステータス`, `案件一覧`, `スカウト`, `スカウト定型文`, `求職者リスト`, `採用実績一覧`, `担当者一覧`, `会社情報編集`, `戻る`, `メッセージ定型文追加`, `編集`, `↑`, `↓`


## 会社情報編集

- route: `/orgs/{id}/portal/edit`
- source: `known` / category: `org_edit`

### API

- `GET api.codeal.work/v1/user/applications/unread_ids` status=200
- `GET api.codeal.work/v1/orgs/{id}/contracts` status=200
- `GET api.codeal.work/v1/regions` status=200
- `GET api.codeal.work/v1/countries` status=200

### List

| Label | Control | Name | Flags | Options |
|---|---|---|---|---|
| 会社名 * | input/text | `` | disabled | none |
| URL | input/text | `` | - | none |
| テキスト入力 プレビュー | textarea/- | `` | - | none |
| 住所をリセット | input/- | `` | - | none |
| 住所 | input/- | `` | - | none |
| 代表者名 | input/text | `` | - | none |

- write-like labels: `保存`


## プラン情報

- route: `/orgs/{id}/portal/plan`
- source: `known` / category: `plan`

### API

- `GET api.codeal.work/v1/user/applications/unread_ids` status=200
- `GET api.codeal.work/v1/orgs/{id}/contracts` status=200

### List

- fields: none visible


## 案件管理一覧

- route: `/orgs/{id}/portal/jobs`
- source: `known` / category: `portal_jobs`
- sampled detail page type: `/jobs/{id}`

### API

- `GET api.codeal.work/v1/user/applications/unread_ids` status=200
- `GET api.codeal.work/v1/orgs/{id}/contracts` status=200
- `GET api.codeal.work/v1/user/applications/unread_ids` status=200
- `GET api.codeal.work/v1/jobs` status=200

### List

- table columns:
  - `編集`, `ステータス`, `案件詳細`, `作成/編集`, `PV`, `気になる`, `応募`, `スカウト`, `スカウト 返信`, `スカウト 返信率`

| Label | Control | Name | Flags | Options |
|---|---|---|---|---|
| 検索条件をリセット | input/text | `` | - | none |
| 下書き | checkbox | `` | - | `下書き` |
| 公開 | checkbox | `` | - | `公開` |
| 限定公開 | checkbox | `` | - | `限定公開` |
| 募集停止 | checkbox | `` | - | `募集停止` |
| 公開停止 | checkbox | `` | - | `公開停止` |

### Detail

- labels:
  - `職種`, `業務内容`, `報酬目安`, `稼働時間目安`, `はたらく場所`, `スキル`

- fields: none visible

- write-like labels: `応募して要件を聞く`


## 公開案件検索

- route: `/jobs`
- source: `known` / category: `public_jobs`
- sampled detail page type: `/jobs/{id}`

### API

- `GET api.codeal.work/v1/user/applications/unread_ids` status=200
- `GET api.codeal.work/v1/user/saved_job_searches` status=200
- `GET api.codeal.work/v1/user/saved_job_searches` status=200
- `GET api.codeal.work/v1/user/applications/unread_ids` status=200
- `GET api.codeal.work/v1/jobs` status=200

### List

| Label | Control | Name | Flags | Options |
|---|---|---|---|---|
| 検索条件 検索条件をリセット | input/text | `` | - | none |
| スキル | input/- | `` | - | none |
| 職種 | radio | `__cid__167_job-search-pc-category` | - | `指定しない`, `エンジニア`, `PM・ディレクション`, `デザイナー`, `マーケッター`, `コンサルタント`, `セールス`, `経営・事業企画`, `広報・PR`, `ライター`, `カスタマーサクセス`, `人事・労務・総務`, `財務・経理`, `その他` |
| 業務対象の種類 | checkbox | `` | - | `自社サービス`, `受託`, `請負`, `SES` |
| 稼働時間目安 | checkbox | `` | - | `週5日`, `週4日`, `週3日`, `週2日`, `週1日` |
| はたらく場所 | checkbox | `` | - | `フルリモート可`, `北海道`, `東北`, `関東`, `中部`, `近畿`, `中国`, `四国`, `九州・沖縄`, `海外` |
| 募集状況 | checkbox | `` | - | `現在募集中の案件のみを表示する` |
| 平日コアタイム稼働可能 | checkbox | `` | - | `平日コアタイム稼働可能` |

- write-like labels: `検索条件を保存`

### Detail

- labels:
  - `職種`, `業務内容`, `報酬目安`, `稼働時間目安`, `はたらく場所`, `スキル`

- fields: none visible

- write-like labels: `応募して要件を聞く`


## 公開会社案件一覧

- route: `/orgs/{id}/jobs`
- source: `known` / category: `public_org_jobs`
- sampled detail page type: `/jobs/{id}`

### API

- `GET api.codeal.work/v1/user/applications/unread_ids` status=200
- `GET api.codeal.work/v1/user/applications/unread_ids` status=200
- `GET api.codeal.work/v1/jobs` status=200

### List

- fields: none visible

### Detail

- labels:
  - `職種`, `業務内容`, `報酬目安`, `稼働時間目安`, `はたらく場所`, `スキル`

- fields: none visible

- write-like labels: `応募して要件を聞く`


## 担当者一覧

- route: `/orgs/{id}/portal/recruiters`
- source: `known` / category: `recruiters`

### API

- `GET api.codeal.work/v1/user/applications/unread_ids` status=200
- `GET api.codeal.work/v1/orgs/{id}/contracts` status=200

### List

| Label | Control | Name | Flags | Options |
|---|---|---|---|---|
| 下記のURLにアクセスすることで担当者を招待できます。 (再生成すると以前のURLは無効になります。) | input/- | `` | readonly | none |
| 役員 | radio | `__cid__237` | - | `役員`, `管理職`, `メンバー` |
| 役員 | radio | `__cid__255` | - | `役員`, `管理職`, `メンバー` |
| 役員 | radio | `__cid__273` | - | `役員`, `管理職`, `メンバー` |
| 役員 | radio | `__cid__291` | - | `役員`, `管理職`, `メンバー` |
| 役員 | radio | `__cid__309` | - | `役員`, `管理職`, `メンバー` |
| 役員 | radio | `__cid__327` | - | `役員`, `管理職`, `メンバー` |

- write-like labels: `削除`


## 採用ステータス新規作成

- route: `/orgs/{id}/portal/recruitment-statuses/new`
- source: `known` / category: `recruitment_status_form`

### API

- `GET api.codeal.work/v1/user/applications/unread_ids` status=200
- `GET api.codeal.work/v1/orgs/{id}/contracts` status=200

### List

| Label | Control | Name | Flags | Options |
|---|---|---|---|---|
| タイトル * | input/text | `` | required | none |
| 詳細 | textarea/- | `` | - | none |
| ステータスカテゴリー * | radio | `__cid__117` | - | `選考中`, `見送り`, `プール` |

- write-like labels: `追加`


## 採用ステータス一覧

- route: `/orgs/{id}/portal/recruitment-statuses`
- source: `known` / category: `recruitment_statuses`

### API

- `GET api.codeal.work/v1/orgs/{id}/recruitment_statuses/stats` status=200
- `GET api.codeal.work/v1/user/applications/unread_ids` status=200
- `GET api.codeal.work/v1/orgs/{id}/contracts` status=200
- `GET api.codeal.work/v1/orgs/{id}/recruitment_statuses/stats` status=200

### List

| Label | Control | Name | Flags | Options |
|---|---|---|---|---|
| アーカイブを含める | checkbox | `` | - | `アーカイブを含める` |

### Menu 1: `メニューを開く`

| Label | Control | Name | Flags | Options |
|---|---|---|---|---|
| アーカイブを含める | checkbox | `` | - | `アーカイブを含める` |

- write-like labels: `削除`

- menu/list options:
  - `メッセージ件数`, `メッセージ定型文`, `採用ステータス`, `案件一覧`, `スカウト`, `スカウト定型文`, `求職者リスト`, `採用実績一覧`, `担当者一覧`, `会社情報編集`, `戻る`, `採用ステータス追加`, `アーカイブを含める`, `↑`, `↓`, `編集`, `削除`


## スカウト定型文新規作成

- route: `/orgs/{id}/portal/scout-templates/new`
- source: `known` / category: `scout_template_form`

### API

- `GET api.codeal.work/v1/user/applications/unread_ids` status=200
- `GET api.codeal.work/v1/orgs/{id}/contracts` status=200

### List

| Label | Control | Name | Flags | Options |
|---|---|---|---|---|
| 定型文タイトル * | input/text | `` | required | none |
| ${name}タグを使うことで、求職者の氏名を入力することができます。 | textarea/- | `` | - | none |

- write-like labels: `追加`


## スカウト定型文一覧

- route: `/orgs/{id}/portal/scout-templates`
- source: `known` / category: `scout_templates`

### API

- `GET api.codeal.work/v1/orgs/{id}/scout_templates` status=200
- `GET api.codeal.work/v1/user/applications/unread_ids` status=200
- `GET api.codeal.work/v1/orgs/{id}/contracts` status=200

### List

- fields: none visible

### Menu 1: `メニューを開く`

- fields: none visible

- write-like labels: `削除`

- menu/list options:
  - `メッセージ件数`, `メッセージ定型文`, `採用ステータス`, `案件一覧`, `スカウト`, `スカウト定型文`, `求職者リスト`, `採用実績一覧`, `担当者一覧`, `会社情報編集`, `戻る`, `スカウト定型文追加`, `↑`, `↓`, `編集`, `削除`


## helps detail

- route: `/helps/{id}`
- source: `surface-link` / category: `discovered`

### List

- fields: none visible


## user

- route: `/user`
- source: `surface-link` / category: `discovered`

### API

- `GET api.codeal.work/v1/user/applications/unread_ids` status=200

### List

| Label | Control | Name | Flags | Options |
|---|---|---|---|---|
| select-org | radio | `select-org` | - | omitted: dynamic or live-data option set (1 options) |


## portfolio

- route: `/user/edit/portfolio`
- source: `surface-link` / category: `discovered`

### API

- `GET api.codeal.work/v1/user/applications/unread_ids` status=200
- `GET api.codeal.work/v1/job_skills` status=200

### List

| Label | Control | Name | Flags | Options |
|---|---|---|---|---|
| スキル* | input/- | `` | - | none |
| 年収 | input/text | `` | - | none |
| 業務内容詳細 | textarea/- | `` | - | none |
| スカウトを受けたいスキルを入力してください。 | input/- | `` | - | none |
| アピールしたいURLがある場合はこちらに入力してください。（上限20個まで） | input/text | `` | - | none |
| テキスト入力 プレビュー | textarea/- | `` | - | none |
| 正社員経験 * | radio | `__cid__62` | - | `あり`, `なし` |
| 役職 | radio | `__cid__158` | - | `管理職`, `メンバー` |

- write-like labels: `保存`, `削除`, `経歴を保存`, `追加`


## request

- route: `/user/edit/request`
- source: `surface-link` / category: `discovered`

### API

- `GET api.codeal.work/v1/user/applications/unread_ids` status=200

### List

| Label | Control | Name | Flags | Options |
|---|---|---|---|---|
| 最低時間単価 | input/text | `` | - | none |
| 備考 | textarea/- | `` | - | none |
| 稼働可能日数 週何日程度稼働したいかを記入してください | checkbox | `` | - | `平日コアタイム稼働可能` |
| 希望するオフィス出社頻度* | checkbox | `` | - | `フルリモート`, `リモート併用`, `常駐可能` |
| 希望する雇用形態*（いずれか必ず選択） | checkbox | `` | - | `業務委託`, `正社員` |
| 業務対象の種類 | checkbox | `` | - | `自社サービス`, `受託`, `請負`, `SES` |


## setting

- route: `/user/edit/setting`
- source: `surface-link` / category: `discovered`

### API

- `GET api.codeal.work/v1/user/applications/unread_ids` status=200

### List

| Label | Control | Name | Flags | Options |
|---|---|---|---|---|
| プロフィールを公開する | checkbox | `` | - | `プロフィールを公開する` |
| 案件スカウト | checkbox | `` | - | omitted: dynamic or live-data option set (1 options) |
| 新着案件通知 | checkbox | `` | - | omitted: dynamic or live-data option set (1 options) |
| 求職者の更新通知 | checkbox | `` | - | omitted: dynamic or live-data option set (1 options) |
| メッセージの新着通知 | checkbox | `` | - | omitted: dynamic or live-data option set (5 options) |
| デスクトップ通知 | checkbox | `` | - | `新着メッセージをデスクトップ通知で受け取る`, `公開中の案件が「気になる！」された場合デスクトップ通知を受け取る` |


## schedule adjustment request

- route: `/orgs/{id}/portal/message-templates/special/schedule_adjustment_request`
- source: `surface-link` / category: `discovered`

### List

- fields: none visible


## create

- route: `/user/totp/create`
- source: `surface-link` / category: `discovered`

### API

- `GET api.codeal.work/v1/user/applications/unread_ids` status=200

### List

| Label | Control | Name | Flags | Options |
|---|---|---|---|---|
| 認証コード | input/text | `` | - | none |

- write-like labels: `送信`


## Notes

- Concrete org IDs, user UUIDs, job IDs, application IDs, and API record IDs are normalized.
- User-created saved searches, list filter variants, and per-record pages are excluded from route discovery.
- Detail pages are sampled only as representative page types from the first visible link.
- Current field values, request/response bodies, cookies, auth headers, emails, phones, and UUIDs are not stored.
