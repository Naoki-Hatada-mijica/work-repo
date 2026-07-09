#!/usr/bin/env bash
# deploy-wd-replay.sh — fixture replay (workflow_run failed event)
set -uo pipefail
LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../_lib" && pwd)"
# shellcheck disable=SC1091
source "$LIB_DIR/secrets.sh"

FIXTURE="${1:-}"
[[ -f "$FIXTURE" ]] || { echo "fixture not found: $FIXTURE" >&2; exit 2; }
BASE="${RECEIVER_BASE_URL:-http://localhost:8080}"
SECRET="$(secret_get webhook_receiver_shared_secret 2>/dev/null || echo "")"
PAYLOAD="$(cat "$FIXTURE")"
SIG=""
[[ -n "$SECRET" ]] && SIG="$(printf '%s' "$PAYLOAD" | openssl dgst -sha256 -hmac "$SECRET" -hex | awk '{print $NF}')"
echo "[replay] POST ${BASE}/webhook/github/actions"
curl -sS -m 30 -X POST -H 'content-type: application/json' \
  ${SIG:+-H "X-Mijica-Signature: $SIG"} -d "$PAYLOAD" \
  "${BASE}/webhook/github/actions" | jq .
