#!/usr/bin/env bash

# Run all repository test suites and return non-zero if any stage fails.
# This script continues through all stages to provide a full failure summary.

set -u

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FAILED_STAGES=()

print_header() {
  local title="$1"
  echo
  echo "============================================================"
  echo "$title"
  echo "============================================================"
}

run_stage() {
  local name="$1"
  local dir="$2"
  local cmd="$3"

  print_header "$name"
  echo "Directory: $dir"
  echo "Command:   $cmd"

  (
    cd "$dir" || exit 1
    eval "$cmd"
  )
  local exit_code=$?

  if [[ $exit_code -ne 0 ]]; then
    echo "Result: FAIL ($exit_code)"
    FAILED_STAGES+=("$name")
  else
    echo "Result: PASS"
  fi
}

run_stage_if_dir() {
  local name="$1"
  local dir="$2"
  local cmd="$3"

  if [[ -d "$dir" ]]; then
    run_stage "$name" "$dir" "$cmd"
  else
    print_header "$name"
    echo "Skipped: missing directory $dir"
  fi
}

print_header "Starting Full Test Run"
echo "Repository root: $ROOT_DIR"

run_stage_if_dir "Axiom API - Unit Tests" "$ROOT_DIR/axiom-api" "mvn test"
run_stage_if_dir "Axiom API - Verify (Coverage)" "$ROOT_DIR/axiom-api" "mvn verify"

run_stage_if_dir "Archon API - Unit Tests" "$ROOT_DIR/archon-api" "mvn test"
run_stage_if_dir "Archon API - Verify (Coverage)" "$ROOT_DIR/archon-api" "mvn verify"

run_stage_if_dir "Archon Agent - Unit Tests" "$ROOT_DIR/archon-agent" "pytest tests/unit/ -v"
run_stage_if_dir "Archon Agent - Integration Tests" "$ROOT_DIR/archon-agent" "pytest tests/integration/ -v"
run_stage_if_dir "Archon Agent - Coverage Gate" "$ROOT_DIR/archon-agent" "pytest --cov=app --cov-report=term-missing --cov-fail-under=80"

run_stage_if_dir "Axiom UI - Test Suite" "$ROOT_DIR/axiom-ui" "npx vitest run"
run_stage_if_dir "Axiom UI - Coverage Gate" "$ROOT_DIR/axiom-ui" "npx vitest run --coverage"

run_stage_if_dir "Fitness Rules" "$ROOT_DIR/fitness" "./run-all.sh"

print_header "Test Run Summary"
if [[ ${#FAILED_STAGES[@]} -eq 0 ]]; then
  echo "All test stages passed."
  exit 0
fi

echo "Failed stages (${#FAILED_STAGES[@]}):"
for stage in "${FAILED_STAGES[@]}"; do
  echo "- $stage"
done

exit 1
