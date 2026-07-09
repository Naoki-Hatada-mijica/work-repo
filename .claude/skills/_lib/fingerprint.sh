#!/usr/bin/env bash
# fingerprint.sh — 12-char SHA256 fingerprint generator
#
# usage:
#   source _lib/fingerprint.sh
#   fp=$(compute_fingerprint "sentry:proj-abc:issue-123:production")

compute_fingerprint() {
  local seed="$1"
  if [[ -z "$seed" ]]; then
    echo "compute_fingerprint: seed required" >&2
    return 1
  fi
  printf '%s' "$seed" | sha256sum | cut -c1-12
}
