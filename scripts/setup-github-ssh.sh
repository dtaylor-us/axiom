#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   scripts/setup-github-ssh.sh your_email@example.com
# Optional env vars:
#   KEY_PATH (default: ~/.ssh/id_ed25519_github)
#   FORCE_OVERWRITE=true to replace an existing key file

EMAIL="${1:-}"
if [[ -z "$EMAIL" ]]; then
  echo "Usage: $0 your_email@example.com"
  exit 1
fi

KEY_PATH="${KEY_PATH:-$HOME/.ssh/id_ed25519_github}"
PUB_PATH="${KEY_PATH}.pub"
SSH_DIR="$HOME/.ssh"
CONFIG_PATH="$SSH_DIR/config"
MANAGED_BEGIN="# >>> github-ssh-setup managed block >>>"
MANAGED_END="# <<< github-ssh-setup managed block <<<"

mkdir -p "$SSH_DIR"
chmod 700 "$SSH_DIR"

if [[ -f "$KEY_PATH" && "${FORCE_OVERWRITE:-false}" != "true" ]]; then
  echo "Key already exists at $KEY_PATH"
  echo "Set FORCE_OVERWRITE=true to replace it, or delete the file and rerun."
else
  if [[ -f "$KEY_PATH" ]]; then
    rm -f "$KEY_PATH" "$PUB_PATH"
  fi
  ssh-keygen -t ed25519 -C "$EMAIL" -f "$KEY_PATH" -N ""
  chmod 600 "$KEY_PATH"
  chmod 644 "$PUB_PATH"
  echo "Created key: $KEY_PATH"
fi

# Start agent if needed.
if ! ssh-add -l >/dev/null 2>&1; then
  eval "$(ssh-agent -s)" >/dev/null
fi

# Add key to agent and macOS keychain.
ssh-add --apple-use-keychain "$KEY_PATH" >/dev/null

echo "Loaded key into ssh-agent and macOS keychain."

# Ensure config file exists.
touch "$CONFIG_PATH"
chmod 600 "$CONFIG_PATH"

# Remove prior managed block, if present.
TMP_CONFIG="$(mktemp)"
awk -v begin="$MANAGED_BEGIN" -v end="$MANAGED_END" '
  $0 == begin { in_block=1; next }
  $0 == end { in_block=0; next }
  !in_block { print }
' "$CONFIG_PATH" > "$TMP_CONFIG"
mv "$TMP_CONFIG" "$CONFIG_PATH"

# Append managed GitHub host block.
cat >> "$CONFIG_PATH" <<EOF
$MANAGED_BEGIN
Host github.com
  HostName github.com
  User git
  AddKeysToAgent yes
  UseKeychain yes
  IdentityFile $KEY_PATH
  IdentitiesOnly yes
$MANAGED_END
EOF

echo "Updated SSH config at $CONFIG_PATH"

# Print public key and convenience next steps.
echo
printf 'Public key (copy this into GitHub -> Settings -> SSH and GPG keys):\n\n'
cat "$PUB_PATH"
echo

echo "Testing SSH auth to GitHub..."
if ssh -o BatchMode=yes -T git@github.com 2>&1 | grep -q "successfully authenticated"; then
  echo "SSH auth test passed."
else
  echo "SSH test did not fully authenticate yet."
  echo "This is expected until you add the public key to your GitHub account."
fi

echo
echo "Done."
echo "Next steps:"
echo "1) Copy the public key above"
echo "2) Add it in GitHub: https://github.com/settings/keys"
echo "3) Re-test: ssh -T git@github.com"
