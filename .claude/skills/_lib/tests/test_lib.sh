#!/usr/bin/env bash
# test_lib.sh — minimal unit tests for _lib/* (no receiver / no Firestore)
set -uo pipefail

LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck disable=SC1091
source "$LIB_DIR/fingerprint.sh"
# shellcheck disable=SC1091
source "$LIB_DIR/duration.sh"
# shellcheck disable=SC1091
source "$LIB_DIR/issue-body.sh"

PASS=0
FAIL=0

assert_eq() {
  local got="$1" want="$2" name="$3"
  if [[ "$got" == "$want" ]]; then
    echo "PASS $name"
    PASS=$((PASS + 1))
  else
    echo "FAIL $name: got=[$got] want=[$want]"
    FAIL=$((FAIL + 1))
  fi
}

assert_rc() {
  local rc="$1" want="$2" name="$3"
  if [[ "$rc" -eq "$want" ]]; then
    echo "PASS $name"
    PASS=$((PASS + 1))
  else
    echo "FAIL $name: rc=$rc want=$want"
    FAIL=$((FAIL + 1))
  fi
}

# fingerprint
fp1="$(compute_fingerprint "test-seed")"
assert_eq "${#fp1}" "12" "fingerprint length 12"
fp2="$(compute_fingerprint "test-seed")"
assert_eq "$fp1" "$fp2" "fingerprint deterministic"
fp3="$(compute_fingerprint "different-seed")"
[[ "$fp1" != "$fp3" ]] && { echo "PASS fingerprint different seed"; PASS=$((PASS+1)); } || { echo "FAIL fingerprint different seed"; FAIL=$((FAIL+1)); }

# duration
validate_duration_string "30s"; assert_rc "$?" "0" "duration 30s ok"
validate_duration_string "1h";  assert_rc "$?" "0" "duration 1h ok"
validate_duration_string "6d";  assert_rc "$?" "0" "duration 6d ok"
validate_duration_string "1w";  assert_rc "$?" "0" "duration 1w ok"
validate_duration_string "abc"; assert_rc "$?" "1" "duration abc rejected"
validate_duration_string "30";  assert_rc "$?" "1" "duration 30 (no unit) rejected"
validate_duration_string "";    assert_rc "$?" "1" "duration empty rejected"

# issue-body
body="$(format_body "[CC]" "Hello world" "issue-rec" "weekly-1" "abc123def456")"
expected="[CC]

Hello world

---
source: issue-rec:weekly-1
fingerprint: abc123def456"
assert_eq "$body" "$expected" "format_body with [CC]"

body2="$(format_body "" "Plain text" "x" "y" "z")"
expected2="Plain text

---
source: x:y
fingerprint: z"
assert_eq "$body2" "$expected2" "format_body with empty owner_tag"

tag="$(extract_owner_tag "[CC]
body line")"
assert_eq "$tag" "[CC]" "extract_owner_tag [CC]"

tag2="$(extract_owner_tag "[?]
body")"
assert_eq "$tag2" "[?]" "extract_owner_tag [?]"

tag3="$(extract_owner_tag "no tag here
body")"
assert_eq "$tag3" "" "extract_owner_tag no tag returns empty"

echo
echo "===== ${PASS} PASS / ${FAIL} FAIL ====="
[[ "$FAIL" -eq 0 ]] || exit 1
