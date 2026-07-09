#!/usr/bin/env bash
# kill-switch.sh — Firestore kill_switch/global + per-skill check (via receiver)
#
# usage:
#   source _lib/kill-switch.sh
#   check_kill_switch "issue-recurring" || exit 0

# shellcheck disable=SC1091
SCRIPT_DIR_KILL="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR_KILL/secrets.sh"

# returns 0 if not killed (caller continues), 1 if killed (caller exits 0)
check_kill_switch() {
  local skill_name="${1:-}"
  local base_url="${RECEIVER_BASE_URL:-}"
  if [[ -z "$base_url" ]]; then
    # No receiver configured (local dev) — fail open
    return 0
  fi
  local secret
  secret="$(secret_get webhook_receiver_shared_secret)" || {
    echo "check_kill_switch: secret unavailable, fail-open" >&2
    return 0
  }

  local url="${base_url}/api/kill-switch"
  if [[ -n "$skill_name" ]]; then
    url="${url}?skill=${skill_name}"
  fi

  local resp
  resp="$(curl -fsS -m 10 -H "X-Mijica-Signature: $(_kill_switch_sign "$url" "$secret")" "$url" 2>/dev/null)" || {
    # Network failure — fail open (do not block work)
    return 0
  }

  local global_enabled skill_enabled
  global_enabled="$(printf '%s' "$resp" | jq -r '.global.enabled // false')"
  skill_enabled="$(printf '%s' "$resp" | jq -r '.skill.enabled // false')"

  if [[ "$global_enabled" == "true" || "$skill_enabled" == "true" ]]; then
    return 1
  fi
  return 0
}

# Internal: simple HMAC-SHA256 over URL (for kill-switch GET; skill-side cheap impl)
_kill_switch_sign() {
  local payload="$1"
  local secret="$2"
  printf '%s' "$payload" | openssl dgst -sha256 -hmac "$secret" -hex | awk '{print $NF}'
}
