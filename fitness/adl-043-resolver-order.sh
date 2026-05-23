#!/usr/bin/env bash
# ADL-043 — resolve_questions between reconcile_gaps and elicit_scenarios
set -euo pipefail
cd "$(dirname "$0")/../ai-architect-agent"
AGENT="app/workshop/agent.py"
test -f "$AGENT" || { echo "FAIL: $AGENT not found"; exit 1; }
grep -q 'add_edge("reconcile_gaps", "resolve_questions")' "$AGENT" \
  || { echo "FAIL: missing reconcile_gaps → resolve_questions"; exit 1; }
grep -q 'add_edge("resolve_questions", "elicit_scenarios")' "$AGENT" \
  || { echo "FAIL: missing resolve_questions → elicit_scenarios"; exit 1; }
grep -q 'add_node("resolve_questions"' "$AGENT" \
  || { echo "FAIL: missing resolve_questions node"; exit 1; }
echo "ADL-043 PASSED"
