#!/bin/bash
# Fast programmatic TOTP autofill

SERVICE="${1}"
TARGET_ID="${2}"

if [ -z "$SERVICE" ] || [ -z "$TARGET_ID" ]; then
  echo "Usage: $0 <service> <browser_target_id>"
  echo "Example: $0 m.facebook.com ABC123"
  exit 1
fi

# Check if pyotp is available
if ! python3 -c "import pyotp" 2>/dev/null; then
  echo "Installing pyotp..."
  pip3 install pyotp --quiet
fi

# Try to get secret from keychain
SECRET=$(security find-generic-password -s "${SERVICE}_totp" -w 2>/dev/null)

if [ -z "$SECRET" ]; then
  echo "No TOTP secret found for $SERVICE"
  echo "Setup: security add-generic-password -s '${SERVICE}_totp' -a '$SERVICE' -w 'YOUR_SECRET'"
  exit 1
fi

# Generate current TOTP code
CODE=$(python3 -c "import pyotp; print(pyotp.TOTP('$SECRET').now())")

echo "[TOTP] Generated code for $SERVICE: $CODE"

# Now use moltbot browser tool to fill it
# This would be called from a moltbot session with browser tool access

cat << MOLTBOT_TASK
# From moltbot session, run:

browser.snapshot(targetId: "$TARGET_ID")
# Find code input field ref

browser.act({
  kind: "type",
  ref: "INPUT_REF_FROM_SNAPSHOT",
  text: "$CODE",
  submit: true,
  targetId: "$TARGET_ID"
})

# Verify success
browser.tabs() # Check URL changed
MOLTBOT_TASK

echo ""
echo "Code: $CODE (valid for 30s)"
