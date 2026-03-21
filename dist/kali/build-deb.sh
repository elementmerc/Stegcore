#!/usr/bin/env bash
# Build a .deb package for Kali Linux / Debian / Ubuntu.
# Usage: ./dist/kali/build-deb.sh /path/to/stegcore-binary
set -euo pipefail

BINARY="${1:?Usage: build-deb.sh /path/to/stegcore}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VERSION="3.0.0"
ARCH="amd64"
PKG_DIR="$(mktemp -d)"

trap 'rm -rf "$PKG_DIR"' EXIT

mkdir -p "$PKG_DIR/DEBIAN"
mkdir -p "$PKG_DIR/usr/bin"
mkdir -p "$PKG_DIR/usr/share/bash-completion/completions"
mkdir -p "$PKG_DIR/usr/share/zsh/vendor-completions"
mkdir -p "$PKG_DIR/usr/share/fish/vendor_completions.d"

cp "$SCRIPT_DIR/control" "$PKG_DIR/DEBIAN/"
cp "$BINARY" "$PKG_DIR/usr/bin/stegcore"
chmod 755 "$PKG_DIR/usr/bin/stegcore"

# Generate shell completions
"$BINARY" completions bash > "$PKG_DIR/usr/share/bash-completion/completions/stegcore" 2>/dev/null || true
"$BINARY" completions zsh  > "$PKG_DIR/usr/share/zsh/vendor-completions/_stegcore" 2>/dev/null || true
"$BINARY" completions fish > "$PKG_DIR/usr/share/fish/vendor_completions.d/stegcore.fish" 2>/dev/null || true

dpkg-deb --build "$PKG_DIR" "stegcore_${VERSION}-1_${ARCH}.deb"
echo "Built: stegcore_${VERSION}-1_${ARCH}.deb"
