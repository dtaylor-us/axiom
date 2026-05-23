#!/usr/bin/env bash
# ADL-044 — elicit_scenarios.j2 must reference all_evidence (full history)
set -euo pipefail
cd "$(dirname "$0")/../ai-architect-agent"
PROMPT="app/prompts/workshop/elicit_scenarios.j2"
test -f "$PROMPT" || { echo "FAIL: $PROMPT not found"; exit 1; }
grep -q 'all_evidence' "$PROMPT" \
  || { echo "FAIL: elicit_scenarios.j2 must contain all_evidence"; exit 1; }
echo "ADL-044 PASSED"
