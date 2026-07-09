#!/usr/bin/env bash
# slack-notify.sh — Slack webhook notify with prefix + critical channel routing
#
# usage:
#   source _lib/slack-notify.sh
#   slack_notify "[issue-rec]" "weekly task issued: #123"
#   slack_notify "[critical]" "Firestore unavailable in receiver"

# shellcheck disable=SC1091
SCRIPT_DIR_SLACK="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR_SLACK/secrets.sh"

slack_notify() {
  local prefix="$1"
  local message="$2"
  local webhook_name="slack_webhook_notification"

  if [[ -z "$prefix" || -z "$message" ]]; then
    echo "slack_notify: prefix and message required" >&2
    return 1
  fi

  case "$prefix" in
    '[critical]')
      webhook_name="slack_webhook_critical"
      ;;
  esac

  local webhook_url
  webhook_url="$(secret_get "$webhook_name")" || {
    # Fall back to non-critical webhook if dedicated critical not set
    if [[ "$webhook_name" == "slack_webhook_critical" ]]; then
      webhook_url="$(secret_get slack_webhook_notification)" || {
        echo "slack_notify: no webhook secret available" >&2
        return 2
      }
    else
      return 2
    fi
  }

  local payload
  payload="$(jq -nc --arg text "$prefix $message" '{text: $text}')"

  if curl -fsS -m 10 -X POST -H 'content-type: application/json' \
        -d "$payload" "$webhook_url" >/dev/null 2>&1; then
    return 0
  else
    return 1
  fi
}

# notify_critical_with_ack — post to [critical] channel; if no ack within
# `ack_timeout_seconds`, secondary path (Cloud Monitoring → Email) is expected
# to fire. This function returns immediately after the initial post.
notify_critical_with_ack() {
  local message="$1"
  local issue_number="${2:-0}"
  local ack_timeout="${3:-3600}"
  slack_notify "[critical]" "$message (issue=#${issue_number}, ack within ${ack_timeout}s)"
}
