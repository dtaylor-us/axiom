#!/usr/bin/env bash
# ADL-040 fitness function — Non-QA concern separation
#
# Verifies that:
#   1. NON_QA_CONCEPTS is defined in taxonomy.py
#   2. _separate_non_qa method exists in consolidator.py
#   3. _separate_non_qa is called within consolidate()
#   4. pytest taxonomy + consolidation non-QA tests pass
#
# Usage:
#   bash fitness/adl-040-non-qa-separation.sh
#
# Exit codes:
#   0  All checks pass
#   1  One or more checks fail

set -euo pipefail

TAXONOMY="ai-architect-agent/app/workshop/taxonomy.py"
CONSOLIDATOR="ai-architect-agent/app/workshop/consolidator.py"
PASS=0
FAIL=0

echo "ADL-040  Non-QA concern separation check"
echo "=========================================="

# Check 1: NON_QA_CONCEPTS defined in taxonomy.py
if grep -q "NON_QA_CONCEPTS" "$TAXONOMY" 2>/dev/null; then
  echo "PASS  NON_QA_CONCEPTS defined in taxonomy.py"
  PASS=$((PASS + 1))
else
  echo "FAIL  NON_QA_CONCEPTS not found in $TAXONOMY"
  FAIL=$((FAIL + 1))
fi

# Check 2: _separate_non_qa method exists in consolidator.py
if grep -q "_separate_non_qa" "$CONSOLIDATOR" 2>/dev/null; then
  echo "PASS  _separate_non_qa method found in consolidator.py"
  PASS=$((PASS + 1))
else
  echo "FAIL  _separate_non_qa not found in $CONSOLIDATOR"
  FAIL=$((FAIL + 1))
fi

# Check 3: _separate_non_qa is called inside consolidate()
# Look for a call to _separate_non_qa inside the consolidate method block
if python3 - <<'EOF' 2>/dev/null
import ast, sys

with open("$CONSOLIDATOR".replace("\$CONSOLIDATOR", "${CONSOLIDATOR}")) as f:
    src = f.read()

tree = ast.parse(src)

for node in ast.walk(tree):
    if isinstance(node, ast.AsyncFunctionDef) and node.name == "consolidate":
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                func = child.func
                if isinstance(func, ast.Attribute) and func.attr == "_separate_non_qa":
                    sys.exit(0)
sys.exit(1)
EOF
then
  echo "PASS  _separate_non_qa is called inside consolidate()"
  PASS=$((PASS + 1))
else
  # Fallback: simple grep check
  if grep -A 50 "async def consolidate" "$CONSOLIDATOR" | grep -q "_separate_non_qa"; then
    echo "PASS  _separate_non_qa is called inside consolidate() (grep)"
    PASS=$((PASS + 1))
  else
    echo "FAIL  _separate_non_qa is not called within consolidate() in $CONSOLIDATOR"
    FAIL=$((FAIL + 1))
  fi
fi

# Check 4: pytest taxonomy + consolidation non-QA tests
cd "$(git rev-parse --show-toplevel)/ai-architect/ai-architect-agent" 2>/dev/null || cd ai-architect-agent 2>/dev/null || true
if python -m pytest tests/unit/workshop/test_taxonomy.py \
                    tests/unit/workshop/test_consolidation.py::test_non_qa_separated \
                    -q --tb=short 2>&1 | grep -q "passed"; then
  echo "PASS  pytest non-QA separation tests pass"
  PASS=$((PASS + 1))
else
  echo "FAIL  pytest non-QA separation tests did not all pass"
  FAIL=$((FAIL + 1))
fi

echo ""
echo "Results: $PASS passed, $FAIL failed"

if [ "$FAIL" -gt 0 ]; then
  echo "ADL-040 FAILED: $FAIL check(s) failed"
  exit 1
fi

echo "ADL-040 PASSED"
exit 0
