# FreelanceBase Individual Implementations

非破壊プローブだけで共通化しきれない既存書き込み実装の確認結果。2026-06-01 時点。

## 方針

- 共通化するのはログイン、検索、API 捕捉、詳細 URL、コメント取得、preview / dry-run / 操作ログまで。
- 実際の保存処理は、対象ページごとの必須項目・副作用・外部サービス連携が違うため個別実装に残す。
- 個別実装を拡張する場合も、保存直前に `freelancebase.crud.OperationPreview` を出す。

## Existing Write Flows

| Flow | File | Main Resource | Write Surface | Keep Individual Because |
|---|---|---|---|---|
| 登録面談サマリ CRM 書き込み | `.claude/skills/freelance-meeting-summarize/scripts/crm_write.py` | 人材 | 候補者詳細の各セクション編集ドロワー | セクション別の上書き禁止ルール、スキルタグ一括追加、駅 autocomplete、マスタ変換がある |
| TechDirect 営業対象外 Base 登録 | `.claude/skills/techdirect-register-unsellable/scripts/register_unsellable.py` | 人材 | 人材作成、管理情報更新、コメント投稿 | TechDirect 判定・重複チェック・登録済みラベル付与までが一連の処理 |
| 新規商談準備 FB 企業連携 | `.claude/skills/sales-new-client-meeting-prep/scripts/fb_register_company.py` | 企業 / 企業担当者 / コメント | 企業作成、担当者作成、コメント投稿 | 企業重複判定、担当者重複確認、report.md 全文投稿が固有 |
| FreelanceHub 課金対象ステータス変更 | `.claude/skills/freelancehub-billing-check/scripts/run.py` | FreelanceHub 応募者 | Hub 側ステータス変更 | FreelanceBase ではなく Hub 管理画面の承認/非承認処理 |

## Candidate CRM Update

`crm_write.py` は候補者詳細の既存セクションを1つずつ開き、`PUT /api/enterprise/candidates/update/{id}` の 200 応答を成功判定にする。

個別保持が必要な処理:

- 氏名・フリガナ・生年月日・年齢は既存値がある場合に上書きしない。
- 最寄り駅は autocomplete 候補を選択する。
- 営業情報の日付 select は label ではなく DOM 順の year/month/day trio で扱う。
- スキル・経験情報は `情報から一括追加` を押す。
- 管理情報は option text で select を識別する。

共通化済みまたは共通化候補:

- 管理用IDから内部ID解決: `freelancebase.candidates` へ寄せられる。
- ドロワー保存前 preview: `freelancebase.crud.OperationPreview` を挟む余地がある。

## TechDirect Candidate Create

`register_unsellable.py` は人材作成後、管理情報を更新し、コメントを投稿する。

個別保持が必要な処理:

- TechDirect 側の氏名判定・添付ファイル氏名抽出・処理済みURLキャッシュ。
- 同姓同名重複チェックで既存 FB 人材がある場合は登録を止める。
- 新規メールアドレスを生成し、`POST /api/enterprise/candidates/create` の応答から `id_by_enterprise_id` を取る。
- FB 登録後に TechDirect 側へ `Base登録済/営業対象外` ラベルを付与する。

共通化済み:

- 同姓同名検索は `freelancebase.candidates.search_candidates()` / `find_candidate_matches()` に置換済み。
- API 失敗時は `raise_on_error=True` で fail closed を維持。

## Company / Contact / Comment Create

`fb_register_company.py` は企業検索、未登録なら企業作成、担当者重複確認、コメント投稿を行う。

個別保持が必要な処理:

- 企業作成後に自動遷移しない場合、再検索して詳細画面へ戻す。
- 担当者は姓名分割、メール重複、手動確認が必要。
- コメント本文は商談準備レポート全文で、投稿先は企業詳細のコメントタブ。

共通化済み:

- 企業一覧の企業ID抽出は `freelancebase.companies.search_company_id_from_table()` に置換済み。

## Hub Status Change

`freelancehub-billing-check/scripts/run.py` のステータス変更は FreelanceBase ではなく FreelanceHub 側。

個別保持が必要な処理:

- Hub の承認/非承認モーダル構造。
- 非承認理由 checkbox の mapping。
- 段階A（非承認）と段階B（承認推奨）の別承認。

共通化済み:

- FreelanceBase 突合の候補者検索は `freelancebase.candidates` に置換済み。

## Non-CRUD Write-Like Surfaces

全ページ非破壊プローブで CRUD 以外の write-like 操作を確認した。

- 商談: `成約を確定` / `見送り` / `辞退`
- 請求・支払: `合算請求候補を抽出`
- 合算請求書: `合算請求候補を抽出`
- 自動化: `処理順を編集` / `公開する`
- フォーム: `リリース`
- 案件サイト: `保存` / `公開する`
- 記事: `下書き保存` / `本番に公開`

これらは保存・投稿・削除ではなくても社内状態や公開状態を変える可能性があるため、個別タスクで preview と明示承認を必須にする。
