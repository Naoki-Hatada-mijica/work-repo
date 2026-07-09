# FreelanceBase Candidates

## URL

- 一覧: `/enterprise/candidates`
- 詳細: `/enterprise/candidates/{id_by_enterprise_id}`
- コメントタブ: `/enterprise/candidates/{id_by_enterprise_id}#comment-tab`

`id_by_enterprise_id` が詳細 URL と update API に使う人材 ID。create API の top-level `id` は別 ID のため混同しない。

## 検索

推奨は `/api/enterprise/candidates/index` の捕捉・再利用。

```python
from freelancebase.candidates import search_candidates, find_candidate_matches

candidates = search_candidates(page, "山田 太郎")
matches = find_candidate_matches(candidates, full_name="山田太郎")
```

重複登録防止など fail closed にしたい処理では `raise_on_error=True` を指定する。

一意特定には次を優先する。

1. 管理用ID `name_for_company`
2. メールアドレス
3. 姓・名完全一致
4. `name` / `supplier_name` の空白除去一致

同姓同名や媒体違いで複数ヒットするため、書き込み前は必ず一意確認する。

## 詳細・タブ

候補者詳細は Vue SPA。タブやドロワーはページ遷移なしで状態が変わる。連続編集時に `page.goto()` でリロードすると SPA 状態が壊れることがあるため、ドロワーを閉じてから次操作に進む。

## 既知の注意

- 保存 API: `PUT /api/enterprise/candidates/update/{id_by_enterprise_id}`
- 保存成功判定は API 200 を監視する。トーストだけに依存しない。
- コメントカードの長文は「詳細をみる」で展開が必要な場合がある。
