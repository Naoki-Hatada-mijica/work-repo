#!/usr/bin/env bash
# smoke.sh — issue-from-monitoring (operator-side scripts only; receiver tested separately)
set -uo pipefail
SKILL="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PASS=0; FAIL=0
ok() { echo "PASS $1"; PASS=$((PASS+1)); }
ng() { echo "FAIL $1: $2"; FAIL=$((FAIL+1)); }

[[ -f "$SKILL/SKILL.md" ]] && grep -q '^name: issue-from-monitoring' "$SKILL/SKILL.md" && ok "SKILL.md frontmatter" || ng "SKILL.md" "missing"

for s in scripts/issue-mon-init.sh scripts/issue-mon-replay.sh scripts/issue-mon-create.sh; do
  head -1 "$SKILL/$s" | grep -q '^#!/usr/bin/env bash' && ok "$s shebang" || ng "$s" "shebang"
done

# init dry-run prints operator action items
TMPDIR=$(mktemp -d); git init -q "$TMPDIR/p"
out="$(bash "$SKILL/scripts/issue-mon-init.sh" --dry-run --target "$TMPDIR/p" 2>&1)"
echo "$out" | grep -q "operator action items" && ok "init prints operator runbook" || ng "init runbook" "no items"
echo "$out" | grep -q "/webhook/sentry" && ok "init mentions sentry endpoint" || ng "init sentry" "missing"
echo "$out" | grep -q "/webhook/security-audit" && ok "init mentions secaudit endpoint" || ng "init secaudit" "missing"
echo "$out" | grep -q "/webhook/github/actions" && ok "init mentions github actions endpoint" || ng "init gha" "missing"
echo "$out" | grep -q "WEBHOOK_RECEIVER_SHARED_SECRET" && ok "init mentions HMAC secret" || ng "init secret" "missing"

# fingerprint seed coverage in SKILL.md
for src in sentry secaudit gha; do
  grep -q "$src" "$SKILL/SKILL.md" && ok "SKILL.md mentions $src" || ng "SKILL.md $src" "missing"
done

# environment 必須化 hint
grep -q "environment" "$SKILL/SKILL.md" && ok "SKILL.md mentions environment in fingerprint" || ng "env fingerprint" "missing"

# 永久 sink 防止
grep -q "永久 sink\|comment 追加" "$SKILL/SKILL.md" && ok "SKILL.md mentions sink防止" || ng "sink mention" "missing"

# replay fixture syntax (no fixture passed -> exit 2)
out2="$(bash "$SKILL/scripts/issue-mon-replay.sh" 2>&1 || true)"
echo "$out2" | grep -q "fixture not found" && ok "replay rejects missing fixture" || ng "replay missing" "no error"

# fingerprint helper used in create.sh
grep -q "compute_fingerprint" "$SKILL/scripts/issue-mon-create.sh" && ok "create.sh uses compute_fingerprint" || ng "create.sh fp" "missing"

# claim/finalize/release in create.sh
grep -q "dedup_claim" "$SKILL/scripts/issue-mon-create.sh" && ok "create.sh uses dedup_claim" || ng "create.sh claim" "missing"
grep -q "dedup_finalize" "$SKILL/scripts/issue-mon-create.sh" && ok "create.sh uses dedup_finalize" || ng "create.sh finalize" "missing"
grep -q "dedup_release" "$SKILL/scripts/issue-mon-create.sh" && ok "create.sh uses dedup_release" || ng "create.sh release" "missing"

# critical Slack notify on fail
grep -q '\[critical\]' "$SKILL/scripts/issue-mon-create.sh" && ok "create.sh notifies critical on fail" || ng "create.sh critical" "missing"

# format_body usage (footer skill-side, anti-injection)
grep -q "format_body" "$SKILL/scripts/issue-mon-create.sh" && ok "create.sh uses format_body" || ng "create.sh body" "missing"

# replay sends to /webhook/<adapter>
grep -q "/webhook/" "$SKILL/scripts/issue-mon-replay.sh" && ok "replay POSTs to /webhook/" || ng "replay endpoint" "missing"

# replay HMAC sign (X-Mijica-Signature)
grep -q "X-Mijica-Signature" "$SKILL/scripts/issue-mon-replay.sh" && ok "replay signs HMAC" || ng "replay sign" "missing"

# fingerprint seed env required (environment in seed examples)
grep -E ":<environment>|:<env>" "$SKILL/SKILL.md" >/dev/null && ok "fingerprint seed has env placeholder" || ng "fp seed env" "missing"

# 7d block + 24h cooldown documented
grep -q "7d\|24h" "$SKILL/SKILL.md" && ok "SKILL.md mentions cooldown durations" || ng "SKILL.md cooldown" "missing"

# init script accepts --target
init_out="$( (bash "$SKILL/scripts/issue-mon-init.sh" 2>&1 || true) )"
echo "$init_out" | grep -q "usage" && ok "init prints usage" || ng "init usage" "missing"

# create script accepts arguments (no positional → fail)
out3="$(bash "$SKILL/scripts/issue-mon-create.sh" 2>&1 || true)"
[[ -n "$out3" ]] && ok "create rejects missing args" || ng "create no args" "silent"

echo
echo "===== ${PASS} PASS / ${FAIL} FAIL ====="
[[ $FAIL -eq 0 ]] || exit 1
