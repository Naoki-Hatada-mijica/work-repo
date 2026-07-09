#!/usr/bin/env bash
# issue-mon-create.sh — operator local manual issue creation (replay fixture)
#
# usage: issue-mon-create.sh <skill_subname> <fingerprint_seed> <repo> <title> <body> [owner_tag]

set -uo pipefail

LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../_lib" && pwd)"
# shellcheck disable=SC1091
source "$LIB_DIR/issue-dedup.sh"
# shellcheck disable=SC1091
source "$LIB_DIR/issue-body.sh"
# shellcheck disable=SC1091
source "$LIB_DIR/fingerprint.sh"
# shellcheck disable=SC1091
source "$LIB_DIR/slack-notify.sh"

SUB="$1"; SEED="$2"; REPO="$3"; TITLE="$4"; BODY_TEXT="$5"; OWNER="${6:-}"
FP="$(compute_fingerprint "$SEED")"
CID="$(uuidgen)"
PAYLOAD="$(jq -nc --arg t "$TITLE" --arg b "$BODY_TEXT" '{title:$t, body:$b, labels:[]}')"

resp="$(dedup_claim "issue-from-monitoring:${SUB}" "$FP" "$REPO" "$PAYLOAD" "$CID")" || {
  echo "claim failed" >&2; exit 3
}
sc="$(echo "$resp" | jq -r .should_create)"
if [[ "$sc" != "true" ]]; then
  echo "[issue-mon] skip: $(echo "$resp" | jq -r .reason)"; exit 0
fi

FINAL="$(format_body "$OWNER" "$BODY_TEXT" "issue-from-monitoring:${SUB}" "$SEED" "$FP")"
url="$(GH_REPO="$REPO" gh issue create -R "$REPO" --title "$TITLE" --body "$FINAL" 2>/dev/null)" || {
  dedup_release "$CID" "gh failed" >/dev/null 2>&1 || true
  slack_notify "[critical]" "issue-mon manual create failed for $REPO"
  exit 1
}
num="${url##*/}"
dedup_finalize "$CID" "$num" >/dev/null
slack_notify "[issue-mon]" "manual created #$num for $REPO ($SUB)"
