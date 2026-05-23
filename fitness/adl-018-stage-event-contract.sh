#!/usr/bin/env bash
# ADL-018: Agent Orchestration Service — Stage Event Contract (Soft enforcement)
#
# Verifies that graph.py's run_pipeline() orchestrator emits both
# STAGE_START and STAGE_COMPLETE for every stage.
#
# NOTE: Events are emitted by the orchestrator in graph.py (not per-node
# functions in nodes.py). The orchestrator wraps every node call with
# STAGE_START (before) and STAGE_COMPLETE (after), so one check on
# graph.py covers all stages without coupling nodes to the event protocol.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
GRAPH_FILE="$REPO_ROOT/ai-architect-agent/app/pipeline/graph.py"

echo "=== ADL-018: Checking stage event contracts in pipeline orchestrator ==="

if [ ! -f "$GRAPH_FILE" ]; then
  echo "FAILED: $GRAPH_FILE not found"
  exit 1
fi

# Use a single Python invocation to verify run_pipeline emits both events
python3 - "$GRAPH_FILE" <<'PYEOF'
import ast, sys

graph_file = sys.argv[1]

with open(graph_file) as f:
    source = f.read()

tree = ast.parse(source)
violations = 0
checked = 0

for node in ast.walk(tree):
    if not isinstance(node, ast.AsyncFunctionDef):
        continue
    if node.name != "run_pipeline" and node.name != "_pipeline_chunks":
        continue

    checked += 1
    lines = source.splitlines()
    body_source = "\n".join(lines[node.lineno - 1 : node.end_lineno])

    has_start = '"STAGE_START"' in body_source or "'STAGE_START'" in body_source
    has_complete = '"STAGE_COMPLETE"' in body_source or "'STAGE_COMPLETE'" in body_source

    missing = []
    if not has_start:
        missing.append("STAGE_START")
    if not has_complete:
        missing.append("STAGE_COMPLETE")

    if missing:
        print(f"  {node.name}() is missing: {', '.join(missing)}")
        violations += 1

if checked == 0:
    print("WARNING: run_pipeline / _pipeline_chunks not found in graph.py")
    sys.exit(1)

if violations > 0:
    print(f"FAILED: {violations} orchestrator function(s) missing STAGE_START or STAGE_COMPLETE events")
    sys.exit(1)
else:
    print(f"PASSED: Orchestrator emits both STAGE_START and STAGE_COMPLETE events ({checked} function(s) checked)")
    sys.exit(0)
PYEOF
