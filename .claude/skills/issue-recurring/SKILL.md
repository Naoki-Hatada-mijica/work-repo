---
name: issue-recurring
description: GitHub Actions schedule から定期 task を GitHub issue として自動起票する skill。weekly deps-check / monthly review / 定期 housekeeping を `.github/recurring-tasks.toml` 経由で宣言、receiver 経由で fingerprint dedup + cooldown + cron drift detection。「定期タスク自動化を初期化して」「`/issue-recurring init`」で project 適用、CI で自動実行。
---

# issue-recurring スキル

このスキルは **CI runner 上で動く** ことが基本動作。Operator-Claude は init / list 操作のみ呼び出し、起票本体は GitHub Actions cron が `scripts/issue-rec-create.sh` を直接実行する。

## 役割分離

| 役割 | 何をするか | 配置 |
|---|---|---|
| **CI runner (cron 駆動)** | `scripts/issue-rec-create.sh <task_id>` を起動して issue を起票 | GitHub Actions |
| **Operator-Claude** | `init.sh` で project に workflow + config を配布、`list.sh` で運用確認 | operator local |
| **receiver** | claim/finalize/release transaction、Firestore dedup、Slack 通知 | Cloud Run |

## 配信モデル

- canonical path: `~/.claude/skills/issue-recurring/`
- 各 project の **project-local 残置物** (`init.sh --apply` が生成):
  - `.github/workflows/recurring-issues.yml` (cron schedule、init.sh が `local_time` (JST) → UTC cron に変換して埋め込む)
  - `.github/recurring-tasks.toml` (task 定義、operator が編集)
- runtime state: Firestore (dedup) + Cloud Logging (audit)

## 前提

- receiver が Cloud Run で稼働 + Firestore + Secret Manager の 3 サービス + GitHub Actions secrets `WEBHOOK_RECEIVER_SHARED_SECRET` 設定済
- `gh` CLI auth 済
- 横断 lib (`~/.claude/skills/_lib/*`) が source 可
- `_lib/duration.sh` の cooldown_duration format `[0-9]+(s|m|h|d|w)` を満たす

## 呼び出し方 (operator 視点)

| operator が言う / 入力する | Operator-Claude が実行する処理 |
|---|---|
| 「定期タスク自動化を初期化して `<project>`」 | `bash ~/.claude/skills/issue-recurring/scripts/issue-rec-init.sh --apply --target <project>` |
| 「定期タスク一覧 `<project>`」 | `bash ~/.claude/skills/issue-recurring/scripts/issue-rec-list.sh --target <project>` |
| (CI 自動) | `bash ~/.claude/skills/issue-recurring/scripts/issue-rec-create.sh <task_id>` (workflow 内) |

## 手順 (Operator-Claude 視点)

### init モード — workflow + config 配布

1. target が git work tree か確認 (`Bash` tool で `git -C <target> rev-parse --is-inside-work-tree`)
2. dry-run で diff を operator に提示:
   ```bash
   bash ~/.claude/skills/issue-recurring/scripts/issue-rec-init.sh --dry-run --target <target>
   ```
3. operator 許可後に apply:
   ```bash
   bash ~/.claude/skills/issue-recurring/scripts/issue-rec-init.sh --apply --target <target>
   ```
4. 適用結果:
   - `.github/recurring-tasks.toml` template 配置 (operator が編集)
   - `.github/workflows/recurring-issues.yml` 配置 (cron 文字列は config から自動変換)
5. 既存 `.github/workflows/recurring-issues.yml` がある場合は **`--force-overwrite` 明示時のみ** 上書き、既存ありで default abort

### list モード — 設定確認

`scripts/issue-rec-list.sh --target <project>` で `recurring-tasks.toml` を pretty print + 直近 7d の起票履歴 (Firestore `last_executed_at` 経由で receiver から取得)。

### create モード — CI 自動 (operator は通常呼ばない)

CI が `scripts/issue-rec-create.sh <task_id>` を呼ぶ。skill の中で:

1. `_lib/kill-switch.sh::check_kill_switch issue-recurring` で kill switch 確認
2. `_lib/backpressure.sh::check_backpressure <repo>` で backpressure 確認
3. `recurring-tasks.toml` から task 設定を読み、`fingerprint = compute_fingerprint("recurring:<task_id>:<YYYY-WW>")` 生成
4. `claim_id = uuidgen` で UUIDv4 生成
5. `_lib/issue-dedup.sh::dedup_claim` で Firestore claim
6. `should_create=true` なら body を `_lib/issue-body.sh::format_body` で生成
7. `gh issue create` を 3 回 retry
8. 成功で `dedup_finalize`、失敗で `dedup_release` + Slack `[critical]`

## 失敗モード

| failure | 動作 |
|---|---|
| receiver unreachable | 3 回 retry → fail-closed (exit 3、起票 skip) + Slack `[critical]` |
| TOML parse error | exit 2 + 行番号 + Actions log |
| cooldown 内 | claim 段階で `should_create=false`、Slack `[issue-rec]` "skipped: cooldown" |
| backpressure 抵触 | claim で skip + Slack `[issue-rec]` "skipped: backpressure" |
| kill switch ON | exit 0 + Cloud Logging のみ |
| `gh issue create` 3 回失敗 | release + Slack `[critical]` |

## トラブルシュート

- **cron が走らない**: GitHub Actions schedule の遅延 / silent skip。`output/last_executed_at` を Firestore で確認、25h 無音で別経路 heartbeat (drift detector) が `[critical]` 起票
- **重複起票**: fingerprint seed (`recurring:<task_id>:<YYYY-WW>`) を確認、同 week 内は dedup される
- **TZ 解釈ずれ**: GitHub Actions cron は **UTC 解釈固定**、`local_time` (JST) → UTC 変換は `init.sh` のみ。`recurring-tasks.toml` で `timezone = "Asia/Tokyo"` literal 固定 (v0、他 TZ は init.sh が reject)

## 参考

- SPEC: `tasks/20260505-設計・実装_自走パイプライン拡張_auto-issue-deploy-watchdog/SPEC.md` §1
- 横断 lib API: `tasks/.../output/lib-interfaces.md`
- Firestore schema: `tasks/.../output/firestore-schema.md`
