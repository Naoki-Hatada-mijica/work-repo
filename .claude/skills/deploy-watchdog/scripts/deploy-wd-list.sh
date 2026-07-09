#!/usr/bin/env bash
# deploy-wd-list.sh — list past rollback issues for the project
set -uo pipefail
LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../_lib" && pwd)"
# shellcheck disable=SC1091
source "$LIB_DIR/secrets.sh"

TARGET=""; SINCE="30d"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --target) TARGET="$2"; shift 2 ;;
    --since) SINCE="$2"; shift 2 ;;
    *) shift ;;
  esac
done
[[ -z "$TARGET" ]] && { echo "usage: $0 --target <project> [--since 30d]" >&2; exit 2; }

REPO="$(cd "$TARGET" && git config --get remote.origin.url | sed -E 's#.*[/:]([^/]+/[^/]+)\.git$#\1#')"
BASE="${RECEIVER_BASE_URL:-}"
[[ -z "$BASE" ]] && { echo "RECEIVER_BASE_URL not set" >&2; exit 2; }
SECRET="$(secret_get webhook_receiver_shared_secret)" || exit 2

BODY="$(jq -nc --arg repo "$REPO" --arg since "$SINCE" '{repo:$repo, since:$since, source_filter:"deploy-watchdog"}')"
SIG="$(printf '%s' "$BODY" | openssl dgst -sha256 -hmac "$SECRET" -hex | awk '{print $NF}')"
curl -fsS -m 10 -X POST -H "X-Mijica-Signature: $SIG" -H 'content-type: application/json' \
  -d "$BODY" "${BASE}/api/state/recent-issues" | jq .
