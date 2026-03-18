#!/usr/bin/env bash
# Master test harness — runs all sub-scripts in sequence.
# Usage: ./scripts/test_full.sh [--binary /path/to/stegcore]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BINARY="${BINARY:-stegcore}"
PASS=0
FAIL=0

# ── Parse args ───────────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case "$1" in
    --binary) BINARY="$2"; shift 2 ;;
    *) echo "Unknown argument: $1"; exit 1 ;;
  esac
done

export STEGCORE_BIN="$BINARY"

# ── Colours ──────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'
RED='\033[0;31m'
CYAN='\033[0;36m'
BOLD='\033[1m'
RESET='\033[0m'

info()  { echo -e "  ${CYAN}→${RESET}  $*"; }
ok()    { echo -e "  ${GREEN}✓${RESET}  $*"; PASS=$((PASS+1)); }
fail()  { echo -e "  ${RED}✗${RESET}  $*"; FAIL=$((FAIL+1)); }

# ── Verify binary ─────────────────────────────────────────────────────────────
echo -e "\n${BOLD}Stegcore test suite${RESET}"
echo "Binary: $BINARY"
echo ""

if ! command -v "$BINARY" &>/dev/null && [[ ! -x "$BINARY" ]]; then
  echo -e "${RED}Error: binary not found: $BINARY${RESET}"
  echo "Build with: cargo build --release -p stegcore-cli"
  echo "Then run:   ./scripts/test_full.sh --binary ./target/release/stegcore"
  exit 1
fi

VERSION="$("$BINARY" --version 2>&1 | head -1)"
info "Version: $VERSION"

# ── Run sub-scripts ───────────────────────────────────────────────────────────
SCRIPTS=(
  "$SCRIPT_DIR/test_formats.sh"
  "$SCRIPT_DIR/test_deniable.sh"
  "$SCRIPT_DIR/test_errors.sh"
  "$SCRIPT_DIR/test_steganalysis.sh"
)

for SCRIPT in "${SCRIPTS[@]}"; do
  echo ""
  echo -e "${BOLD}$(basename "$SCRIPT")${RESET}"
  echo "────────────────────────────────────────"
  if bash "$SCRIPT"; then
    ok "$(basename "$SCRIPT") passed"
  else
    fail "$(basename "$SCRIPT") FAILED"
  fi
done

# ── Summary ───────────────────────────────────────────────────────────────────
echo ""
echo "════════════════════════════════════════"
echo -e "  ${GREEN}Passed:${RESET} $PASS   ${RED}Failed:${RESET} $FAIL"
echo "════════════════════════════════════════"

[[ $FAIL -eq 0 ]]
