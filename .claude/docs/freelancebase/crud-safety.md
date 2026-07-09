# FreelanceBase CRUD Safety

FreelanceBase は本番 CRM。作成・変更・削除は社内データに即時反映される。

## 原則

- 読み取りを先に実装する。
- 書き込み helper は既定 dry-run。
- 実行前に対象・変更前・変更後・API endpoint を表示する。
- 一意特定できない場合は停止する。
- auth headers / cookies / session state は出力しない。
- HTML / screenshot / API body は PII を含むためコミットしない。

## 作成

作成前に同一候補者・同一企業の重複検索を行う。

- 候補者: 管理用ID、メール、氏名完全一致
- 企業: 社名完全一致、必要に応じてドメイン・電話番号

作成後は URL / ID / API status をログに残す。

## 更新

更新前に現在値を取得し、差分 preview を出す。

推奨 format:

```text
target: /enterprise/candidates/1234
section: 管理情報
field: 営業ステータス
before: 営業中
after: 営業不可
api: PUT /api/enterprise/candidates/update/1234
```

## 削除

削除は最も危険なため、共通 helper の初期実装では実行関数を提供しない。仕様プローブで DELETE endpoint を発見した場合も、ドキュメントに記録するだけに留める。

削除が必要な場合は、個別タスクで対象・理由・復旧可能性を確認し、ユーザーの明示承認を取る。

## CRUD 以外の write-like action

`公開する` / `リリース` / `成約を確定` / `見送り` / `辞退` / `合算請求候補を抽出` のような操作は、作成・更新・削除ではなくても社内状態や公開状態を変える可能性がある。

これらは CRUD helper に含めない。個別タスクで対象、現在状態、変更後、復旧可能性を preview し、明示承認後に実行する。

危険アクションを調査する場合は `danger_probe.py` を使い、最終ボタンの直前で止める。必要な場合はブラウザ route guard で destructive candidate の API を abort する。

## dry-run 判定

`freelancebase.api.fetch_json()` は destructive 候補を `dry_run=True` または `read_only=True` で呼ぶと API を実行せず skip する。

## preview / log helper

`freelancebase.crud` に write 前提の共通型を置く。

```python
from freelancebase.crud import FieldChange, OperationPreview, dry_run_result

preview = OperationPreview(
    action="update",
    resource="candidate",
    target_url="https://freelancebase.jp/enterprise/candidates/1234",
    target_id=1234,
    endpoint="/api/enterprise/candidates/update/1234",
    method="PUT",
    changes=[
        FieldChange("営業ステータス", "営業中", "営業不可"),
    ],
)
print(preview.render())
result = dry_run_result(preview)
```

実 write を行う個別スクリプトは、`OperationPreview.render()` を表示してから承認を取り、`write_operation_log()` で JSONL ログを残す。
