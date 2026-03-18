#!/usr/bin/env bash
# Error path battery — exit codes, error messages, and edge cases.
set -euo pipefail

BIN="${STEGCORE_BIN:-stegcore}"
TMPDIR_WORK="$(mktemp -d)"
PASS=0
FAIL=0

cleanup() { rm -rf "$TMPDIR_WORK"; }
trap cleanup EXIT

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
RESET='\033[0m'

ok()   { echo -e "  ${GREEN}✓${RESET}  $*"; PASS=$((PASS+1)); }
fail() { echo -e "  ${RED}✗${RESET}  $*"; FAIL=$((FAIL+1)); }
skip() { echo -e "  ${YELLOW}-${RESET}  skip: $*"; }

assert_exit() {
  local DESC="$1"
  local EXPECTED="$2"
  shift 2
  local ACTUAL
  ACTUAL=$("$@" 2>/dev/null; echo $?) || ACTUAL=$?
  # Capture exit code properly
  "$@" &>/dev/null; ACTUAL=$?
  if [[ "$ACTUAL" -eq "$EXPECTED" ]]; then
    ok "$DESC (exit $EXPECTED)"
  else
    fail "$DESC — expected exit $EXPECTED, got $ACTUAL"
  fi
}

assert_stderr_contains() {
  local DESC="$1"
  local NEEDLE="$2"
  shift 2
  local OUTPUT
  OUTPUT="$("$@" 2>&1 || true)"
  if echo "$OUTPUT" | grep -qi "$NEEDLE"; then
    ok "$DESC — stderr contains '$NEEDLE'"
  else
    fail "$DESC — expected '$NEEDLE' in stderr: $OUTPUT"
  fi
}

# ── Prepare ───────────────────────────────────────────────────────────────────
COVER="$TMPDIR_WORK/cover.png"
PAYLOAD="$TMPDIR_WORK/payload.txt"
STEGO="$TMPDIR_WORK/stego.png"
EMPTY="$TMPDIR_WORK/empty.txt"
EXTRACTED="$TMPDIR_WORK/out.txt"

echo "Hello world" > "$PAYLOAD"
touch "$EMPTY"

if command -v convert &>/dev/null; then
  convert -size 100x100 plasma:blue "$COVER" 2>/dev/null
  # Tiny cover — too small for large payload
  convert -size 5x5 plasma:red "$TMPDIR_WORK/tiny.png" 2>/dev/null
fi

# Embed a valid stego file for subsequent extract tests
PASS_PHRASE="correct-passphrase-abc123"
"$BIN" embed "$COVER" "$PAYLOAD" "$STEGO" \
  --passphrase "$PASS_PHRASE" --json &>/dev/null || true

# ── Wrong passphrase → exit 2 ─────────────────────────────────────────────────
if [[ -f "$STEGO" ]]; then
  assert_exit "Wrong passphrase → exit 2" 2 \
    "$BIN" extract "$STEGO" "$EXTRACTED" --passphrase "wrong-passphrase"
  assert_stderr_contains "Wrong passphrase → user-friendly message" \
    "passphrase\|corrupted\|decryption" \
    "$BIN" extract "$STEGO" "$EXTRACTED" --passphrase "wrong-passphrase"
else
  skip "stego file not available — skipping passphrase tests"
fi

# ── Empty payload → exit 1 ────────────────────────────────────────────────────
if [[ -f "$COVER" ]]; then
  assert_exit "Empty payload → exit 1" 1 \
    "$BIN" embed "$COVER" "$EMPTY" "$TMPDIR_WORK/out_empty.png" --passphrase "$PASS_PHRASE"
fi

# ── File not found → exit 3 ───────────────────────────────────────────────────
assert_exit "Missing cover → exit 3" 3 \
  "$BIN" embed "$TMPDIR_WORK/nonexistent.png" "$PAYLOAD" "$TMPDIR_WORK/out.png" --passphrase "$PASS_PHRASE"

assert_exit "Missing stego file → exit 3" 3 \
  "$BIN" extract "$TMPDIR_WORK/nonexistent.png" "$EXTRACTED" --passphrase "$PASS_PHRASE"

# ── Unsupported format → exit 4 ───────────────────────────────────────────────
echo "fake file" > "$TMPDIR_WORK/file.xyz"
assert_exit "Unsupported format → exit 4" 4 \
  "$BIN" embed "$TMPDIR_WORK/file.xyz" "$PAYLOAD" "$TMPDIR_WORK/out.png" --passphrase "$PASS_PHRASE"

# ── Cover too small → exit 1 ─────────────────────────────────────────────────
if [[ -f "$TMPDIR_WORK/tiny.png" ]]; then
  BIG_PAYLOAD="$TMPDIR_WORK/big.txt"
  head -c 50000 /dev/urandom | base64 > "$BIG_PAYLOAD"
  assert_exit "Payload too large → exit 1" 1 \
    "$BIN" embed "$TMPDIR_WORK/tiny.png" "$BIG_PAYLOAD" "$TMPDIR_WORK/out_tiny.png" --passphrase "$PASS_PHRASE"
fi

# ── Corrupt stego file → exit 2 ───────────────────────────────────────────────
if [[ -f "$STEGO" ]]; then
  CORRUPT="$TMPDIR_WORK/corrupt.png"
  cp "$STEGO" "$CORRUPT"
  # Flip a byte in the middle of the file
  FILESIZE=$(wc -c < "$CORRUPT")
  MID=$((FILESIZE / 2))
  printf '\xff' | dd of="$CORRUPT" bs=1 seek=$MID conv=notrunc 2>/dev/null
  assert_exit "Corrupted stego file → exit 2" 2 \
    "$BIN" extract "$CORRUPT" "$EXTRACTED" --passphrase "$PASS_PHRASE"
fi

# ── Legacy key file → exit 1 + message ───────────────────────────────────────
LEGACY_KEY="$TMPDIR_WORK/legacy.json"
cat > "$LEGACY_KEY" << 'EOF'
{
  "cipher": "aes-256-gcm",
  "nonce": "AAAAAAAAAAAAAAAA",
  "salt": "AAAAAAAAAAAAAAAA"
}
EOF
if [[ -f "$STEGO" ]]; then
  assert_exit "Legacy key file → exit 1" 1 \
    "$BIN" extract "$STEGO" "$EXTRACTED" --passphrase "$PASS_PHRASE" --key-file "$LEGACY_KEY"
  assert_stderr_contains "Legacy key file → mentions older version" \
    "older\|legacy\|version" \
    "$BIN" extract "$STEGO" "$EXTRACTED" --passphrase "$PASS_PHRASE" --key-file "$LEGACY_KEY"
fi

# ── Path in error messages ────────────────────────────────────────────────────
assert_stderr_contains "Missing file path in error" \
  "nonexistent.png" \
  "$BIN" embed "$TMPDIR_WORK/nonexistent.png" "$PAYLOAD" "$TMPDIR_WORK/out.png" --passphrase "$PASS_PHRASE"

# ── Summary ───────────────────────────────────────────────────────────────────
echo ""
echo "  Passed: $PASS   Failed: $FAIL"
[[ $FAIL -eq 0 ]] && exit 0 || exit 1
