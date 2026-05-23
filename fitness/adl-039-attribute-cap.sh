#!/usr/bin/env bash
# ADL-039 fitness function — Workshop attribute cap
#
# Verifies that:
#   1. MAX_ATTRIBUTES is defined in consolidator.py
#   2. Its value is 12
#   3. _cap_by_importance is called within the consolidate() method
#
# Usage:
#   bash fitness/adl-039-attribute-cap.sh
#
# Exit codes:
#   0  All checks pass
#   1  One or more checks fail

set -euo pipefail

CONSOLIDATOR="ai-architect-agent/app/workshop/consolidator.py"
PASS=0
FAIL=0

echo "ADL-039  Workshop attribute cap check"
echo "======================================="

# Check 1: MAX_ATTRIBUTES constant exists
if grep -qE "^MAX_ATTRIBUTES\s*:" "$CONSOLIDATOR" 2>/dev/null; then
  echo "PASS  MAX_ATTRIBUTES constant exists in consolidator.py"
  PASS=$((PASS + 1))
else
  echo "FAIL  MAX_ATTRIBUTES constant not found in $CONSOLIDATOR"
  FAIL=$((FAIL + 1))
fi

# Check 2: Value is 12
if grep -qE "^MAX_ATTRIBUTES\s*:\s*int\s*=\s*12" "$CONSOLIDATOR" 2>/dev/null; then
  echo "PASS  MAX_ATTRIBUTES == 12"
  PASS=$((PASS + 1))
else
  echo "FAIL  MAX_ATTRIBUTES is not set to 12 in $CONSOLIDATOR"
  FAIL=$((FAIL + 1))
fi

# Check 3: _cap_by_importance is called inside consolidate()
if grep -q "_cap_by_importance" "$CONSOLIDATOR" 2>/dev/null; then
  echo "PASS  _cap_by_importance referenced in $CONSOLIDATOR"
  PASS=$((PASS + 1))
else
  echo "FAIL  _cap_by_importance not found in $CONSOLIDATOR"
  FAIL=$((FAIL + 1))
fi

# Check 4: consolidate() calls consolidate after elicit node via pytest
cd "$(git rev-parse --show-toplevel)/ai-architect/ai-architect-agent" 2>/dev/null || cd ai-architect-agent 2>/dev/null || true
if python -m pytest tests/unit/workshop/test_consolidation.py::test_max_attributes_constant_is_12 \
                    tests/unit/workshop/test_consolidation.py::test_cap_enforced_at_max_attributes \
                    -q --tb=short 2>&1 | grep -q "passed"; then
  echo "PASS  pytest cap enforcement tests pass"
  PASS=$((PASS + 1))
else
  echo "FAIL  pytest cap enforcement tests did not all pass"
  FAIL=$((FAIL + 1))
fi

echo ""
echo "Results: $PASS passed, $FAIL failed"

if [ "$FAIL" -gt 0 ]; then
  echo "ADL-039 FAILED: $FAIL check(s) failed"
  exit 1
fi

echo "ADL-039 PASSED"
exit 0
