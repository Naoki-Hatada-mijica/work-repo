#!/usr/bin/env bash
# issue-slack-init.sh — Slack bot 設定確認 + Firestore allowlist 案内 (operator runbook)

set -uo pipefail
TARGET=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --target) TARGET="$2"; shift 2 ;;
    *) shift ;;
  esac
done

if [[ -z "$TARGET" ]]; then
  echo "usage: $0 --target <project>" >&2
  exit 2
fi

REPO="$(cd "$TARGET" && git config --get remote.origin.url 2>/dev/null | sed -E 's#.*[/:]([^/]+/[^/]+)\.git$#\1#')"

cat <<EOF
[issue-slack-init] target: $TARGET ($REPO)

operator action items:
  1. Slack App 作成 (https://api.slack.com/apps):
     - Events API enabled
     - Request URL: https://<receiver-slack-host>/webhook/slack/events
     - Bot token scopes: chat:write, channels:history, im:history, groups:history, app_mentions:read
     - Subscribed events: message.channels, message.groups, message.im

  2. Slack signing secret を GCP Secret Manager に登録:
     gcloud secrets create SLACK_SIGNING_SECRET_CURRENT --data-file=-

  3. Firestore repo_config/$REPO.slack_config に設定:
     {
       "channel_id": "C0XXXXX",
       "user_allowlist": ["U0AAAA", "U0BBBB"],
       "team_id": "T0XXXXX",
       "allow_external_shared": false,
       "allow_bot": false,
       "allow_private_only": true,
       "rate_limit_duration": "30s",
       "default_owner_tag": "",
       "labels_default": []
     }

  4. claude-haiku-4-5 API key を GCP Secret Manager:
     gcloud secrets create ANTHROPIC_API_KEY_CURRENT --data-file=-

  5. Firestore pricing/claude-haiku-4-5:v$(date -u +%Y-%m) に最新単価を commit (operator 月初手動)

EOF
