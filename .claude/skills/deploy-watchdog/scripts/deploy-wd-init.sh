#!/usr/bin/env bash
# deploy-wd-init.sh — apply deploy template (optional) + GitHub repo webhook setup runbook
#
# usage:
#   deploy-wd-init.sh --apply --target <project>                 (template skip、runbook only)
#   deploy-wd-init.sh --apply --target <project> --with-deploy   (template apply、interactive only)
#   deploy-wd-init.sh --dry-run --target <project> [--with-deploy]

set -uo pipefail
SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TPL_DIR="${SKILL_DIR}/templates"

MODE=""; TARGET=""; WITH_DEPLOY=0; FORCE=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --apply) MODE="apply"; shift ;;
    --dry-run) MODE="dry"; shift ;;
    --target) TARGET="$2"; shift 2 ;;
    --with-deploy) WITH_DEPLOY=1; shift ;;
    --force-overwrite) FORCE=1; shift ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done

if [[ -z "$MODE" || -z "$TARGET" ]]; then
  echo "usage: $0 --apply|--dry-run --target <project> [--with-deploy] [--force-overwrite]" >&2
  exit 2
fi

# --apply --with-deploy requires interactive TTY (Round 1 C6)
if [[ "$MODE" == "apply" && $WITH_DEPLOY -eq 1 && ! -t 0 ]]; then
  echo "deploy-wd-init: --with-deploy requires interactive TTY" >&2
  exit 2
fi

[[ -d "$TARGET" ]] || { echo "target not found: $TARGET" >&2; exit 2; }

REPO="$(cd "$TARGET" && git config --get remote.origin.url 2>/dev/null | sed -E 's#.*[/:]([^/]+/[^/]+)\.git$#\1#')"

cat <<EOF
[deploy-wd-init] target: $TARGET ($REPO)
[deploy-wd-init] mode: $MODE  with_deploy: $WITH_DEPLOY  force: $FORCE

operator runbook (deploy.yml template:'$([[ $WITH_DEPLOY -eq 1 ]] && echo apply || echo skip)'):

  1. GitHub repo Settings → Webhooks に追加:
     URL: https://<receiver-host>/webhook/github/actions
     Content type: application/json
     Secret: WEBHOOK_RECEIVER_SHARED_SECRET_CURRENT
     Events: workflow_runs (failed のみ filter receiver 側で適用)

  2. Firestore repo_config/$REPO に以下を設定:
     {
       "environment": "staging",   # production にすると watchdog が動かない (初期は staging のみ)
       "max_pending_issues": 10,
       "require_deploy_ok_label": true
     }

  3. GitHub repo Settings → Variables に DEPLOY_ENVIRONMENT, DEPLOY_TARGET 等を追加 (deploy.yml が参照)

  4. GitHub repo Settings → Secrets に SLACK_WEBHOOK_NOTIFICATION_URL を追加 (deploy.yml の post-deploy notify)

EOF

if [[ $WITH_DEPLOY -eq 1 ]]; then
  WORKFLOW_PATH="$TARGET/.github/workflows/deploy.yml"
  SCRIPTS_DIR="$TARGET/scripts"
  if [[ -f "$WORKFLOW_PATH" && $FORCE -eq 0 ]]; then
    echo "[abort] $WORKFLOW_PATH already exists. Use --force-overwrite to replace (will backup .bak.*)." >&2
    exit 2
  fi
  if [[ "$MODE" == "dry" ]]; then
    echo "[dry-run] would write $WORKFLOW_PATH"
    echo "[dry-run] would write $SCRIPTS_DIR/{ci.sh,deploy.sh,smoke.sh}"
  else
    [[ -f "$WORKFLOW_PATH" ]] && cp "$WORKFLOW_PATH" "${WORKFLOW_PATH}.bak.$(date -u +%Y%m%d-%H%M%S)"
    mkdir -p "$(dirname "$WORKFLOW_PATH")" "$SCRIPTS_DIR"
    cp "$TPL_DIR/deploy.yml" "$WORKFLOW_PATH"
    for s in ci.sh deploy.sh smoke.sh; do
      cp "$TPL_DIR/scripts/$s" "$SCRIPTS_DIR/$s"
      chmod +x "$SCRIPTS_DIR/$s"
    done
    echo "[apply] wrote $WORKFLOW_PATH + scripts/{ci.sh,deploy.sh,smoke.sh}"
  fi
fi

echo "[done] deploy-wd-init"
