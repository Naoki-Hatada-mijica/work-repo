#!/usr/bin/env bash
# backpressure.sh — Firestore counter-based backpressure check (via receiver)
#
# Round 2 W2: do not call `gh issue list` directly (rate limit + AND filter pitfall).

# shellcheck disable=SC1091
SCRIPT_DIR_BP="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR_BP/secrets.sh"

# check_backpressure <repo> [bypass_backpressure]
# returns 0 if OK to issue, 1 if backpressure tripped, 2 on network error
check_backpressure() {
  local repo="$1" bypass="${2:-false}"
  local base_url="${RECEIVER_BASE_URL:-}"
  if [[ -z "$base_url" ]]; then
    return 0  # local dev — fail open
  fi
  local secret
  secret="$(secret_get webhook_receiver_shared_secret)" || return 2

  local body
  body="$(jq -nc --arg repo "$repo" '{repo:$repo}')"
  local sig
  sig="$(printf '%s' "$body" | openssl dgst -sha256 -hmac "$secret" -hex | awk '{print $NF}')"

  local resp
  resp="$(curl -fsS -m 10 -X POST \
            -H 'content-type: application/json' \
            -H "X-Mijica-Signature: $sig" \
            -d "$body" \
            "${base_url}/api/state/pending-count" 2>/dev/null)" || return 2

  local count max
  count="$(printf '%s' "$resp" | jq -r '.count // 0')"
  max="$(printf '%s' "$resp" | jq -r '.max // 10')"

  if [[ "$bypass" == "true" ]]; then
    # bypass is allowed but rate-limited on the receiver side
    return 0
  fi

  if (( count >= max )); then
    return 1
  fi
  return 0
}
