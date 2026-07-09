#!/usr/bin/env bash
# issue-slack-list.sh — query receiver for last N hours of Slack-issued events

set -uo pipefail
LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../_lib" && pwd)"
# shellcheck disable=SC1091
source "$LIB_DIR/secrets.sh"

TARGET=""; SINCE="24h"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --target) TARGET="$2"; shift 2 ;;
    --since) SINCE="$2"; shift 2 ;;
    *) shift ;;
  esac
done

[[ -z "$TARGET" ]] && { echo "usage: $0 --target <project> [--since 24h]" >&2; exit 2; }

REPO="$(cd "$TARGET" && git config --get remote.origin.url | sed -E 's#.*[/:]([^/]+/[^/]+)\.git$#\1#')"
BASE="${RECEIVER_BASE_URL:-}"
[[ -z "$BASE" ]] && { echo "RECEIVER_BASE_URL not set" >&2; exit 2; }

SECRET="$(secret_get webhook_receiver_shared_secret)" || exit 2
BODY="$(jq -nc --arg repo "$REPO" --arg since "$SINCE" '{repo:$repo, since:$since, source_filter:"issue-from-slack"}')"
SIG="$(printf '%s' "$BODY" | openssl dgst -sha256 -hmac "$SECRET" -hex | awk '{print $NF}')"

curl -fsS -m 10 -X POST -H "X-Mijica-Signature: $SIG" -H 'content-type: application/json' \
  -d "$BODY" "${BASE}/api/state/recent-issues" | jq .
