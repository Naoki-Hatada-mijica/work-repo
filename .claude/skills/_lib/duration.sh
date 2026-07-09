#!/usr/bin/env bash
# duration.sh — cooldown_duration string validator (skill side stub)
#
# Real parse is on receiver side (app/duration.py with humanfriendly).
# This lib only validates the format before sending to receiver.
#
# Accepted format: ^[0-9]+(s|m|h|d|w)$  (e.g. "30s", "1h", "6d", "1w")

validate_duration_string() {
  local s="$1"
  if [[ -z "$s" ]]; then
    echo "validate_duration_string: argument required" >&2
    return 1
  fi
  if [[ "$s" =~ ^[0-9]+(s|m|h|d|w)$ ]]; then
    return 0
  fi
  return 1
}
