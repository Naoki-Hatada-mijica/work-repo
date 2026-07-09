#!/usr/bin/env bash
# issue-mon-init.sh — operator runbook: webhook URL 設定の指示を表示

set -uo pipefail

TARGET=""
MODE="dry"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --target) TARGET="$2"; shift 2 ;;
    --apply) MODE="apply"; shift ;;
    --dry-run) MODE="dry"; shift ;;
    *) shift ;;
  esac
done

if [[ -z "$TARGET" ]]; then
  echo "usage: $0 --apply|--dry-run --target <project>" >&2
  exit 2
fi

REPO_NAME="$(cd "$TARGET" && git config --get remote.origin.url 2>/dev/null | sed -E 's#.*[/:]([^/]+/[^/]+)\.git$#\1#')"

cat <<EOF
[issue-mon-init] target: $TARGET ($REPO_NAME)
[issue-mon-init] mode: $MODE

operator action items (handle outside this script):
  1. Sentry project の Alert Rules で webhook URL を receiver に設定:
     URL:    https://<receiver-host>/webhook/sentry
     Secret: GCP Secret Manager の WEBHOOK_RECEIVER_SHARED_SECRET_CURRENT を Sentry に登録

  2. mijica-inc/security-audit (D 層) の notify-slack.sh に webhook POST を追加:
     URL:    https://<receiver-host>/webhook/security-audit

  3. GitHub repo ($REPO_NAME) の Settings → Webhooks で workflow_run + issues event:
     URL:    https://<receiver-host>/webhook/github/actions
             https://<receiver-host>/webhook/github/issues
     Content type: application/json
     Secret: WEBHOOK_RECEIVER_SHARED_SECRET_CURRENT

  4. allowlist 設定 (Firestore repo_config/<owner-repo>):
     environment: staging|production
     max_pending_issues: 10

EOF

if [[ "$MODE" == "apply" ]]; then
  echo "[issue-mon-init] (no project-local files written; this skill is operator-runbook driven)"
fi
