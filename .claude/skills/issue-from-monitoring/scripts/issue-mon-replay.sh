#!/usr/bin/env bash
# issue-mon-replay.sh — replay a fixture JSON to local receiver (testing)
#
# usage: issue-mon-replay.sh <fixture.json> [adapter]

set -uo pipefail

LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../_lib" && pwd)"
# shellcheck disable=SC1091
source "$LIB_DIR/secrets.sh"

FIXTURE="${1:-}"
ADAPTER="${2:-sentry}"
[[ -f "$FIXTURE" ]] || { echo "fixture not found: $FIXTURE" >&2; exit 2; }

BASE="${RECEIVER_BASE_URL:-http://localhost:8080}"
SECRET="$(secret_get webhook_receiver_shared_secret 2>/dev/null || echo "")"

PAYLOAD="$(cat "$FIXTURE")"
SIG=""
if [[ -n "$SECRET" ]]; then
  SIG="$(printf '%s' "$PAYLOAD" | openssl dgst -sha256 -hmac "$SECRET" -hex | awk '{print $NF}')"
fi

echo "[replay] POST ${BASE}/webhook/${ADAPTER}"
curl -sS -m 30 -X POST \
     -H 'content-type: application/json' \
     ${SIG:+-H "X-Mijica-Signature: $SIG"} \
     -d "$PAYLOAD" \
     "${BASE}/webhook/${ADAPTER}" | jq .
