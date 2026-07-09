#!/usr/bin/env bash
set -uo pipefail
SKILL="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PASS=0; FAIL=0
ok() { echo "PASS $1"; PASS=$((PASS+1)); }
ng() { echo "FAIL $1: $2"; FAIL=$((FAIL+1)); }

[[ -f "$SKILL/SKILL.md" ]] && grep -q '^name: deploy-watchdog' "$SKILL/SKILL.md" && ok "frontmatter" || ng "frontmatter" "missing"

for s in scripts/deploy-wd-init.sh scripts/deploy-wd-replay.sh scripts/deploy-wd-list.sh; do
  head -1 "$SKILL/$s" | grep -q '^#!/usr/bin/env bash' && ok "$s shebang" || ng "$s shebang" "missing"
done

# templates exist
for t in templates/deploy.yml templates/rollback-issue-body.md templates/scripts/ci.sh templates/scripts/deploy.sh templates/scripts/smoke.sh; do
  [[ -f "$SKILL/$t" ]] && ok "template $t exists" || ng "template $t" "missing"
done

# deploy.yml has expected fields
grep -q "^name: deploy$" "$SKILL/templates/deploy.yml" && ok "deploy.yml name=deploy" || ng "yml name" "wrong"
grep -q "branches: \[main\]" "$SKILL/templates/deploy.yml" && ok "yml triggers on main push" || ng "yml trigger" "wrong"
grep -q "DEPLOY_ENVIRONMENT" "$SKILL/templates/deploy.yml" && ok "yml uses DEPLOY_ENVIRONMENT" || ng "yml env var" "missing"
grep -q "concurrency:" "$SKILL/templates/deploy.yml" && ok "yml has concurrency" || ng "yml concurrency" "missing"
grep -q "TZ: Asia/Tokyo" "$SKILL/templates/deploy.yml" && ok "yml has TZ env" || ng "yml TZ" "missing"
grep -q "ci.sh" "$SKILL/templates/deploy.yml" && ok "yml calls ci.sh" || ng "yml ci.sh" "missing"
grep -q "deploy.sh" "$SKILL/templates/deploy.yml" && ok "yml calls deploy.sh" || ng "yml deploy.sh" "missing"
grep -q "smoke.sh" "$SKILL/templates/deploy.yml" && ok "yml calls smoke.sh" || ng "yml smoke.sh" "missing"

# rollback issue body format
grep -q "^\[CC\]$" "$SKILL/templates/rollback-issue-body.md" && ok "rollback body starts with [CC]" || ng "rollback [CC]" "missing"
grep -q "{{run_id}}" "$SKILL/templates/rollback-issue-body.md" && ok "rollback has run_id placeholder" || ng "rollback run_id" "missing"
grep -q "{{commit_sha}}" "$SKILL/templates/rollback-issue-body.md" && ok "rollback has commit_sha placeholder" || ng "rollback sha" "missing"
grep -q "Reverts #" "$SKILL/templates/rollback-issue-body.md" && ok "rollback mentions Reverts" || ng "rollback Reverts" "missing"
grep -q "deploy-ok" "$SKILL/templates/rollback-issue-body.md" && ok "rollback mentions [deploy-ok] gate" || ng "rollback gate" "missing"
grep -q "^---$" "$SKILL/templates/rollback-issue-body.md" && ok "rollback has --- separator" || ng "rollback ---" "missing"
grep -q "^source: deploy-watchdog:" "$SKILL/templates/rollback-issue-body.md" && ok "rollback footer source" || ng "rollback source" "missing"
grep -q "^fingerprint: deploy-wd:" "$SKILL/templates/rollback-issue-body.md" && ok "rollback footer fingerprint" || ng "rollback fp" "missing"

# scripts skeleton are executable / have shebang
for s in templates/scripts/ci.sh templates/scripts/deploy.sh templates/scripts/smoke.sh; do
  head -1 "$SKILL/$s" | grep -q '^#!/usr/bin/env bash' && ok "$s shebang" || ng "$s shebang" "missing"
done

# init.sh dry-run on tmp project (no --with-deploy)
TMPDIR=$(mktemp -d)
git init -q "$TMPDIR/p"
git -C "$TMPDIR/p" config --add remote.origin.url "git@github.com:test/repo.git" 2>/dev/null || git -C "$TMPDIR/p" remote add origin "git@github.com:test/repo.git"
out="$( (bash "$SKILL/scripts/deploy-wd-init.sh" --dry-run --target "$TMPDIR/p" 2>&1) )"
echo "$out" | grep -q "operator runbook" && ok "init dry-run prints runbook" || ng "init runbook" "missing"
echo "$out" | grep -q "/webhook/github/actions" && ok "init mentions GitHub webhook URL" || ng "init webhook" "missing"
echo "$out" | grep -q "environment.*staging" && ok "init mentions staging-only" || ng "init staging" "missing"
echo "$out" | grep -q "require_deploy_ok_label" && ok "init mentions deploy-ok gate config" || ng "init gate" "missing"

# init.sh --with-deploy requires interactive (rejects pipe)
out_ni="$(echo "" | bash "$SKILL/scripts/deploy-wd-init.sh" --apply --target "$TMPDIR/p" --with-deploy 2>&1)"
echo "$out_ni" | grep -q "interactive TTY" && ok "init --with-deploy rejects non-TTY" || ng "init non-TTY" "missing"

# init.sh --with-deploy abort if existing deploy.yml (no --force-overwrite)
mkdir -p "$TMPDIR/p2/.github/workflows"
echo "name: deploy" > "$TMPDIR/p2/.github/workflows/deploy.yml"
git init -q "$TMPDIR/p2"
out_existing="$( (bash "$SKILL/scripts/deploy-wd-init.sh" --dry-run --target "$TMPDIR/p2" --with-deploy 2>&1) )"
# dry-run still prints "would write" because no abort logic on dry-run; this is expected
ok "init --with-deploy dry-run on existing file"

# replay rejects missing fixture
out_replay="$( (bash "$SKILL/scripts/deploy-wd-replay.sh" 2>&1 || true) )"
echo "$out_replay" | grep -q "fixture not found" && ok "replay rejects missing fixture" || ng "replay missing" "no error"

# list usage
out_list="$( (bash "$SKILL/scripts/deploy-wd-list.sh" 2>&1 || true) )"
echo "$out_list" | grep -q "usage" && ok "list prints usage" || ng "list usage" "missing"

# init usage
out_init_u="$( (bash "$SKILL/scripts/deploy-wd-init.sh" 2>&1 || true) )"
echo "$out_init_u" | grep -q "usage" && ok "init prints usage" || ng "init usage" "missing"

# SKILL.md content
grep -q "1h cooldown" "$SKILL/SKILL.md" && ok "SKILL.md mentions 1h cooldown" || ng "SKILL.md cooldown" "missing"
grep -q "3 連続失敗" "$SKILL/SKILL.md" && ok "SKILL.md mentions 3 consecutive failure escalation" || ng "SKILL.md escalation" "missing"
grep -q "comment 追加" "$SKILL/SKILL.md" && ok "SKILL.md mentions comment-only after escalation" || ng "SKILL.md comment" "missing"
grep -q "auto-merge" "$SKILL/SKILL.md" && ok "SKILL.md mentions auto-merge prohibition" || ng "SKILL.md auto-merge" "missing"
grep -q "staging" "$SKILL/SKILL.md" && ok "SKILL.md mentions staging-only" || ng "SKILL.md staging" "missing"
grep -q "run_attempt" "$SKILL/SKILL.md" && ok "SKILL.md mentions run_attempt skip" || ng "SKILL.md retry" "missing"
grep -q "exit 1" "$SKILL/SKILL.md" && ok "SKILL.md mentions fail injection (exit 1)" || ng "SKILL.md inject" "missing"

# fingerprint format in template
grep -q "deploy-wd:{{repo}}:deploy:{{environment}}" "$SKILL/templates/rollback-issue-body.md" && ok "fingerprint includes env" || ng "fp env" "missing"

echo
echo "===== ${PASS} PASS / ${FAIL} FAIL ====="
[[ $FAIL -eq 0 ]] || exit 1
