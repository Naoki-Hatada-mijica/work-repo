---
name: deploy-watchdog
description: GitHub Actions deploy.yml の失敗を検知し rollback issue を起票する skill。3 連続失敗で escalation、staging-only filter、auto-merge せず parallel-claude-codex の通常レビューフロー + `[deploy-ok]` gate に乗せる。「deploy 監視を初期化して」「`/deploy-watchdog init`」で project 適用 (deploy.yml template + ci/deploy/smoke skeleton 配布、interactive only)。
---

# deploy-watchdog スキル

GitHub Actions の `workflow_run` event を receiver の `/webhook/github/actions` で受信、deploy.yml フィルタ通過で deploy-watchdog 専用 path に dispatch。失敗で rollback issue 起票、3 連続失敗で escalation。

## 役割分離

| 役割 | 何をするか | 配置 |
|---|---|---|
| **receiver adapter** | workflow_run failure 受信 → deploy.yml フィルタ → 1h cooldown / 3 連続 escalation 判定 → rollback issue 起票 | Cloud Run |
| **Operator-Claude** | `init.sh` で deploy.yml template + ci/deploy/smoke skeleton を project に配布、`replay.sh` で fixture 再現 | operator local |

## 配信モデル

- canonical path: `~/.claude/skills/deploy-watchdog/`
- **project-local 残置物** (`init.sh --apply --with-deploy` で配布):
  - `.github/workflows/deploy.yml` (template、interactive only / 既存ありで default abort)
  - `scripts/{ci.sh,deploy.sh,smoke.sh}` skeleton (project 側で実装)
- runtime state: Firestore `issue_dedup` + Cloud Logging

## 前提

- receiver が Cloud Run で稼働
- repo webhook で `workflow_run` event を receiver `/webhook/github/actions` に POST する設定済
- `repo_config/<owner-repo>.environment ∈ {staging, production}` 設定済
- 初期は staging のみで動作 (`environment != production` で起票)

## 呼び出し方

| operator が言う / 入力する | Operator-Claude が実行する処理 |
|---|---|
| 「deploy 監視を初期化 (template 配布なし) `<project>`」 | `bash ~/.claude/skills/deploy-watchdog/scripts/deploy-wd-init.sh --apply --target <project>` |
| 「deploy 監視を初期化 (template 配布) `<project>`」 | `bash ~/.claude/skills/deploy-watchdog/scripts/deploy-wd-init.sh --apply --target <project> --with-deploy` (interactive、既存ありで default abort) |
| 「deploy 監視を replay `<fixture>`」 | `bash ~/.claude/skills/deploy-watchdog/scripts/deploy-wd-replay.sh <fixture>` |
| 「deploy 監視履歴 `<project>`」 | `bash ~/.claude/skills/deploy-watchdog/scripts/deploy-wd-list.sh --target <project> --since 30d` |

## rollback issue 仕様

- title: `[CC] rollback: deploy failed at <commit_sha_short>`
- body 1 行目: `[CC]` (= owner CC 指名、責任の所在を明確化)
- body 末尾と `---` の間に空行 1 行 (Round 2 I6)
- footer: `source: deploy-watchdog:run-<run_id>` / `fingerprint: deploy-wd:<repo>:deploy:<env>`
- label: `[critical]`

## 連続失敗 / 永久 sink 防止

- `run_attempt > 1` (GitHub re-run) → initial failure を見て判定 (re-run 自体では起票しない)
- 1h cooldown
- 同 fingerprint の 3 連続失敗 → 既存 issue に **comment 追加** + `[escalated]` label flip (新規起票なし)
- escalation 中は parallel-claude-codex に渡らない (sync.sh の label filter で skip)
- `[critical]` Slack で 1h おき再送 (operator ack まで)
- close から 7d 経過で cooldown reset (`closed_by != bot` 必須)

## 安全装置

- rollback PR の auto-merge は **しない**。`[deploy-ok]` 必須 (parallel-claude-codex 本体改修済)
- 初期は staging deploy のみ (Phase 4 staging のみ、production は Phase 8 以降)
- `repo_config.environment != production` でのみ起票

## deploy.yml template + scripts/{ci,deploy,smoke}.sh

Round 4 I2: 意図的 fail を仕込むときは `scripts/deploy.sh` 末尾に `exit 1` を 1 commit 追加 → 再 push、確認後 revert。

## 参考

- SPEC: `tasks/20260505-設計・実装_自走パイプライン拡張_auto-issue-deploy-watchdog/SPEC.md` §4 / §5
