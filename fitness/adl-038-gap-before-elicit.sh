#!/usr/bin/env bash
# ============================================================
# ADL-038 fitness function — Gap-before-elicit ordering
#
# ASSERT: In app/workshop/agent.py, identify_gaps is wired before scenario
#         elicitation (elicit_scenarios), preserving "ask before you assert".
#
# Run from the ai-architect-agent/ directory:
#   bash fitness/adl-038-gap-before-elicit.sh
# ============================================================
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
AGENT_FILE="${1:-$REPO_ROOT/ai-architect-agent/app/workshop/agent.py}"

echo "ADL-038  Gap-before-elicit ordering check"
echo "File:    $AGENT_FILE"
echo "-----------------------------------"

if [ ! -f "$AGENT_FILE" ]; then
  echo "FAIL  File not found: $AGENT_FILE"
  exit 1
fi

LINE_IDENTIFY=$(grep -n 'add_edge("identify_gaps"' "$AGENT_FILE" | head -1 | cut -d: -f1)
LINE_ELICIT_SC=$(grep -n 'add_edge("elicit_scenarios"' "$AGENT_FILE" | head -1 | cut -d: -f1)

if [ -z "$LINE_IDENTIFY" ]; then
  echo "FAIL  Could not find add_edge(\"identify_gaps\" ...) in $AGENT_FILE"
  exit 1
fi

if [ -z "$LINE_ELICIT_SC" ]; then
  echo "FAIL  Could not find add_edge(\"elicit_scenarios\" ...) in $AGENT_FILE"
  exit 1
fi

echo "add_edge identify_gaps          at line $LINE_IDENTIFY"
echo "add_edge elicit_scenarios       at line $LINE_ELICIT_SC"
echo "-----------------------------------"

if [ "$LINE_IDENTIFY" -lt "$LINE_ELICIT_SC" ]; then
  echo "ADL-038 PASSED: identify_gaps precedes elicit_scenarios"
  exit 0
else
  echo "ADL-038 FAILED: elicit_scenarios edge appears before identify_gaps edge"
  exit 1
fi
