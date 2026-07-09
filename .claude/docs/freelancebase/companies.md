# FreelanceBase Companies

## URL

- 一覧: `/enterprise/companies`
- 詳細: `/enterprise/companies/{company_id}`

一覧行クリックは右ドロワー表示だけで URL が変わらないことがある。企業 ID が取れる場合は `/enterprise/companies/{id}` に直接 `goto` する方が安定する。

## 検索

```python
from freelancebase.companies import search_and_open_company

detail_url = search_and_open_company(page, "株式会社サンプル")
```

`search_company_id_from_table()` はクイック検索後、表示テーブルの数値セルから企業 ID を抽出する。表のセル値には社名・担当情報が含まれるため、探索ログには raw cell values を残さない。

## コメントタブ

コメントタブは `コメント(0件)` のような件数付き表記。完全一致の role name では拾えない場合があるため、`click_counted_tab(page, "コメント")` を使う。

## 企業担当者

企業担当者作成ドロワーの氏名は姓・名の2分割。

- 姓 placeholder: `田中`
- 名 placeholder: `太郎`

自社担当者1 select は Vue の v-model 反映が必要なため、値変更後に `change` / `input` event を dispatch する。

