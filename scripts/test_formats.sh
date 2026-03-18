#!/usr/bin/env bash
# Format battery — round-trip embed/extract for all supported formats.
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

# ── Generate test assets ──────────────────────────────────────────────────────
PAYLOAD="$TMPDIR_WORK/message.txt"
echo "The quick brown fox jumps over the lazy dog. 1234567890 !@#\$%^&*()" > "$PAYLOAD"

# Create a 100×100 PNG cover using convert (ImageMagick) or a Rust helper
if command -v convert &>/dev/null; then
  convert -size 100x100 plasma:blue "$TMPDIR_WORK/cover.png" 2>/dev/null
  convert -size 100x100 plasma:red  "$TMPDIR_WORK/cover.bmp" 2>/dev/null
  convert -size 100x100 plasma:green "$TMPDIR_WORK/cover.jpg" 2>/dev/null
  convert -size 100x100 plasma:cyan  "$TMPDIR_WORK/cover.webp" 2>/dev/null
fi

# Generate a WAV cover (1s silence, 44100 Hz, 16-bit mono)
if command -v sox &>/dev/null; then
  sox -n -r 44100 -c 1 -b 16 "$TMPDIR_WORK/cover.wav" trim 0.0 1.0 2>/dev/null
fi

PASS_PHRASE="test-passphrase-secure"

# ── Round-trip tests ──────────────────────────────────────────────────────────
out_ext() { [[ "$1" == "jpg" ]] && echo "jpg" || echo "png"; }

run_roundtrip() {
  local FORMAT="$1"
  local MODE="$2"
  local COVER="$TMPDIR_WORK/cover.${FORMAT}"
  local OUTPUT="$TMPDIR_WORK/output_${FORMAT}_${MODE}.$(out_ext "$FORMAT")"
  local EXTRACTED="$TMPDIR_WORK/extracted_${FORMAT}_${MODE}.txt"

  [[ -f "$COVER" ]] || { echo "  skip  (no cover for $FORMAT)"; return 0; }

  if "$BIN" embed "$COVER" "$PAYLOAD" "$OUTPUT" \
       --passphrase "$PASS_PHRASE" \
       --mode "$MODE" \
       --cipher chacha20-poly1305 \
       --json &>/dev/null; then
    if "$BIN" extract "$OUTPUT" "$EXTRACTED" \
         --passphrase "$PASS_PHRASE" \
         --json &>/dev/null; then
      if diff -q "$PAYLOAD" "$EXTRACTED" &>/dev/null; then
        ok "$FORMAT / $MODE: round-trip match"
      else
        fail "$FORMAT / $MODE: extracted bytes differ from original"
      fi
    else
      fail "$FORMAT / $MODE: extract failed"
    fi
  else
    fail "$FORMAT / $MODE: embed failed"
  fi
}

run_roundtrip_with_keyfile() {
  local FORMAT="$1"
  local COVER="$TMPDIR_WORK/cover.${FORMAT}"
  local OUTPUT="$TMPDIR_WORK/output_${FORMAT}_keyfile.$(out_ext "$FORMAT")"
  local KEYFILE="$TMPDIR_WORK/output_${FORMAT}_keyfile.json"
  local EXTRACTED="$TMPDIR_WORK/extracted_${FORMAT}_keyfile.txt"

  [[ -f "$COVER" ]] || return 0

  if "$BIN" embed "$COVER" "$PAYLOAD" "$OUTPUT" \
       --passphrase "$PASS_PHRASE" \
       --export-key "$KEYFILE" \
       --json &>/dev/null; then
    if "$BIN" extract "$OUTPUT" "$EXTRACTED" \
         --passphrase "$PASS_PHRASE" \
         --key-file "$KEYFILE" \
         --json &>/dev/null; then
      if diff -q "$PAYLOAD" "$EXTRACTED" &>/dev/null; then
        ok "$FORMAT / with key file: round-trip match"
      else
        fail "$FORMAT / with key file: extracted bytes differ"
      fi
    else
      fail "$FORMAT / with key file: extract failed"
    fi
  else
    fail "$FORMAT / with key file: embed failed"
  fi
}

check_jpeg_output_is_jpeg() {
  local OUTPUT="$TMPDIR_WORK/output_jpg_adaptive.jpg"
  if [[ -f "$OUTPUT" ]]; then
    HEADER="$(xxd -p -l 4 "$OUTPUT" 2>/dev/null || od -A n -t x1 -N 4 "$OUTPUT" 2>/dev/null | tr -d ' ')"
    if [[ "$HEADER" == "ffd8ff"* ]]; then
      ok "JPEG → output remains JPEG (header check)"
    else
      fail "JPEG → output is not a JPEG (header: $HEADER)"
    fi
  fi
}

for FORMAT in png bmp jpg webp wav; do
  for MODE in adaptive sequential; do
    run_roundtrip "$FORMAT" "$MODE"
  done
  run_roundtrip_with_keyfile "$FORMAT"
done

check_jpeg_output_is_jpeg

# ── Summary ───────────────────────────────────────────────────────────────────
[[ $FAIL -eq 0 ]] && exit 0 || exit 1
