#!/usr/bin/env bash
# Performance benchmarks — embed/extract throughput at various payload sizes.
# Informational only — no pass/fail thresholds.
set -euo pipefail

BIN="${STEGCORE_BIN:-stegcore}"
TMPDIR_WORK="$(mktemp -d)"

cleanup() { rm -rf "$TMPDIR_WORK"; }
trap cleanup EXIT

CYAN='\033[0;36m'
BOLD='\033[1m'
RESET='\033[0m'

info() { echo -e "  ${CYAN}→${RESET}  $*"; }

# ── Prepare cover ─────────────────────────────────────────────────────────────
COVER="$TMPDIR_WORK/cover.png"
if command -v convert &>/dev/null; then
  convert -size 800x600 plasma:blue "$COVER" 2>/dev/null
else
  echo "ImageMagick not available — cannot generate cover."
  exit 0
fi

PASS_PHRASE="bench-passphrase-2024"

echo -e "\n${BOLD}Stegcore benchmark${RESET}"
echo "Binary: $BIN"
echo "Cover:  800×600 PNG"
echo ""
printf "  %-16s %-16s %-16s %-16s\n" "Payload size" "Embed time" "Extract time" "Throughput"
printf "  %-16s %-16s %-16s %-16s\n" "────────────" "──────────" "────────────" "──────────"

for SIZE_KB in 1 10 100 500; do
  PAYLOAD="$TMPDIR_WORK/payload_${SIZE_KB}k.bin"
  OUTPUT="$TMPDIR_WORK/output_${SIZE_KB}k.png"
  EXTRACTED="$TMPDIR_WORK/extracted_${SIZE_KB}k.bin"

  head -c $((SIZE_KB * 1024)) /dev/urandom > "$PAYLOAD"

  # Embed
  START=$(date +%s%N)
  "$BIN" embed "$COVER" "$PAYLOAD" "$OUTPUT" \
    --passphrase "$PASS_PHRASE" --mode adaptive --json &>/dev/null || { echo "  embed failed for ${SIZE_KB}KB"; continue; }
  END=$(date +%s%N)
  EMBED_MS=$(( (END - START) / 1000000 ))

  # Extract
  START=$(date +%s%N)
  "$BIN" extract "$OUTPUT" "$EXTRACTED" \
    --passphrase "$PASS_PHRASE" --json &>/dev/null || { echo "  extract failed for ${SIZE_KB}KB"; continue; }
  END=$(date +%s%N)
  EXTRACT_MS=$(( (END - START) / 1000000 ))

  TOTAL_MS=$((EMBED_MS + EXTRACT_MS))
  if [[ $TOTAL_MS -gt 0 ]]; then
    THROUGHPUT=$(python3 -c "print(f'{($SIZE_KB / ($TOTAL_MS / 1000)):.1f} KB/s')" 2>/dev/null || echo "n/a")
  else
    THROUGHPUT="n/a"
  fi

  printf "  %-16s %-16s %-16s %-16s\n" \
    "${SIZE_KB} KB" "${EMBED_MS}ms" "${EXTRACT_MS}ms" "$THROUGHPUT"
done

echo ""
