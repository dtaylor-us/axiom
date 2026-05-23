#!/usr/bin/env bash
# ADL-059 — PasswordResetService must persist only bcrypt-hashed reset tokens.
set -euo pipefail

cd "$(dirname "$0")/.."
SERVICE_FILE="ai-architect-api/src/main/java/com/aiarchitect/api/service/PasswordResetService.java"

test -f "$SERVICE_FILE" || {
  echo "FAIL: $SERVICE_FILE not found"
  exit 1
}

if ! grep -qE 'passwordEncoder\.encode\(rawToken\)' "$SERVICE_FILE"; then
  echo "FAIL: PasswordResetService must encode rawToken before persistence"
  exit 1
fi

if grep -qE '\.tokenHash\(rawToken\)|setTokenHash\(rawToken\)|tokenHash\s*=\s*rawToken' "$SERVICE_FILE"; then
  echo "FAIL: PasswordResetService must not persist rawToken directly"
  exit 1
fi

echo "ADL-059 PASSED"
