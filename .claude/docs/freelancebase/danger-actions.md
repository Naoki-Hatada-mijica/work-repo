# FreelanceBase Danger Actions

Danger action boundary probe result. Generated on 2026-06-01 with a non-destructive Playwright probe.

The probe opened only safe setup surfaces such as detail action menus and create drawers. It did not click final write-like buttons. A route guard aborted write-like `/api/enterprise/...` requests if any were triggered; no such request was triggered during this run.

## Summary

| Surface | Stop Point | Final / Dangerous Actions Visible | Inputs Before Final |
|---|---|---|---:|
| 人材 detail action menu | `アクション` menu opened | `削除`, `コピーする` | 0 |
| 企業 detail action menu | `アクション` menu opened | `削除` | 0 |
| 案件 detail action menu | `アクション` menu opened | `案件を複製`, `削除`, `コピーする` | 0 |
| 商談 detail status actions | detail page opened | `成約を確定`, `見送り`, `辞退` | 0 |
| 契約 create wizard | `契約を作成` wizard opened | none yet; `次へ` visible | 4 |
| 請求・支払 aggregation | list page opened | `合算請求候補を抽出` | 0 |
| 合算請求書 aggregation | list page opened | `合算請求候補を抽出` | 0 |
| 自動化 publish | list page opened | `処理順を編集`, `公開する` | 0 |
| 自動化 create condition | `条件を新規作成` drawer opened | `保存する` | 9 |
| フォーム create/release | `フォームを作成` surface opened | `保存する`, `リリース` | 1 |
| 配信 create wizard | `配信を作成` wizard opened | none yet; `次へ` visible | 1 |
| 案件サイト save/publish | page opened | `保存`, `公開する`, `削除` | 0 |
| 記事 create/publish | `記事を作成` surface opened | `下書き保存`, `本番に公開` | 7 |

## Boundaries

- `削除`, `コピーする`, `案件を複製`, `成約を確定`, `見送り`, `辞退`, `合算請求候補を抽出`, `公開する`, `保存`, `保存する`, `リリース`, `下書き保存`, `本番に公開` were not clicked.
- `契約` and `配信` expose wizard `次へ` before a final action. This probe did not advance the wizard because required context or selection can affect downstream side effects.
- `案件サイト` exposes page-level `保存` / `公開する` and a visible `削除` action. Treat all as write-like.
- No write-like API request was triggered or blocked in this run.

## Implementation Guidance

- Use `snippets/freelancebase/danger_probe.py` when inspecting dangerous actions.
- Do not store the raw probe JSON/Markdown in git if it includes live page labels beyond the summarized action names.
- For any future implementation, capture the current state first, render `OperationPreview`, and require explicit approval before clicking final actions.
- If a future probe must click a setup button that might write immediately, keep the write guard enabled and abort all destructive candidates.
