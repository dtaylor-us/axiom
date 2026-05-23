#!/usr/bin/env bash
# fitness/run-all.sh — Execute every fitness function and fail the build if any fail.
#
# Each fitness function is a self-contained script that exits 0 on PASS or 1 on FAIL.
# This wrapper collects results across all functions and exits 1 if ANY function failed,
# so a single command can gate the CI build on all ADL fitness requirements.
#
# Usage:
#   bash fitness/run-all.sh              # from the repo root
#   bash fitness/run-all.sh --fail-fast  # stop after the first failure

set -uo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
FAIL_FAST=false

for arg in "$@"; do
  if [ "$arg" = "--fail-fast" ]; then
    FAIL_FAST=true
  fi
done

PASSED=0
FAILED=0
declare -a FAILED_FUNCTIONS=()

run_function() {
  local script="$1"
  local name
  name="$(basename "$script" .sh)"

  echo ""
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "  RUNNING: $name"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

  if bash "$script"; then
    echo "  RESULT: PASS"
    PASSED=$((PASSED + 1))
  else
    echo "  RESULT: FAIL  ← $name"
    FAILED=$((FAILED + 1))
    FAILED_FUNCTIONS+=("$name")
    if [ "$FAIL_FAST" = true ]; then
      echo ""
      echo "Stopping early due to --fail-fast."
      print_summary
      exit 1
    fi
  fi
}

print_summary() {
  local total=$((PASSED + FAILED))
  echo ""
  echo "════════════════════════════════════════════════════"
  echo "  FITNESS FUNCTION RESULTS"
  echo "  Passed : $PASSED / $total"
  echo "  Failed : $FAILED / $total"
  if [ ${#FAILED_FUNCTIONS[@]} -gt 0 ]; then
    echo ""
    echo "  Failing functions:"
    for fn in "${FAILED_FUNCTIONS[@]}"; do
      echo "    ✗  $fn"
    done
  fi
  echo "════════════════════════════════════════════════════"
}

# Run all fitness function scripts in alphabetical order
for script in "$REPO_ROOT/fitness"/*.sh; do
  # Skip this script itself
  [ "$(realpath "$script")" = "$(realpath "$0")" ] && continue
  run_function "$script"
done

print_summary

if [ "$FAILED" -gt 0 ]; then
  echo ""
  echo "BUILD FAILED: $FAILED fitness function(s) did not pass."
  exit 1
else
  echo ""
  echo "BUILD PASSED: All $PASSED fitness functions passed."
  exit 0
fi
