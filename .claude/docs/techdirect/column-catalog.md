# TechDirect Column And Choice Catalog

- generated_at: `2026-06-02T02:30:08`
- scope: page types, excluding user-created saved searches and job-seeker list variants
- table row values and current control values are not recorded
- dynamic/live-data option labels are omitted


## 公開案件検索

- path: `/jobs`
- visible table columns: none

| Source | Column/Control | Control | Name | Choices |
|---|---|---|---|---|
| List | 職種 | radio | `__cid__167_job-search-pc-category` | `指定しない`, `エンジニア`, `PM・ディレクション`, `デザイナー`, `マーケッター`, `コンサルタント`, `セールス`, `経営・事業企画`, `広報・PR`, `ライター`, `カスタマーサクセス`, `人事・労務・総務`, `財務・経理`, `その他` |
| List | 業務対象の種類 | checkbox | `` | `自社サービス`, `受託`, `請負`, `SES` |
| List | 稼働時間目安 | checkbox | `` | `週5日`, `週4日`, `週3日`, `週2日`, `週1日` |
| List | はたらく場所 | checkbox | `` | `フルリモート可`, `北海道`, `東北`, `関東`, `中部`, `近畿`, `中国`, `四国`, `九州・沖縄`, `海外` |
| List | 募集状況 | checkbox | `` | `現在募集中の案件のみを表示する` |
| List | 平日コアタイム稼働可能 | checkbox | `` | `平日コアタイム稼働可能` |

## 公開会社案件一覧

- path: `/orgs/{id}/jobs`
- visible table columns: none
- column/filter choices: none visible

## 採用管理ダッシュボード

- path: `/orgs/{id}/portal/`
- visible table columns: none

| Source | Column/Control | Control | Name | Choices |
|---|---|---|---|---|
| List | 現在 | radio | `__cid__137` | `現在`, `期間` |

## 旧ダッシュボード

- path: `/orgs/{id}/portal/old-dashboard`
- visible table columns: none
- column/filter choices: none visible

## 旧統計ダッシュボード

- path: `/orgs/{id}/portal/dashboard`
- visible table columns: none

| Source | Column/Control | Control | Name | Choices |
|---|---|---|---|---|
| List | 現在 | radio | `__cid__135` | `現在`, `期間` |

## 統計一覧

- path: `/orgs/{id}/portal/analysis`
- visible table columns:
  - `項目名`, `12月1日`, `1月1日`, `2月1日`, `3月1日`, `4月1日`, `5月1日`

| Source | Column/Control | Control | Name | Choices |
|---|---|---|---|---|
| List | 月次 | radio | `__cid__87` | `月次`, `週次`, `日次` |

## メッセージ/応募一覧

- path: `/orgs/{id}/portal/applications/`
- visible table columns: none

| Source | Column/Control | Control | Name | Choices |
|---|---|---|---|---|
| List | アーカイブ・ミュートを含む | checkbox | `` | `アーカイブ・ミュートを含む` |

## 採用実績一覧

- path: `/orgs/{id}/portal/accepted-users`
- visible table columns:
  - `編集`, `ニックネーム`, `氏名`, `メッセージ`, `職種`, `はたらく場所`, `ステータス変更日`, `時間単価`
- column/filter choices: none visible

## 案件管理一覧

- path: `/orgs/{id}/portal/jobs`
- visible table columns:
  - `編集`, `ステータス`, `案件詳細`, `作成/編集`, `PV`, `気になる`, `応募`, `スカウト`, `スカウト 返信`, `スカウト 返信率`

| Source | Column/Control | Control | Name | Choices |
|---|---|---|---|---|
| List | 下書き | checkbox | `` | `下書き` |
| List | 公開 | checkbox | `` | `公開` |
| List | 限定公開 | checkbox | `` | `限定公開` |
| List | 募集停止 | checkbox | `` | `募集停止` |
| List | 公開停止 | checkbox | `` | `公開停止` |

## 案件新規作成

- path: `/orgs/{id}/portal/jobs/new`
- visible table columns: none

| Source | Column/Control | Control | Name | Choices |
|---|---|---|---|---|
| List | 業務対象の種類 *1つ以上選択必須、複数指定可 | checkbox | `` | `自社サービス`, `受託`, `請負`, `SES` |
| List | 契約の特徴 | checkbox | `` | `社員転向あり` |
| List | 稼働時間目安 * | checkbox | `` | `週1日`, `週2日`, `週3日`, `週4日`, `週5日` |
| List | はたらく場所 * | radio | `__cid__153` | `フルリモート`, `リモート併用`, `リモート不可（常駐）` |

## スカウト候補者一覧

- path: `/orgs/{id}/portal/job-seekers-tabular`
- visible table columns:
  - `ニックネーム`, `気になる履歴`, `メッセージ`, `リスト`, `職種`, `業務経験スキル`, `希望する業務開始時期`, `稼働可能日数`, `最低時間単価`

| Source | Column/Control | Control | Name | Choices |
|---|---|---|---|---|
| List | 気になる!可のみ表示 | checkbox | `` | `気になる!可のみ表示` |
| List | スカウト可のみ表示 | checkbox | `` | `スカウト可のみ表示` |
| List | メッセージ可のみ表示 | checkbox | `` | `メッセージ可のみ表示` |
| List | 求職者一覧件数 | checkbox | `` | `true` |
| List | リスト追加 | checkbox | `` | `営業対象外`, `他媒体から営業中・対応済み`, `🌟再スカウト（稼働条件）`, `🌟再スカウト（時期）`, `🌟再スカウト（スキル）`, `🌟再スカウト（情報不足）`, `案件が見つけられるか不明`, `対応保留中`, `再スカウト送付済み（2026.1~）`, `NW`, `Base登録済/営業対象外` |
| List | 編集 | checkbox | `` | `気になる履歴`, `メッセージ`, `リスト`, `職種`, `業務経験スキル`, `添付ファイル`, `稼働可能日数`, `最低時間単価`, `備考`, `最新の雇用形態`, `最新の年収`, `登録日`, `最終活動日`, `プロフィール更新日`, `年齢`, `都道府県` |
| List | ニックネーム 気になる履歴 メッセージ リスト 職種 業務経験スキル 希望する業務開始時期 稼働可能日数 最低時間単価 | checkbox | `` | omitted: row-selection or live-data option set (1 options) |
| Menu: 条件追加 | 気になる!可のみ表示 | checkbox | `` | `気になる!可のみ表示` |
| Menu: 条件追加 | スカウト可のみ表示 | checkbox | `` | `スカウト可のみ表示` |
| Menu: 条件追加 | メッセージ可のみ表示 | checkbox | `` | `メッセージ可のみ表示` |
| Menu: 条件追加 | 求職者一覧件数 | checkbox | `` | `true` |
| Menu: 条件追加 | リスト追加 | checkbox | `` | `営業対象外`, `他媒体から営業中・対応済み`, `🌟再スカウト（稼働条件）`, `🌟再スカウト（時期）`, `🌟再スカウト（スキル）`, `🌟再スカウト（情報不足）`, `案件が見つけられるか不明`, `対応保留中`, `再スカウト送付済み（2026.1~）`, `NW`, `Base登録済/営業対象外` |
| Menu: 条件追加 | 編集 | checkbox | `` | `気になる履歴`, `メッセージ`, `リスト`, `職種`, `業務経験スキル`, `添付ファイル`, `稼働可能日数`, `最低時間単価`, `備考`, `最新の雇用形態`, `最新の年収`, `登録日`, `最終活動日`, `プロフィール更新日`, `年齢`, `都道府県` |
| Menu: 条件追加 | ニックネーム 気になる履歴 メッセージ リスト 職種 業務経験スキル 希望する業務開始時期 稼働可能日数 最低時間単価 | checkbox | `` | omitted: row-selection or live-data option set (1 options) |
| Menu: 編集 | 気になる!可のみ表示 | checkbox | `` | `気になる!可のみ表示` |
| Menu: 編集 | スカウト可のみ表示 | checkbox | `` | `スカウト可のみ表示` |
| Menu: 編集 | メッセージ可のみ表示 | checkbox | `` | `メッセージ可のみ表示` |
| Menu: 編集 | 求職者一覧件数 | checkbox | `` | `true` |
| Menu: 編集 | リスト追加 | checkbox | `` | `営業対象外`, `他媒体から営業中・対応済み`, `🌟再スカウト（稼働条件）`, `🌟再スカウト（時期）`, `🌟再スカウト（スキル）`, `🌟再スカウト（情報不足）`, `案件が見つけられるか不明`, `対応保留中`, `再スカウト送付済み（2026.1~）`, `NW`, `Base登録済/営業対象外` |
| Menu: 編集 | 気になる履歴 | checkbox | `` | `気になる履歴` |
| Menu: 編集 | メッセージ | checkbox | `` | `メッセージ` |
| Menu: 編集 | リスト | checkbox | `` | `リスト` |
| Menu: 編集 | 職種 | checkbox | `` | `職種` |
| Menu: 編集 | 業務経験スキル | checkbox | `` | `業務経験スキル` |
| Menu: 編集 | 添付ファイル | checkbox | `` | `添付ファイル` |
| Menu: 編集 | 稼働可能日数 | checkbox | `` | `稼働可能日数` |
| Menu: 編集 | 最低時間単価 | checkbox | `` | `最低時間単価` |
| Menu: 編集 | 備考 | checkbox | `` | `備考` |
| Menu: 編集 | 最新の雇用形態 | checkbox | `` | `最新の雇用形態` |
| Menu: 編集 | 最新の年収 | checkbox | `` | `最新の年収` |
| Menu: 編集 | 登録日 | checkbox | `` | `登録日` |
| Menu: 編集 | 最終活動日 | checkbox | `` | `最終活動日` |
| Menu: 編集 | プロフィール更新日 | checkbox | `` | `プロフィール更新日` |
| Menu: 編集 | 年齢 | checkbox | `` | `年齢` |
| Menu: 編集 | 都道府県 | checkbox | `` | `都道府県` |
| Menu: 編集 | ニックネーム 気になる履歴 メッセージ リスト 職種 業務経験スキル 希望する業務開始時期 稼働可能日数 最低時間単価 | checkbox | `` | omitted: row-selection or live-data option set (1 options) |
| Menu: リスト追加 | 気になる!可のみ表示 | checkbox | `` | `気になる!可のみ表示` |
| Menu: リスト追加 | スカウト可のみ表示 | checkbox | `` | `スカウト可のみ表示` |
| Menu: リスト追加 | メッセージ可のみ表示 | checkbox | `` | `メッセージ可のみ表示` |
| Menu: リスト追加 | 求職者一覧件数 | checkbox | `` | `true` |
| Menu: リスト追加 | リスト追加 | checkbox | `` | `営業対象外`, `他媒体から営業中・対応済み`, `🌟再スカウト（稼働条件）`, `🌟再スカウト（時期）`, `🌟再スカウト（スキル）`, `🌟再スカウト（情報不足）`, `案件が見つけられるか不明`, `対応保留中`, `再スカウト送付済み（2026.1~）`, `NW`, `Base登録済/営業対象外` |
| Menu: リスト追加 | 気になる履歴 | checkbox | `` | `気になる履歴` |
| Menu: リスト追加 | メッセージ | checkbox | `` | `メッセージ` |
| Menu: リスト追加 | リスト | checkbox | `` | `リスト` |
| Menu: リスト追加 | 職種 | checkbox | `` | `職種` |
| Menu: リスト追加 | 業務経験スキル | checkbox | `` | `業務経験スキル` |
| Menu: リスト追加 | 添付ファイル | checkbox | `` | `添付ファイル` |
| Menu: リスト追加 | 稼働可能日数 | checkbox | `` | `稼働可能日数` |
| Menu: リスト追加 | 最低時間単価 | checkbox | `` | `最低時間単価` |
| Menu: リスト追加 | 備考 | checkbox | `` | `備考` |
| Menu: リスト追加 | 最新の雇用形態 | checkbox | `` | `最新の雇用形態` |
| Menu: リスト追加 | 最新の年収 | checkbox | `` | `最新の年収` |
| Menu: リスト追加 | 登録日 | checkbox | `` | `登録日` |
| Menu: リスト追加 | 最終活動日 | checkbox | `` | `最終活動日` |
| Menu: リスト追加 | プロフィール更新日 | checkbox | `` | `プロフィール更新日` |
| Menu: リスト追加 | 年齢 | checkbox | `` | `年齢` |
| Menu: リスト追加 | 都道府県 | checkbox | `` | `都道府県` |
| Menu: リスト追加 | ニックネーム 気になる履歴 メッセージ リスト 職種 業務経験スキル 希望する業務開始時期 稼働可能日数 最低時間単価 | checkbox | `` | omitted: row-selection or live-data option set (1 options) |

## 求職者リスト管理

- path: `/orgs/{id}/portal/job-seeker-lists`
- visible table columns: none
- column/filter choices: none visible

## 求職者リスト新規作成

- path: `/orgs/{id}/portal/job-seeker-lists/new`
- visible table columns: none
- column/filter choices: none visible

## 採用ステータス一覧

- path: `/orgs/{id}/portal/recruitment-statuses`
- visible table columns: none

| Source | Column/Control | Control | Name | Choices |
|---|---|---|---|---|
| List | アーカイブを含める | checkbox | `` | `アーカイブを含める` |
| Menu: メニューを開く | アーカイブを含める | checkbox | `` | `アーカイブを含める` |

## 採用ステータス新規作成

- path: `/orgs/{id}/portal/recruitment-statuses/new`
- visible table columns: none

| Source | Column/Control | Control | Name | Choices |
|---|---|---|---|---|
| List | ステータスカテゴリー * | radio | `__cid__117` | `選考中`, `見送り`, `プール` |

## メッセージ定型文一覧

- path: `/orgs/{id}/portal/message-templates`
- visible table columns: none
- column/filter choices: none visible

## メッセージ定型文新規作成

- path: `/orgs/{id}/portal/message-templates/new`
- visible table columns: none
- column/filter choices: none visible

## スカウト定型文一覧

- path: `/orgs/{id}/portal/scout-templates`
- visible table columns: none
- column/filter choices: none visible

## スカウト定型文新規作成

- path: `/orgs/{id}/portal/scout-templates/new`
- visible table columns: none
- column/filter choices: none visible

## 担当者一覧

- path: `/orgs/{id}/portal/recruiters`
- visible table columns: none

| Source | Column/Control | Control | Name | Choices |
|---|---|---|---|---|
| List | 役員 | radio | `__cid__237` | `役員`, `管理職`, `メンバー` |
| List | 役員 | radio | `__cid__255` | `役員`, `管理職`, `メンバー` |
| List | 役員 | radio | `__cid__273` | `役員`, `管理職`, `メンバー` |
| List | 役員 | radio | `__cid__291` | `役員`, `管理職`, `メンバー` |
| List | 役員 | radio | `__cid__309` | `役員`, `管理職`, `メンバー` |
| List | 役員 | radio | `__cid__327` | `役員`, `管理職`, `メンバー` |

## 会社情報編集

- path: `/orgs/{id}/portal/edit`
- visible table columns: none
- column/filter choices: none visible

## プラン情報

- path: `/orgs/{id}/portal/plan`
- visible table columns: none
- column/filter choices: none visible
