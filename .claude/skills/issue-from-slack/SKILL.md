---
name: issue-from-slack
description: Slack channel への投稿を receiver 経由で GitHub issue に自動起票する skill。LLM (claude-haiku-4-5) で title/body 整形、Cloud Tasks 経由 async (Slack 3s ack 制約)、専用 Cloud Run service `receiver-slack` (min-instance=1)。「Slack 投稿起票を初期化して」「`/issue-from-slack init`」で project 適用。
---

# issue-from-slack スキル

Slack channel `#dev-requests` への投稿を receiver が受け、Cloud Tasks 経由で worker が LLM 整形 + claim + `gh issue create` を実行。skill 配下は operator local の init / list 用。

## 役割分離

| 役割 | 何をするか | 配置 |
|---|---|---|
| **Slack adapter (receiver)** | 受信即 200 ack + allowlist 多重判定 + Cloud Tasks queue 投入 | Cloud Run `receiver-slack` (min-instance=1) |
| **Slack worker** | LLM 整形 + claim + gh issue create + finalize + thread reply | Cloud Tasks worker |
| **Operator-Claude** | `init.sh` で Slack bot 設定確認 + allowlist、`list.sh` で過去 24h 履歴 | operator local |

## 配信モデル

- canonical path: `~/.claude/skills/issue-from-slack/`
- runtime state: Firestore + Cloud Logging
- Cloud Run service `receiver-slack` (min-instance=1、Slack 3s ack 制約)
- Cloud Tasks queue `slack-issue-create` (`retry_max_attempts=1` = 0 retry + dead letter)

## 前提

- Slack App 作成済 (Events API 有効、scope: `chat:write`, `channels:history` 等、operator 操作必須)
- Slack signing secret を Secret Manager `SLACK_SIGNING_SECRET_CURRENT` に登録
- `claude-haiku-4-5` API key を Secret Manager `ANTHROPIC_API_KEY_CURRENT` に登録
- Firestore `repo_config/<owner-repo>.slack_config` に channel_id / user_allowlist / team_id 等 (SPEC §3.3) を設定
- Firestore `pricing/claude-haiku-4-5:v<YYYY-MM>` に最新単価を operator が月初手動 commit (Round 4 W4: v0 manual)

## 呼び出し方 (operator 視点)

| operator が言う / 入力する | Operator-Claude が実行する処理 |
|---|---|
| 「Slack 投稿起票を初期化して `<repo>`」 | `bash ~/.claude/skills/issue-from-slack/scripts/issue-slack-init.sh --target <project>` |
| 「Slack 投稿起票履歴」 | `bash ~/.claude/skills/issue-from-slack/scripts/issue-slack-list.sh --target <project> --since 24h` |

## 処理フロー (receiver 内)

```
Slack Events API (POST /webhook/slack/events)
  ↓ Slack signature 検証 (~50ms)
  ↓ allowlist 多重判定 (user / team / bot / external / private channel) ~10ms
  ↓ kill switch check (ON なら thread reply で disabled、Cloud Tasks 投入せず 200 ack)
  ↓ Cloud Tasks queue.enqueue(payload) ~50ms
  ↓ 200 ack (合計 ~200ms、3s 制約余裕)
  
Cloud Tasks worker (slack_worker.py)
  ↓ kill switch check (ON なら release_claim + ack 即終了)
  ↓ LLM 整形 (claude-haiku-4-5、1-3s) — schema validation + retry 1
  ↓ Firestore claim (claim_id = idempotency key in payload)
  ↓ gh issue create (PyGithub、1-2s)
  ↓ Firestore finalize
  ↓ Slack thread reply
```

## allowlist 多重判定 (Slack 偽装防止)

- `user_id` ∈ `user_allowlist`
- AND `team_id` == `slack_config.team_id`
- AND `is_bot == false`
- AND `is_external_shared == false`
- AND channel が private (`allow_private_only=true` の場合)
- AND `enterprise_user.id` (存在すれば team_id と整合)

不一致 → adapter で Slack thread reply "起票権限なし"、Cloud Tasks に投入しない。

## LLM 整形

- model: `claude-haiku-4-5`
- prompt: `prompts/format-prompt.txt` (投稿原文 → JSON `{title, body, suggested_owner_tag}`)
- 失敗 (retry も失敗) → raw fallback: code fence + `[draft]` label + footer skill 生成
- cost cap: Firestore `cost_counters/llm-haiku:<YYYY-MM>` を transaction increment、超過で raw fallback + `[critical]`

## 失敗モード

| failure | 動作 |
|---|---|
| Slack signature 失敗 | 401 + Cloud Logging |
| allowlist 不一致 | 200 ack + thread reply "起票権限なし" |
| rate_limit (1 投稿 / 30s) | 200 ack + thread reply "起票多すぎ" |
| LLM 失敗 (worker、retry も失敗) | raw fallback (code fence + `[draft]` label + footer skill 生成) |
| LLM cost cap | raw fallback + `[critical]` |
| `gh issue create` 失敗 | claim release + thread reply "GitHub 起票失敗" + `[critical]` |
| backpressure | thread reply "queue full" |
| kill switch ON | thread reply "system temporarily disabled" + 200 ack |

## 参考

- SPEC: `tasks/20260505-設計・実装_自走パイプライン拡張_auto-issue-deploy-watchdog/SPEC.md` §3
