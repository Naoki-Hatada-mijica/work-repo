#!/usr/bin/env bash
set -uo pipefail
SKILL="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PASS=0; FAIL=0
ok() { echo "PASS $1"; PASS=$((PASS+1)); }
ng() { echo "FAIL $1: $2"; FAIL=$((FAIL+1)); }

[[ -f "$SKILL/SKILL.md" ]] && grep -q '^name: issue-from-slack' "$SKILL/SKILL.md" && ok "frontmatter" || ng "frontmatter" "missing"

for s in scripts/issue-slack-init.sh scripts/issue-slack-list.sh; do
  head -1 "$SKILL/$s" | grep -q '^#!/usr/bin/env bash' && ok "$s shebang" || ng "$s shebang" "missing"
done

# init prints operator runbook
TMPDIR=$(mktemp -d); git init -q "$TMPDIR/p"
out="$( (bash "$SKILL/scripts/issue-slack-init.sh" --target "$TMPDIR/p" 2>&1) )"
echo "$out" | grep -q "Slack App 作成" && ok "init mentions Slack App setup" || ng "init Slack App" "missing"
echo "$out" | grep -q "/webhook/slack/events" && ok "init mentions Slack endpoint" || ng "init endpoint" "missing"
echo "$out" | grep -q "user_allowlist" && ok "init mentions allowlist" || ng "init allowlist" "missing"
echo "$out" | grep -q "team_id" && ok "init mentions team_id" || ng "init team_id" "missing"
echo "$out" | grep -q "allow_external_shared" && ok "init mentions allow_external_shared" || ng "init external_shared" "missing"
echo "$out" | grep -q "allow_private_only" && ok "init mentions private only" || ng "init private" "missing"
echo "$out" | grep -q "ANTHROPIC_API_KEY" && ok "init mentions Anthropic API key" || ng "init key" "missing"
echo "$out" | grep -q "pricing" && ok "init mentions pricing collection" || ng "init pricing" "missing"
echo "$out" | grep -q "rate_limit_duration" && ok "init mentions rate_limit" || ng "init ratelimit" "missing"

# init usage
init_usage="$( (bash "$SKILL/scripts/issue-slack-init.sh" 2>&1 || true) )"
echo "$init_usage" | grep -q "usage" && ok "init prints usage" || ng "init usage" "missing"

# list usage
list_usage="$( (bash "$SKILL/scripts/issue-slack-list.sh" 2>&1 || true) )"
echo "$list_usage" | grep -q "usage" && ok "list prints usage" || ng "list usage" "missing"

# SKILL.md content
grep -q "Cloud Tasks" "$SKILL/SKILL.md" && ok "SKILL.md mentions Cloud Tasks" || ng "SKILL.md tasks" "missing"
grep -q "min-instance=1" "$SKILL/SKILL.md" && ok "SKILL.md mentions min-instance=1" || ng "SKILL.md min-inst" "missing"
grep -q "claude-haiku-4-5" "$SKILL/SKILL.md" && ok "SKILL.md mentions claude-haiku-4-5" || ng "SKILL.md model" "missing"
grep -q "3s ack" "$SKILL/SKILL.md" && ok "SKILL.md mentions 3s ack" || ng "SKILL.md 3s" "missing"
grep -q "raw fallback" "$SKILL/SKILL.md" && ok "SKILL.md mentions raw fallback" || ng "SKILL.md fallback" "missing"
grep -q '\[draft\]' "$SKILL/SKILL.md" && ok "SKILL.md mentions [draft] label" || ng "SKILL.md draft" "missing"
grep -q "kill switch" "$SKILL/SKILL.md" && ok "SKILL.md mentions kill switch" || ng "SKILL.md kill" "missing"
grep -q "cost cap" "$SKILL/SKILL.md" && ok "SKILL.md mentions cost cap" || ng "SKILL.md cap" "missing"
grep -q "allowlist 多重判定" "$SKILL/SKILL.md" && ok "SKILL.md mentions multi-criteria allowlist" || ng "SKILL.md allowlist" "missing"

# prompt template
[[ -f "$SKILL/prompts/format-prompt.txt" ]] && ok "format-prompt.txt exists" || ng "prompt" "missing"
grep -q "STRICTLY JSON" "$SKILL/prompts/format-prompt.txt" && ok "prompt requests strict JSON" || ng "prompt strict" "missing"
grep -q "suggested_owner_tag" "$SKILL/prompts/format-prompt.txt" && ok "prompt asks for owner_tag" || ng "prompt owner" "missing"
grep -q "Never output footer" "$SKILL/prompts/format-prompt.txt" && ok "prompt forbids footer (anti-injection)" || ng "prompt footer" "missing"
grep -q '\[CC\]\|\[CX\]\|\[?\]' "$SKILL/prompts/format-prompt.txt" && ok "prompt enumerates owner tags" || ng "prompt tags" "missing"

# rate_limit_duration validates
bash -c "source $SKILL/../_lib/duration.sh; validate_duration_string '30s'" && ok "duration 30s valid" || ng "duration" "fail"

# SKILL.md mentions multi-criteria for allowlist (user/team/bot/external)
grep -q "user_id" "$SKILL/SKILL.md" && grep -q "team_id" "$SKILL/SKILL.md" && grep -q "is_bot" "$SKILL/SKILL.md" && grep -q "is_external_shared" "$SKILL/SKILL.md" && ok "SKILL.md enumerates allowlist criteria" || ng "SKILL.md criteria" "missing"

echo
echo "===== ${PASS} PASS / ${FAIL} FAIL ====="
[[ $FAIL -eq 0 ]] || exit 1
