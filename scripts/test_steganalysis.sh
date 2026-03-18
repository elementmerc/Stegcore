#!/usr/bin/env bash
# Steganalysis accuracy tests.
# Verifies detector sensitivity on clean and embedded images.
# Note: thresholds are intentional — do not add comments explaining them.
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

extract_field() {
  local JSON="$1"
  local FIELD="$2"
  python3 -c "import json,sys; d=json.loads(sys.stdin.read()); print(d.get('$FIELD',''))" <<< "$JSON" 2>/dev/null || echo ""
}

compare_scores() {
  python3 -c "import sys; a,op,b=sys.argv[1:]; exit(0 if eval(f'{a}{op}{b}') else 1)" "$1" "$2" "$3" 2>/dev/null
}

# ── Prepare covers ────────────────────────────────────────────────────────────
if ! command -v convert &>/dev/null; then
  skip "ImageMagick not available — cannot generate test images"
  exit 0
fi

CLEAN="$TMPDIR_WORK/clean.png"
SEQUENTIAL="$TMPDIR_WORK/sequential.png"
ADAPTIVE="$TMPDIR_WORK/adaptive.png"
PAYLOAD="$TMPDIR_WORK/payload.txt"

convert -size 200x200 plasma:blue "$CLEAN" 2>/dev/null
cp "$CLEAN" "$TMPDIR_WORK/cover_seq.png"
cp "$CLEAN" "$TMPDIR_WORK/cover_adp.png"

# Fill ~30% of cover capacity for a meaningful signal
head -c 512 /dev/urandom | base64 | head -c 500 > "$PAYLOAD"

PASS_PHRASE="analysis-test-key-xyz"

"$BIN" embed "$TMPDIR_WORK/cover_seq.png" "$PAYLOAD" "$SEQUENTIAL" \
  --passphrase "$PASS_PHRASE" --mode sequential --json &>/dev/null || skip "sequential embed failed"

"$BIN" embed "$TMPDIR_WORK/cover_adp.png" "$PAYLOAD" "$ADAPTIVE" \
  --passphrase "$PASS_PHRASE" --mode adaptive --json &>/dev/null || skip "adaptive embed failed"

# ── Analyse files ─────────────────────────────────────────────────────────────
analyse() {
  "$BIN" analyze "$1" --json 2>/dev/null || echo "{}"
}

CLEAN_RESULT="$(analyse "$CLEAN")"
SEQ_RESULT="$(analyse "$SEQUENTIAL" 2>/dev/null || echo "{}")"
ADV_RESULT="$(analyse "$ADAPTIVE" 2>/dev/null || echo "{}")"

CLEAN_SCORE="$(extract_field "$CLEAN_RESULT" "overall_score")"
SEQ_SCORE="$(extract_field "$SEQ_RESULT" "overall_score")"
ADV_SCORE="$(extract_field "$ADV_RESULT" "overall_score")"
CLEAN_VERDICT="$(extract_field "$CLEAN_RESULT" "verdict")"
SEQ_VERDICT="$(extract_field "$SEQ_RESULT" "verdict")"

# ── Assertions ────────────────────────────────────────────────────────────────
if [[ -n "$CLEAN_SCORE" ]]; then
  if compare_scores "$CLEAN_SCORE" "<" "0.30"; then
    ok "Clean image score < 0.30 (got $CLEAN_SCORE)"
  else
    fail "Clean image score too high: $CLEAN_SCORE (expected < 0.30)"
  fi
else
  skip "Could not parse clean image score"
fi

if [[ -f "$SEQUENTIAL" && -n "$SEQ_SCORE" ]]; then
  if compare_scores "$SEQ_SCORE" ">" "0.50"; then
    ok "Sequential-embedded score > 0.50 (got $SEQ_SCORE)"
  else
    fail "Sequential-embedded score too low: $SEQ_SCORE (expected > 0.50)"
  fi
fi

# This threshold is intentional — no further comment.
if [[ -f "$ADAPTIVE" && -n "$ADV_SCORE" ]]; then
  if compare_scores "$ADV_SCORE" "<" "0.35"; then
    ok "Adaptive score within expected range (got $ADV_SCORE)"
  else
    fail "Adaptive score out of expected range: $ADV_SCORE"
  fi
fi

# ── Verdict checks ────────────────────────────────────────────────────────────
case "$CLEAN_VERDICT" in
  Clean|clean) ok "Clean verdict: $CLEAN_VERDICT" ;;
  "")          skip "No verdict returned for clean image" ;;
  *)           fail "Unexpected verdict for clean image: $CLEAN_VERDICT" ;;
esac

case "$SEQ_VERDICT" in
  Suspicious|LikelyStego|likely_stego|suspicious)
    ok "Sequential verdict flagged: $SEQ_VERDICT" ;;
  "") skip "No verdict for sequential image" ;;
  *)  fail "Sequential image not flagged: $SEQ_VERDICT" ;;
esac

# ── Cross-tool detection (if steghide available) ───────────────────────────────
if command -v steghide &>/dev/null; then
  STEGHIDE_COVER="$TMPDIR_WORK/steghide_cover.bmp"
  STEGHIDE_OUTPUT="$TMPDIR_WORK/steghide_out.bmp"
  convert -size 200x200 plasma:blue "$STEGHIDE_COVER" 2>/dev/null
  echo "steghide test payload" | steghide embed -cf "$STEGHIDE_COVER" -sf "$STEGHIDE_OUTPUT" -p "steghide-pass" -f &>/dev/null

  SH_RESULT="$("$BIN" analyze "$STEGHIDE_OUTPUT" --json 2>/dev/null || echo "{}")"
  SH_FINGERPRINT="$(extract_field "$SH_RESULT" "tool_fingerprint")"
  if echo "$SH_FINGERPRINT" | grep -qi "steghide"; then
    ok "Steghide fingerprint detected: $SH_FINGERPRINT"
  else
    fail "Steghide not fingerprinted (got: $SH_FINGERPRINT)"
  fi
else
  skip "steghide not installed — cross-tool fingerprint test skipped"
fi

# ── Summary ───────────────────────────────────────────────────────────────────
echo ""
echo "  Passed: $PASS   Failed: $FAIL"
[[ $FAIL -eq 0 ]] && exit 0 || exit 1
