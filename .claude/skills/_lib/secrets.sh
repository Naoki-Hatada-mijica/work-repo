#!/usr/bin/env bash
# secrets.sh — function-call style secret access (no export)
#
# usage:
#   source _lib/secrets.sh
#   SLACK_WEBHOOK="$(secret_get slack_webhook_notification)" curl ...
#
# Lookup order:
#   1. GCP Secret Manager (`gcloud secrets versions access latest --secret=<NAME>_CURRENT`)
#   2. ~/.config/claude/secrets/<name> (mode 700, local fallback)
#
# IMPORTANT: never `export` secrets. Use call-scoped env injection only.

secret_get() {
  local name="$1"
  if [[ -z "$name" ]]; then
    echo "secret_get: name required" >&2
    return 1
  fi

  # 1. GCP Secret Manager (Cloud Run / when gcloud is available + ADC works)
  if command -v gcloud >/dev/null 2>&1; then
    local upper
    upper="$(echo "$name" | tr '[:lower:]' '[:upper:]')_CURRENT"
    local val
    val="$(gcloud secrets versions access latest --secret="$upper" 2>/dev/null)" || val=""
    if [[ -n "$val" ]]; then
      printf '%s' "$val"
      return 0
    fi
  fi

  # 2. Local fallback
  local local_path="$HOME/.config/claude/secrets/$name"
  if [[ -f "$local_path" ]]; then
    # Enforce mode 700 on dir / 600 on file
    local mode
    mode="$(stat -c %a "$local_path" 2>/dev/null || stat -f %A "$local_path" 2>/dev/null || echo "")"
    if [[ "$mode" != "600" && "$mode" != "400" ]]; then
      echo "secret_get: $local_path must be mode 600 or 400 (got $mode)" >&2
      return 2
    fi
    cat "$local_path"
    return 0
  fi

  echo "secret_get: secret '$name' not found in Secret Manager or $local_path" >&2
  return 1
}
