#!/usr/bin/env bash
# issue-rec-init.sh — apply recurring-tasks workflow + config to a project
#
# usage:
#   issue-rec-init.sh --dry-run --target <project>
#   issue-rec-init.sh --apply --target <project> [--force-overwrite]
#
# Behavior:
#   - timezone literal: "Asia/Tokyo" (Round 3 C4 / v0)
#   - converts each task's local_time (JST) → cron (UTC) and embeds in workflow yml
#   - workflow yml has `# DO NOT EDIT` header + `# config-hash:` line
#   - default abort if workflow yml exists; --force-overwrite to replace

set -uo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TPL_DIR="${SKILL_DIR}/templates"

MODE=""
TARGET=""
FORCE=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run) MODE="dry"; shift ;;
    --apply)   MODE="apply"; shift ;;
    --target)  TARGET="$2"; shift 2 ;;
    --force-overwrite) FORCE=1; shift ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done

[[ -z "$MODE" || -z "$TARGET" ]] && {
  echo "usage: $0 --dry-run|--apply --target <project> [--force-overwrite]" >&2
  exit 2
}

# Interactive only when applying
if [[ "$MODE" == "apply" && ! -t 0 ]]; then
  echo "issue-rec-init: --apply requires interactive TTY (TTY check failed)" >&2
  exit 2
fi

[[ -d "$TARGET" ]] || { echo "target dir not found: $TARGET" >&2; exit 2; }

CONFIG_PATH="$TARGET/.github/recurring-tasks.toml"
WORKFLOW_PATH="$TARGET/.github/workflows/recurring-issues.yml"

# Phase 1 of plan: place config template if missing
if [[ ! -f "$CONFIG_PATH" ]]; then
  if [[ "$MODE" == "dry" ]]; then
    echo "[dry-run] would create $CONFIG_PATH from template"
  else
    mkdir -p "$(dirname "$CONFIG_PATH")"
    cp "$TPL_DIR/recurring-config.toml" "$CONFIG_PATH"
    echo "[apply] created $CONFIG_PATH"
  fi
else
  echo "[note] $CONFIG_PATH already exists; preserving"
fi

# Phase 2: generate workflow yml (only if config has at least one task)
if [[ -f "$CONFIG_PATH" ]]; then
  TZ_NAME="$(python3 -c "import tomllib,sys; print(tomllib.load(open('$CONFIG_PATH','rb')).get('meta',{}).get('timezone',''))")"
  if [[ "$TZ_NAME" != "Asia/Tokyo" ]]; then
    echo "[error] timezone must be 'Asia/Tokyo' (v0 only), got '$TZ_NAME'" >&2
    exit 2
  fi

  # Compute config hash
  CONFIG_HASH="$(sha256sum "$CONFIG_PATH" | cut -c1-12)"

  # Generate workflow yml content
  generate_workflow() {
    local hash="$1"
    cat <<EOF
# DO NOT EDIT — regenerated from .github/recurring-tasks.toml by issue-rec-init.sh
# config-hash: ${hash}
name: recurring-issues

on:
  schedule:
EOF
    # Each task's cron (JST → UTC)
    python3 - "$CONFIG_PATH" <<'PY'
import sys, tomllib, re
data = tomllib.load(open(sys.argv[1], 'rb'))
DAY = {'MON':1,'TUE':2,'WED':3,'THU':4,'FRI':5,'SAT':6,'SUN':0}
for t in data.get('task', []):
    lt = t.get('local_time','')
    m = re.match(r'^(MON|TUE|WED|THU|FRI|SAT|SUN)\s+(\d{1,2}):(\d{2})$', lt.strip())
    if not m:
        continue
    day, hour, minute = m.group(1), int(m.group(2)), int(m.group(3))
    # JST → UTC: UTC = JST - 9h
    utc_hour = (hour - 9) % 24
    # if hour rolls over (negative), shift day back
    day_shift = -1 if hour - 9 < 0 else 0
    days_order = ['SUN','MON','TUE','WED','THU','FRI','SAT']
    cron_dow = (DAY[day] + day_shift) % 7
    print(f"    - cron: '{minute} {utc_hour} * * {cron_dow}'")
PY
    cat <<'EOF'

  workflow_dispatch:
    inputs:
      task_id:
        description: 'task id (matches recurring-tasks.toml)'
        required: true

permissions:
  contents: read
  issues: write

jobs:
  create:
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
      matrix:
        task_id:
EOF
    python3 - "$CONFIG_PATH" <<'PY'
import sys, tomllib
data = tomllib.load(open(sys.argv[1], 'rb'))
for t in data.get('task', []):
    print(f"          - {t.get('id')}")
PY
    cat <<'EOF'
    steps:
      - uses: actions/checkout@v4
      - name: Setup
        run: |
          curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg
          echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list >/dev/null
          sudo apt update && sudo apt install -y gh jq curl
      - name: Issue create
        env:
          RECEIVER_BASE_URL: ${{ vars.RECEIVER_BASE_URL }}
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          # secret_get fallback path inside CI: env-var injection
          WEBHOOK_RECEIVER_SHARED_SECRET: ${{ secrets.WEBHOOK_RECEIVER_SHARED_SECRET }}
        run: |
          # In CI we don't have ~/.claude/skills/_lib symlink; clone or pull from skill repo.
          git clone --depth 1 https://github.com/hiroshiiiiiiiii/claude_global_settings.git /tmp/cgs
          chmod +x /tmp/cgs/skills/issue-recurring/scripts/issue-rec-create.sh
          # Set up local secrets fallback for secret_get
          mkdir -p ~/.config/claude/secrets
          chmod 700 ~/.config/claude/secrets
          printf '%s' "$WEBHOOK_RECEIVER_SHARED_SECRET" > ~/.config/claude/secrets/webhook_receiver_shared_secret
          chmod 600 ~/.config/claude/secrets/webhook_receiver_shared_secret
          bash /tmp/cgs/skills/issue-recurring/scripts/issue-rec-create.sh "${{ matrix.task_id }}"
EOF
  }

  if [[ -f "$WORKFLOW_PATH" ]]; then
    EXISTING_HASH="$(grep -oE 'config-hash: [a-f0-9]+' "$WORKFLOW_PATH" | head -1 | awk '{print $2}')"
    if [[ "$EXISTING_HASH" == "$CONFIG_HASH" ]]; then
      echo "[note] workflow yml already up-to-date (config-hash: $CONFIG_HASH)"
    elif [[ $FORCE -eq 1 ]]; then
      if [[ "$MODE" == "dry" ]]; then
        echo "[dry-run] would regenerate $WORKFLOW_PATH (config-hash mismatch, force)"
      else
        cp "$WORKFLOW_PATH" "${WORKFLOW_PATH}.bak.$(date -u +%Y%m%d-%H%M%S)"
        generate_workflow "$CONFIG_HASH" > "$WORKFLOW_PATH"
        echo "[apply] regenerated $WORKFLOW_PATH (config-hash: $CONFIG_HASH)"
      fi
    else
      echo "[abort] $WORKFLOW_PATH exists with old config-hash ($EXISTING_HASH != $CONFIG_HASH)" >&2
      echo "        rerun with --force-overwrite to regenerate" >&2
      exit 2
    fi
  else
    if [[ "$MODE" == "dry" ]]; then
      echo "[dry-run] would create $WORKFLOW_PATH (config-hash: $CONFIG_HASH)"
    else
      mkdir -p "$(dirname "$WORKFLOW_PATH")"
      generate_workflow "$CONFIG_HASH" > "$WORKFLOW_PATH"
      echo "[apply] created $WORKFLOW_PATH (config-hash: $CONFIG_HASH)"
    fi
  fi
fi

echo "[done] issue-rec-init mode=$MODE target=$TARGET"
