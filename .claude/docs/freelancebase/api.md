# FreelanceBase API Capture

## 基本方針

FreelanceBase の内部 API はブラウザで自然発火した request を捕捉し、同じ session の auth headers と payload を再利用する。認証ヘッダをログや成果物に出さない。

## 認証ヘッダ

`/api/enterprise/...` request から以下を抽出する。

- `x-csrf-token`
- `uid`
- `client`
- `access-token`
- `token-type`
- `strategies`

`freelancebase.api.enterprise_auth_headers()` は上記を API 呼び出し用の表記に整形する。表示・保存時は必ず redaction する。

## 読み取り系 POST

FreelanceBase は読み取り一覧でも POST を使う。

- `/api/enterprise/candidates/index`
- `/api/enterprise/companies/index`
- `/api/enterprise/projects/index`

これらは read-only 扱いとして `fetch_json(..., dry_run=False, read_only=True)` で実行できる。

## destructive candidate

以下は destructive 候補として扱う。

- `PUT`
- `PATCH`
- `DELETE`
- index 系以外の `POST`

`fetch_json()` は destructive 候補を `dry_run=True` または `read_only=True` で呼んだ場合、実 API を呼ばず skip 結果を返す。

## ページ仕様プローブ

`ApiRecorder` は API body や auth headers を保存せず、以下だけを残す。

- method
- path
- status
- request JSON の top-level keys
- response JSON の top-level keys
- destructive candidate 判定

PII を含むレスポンス本文は保存しない。

