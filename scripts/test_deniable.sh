#!/usr/bin/env bash
# Deniable mode battery — real/decoy passphrase separation + structural parity.
set -euo pipefail

BIN="${STEGCORE_BIN:-stegcore}"
TMPDIR_WORK="$(mktemp -d)"
PASS=0
FAIL=0

cleanup() { rm -rf "$TMPDIR_WORK"; }
trap cleanup EXIT

GREEN='\033[0;32m'
RED='\033[0;31m'
RESET='\033[0m'

ok()   { echo -e "  ${GREEN}✓${RESET}  $*"; PASS=$((PASS+1)); }
fail() { echo -e "  ${RED}✗${RESET}  $*"; FAIL=$((FAIL+1)); }

# ── Prepare ───────────────────────────────────────────────────────────────────
REAL_MSG="$TMPDIR_WORK/real.txt"
DECOY_MSG="$TMPDIR_WORK/decoy.txt"
echo "This is the real message — top secret." > "$REAL_MSG"
echo "Nothing to see here. Just notes." > "$DECOY_MSG"

COVER="$TMPDIR_WORK/cover.png"
if command -v convert &>/dev/null; then
  convert -size 200x200 plasma:blue "$COVER" 2>/dev/null
else
  fail "ImageMagick not available — cannot generate cover. Skipping deniable tests."
  exit 1
fi

OUTPUT="$TMPDIR_WORK/stego.png"
REAL_KEY="$TMPDIR_WORK/real.json"
DECOY_KEY="$TMPDIR_WORK/decoy.json"
REAL_PASS="correct-real-passphrase"
DECOY_PASS="correct-decoy-passphrase"
EXTRACTED_REAL="$TMPDIR_WORK/out_real.txt"
EXTRACTED_DECOY="$TMPDIR_WORK/out_decoy.txt"

# ── Embed deniable ────────────────────────────────────────────────────────────
if "$BIN" embed "$COVER" "$REAL_MSG" "$OUTPUT" \
     --passphrase "$REAL_PASS" \
     --deniable \
     --decoy "$DECOY_MSG" \
     --decoy-passphrase "$DECOY_PASS" \
     --export-key "$REAL_KEY" \
     --decoy-key "$DECOY_KEY" \
     --json &>/dev/null; then
  ok "Deniable embed succeeded"
else
  fail "Deniable embed failed"
  exit 1
fi

# ── Extract with real passphrase ──────────────────────────────────────────────
if "$BIN" extract "$OUTPUT" "$EXTRACTED_REAL" \
     --passphrase "$REAL_PASS" \
     --json &>/dev/null; then
  if diff -q "$REAL_MSG" "$EXTRACTED_REAL" &>/dev/null; then
    ok "Real passphrase → real message"
  else
    fail "Real passphrase → wrong content"
  fi
else
  fail "Real passphrase → extract failed"
fi

# ── Extract with decoy passphrase ─────────────────────────────────────────────
if "$BIN" extract "$OUTPUT" "$EXTRACTED_DECOY" \
     --passphrase "$DECOY_PASS" \
     --json &>/dev/null; then
  if diff -q "$DECOY_MSG" "$EXTRACTED_DECOY" &>/dev/null; then
    ok "Decoy passphrase → decoy message"
  else
    fail "Decoy passphrase → wrong content"
  fi
else
  fail "Decoy passphrase → extract failed"
fi

# ── Outputs are different ─────────────────────────────────────────────────────
if ! diff -q "$EXTRACTED_REAL" "$EXTRACTED_DECOY" &>/dev/null; then
  ok "Real and decoy outputs are different"
else
  fail "Real and decoy outputs are identical — deniable mode broken"
fi

# ── Key files are structurally identical (both have same fields) ───────────────
if [[ -f "$REAL_KEY" && -f "$DECOY_KEY" ]]; then
  REAL_FIELDS="$(python3 -c "import json,sys; d=json.load(open('$REAL_KEY')); print(sorted(d.keys()))" 2>/dev/null)"
  DECOY_FIELDS="$(python3 -c "import json,sys; d=json.load(open('$DECOY_KEY')); print(sorted(d.keys()))" 2>/dev/null)"
  if [[ "$REAL_FIELDS" == "$DECOY_FIELDS" ]]; then
    ok "Key files have identical structure (no 'real' marker)"
  else
    fail "Key file structures differ: real=$REAL_FIELDS decoy=$DECOY_FIELDS"
  fi
else
  echo "  skip  (key files not exported — check --export-key / --decoy-key flags)"
fi

[[ $FAIL -eq 0 ]] && exit 0 || exit 1
