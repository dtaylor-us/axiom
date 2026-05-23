#!/usr/bin/env bash
# ADL-023: UI Service — Token Storage Prohibition (Hard enforcement)
#
# Detects JWT tokens being stored in localStorage or sessionStorage.
# Storing tokens in browser storage exposes them to XSS attacks.
#
# Checks:
#   1. setItem call whose VALUE argument is JSON.stringify of an object
#      containing a "token" field — catches the classic pattern of serialising
#      the auth object (with token) into storage.
#   2. setItem call whose KEY argument is a string literal that includes the
#      word "token", "jwt", or "bearer" — catches direct token key naming.
#   3. The PersistedAuth type (or equivalent) declaring a "token" field,
#      indicating the auth persistence layer intends to persist the JWT.
#
# Test files (*.test.ts, *.spec.ts) are excluded so that test helpers that
# construct mock token values do not trigger false positives.
#
# Non-sensitive localStorage usage (conversationId, display username) is
# permitted and does not trigger this check.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
UI_SRC="$REPO_ROOT/ai-architect-ui/src"

echo "=== ADL-023: Checking for JWT token storage in localStorage/sessionStorage ==="

VIOLATIONS=0

# Check 1: setItem(key, JSON.stringify({ ..., token, ... }))
# Pattern: setItem followed on the same line by JSON.stringify containing "token".
MATCHES=$(grep -rn --include='*.ts' --include='*.tsx' \
    -E 'setItem\([^,]+,\s*JSON\.stringify\([^)]*\btoken\b' \
    "$UI_SRC" 2>/dev/null \
    | grep -v '\.test\.\|\.spec\.' || true)
if [ -n "$MATCHES" ]; then
  echo "VIOLATION: Found setItem with JSON.stringify containing a token field"
  echo "$MATCHES"
  VIOLATIONS=$((VIOLATIONS + 1))
fi

# Check 2: setItem('token-related-key', ...) — key contains token/jwt/bearer.
# Pattern: setItem with a string-literal key that names a token concept.
MATCHES=$(grep -rn --include='*.ts' --include='*.tsx' \
    -E "(localStorage|sessionStorage)\.setItem\(['\"][^'\"']*(token|jwt|bearer)[^'\"']*['\"]" \
    "$UI_SRC" 2>/dev/null \
    | grep -v '\.test\.\|\.spec\.' || true)
if [ -n "$MATCHES" ]; then
  echo "VIOLATION: setItem called with a token-related storage key name"
  echo "$MATCHES"
  VIOLATIONS=$((VIOLATIONS + 1))
fi

# Check 3: PersistedAuth type (or equivalent) that declares a token field.
# A type containing "token" means the persistence layer intends to write the JWT.
# Excludes comment lines (those where the content portion starts with //).
MATCHES=$(grep -rn --include='*.ts' --include='*.tsx' \
    -E 'PersistedAuth|PersistedToken|StoredAuth' \
    "$UI_SRC" 2>/dev/null \
    | grep -v '\.test\.\|\.spec\.' \
    | grep -vE ':[[:space:]]*//' \
    | grep '\btoken\b' || true)
if [ -n "$MATCHES" ]; then
  echo "VIOLATION: Auth persistence type declares a token field — JWT must not be persisted"
  echo "$MATCHES"
  VIOLATIONS=$((VIOLATIONS + 1))
fi

if [ "$VIOLATIONS" -gt 0 ]; then
  echo "FAILED: JWT token storage violation(s) found — store tokens in memory only"
  exit 1
else
  echo "PASSED: No JWT token storage in localStorage/sessionStorage detected"
  exit 0
fi
