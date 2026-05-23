#!/usr/bin/env bash
# ADL-023: UI Service — Token Storage Prohibition (Hard enforcement)
#
# Scans all TypeScript and TSX files under ui/src/ for calls to
# localStorage.setItem or sessionStorage.setItem. Exits with code 1
# if any match is found.
#
# Storing tokens in localStorage or sessionStorage exposes them to
# cross-site scripting (XSS) attacks, creating a security vulnerability.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
UI_SRC="$REPO_ROOT/ai-architect-ui/src"

echo "=== ADL-023: Checking for token storage in localStorage/sessionStorage ==="

VIOLATIONS=0

# Search for localStorage.setItem and sessionStorage.setItem
if grep -rn --include='*.ts' --include='*.tsx' \
    -e 'localStorage\.setItem' \
    "$UI_SRC" 2>/dev/null; then
  echo "VIOLATION: localStorage.setItem usage detected"
  VIOLATIONS=$((VIOLATIONS + 1))
fi

if grep -rn --include='*.ts' --include='*.tsx' \
    -e 'sessionStorage\.setItem' \
    "$UI_SRC" 2>/dev/null; then
  echo "VIOLATION: sessionStorage.setItem usage detected"
  VIOLATIONS=$((VIOLATIONS + 1))
fi

if [ "$VIOLATIONS" -gt 0 ]; then
  echo "FAILED: Token storage violation(s) found — do not store tokens in browser storage"
  exit 1
else
  echo "PASSED: No localStorage.setItem or sessionStorage.setItem calls found"
  exit 0
fi
