#!/usr/bin/env bash
# scripts/deploy.sh — project ごとに実装。default は echo deploy のみ。
# To inject failure for e2e (Round 4 I2):
#   末尾に `exit 1` を 1 commit 追加 → push → workflow_run failure → deploy-watchdog が rollback issue 起票
#   確認後に revert
set -euo pipefail
echo "[deploy] target=${DEPLOY_TARGET:-staging-default}"
echo "[deploy] sha=${GITHUB_SHA:-unknown}"
echo "[deploy] no-op (replace with actual deploy command)"
exit 0
