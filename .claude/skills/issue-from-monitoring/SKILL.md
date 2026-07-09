---
name: issue-from-monitoring
description: Sentry / security-audit / GitHub Actions failure 等の外部監視 webhook を受け、GitHub issue として自動起票する skill。webhook receiver (mijica-inc/issue-webhook-receiver) が一次起票、operator local の skill は手動 replay / init / list 用。「監視 webhook を初期化して」「`/issue-from-monitoring init`」で project 適用。
---

# issue-from-monitoring スキル

このスキルの **一次起票は webhook receiver (Cloud Run) が同期処理** で行う。skill 配下の script は operator local の手動 replay / init / list 用。

## 役割分離

| 役割 | 何をするか | 配置 |
|---|---|---|
| **webhook receiver** | `/webhook/<adapter>` で受信 → adapter で正規化 → Firestore claim → `gh issue create` 直叩き → finalize → 200 | Cloud Run |
| **Operator-Claude** | `init.sh` で project 適用、`replay.sh` で fixture 再現、`list.sh` で過去 24h 履歴確認 | operator local |

## 配信モデル

- canonical path: `~/.claude/skills/issue-from-monitoring/`
- 各 project の **project-local 残置物**: 監視 system 側の webhook URL を receiver に向ける設定 (Sentry / GitHub repo webhook 等)
- runtime state: Firestore + Cloud Logging

## 前提

- receiver が Cloud Run で稼働
- monitoring system (Sentry / security-audit / GitHub Actions) が receiver の `/webhook/<adapter>` に POST する HMAC 設定済
- `gh` CLI auth 済 (operator local replay 用)

## 呼び出し方 (operator 視点)

| operator が言う / 入力する | Operator-Claude が実行する処理 |
|---|---|
| 「監視 webhook を初期化して `<project>`」 | `bash ~/.claude/skills/issue-from-monitoring/scripts/issue-mon-init.sh --apply --target <project>` |
| 「監視 webhook を replay `<fixture>`」 | `bash ~/.claude/skills/issue-from-monitoring/scripts/issue-mon-replay.sh <fixture>` |
| 「監視 webhook 履歴」 | `bash ~/.claude/skills/issue-from-monitoring/scripts/issue-mon-list.sh --target <project> --since 24h` |

## 失敗モード (receiver 側)

| failure | 動作 |
|---|---|
| HMAC 失敗 | 401 + Cloud Logging |
| schema 不一致 | 400 + body 200 char log |
| Firestore unavailable | 503 + retry 3 + Slack `[critical]` |
| `gh issue create` 失敗 | 内部 retry 3 + claim release + Slack `[critical]` |
| backpressure | 200 + body `{skipped:'backpressure'}` |
| kill switch | 503 |

## fingerprint seed

| source | seed |
|---|---|
| Sentry | `sentry:<project_id>:<issue_id>:<environment>` |
| security-audit | `secaudit:<host>:<finding_type>:<resource>:<env>` |
| github-actions-failure | `gha:<repo>:<workflow_name>:<job_name>:<environment>` |

## 永久 sink 防止

- 3 連続失敗で既存 escalated issue に **comment 追加**、新規起票しない
- close から 7d で cooldown reset (`closed_by != bot` 必須)

## 参考

- SPEC: `tasks/20260505-設計・実装_自走パイプライン拡張_auto-issue-deploy-watchdog/SPEC.md` §2
- receiver API: `tasks/.../output/receiver-api-spec.md`
