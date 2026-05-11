#!/usr/bin/env bash
# ============================================================
# ADL-037 fitness function — Workshop module isolation
#
# ASSERT: app.workshop MUST NOT import from app.pipeline or app.tools
#
# Run from the ai-architect-agent/ directory:
#   bash fitness/adl-037-workshop-isolation.sh
# ============================================================
set -euo pipefail

WORKSHOP_DIR="${1:-app/workshop}"
FORBIDDEN_PATTERNS=("from app\.pipeline" "import app\.pipeline" "from app\.tools" "import app\.tools")

echo "ADL-037  Workshop isolation check"
echo "Scanning: $WORKSHOP_DIR"
echo "-----------------------------------"

VIOLATIONS=0

for pattern in "${FORBIDDEN_PATTERNS[@]}"; do
  while IFS=: read -r file line match; do
    echo "FAIL  $file:$line  →  $match"
    VIOLATIONS=$((VIOLATIONS + 1))
  done < <(grep -rn --include="*.py" -E "$pattern" "$WORKSHOP_DIR" 2>/dev/null || true)
done

echo "-----------------------------------"
if [ "$VIOLATIONS" -gt 0 ]; then
  echo "ADL-037 FAILED: $VIOLATIONS violation(s) found"
  exit 1
else
  echo "ADL-037 PASSED: No forbidden imports in $WORKSHOP_DIR"
  exit 0
fi
