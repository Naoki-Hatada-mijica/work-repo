# FreelanceBase Automation Notes

FreelanceBase 自動化の共通参照。詳細な画面仕様はここに分離し、各スキルの `SKILL.md` や `playwright_freelancebase.py` を肥大化させない。

## 入口

```python
import sys
sys.path.insert(0, __import__("os").path.expanduser("~/.claude/snippets"))

from playwright.sync_api import sync_playwright
import playwright_freelancebase as fb

with sync_playwright() as pw:
    browser, context, page = fb.login(pw, headless=True)
```

既存互換の `fb.login(pw)` は維持する。ページ別 helper は `freelancebase.*` から import する。

## 構成

- `snippets/playwright_freelancebase.py`: 後方互換のログイン入口
- `snippets/freelancebase/core.py`: URL / navigation / 共通定数
- `snippets/freelancebase/api.py`: `/api/enterprise/...` 捕捉と read-only API 呼び出し
- `snippets/freelancebase/candidates.py`: 候補者検索・詳細 URL
- `snippets/freelancebase/companies.py`: 企業検索・詳細 URL・担当者一覧
- `snippets/freelancebase/comments.py`: コメントタブ・最新コメント取得
- `snippets/freelancebase/crud.py`: write 前の preview / dry-run / 操作ログ
- `snippets/freelancebase/schema.py`: ページ種別単位の統合カタログ生成（CRUD / API / カラム / 選択肢）
- `snippets/freelancebase/probe.py`: ページ仕様プローブ
- `snippets/freelancebase/schema_probe.py`: ページ種別単位の統合プローブ CLI
- `snippets/freelancebase/spec_probe.py`: プローブ CLI
- `snippets/freelancebase/site_probe.py`: ナビゲーションリンク単位の複数ページプローブ
- `snippets/freelancebase/crud_probe.py`: 既知19ページの CRUD / write-like surface 非破壊プローブ
- `snippets/freelancebase/danger_probe.py`: 危険アクションの最終クリック直前 UI 非破壊プローブ
- `snippets/freelancebase/field_catalog_probe.py`: 詳細・作成・編集画面の項目/選択肢カタログ非破壊プローブ

## 仕様プローブ

全ページ種別をまとめて把握する場合は `schema_probe.py` を使う。
ナビゲーションからページ種別を発見し、既知ルートとマージしたうえで、数値IDを含む
データ個別ページは `{id}` に正規化する。各ページ種別につき必要な場合だけ先頭1件の
詳細をサンプルとして開き、一覧カラム、詳細ラベル、作成/編集フィールド、静的な
select/radio/checkbox/custom-select の選択肢、CRUD/write-like UI、観測APIを1つの
Markdown/JSONに統合する。保存・投稿・削除・公開・ステータス変更などの最終操作は
クリックせず、destructive 候補 API は route guard で abort する。
通常はページ種別単位で見るため、画面内タブの追加サンプリングは行わない。必要な場合のみ
`--include-tabs` を付ける。

```bash
/usr/bin/python3 ~/.claude/snippets/freelancebase/schema_probe.py \
  --out-dir /tmp/freelancebase-page-type-schema \
  --docs-out ~/.claude/docs/freelancebase/page-type-schema.md
```

部分確認:

```bash
/usr/bin/python3 ~/.claude/snippets/freelancebase/schema_probe.py \
  --out-dir /tmp/freelancebase-page-type-schema-smoke \
  --limit 3
```

従来の単一ページ確認:

```bash
/usr/bin/python3 ~/.claude/snippets/freelancebase/spec_probe.py \
  /enterprise/candidates \
  --out-dir /tmp/freelancebase-spec \
  --stem candidates
```

出力は raw HTML / screenshot / auth headers / API body を保存しない。ただし表示ラベルに社内情報が含まれる可能性があるため、コミット前に必ず確認する。

複数ページをまとめて見る場合:

```bash
/usr/bin/python3 ~/.claude/snippets/freelancebase/site_probe.py \
  --start /enterprise/candidates \
  --out-dir /tmp/freelancebase-site-spec \
  --limit 20
```

`site_probe.py` は数値 ID を含む詳細ページを既定で除外する。

全ページの CRUD surface を確認する場合:

```bash
/usr/bin/python3 ~/.claude/snippets/freelancebase/crud_probe.py \
  --out-dir /tmp/freelancebase-crud-probe
```

結果をコミットする場合は、raw JSON/Markdown ではなく `all-pages-crud.md` のように ID・本文・値を除いた要約だけを残す。

詳細画面のカラム、作成/編集画面の入力項目、静的な select/radio/checkbox 選択肢をまとめて見る場合:

```bash
/usr/bin/python3 ~/.claude/snippets/freelancebase/field_catalog_probe.py \
  --out-dir /tmp/freelancebase-field-catalog \
  --docs-out ~/.claude/docs/freelancebase/field-catalog.md
```

このプローブは current field values を保存しない。候補者・企業・担当者・案件など live-data 由来の動的選択肢は件数だけを残し、選択肢ラベルは git 管理下に保存しない。

## 参照順

- 候補者: `candidates.md`
- 企業: `companies.md`
- コメント: `comments.md`
- API 捕捉: `api.md`
- 作成・変更・削除: `crud-safety.md`
- 全ページ CRUD マトリクス: `all-pages-crud.md`
- 危険アクションの直前UI: `danger-actions.md`
- 詳細/作成/編集画面のカラム・選択肢: `field-catalog.md`
- ページ種別統合カタログ: `page-type-schema.md`
- 共通化せず個別保持する既存実装: `individual-implementations.md`
