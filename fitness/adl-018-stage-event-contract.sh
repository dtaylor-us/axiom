#!/usr/bin/env bash
# ADL-018: Agent Orchestration Service — Stage Event Contract (Soft enforcement)
#
# Parses app/pipeline/nodes.py and verifies every async stage function emits
# both a STAGE_START and STAGE_COMPLETE event. Exits with code 1 if any stage
# function is missing either event.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
NODES_FILE="$REPO_ROOT/ai-architect-agent/app/pipeline/nodes.py"

echo "=== ADL-018: Checking stage event contracts in pipeline nodes ==="

if [ ! -f "$NODES_FILE" ]; then
  echo "FAILED: $NODES_FILE not found"
  exit 1
fi

# Use a single Python invocation to parse the AST and check all functions
python3 - "$NODES_FILE" <<'PYEOF'
import ast, sys

nodes_file = sys.argv[1]

with open(nodes_file) as f:
    source = f.read()

tree = ast.parse(source)
violations = 0
checked = 0

for node in ast.iter_child_nodes(tree):
    if not isinstance(node, ast.AsyncFunctionDef):
        continue
    if node.name.startswith("_"):
        continue

    checked += 1
    lines = source.splitlines()
    body_source = "\n".join(lines[node.lineno - 1 : node.end_lineno])

    has_start = "STAGE_START" in body_source
    has_complete = "STAGE_COMPLETE" in body_source

    missing = []
    if not has_start:
        missing.append("STAGE_START")
    if not has_complete:
        missing.append("STAGE_COMPLETE")

    if missing:
        print(f"  {node.name}() is missing: {', '.join(missing)}")
        violations += 1

if checked == 0:
    print("WARNING: No async stage functions found in nodes.py")
    sys.exit(0)

if violations > 0:
    print(f"FAILED: {violations} stage function(s) missing STAGE_START or STAGE_COMPLETE events")
    sys.exit(1)
else:
    print(f"PASSED: All {checked} stage functions emit both STAGE_START and STAGE_COMPLETE events")
    sys.exit(0)
PYEOF
