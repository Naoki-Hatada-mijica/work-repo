#!/usr/bin/env bash
# issue-rec-create.sh — CI から呼ばれる起票本体
#
# usage:
#   issue-rec-create.sh <task_id>
#
# env:
#   RECEIVER_BASE_URL   — Cloud Run receiver
#   GITHUB_REPOSITORY   — <owner>/<repo> (Actions が自動 set)
#   CONFIG_PATH         — default .github/recurring-tasks.toml

set -uo pipefail

LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../_lib" && pwd)"
# shellcheck disable=SC1091
source "$LIB_DIR/kill-switch.sh"
# shellcheck disable=SC1091
source "$LIB_DIR/backpressure.sh"
# shellcheck disable=SC1091
source "$LIB_DIR/issue-dedup.sh"
# shellcheck disable=SC1091
source "$LIB_DIR/issue-body.sh"
# shellcheck disable=SC1091
source "$LIB_DIR/fingerprint.sh"
# shellcheck disable=SC1091
source "$LIB_DIR/slack-notify.sh"

TASK_ID="${1:-}"
if [[ -z "$TASK_ID" ]]; then
  echo "usage: $0 <task_id>" >&2
  exit 2
fi

REPO="${GITHUB_REPOSITORY:-}"
if [[ -z "$REPO" ]]; then
  echo "GITHUB_REPOSITORY not set" >&2
  exit 2
fi

CONFIG_PATH="${CONFIG_PATH:-.github/recurring-tasks.toml}"
if [[ ! -f "$CONFIG_PATH" ]]; then
  echo "config not found: $CONFIG_PATH" >&2
  exit 2
fi

# kill switch
check_kill_switch "issue-recurring" || {
  echo "[issue-rec] kill switch ON, exiting"
  exit 0
}

# Parse TOML config (use python tomllib for stability)
read_task() {
  python3 - "$CONFIG_PATH" "$TASK_ID" <<'PY'
import sys, tomllib, json
path, tid = sys.argv[1], sys.argv[2]
with open(path, 'rb') as f:
    data = tomllib.load(f)
for t in data.get('task', []):
    if t.get('id') == tid:
        print(json.dumps(t))
        sys.exit(0)
sys.exit(3)
PY
}

TASK_JSON="$(read_task)" || {
  echo "[issue-rec] task '$TASK_ID' not found in $CONFIG_PATH" >&2
  slack_notify "[critical]" "issue-rec: task '$TASK_ID' not in config"
  exit 2
}

TITLE="$(echo "$TASK_JSON" | jq -r .title)"
BODY_TEXT="$(echo "$TASK_JSON" | jq -r .body)"
OWNER_TAG="$(echo "$TASK_JSON" | jq -r '.owner_tag // ""')"
LABELS_JSON="$(echo "$TASK_JSON" | jq -c '.labels // []')"
SEED="$(echo "$TASK_JSON" | jq -r .fingerprint_seed)"

# Year-Week (ISO 8601) for fingerprint
YEAR_WEEK="$(date -u +%G-W%V)"
FP="$(compute_fingerprint "recurring:${SEED}:${YEAR_WEEK}")"

# backpressure check
if ! check_backpressure "$REPO" false; then
  echo "[issue-rec] backpressure tripped, skipping"
  slack_notify "[issue-rec]" "skipped: backpressure for $TASK_ID ($REPO)"
  exit 0
fi

# claim
CLAIM_ID="$(uuidgen)"
PAYLOAD="$(jq -nc --arg t "$TITLE" --arg b "$BODY_TEXT" --argjson l "$LABELS_JSON" \
            '{title:$t, body:$b, labels:$l}')"

CLAIM_RESP=""
for attempt in 1 2 3; do
  CLAIM_RESP="$(dedup_claim "issue-recurring" "$FP" "$REPO" "$PAYLOAD" "$CLAIM_ID" "info" "false")"
  rc=$?
  if [[ $rc -eq 0 ]]; then break; fi
  if [[ $rc -eq 2 ]]; then break; fi   # 4xx — operator action required, no retry
  sleep $((2 ** attempt))
done
if [[ -z "$CLAIM_RESP" ]]; then
  slack_notify "[critical]" "issue-rec: dedup_claim failed for $FP after 3 retries"
  exit 3
fi

SHOULD_CREATE="$(echo "$CLAIM_RESP" | jq -r '.should_create // false')"
if [[ "$SHOULD_CREATE" != "true" ]]; then
  REASON="$(echo "$CLAIM_RESP" | jq -r '.reason // "unknown"')"
  echo "[issue-rec] skipped: $REASON"
  slack_notify "[issue-rec]" "skipped: $REASON for $TASK_ID"
  exit 0
fi

# Compose body and create issue
FINAL_BODY="$(format_body "$OWNER_TAG" "$BODY_TEXT" "issue-recurring" "${SEED}-${YEAR_WEEK}" "$FP")"

ISSUE_NUM=""
for attempt in 1 2 3; do
  ISSUE_URL="$(gh issue create --title "$TITLE" --body "$FINAL_BODY" 2>/dev/null)" || ISSUE_URL=""
  if [[ -n "$ISSUE_URL" ]]; then
    ISSUE_NUM="$(echo "$ISSUE_URL" | grep -oE '[0-9]+$')"
    break
  fi
  sleep $((2 ** attempt))
done

if [[ -z "$ISSUE_NUM" ]]; then
  # release claim (3 retry)
  for r in 1 2 3; do
    dedup_release "$CLAIM_ID" "gh issue create failed after 3 retries" >/dev/null && break
    sleep $((2 ** r))
  done
  slack_notify "[critical]" "issue-rec: gh issue create failed for $TASK_ID ($REPO)"
  exit 1
fi

# finalize (3 retry)
for f in 1 2 3; do
  if dedup_finalize "$CLAIM_ID" "$ISSUE_NUM" >/dev/null; then
    slack_notify "[issue-rec]" "created #$ISSUE_NUM for $TASK_ID ($REPO)"
    exit 0
  fi
  sleep $((2 ** f))
done

# finalize 3 retry failed — patch issue with [draft] for operator manual finalize
gh issue edit "$ISSUE_NUM" --add-label "[draft]" >/dev/null 2>&1 || true
slack_notify "[critical]" "issue-rec: finalize failed for #$ISSUE_NUM, claim_id=$CLAIM_ID, manual finalize required"
exit 1
