# TechDirect Scraping Notes

TechDirect の非破壊スクレイピング用リファレンス。

## Files

- `pages.md`: 巡回対象ページ、一覧カラム、リンクパターン、API呼び出しの概要。
- `column-catalog.md`: ページ種別ごとの一覧カラム、フィルタ、表示カラム編集、カラム関連の選択肢。
- `field-catalog.md`: 一覧/詳細画面で確認できたラベル、入力欄、ラジオボタン、セレクトボックス、チェックボックス、選択肢。
- `danger-actions.md`: 押下手前まで確認した危険アクション、リスト/メニュー選択肢、安全境界。
- `page-type-schema.md`: ページ種別単位に一覧カラム、詳細ラベル、フィールド/選択肢、write-like UI、APIを統合したカタログ。

## Scope

- 対象はページ種別単位。
- ユーザー作成の `savedSearchId`、求職者リスト絞り込み、ステータス別絞り込みなどの派生URLは対象外。
- ページ種別の代表URLから、一覧カラム、カラム表示切替、フィルタ/フォーム選択肢、詳細画面のラベルを記録する。

## Safety

- 候補者名、メール、電話番号、応募文、添付ファイル名、UUID は記録しない。
- API の request/response body、Cookie、Authorization header は保存しない。
- 非GETの TechDirect/Codeal API は route guard で abort する。
- 候補者詳細を開くと `POST /v1/users/{uuid}/orgs/{id}/viewed` が発火するため、プローブでは abort 済み。

## Regenerate

ページ種別単位で全体を見直す場合は `schema_probe.py` を使う。既知ルートとナビゲーションから発見した
ページ種別をマージし、ユーザー作成の保存検索・リスト派生・データ個別ページは対象外にする。
詳細ページは代表リンクを1件だけサンプルとして開き、`{id}` / `{uuid}` に正規化する。

```bash
/usr/bin/python3 ~/.claude/snippets/techdirect/schema_probe.py \
  --out-dir /tmp/techdirect-page-type-schema \
  --docs-out ~/.claude/docs/techdirect/page-type-schema.md
```

部分確認:

```bash
/usr/bin/python3 ~/.claude/snippets/techdirect/schema_probe.py \
  --out-dir /tmp/techdirect-page-type-schema-smoke \
  --limit 5
```

従来の分割カタログを再生成する場合:

```bash
/usr/bin/python3 ~/.claude/snippets/techdirect/catalog_probe.py \
  --out-dir /tmp/techdirect-catalog \
  --docs-dir ~/.claude/docs/techdirect
```

OTP が必要な場合は `~/.claude/snippets/playwright_techdirect.py` の手順に従い、
`/tmp/techdirect_otp.txt` にワンタイムパスワードを書き込む。
