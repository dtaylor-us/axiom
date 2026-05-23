#!/usr/bin/env bash
# ADL-019: Agent Orchestration Service — Secret Prohibition (Hard enforcement)
#
# Detects hardcoded API keys (strings starting with sk-), hardcoded password
# assignments, and hardcoded secret assignments in Python files under app/.
#
# Hardcoded secrets are a critical security vulnerability that could leak
# credentials through version control or logs.
#
# Uses semgrep when available; falls back to grep-based pattern matching.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
AGENT_APP="$REPO_ROOT/ai-architect-agent/app"

echo "=== ADL-019: Checking for hardcoded secrets in agent Python source ==="

if [ ! -d "$AGENT_APP" ]; then
  echo "FAILED: $AGENT_APP directory not found"
  exit 1
fi

VIOLATIONS=0

if command -v semgrep >/dev/null 2>&1; then
  echo "-- Using semgrep (rule: adl-019-secret-prohibition.yml.semgrep-rule)"
  RULE_FILE="$(dirname "$0")/adl-019-secret-prohibition.yml.semgrep-rule"
  if semgrep --config "$RULE_FILE" "$AGENT_APP" --error --quiet 2>&1; then
    echo "PASSED: No hardcoded secrets detected (semgrep)"
    exit 0
  else
    echo "FAILED: Hardcoded secret(s) detected (semgrep)"
    exit 1
  fi
fi

echo "-- semgrep not installed; using grep-based pattern matching"

# Pattern 1: API key strings starting with sk- (OpenAI, Anthropic, etc.)
#   Matches:  some_var = "sk-..."
if grep -rn --include='*.py' \
    -E '=\s*['\''"]sk-[A-Za-z0-9_-]{10,}['\''"]' \
    "$AGENT_APP" 2>/dev/null; then
  echo "VIOLATION: Hardcoded API key (sk-...) detected"
  VIOLATIONS=$((VIOLATIONS + 1))
fi

# Pattern 2: password = "literal"  (assignment to a password variable)
if grep -rn --include='*.py' \
    -Ei 'password\s*=\s*['\''"][^$\{][^'\''\"]{3,}['\''"]' \
    "$AGENT_APP" 2>/dev/null | grep -v '#'; then
  echo "VIOLATION: Hardcoded password assignment detected"
  VIOLATIONS=$((VIOLATIONS + 1))
fi

# Pattern 3: secret = "literal"  (assignment to a secret variable)
if grep -rn --include='*.py' \
    -Ei '\bsecret\s*=\s*['\''"][^$\{][^'\''\"]{3,}['\''"]' \
    "$AGENT_APP" 2>/dev/null | grep -v '#'; then
  echo "VIOLATION: Hardcoded secret assignment detected"
  VIOLATIONS=$((VIOLATIONS + 1))
fi

# Pattern 4: api_key = "literal"
if grep -rn --include='*.py' \
    -Ei 'api_key\s*=\s*['\''"][^$\{][^'\''\"]{3,}['\''"]' \
    "$AGENT_APP" 2>/dev/null | grep -v '#'; then
  echo "VIOLATION: Hardcoded api_key assignment detected"
  VIOLATIONS=$((VIOLATIONS + 1))
fi

if [ "$VIOLATIONS" -gt 0 ]; then
  echo "FAILED: $VIOLATIONS hardcoded secret pattern(s) found — use environment variables or a secret manager"
  exit 1
else
  echo "PASSED: No hardcoded secrets detected"
  exit 0
fi
