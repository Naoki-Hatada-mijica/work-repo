#!/usr/bin/env bash
# issue-rec-list.sh — pretty print recurring-tasks.toml + recent execution log

set -uo pipefail

TARGET=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --target) TARGET="$2"; shift 2 ;;
    *) shift ;;
  esac
done
[[ -z "$TARGET" ]] && { echo "usage: $0 --target <project>" >&2; exit 2; }

CONFIG_PATH="$TARGET/.github/recurring-tasks.toml"
[[ -f "$CONFIG_PATH" ]] || { echo "config not found: $CONFIG_PATH" >&2; exit 2; }

python3 - "$CONFIG_PATH" <<'PY'
import sys, tomllib
data = tomllib.load(open(sys.argv[1], 'rb'))
meta = data.get('meta', {})
print(f"timezone: {meta.get('timezone','(unset)')}")
print()
for t in data.get('task', []):
    print(f"- id: {t.get('id')}")
    print(f"  local_time: {t.get('local_time')}")
    print(f"  title: {t.get('title')}")
    print(f"  cooldown_duration: {t.get('cooldown_duration','24h')}")
    print(f"  monthly_limit: {t.get('monthly_limit','-')}")
    print(f"  fingerprint_seed: {t.get('fingerprint_seed')}")
    print(f"  owner_tag: {t.get('owner_tag','(empty)')}")
    print()
PY
