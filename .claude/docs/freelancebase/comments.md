# FreelanceBase Comments

## 候補者コメント

候補者詳細のコメントは `#comment-tab` またはコメントタブクリックで取得する。

```python
from freelancebase.comments import latest_candidate_comment

latest = latest_candidate_comment(page)
```

長文コメントは preview と展開行に分かれるため、`div.read-more:not(.d-none)` があれば展開してから読む。

## 企業コメント

企業詳細もタブ名は `コメント(N件)` 形式。`freelancebase.pages.click_counted_tab()` を使う。

コメント投稿ボタンは「コメントを投稿」。担当者作成など他ドロワーの保存ボタンと文言が揃っていない。

## 書き込み安全

コメント投稿は社内 CRM に即時反映される。投稿 helper を使う場合は必ず dry-run で本文・対象 URL・対象 ID を表示し、ユーザー承認後に実行する。

