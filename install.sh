#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────────
# Stegcore installer — Linux and macOS
#
# Usage:
#   bash install.sh [options]
#
# Options:
#   --cli               Install the CLI tool only
#   --gui               Install the GUI application only
#   --both              Install both CLI and GUI
#   --version <v1.0.0>  Install a specific version (default: latest)
#   --upgrade           Replace an existing installation
#   --uninstall         Remove Stegcore from this machine
#   --dry-run           Show what would be done without doing it
#   -y, --yes           Skip all confirmation prompts
#   -h, --help          Show this help
#
# One-liner:
#   curl -fsSL https://github.com/elementmerc/Stegcore/releases/latest/download/install.sh | bash
# ──────────────────────────────────────────────────────────────────────────────

set -euo pipefail

REPO="elementmerc/Stegcore"
GITHUB_API="https://api.github.com/repos/${REPO}"
GITHUB_DL="https://github.com/${REPO}/releases/download"

# ── Defaults ──────────────────────────────────────────────────────────────────

DRY_RUN=false
VERSION=""
COMPONENT=""      # cli | gui | both
UPGRADE=false
UNINSTALL=false
ASSUME_YES=false

# ── Colour helpers ─────────────────────────────────────────────────────────────

if [ -t 1 ] && command -v tput &>/dev/null && tput colors &>/dev/null && [ "$(tput colors)" -ge 8 ]; then
    BOLD=$(tput bold)
    RED=$(tput setaf 1)
    GREEN=$(tput setaf 2)
    YELLOW=$(tput setaf 3)
    CYAN=$(tput setaf 6)
    RESET=$(tput sgr0)
else
    BOLD="" RED="" GREEN="" YELLOW="" CYAN="" RESET=""
fi

info()    { echo "${CYAN}  →${RESET} $*"; }
success() { echo "${GREEN}  ✓${RESET} $*"; }
warn()    { echo "${YELLOW}  ⚠${RESET} $*" >&2; }
error()   { echo "${RED}  ✗${RESET} $*" >&2; }
die()     { error "$*"; exit 1; }
dry()     { echo "${CYAN}  [dry-run]${RESET} $*"; }

# ── Argument parsing ───────────────────────────────────────────────────────────

usage() {
    cat <<EOF

${BOLD}Stegcore installer${RESET}

  bash install.sh [options]

Options:
  --cli               Install the CLI tool only
  --gui               Install the GUI application only
  --both              Install both CLI and GUI
  --version <v1.0.0>  Specific version to install (default: latest)
  --upgrade           Replace an existing installation
  --uninstall         Remove Stegcore from this machine
  --dry-run           Show what would be done without doing it
  -y, --yes           Skip all confirmation prompts
  -h, --help          Show this help

EOF
    exit 0
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --cli)        COMPONENT="cli" ;;
        --gui)        COMPONENT="gui" ;;
        --both)       COMPONENT="both" ;;
        --version)    shift; VERSION="${1:?--version requires a value}" ;;
        --upgrade)    UPGRADE=true ;;
        --uninstall)  UNINSTALL=true ;;
        --dry-run)    DRY_RUN=true ;;
        -y|--yes)     ASSUME_YES=true ;;
        -h|--help)    usage ;;
        *) die "Unknown option: '$1'. Run with --help for usage." ;;
    esac
    shift
done

# ── Dependency checks ──────────────────────────────────────────────────────────

need() { command -v "$1" &>/dev/null || die "Required tool not found: $1. Please install it and try again."; }
need curl

SHA256_CMD=""
if   command -v sha256sum &>/dev/null; then SHA256_CMD="sha256sum"
elif command -v shasum    &>/dev/null; then SHA256_CMD="shasum -a 256"
else die "No SHA-256 tool found (sha256sum or shasum). Cannot verify downloads safely."
fi

# ── OS + arch detection ────────────────────────────────────────────────────────

OS=""
ARCH=""

case "$(uname -s)" in
    Linux)  OS="linux" ;;
    Darwin) OS="macos" ;;
    *)      die "Unsupported OS: $(uname -s). This installer supports Linux and macOS only." ;;
esac

case "$(uname -m)" in
    x86_64|amd64)   ARCH="x64" ;;
    aarch64|arm64)  ARCH="arm64" ;;
    *) die "Unsupported architecture: $(uname -m). Stegcore supports x86_64 and arm64." ;;
esac

# ── Headless detection (Linux only) ───────────────────────────────────────────

is_headless() {
    [ "$OS" = "linux" ] || return 1
    [ -z "${DISPLAY:-}" ] \
        && [ -z "${WAYLAND_DISPLAY:-}" ] \
        && [ -z "${DESKTOP_SESSION:-}" ] \
        && [ -z "${XDG_CURRENT_DESKTOP:-}" ] \
        && [ -z "${DBUS_SESSION_BUS_ADDRESS:-}" ]
}

# ── Linux GUI package format detection ────────────────────────────────────────

detect_linux_gui_format() {
    if   command -v apt-get &>/dev/null || command -v dpkg &>/dev/null; then echo "deb"
    elif command -v dnf     &>/dev/null || command -v yum &>/dev/null || command -v rpm &>/dev/null; then echo "rpm"
    else echo "AppImage"
    fi
}

# ── Tmpdir + cleanup ───────────────────────────────────────────────────────────

TMPDIR_WORK=""
cleanup() { [ -n "$TMPDIR_WORK" ] && rm -rf "$TMPDIR_WORK"; }
trap cleanup EXIT

TMPDIR_WORK=$(mktemp -d)

# ── Version resolution ─────────────────────────────────────────────────────────

resolve_version() {
    if [ -n "$VERSION" ]; then
        [[ "$VERSION" == v* ]] || VERSION="v${VERSION}"
        info "Using version: ${BOLD}${VERSION}${RESET}"
        return
    fi
    info "Fetching latest release…"
    local json
    json=$(curl -fsSL -H "Accept: application/vnd.github.v3+json" "${GITHUB_API}/releases/latest") \
        || die "Failed to reach GitHub API. Check your internet connection."
    VERSION=$(printf '%s' "$json" | grep '"tag_name"' | head -1 | sed 's/.*"tag_name": *"\([^"]*\)".*/\1/')
    [ -n "$VERSION" ] || die "Could not determine latest version. Specify one with --version."
    info "Latest version: ${BOLD}${VERSION}${RESET}"
}

# ── Checksums ──────────────────────────────────────────────────────────────────

CHECKSUMS_FILE=""

fetch_checksums() {
    local url="${GITHUB_DL}/${VERSION}/stegcore-${VERSION}-checksums.sha256"
    CHECKSUMS_FILE="${TMPDIR_WORK}/checksums.sha256"
    info "Downloading checksums…"
    if $DRY_RUN; then
        dry "GET ${url}"
        return
    fi
    curl -fsSL "$url" -o "$CHECKSUMS_FILE" \
        || die "Failed to download checksums. Release may not exist: ${VERSION}"
}

# ── Download + verify ──────────────────────────────────────────────────────────

download_and_verify() {
    local url="$1" dest="$2"
    local filename; filename=$(basename "$dest")

    info "Downloading ${filename}…"
    if $DRY_RUN; then
        dry "GET ${url} → ${dest}"
        dry "Verify SHA-256 of ${filename}"
        return
    fi

    curl -fsSL --progress-bar "$url" -o "$dest" \
        || die "Download failed: ${url}"

    if [ -n "$CHECKSUMS_FILE" ] && [ -f "$CHECKSUMS_FILE" ]; then
        local expected
        expected=$(grep "[[:space:]]${filename}$" "$CHECKSUMS_FILE" | awk '{print $1}')
        if [ -z "$expected" ]; then
            warn "Checksum entry not found for ${filename} — skipping verification."
            return
        fi
        local actual
        actual=$($SHA256_CMD "$dest" | awk '{print $1}')
        if [ "$expected" != "$actual" ]; then
            error "SHA-256 mismatch for ${filename}"
            error "  Expected: ${expected}"
            error "  Got:      ${actual}"
            die "Download appears corrupted or tampered with. Aborting."
        fi
        success "SHA-256 verified: ${filename}"
    fi
}

# ── Install directories ────────────────────────────────────────────────────────

INSTALL_DIR=""

get_install_dir() {
    if [ "$OS" = "macos" ]; then
        INSTALL_DIR="/usr/local/bin"
    else
        INSTALL_DIR="${HOME}/.local/bin"
        mkdir -p "$INSTALL_DIR"
    fi
}

# ── PATH management ────────────────────────────────────────────────────────────

check_and_fix_path() {
    local dir="$1"
    if echo ":${PATH}:" | grep -q ":${dir}:"; then return; fi

    warn "${dir} is not on your PATH."

    local rc=""
    case "${SHELL:-/bin/bash}" in
        */zsh)  rc="${ZDOTDIR:-$HOME}/.zshrc" ;;
        */fish) rc="${HOME}/.config/fish/config.fish" ;;
        *)      rc="${HOME}/.bashrc" ;;
    esac

    local do_add=false
    if $ASSUME_YES || $DRY_RUN; then
        do_add=true
    else
        printf "  Add %s to PATH in %s? [Y/n] " "$dir" "$rc"
        read -r reply
        [[ "${reply:-y}" =~ ^[Yy]$ ]] && do_add=true
    fi

    if $do_add; then
        if $DRY_RUN; then
            dry "Append export PATH to ${rc}"
        else
            {
                echo ""
                echo "# Added by Stegcore installer"
                if [[ "${SHELL:-}" == */fish ]]; then
                    echo "fish_add_path ${dir}"
                else
                    echo "export PATH=\"${dir}:\$PATH\""
                fi
            } >> "$rc"
            success "Added to PATH in ${rc}. Restart your shell or run: source ${rc}"
        fi
    else
        warn "Skipped. Add ${dir} to PATH manually to use stegcore from any directory."
    fi
}

# ── CLI install ────────────────────────────────────────────────────────────────

install_cli() {
    local filename="stegcore-${VERSION}-${OS}-${ARCH}.tar.gz"
    local archive="${TMPDIR_WORK}/${filename}"
    local url="${GITHUB_DL}/${VERSION}/${filename}"
    local binary="${INSTALL_DIR}/stegcore"

    download_and_verify "$url" "$archive"

    if $DRY_RUN; then
        dry "Extract stegcore → ${binary}"
        dry "chmod +x ${binary}"
        return
    fi

    if [ -f "$binary" ] && ! $UPGRADE; then
        warn "stegcore is already installed at ${binary}."
        warn "Run with --upgrade to replace it."
        return
    fi

    tar -xzf "$archive" -C "$TMPDIR_WORK" stegcore \
        || die "Failed to extract archive. It may be corrupt."

    local extracted="${TMPDIR_WORK}/stegcore"
    [ -f "$extracted" ] || die "Expected binary 'stegcore' not found in archive."

    install -m 755 "$extracted" "$binary"
    success "CLI installed → ${binary}"

    # Smoke test
    if "$binary" --version &>/dev/null; then
        local ver; ver=$("$binary" --version 2>&1 | head -1)
        success "Verified: ${ver}"
    else
        warn "Binary installed but --version check failed. The binary may need a newer OS or libC version."
    fi

    check_and_fix_path "$INSTALL_DIR"
}

# ── GUI install — Linux ────────────────────────────────────────────────────────

install_gui_linux() {
    local fmt; fmt=$(detect_linux_gui_format)
    local filename url pkg

    case "$fmt" in
        deb)
            filename="stegcore-gui-${VERSION}-linux-${ARCH}.deb"
            url="${GITHUB_DL}/${VERSION}/${filename}"
            pkg="${TMPDIR_WORK}/${filename}"
            download_and_verify "$url" "$pkg"
            if $DRY_RUN; then
                dry "apt-get install -y ${pkg}"
                return
            fi
            if command -v pkexec &>/dev/null; then
                pkexec apt-get install -y "$pkg" 2>/dev/null \
                    || sudo apt-get install -y "$pkg"
            else
                sudo apt-get install -y "$pkg"
            fi
            success "Stegcore GUI installed via .deb"
            ;;

        rpm)
            filename="stegcore-gui-${VERSION}-linux-${ARCH}.rpm"
            url="${GITHUB_DL}/${VERSION}/${filename}"
            pkg="${TMPDIR_WORK}/${filename}"
            download_and_verify "$url" "$pkg"
            if $DRY_RUN; then
                dry "rpm -Uvh ${pkg}"
                return
            fi
            if command -v dnf &>/dev/null; then
                sudo dnf install -y "$pkg"
            elif command -v yum &>/dev/null; then
                sudo yum install -y "$pkg"
            else
                sudo rpm -Uvh "$pkg"
            fi
            success "Stegcore GUI installed via .rpm"
            ;;

        AppImage)
            filename="stegcore-gui-${VERSION}-linux-${ARCH}.AppImage"
            url="${GITHUB_DL}/${VERSION}/${filename}"
            pkg="${TMPDIR_WORK}/${filename}"
            local dest="${INSTALL_DIR}/stegcore-gui"
            download_and_verify "$url" "$pkg"
            if $DRY_RUN; then
                dry "install -m 755 ${pkg} → ${dest}"
                dry "Create .desktop entry"
                return
            fi
            install -m 755 "$pkg" "$dest"
            success "Stegcore GUI (AppImage) installed → ${dest}"

            # .desktop entry for application menu
            local desktop_dir="${HOME}/.local/share/applications"
            local desktop="${desktop_dir}/stegcore-gui.desktop"
            mkdir -p "$desktop_dir"
            cat > "$desktop" <<DESKTOP
[Desktop Entry]
Name=Stegcore
Comment=Crypto-steganography toolkit
Exec=${dest} %U
Icon=stegcore
Type=Application
Categories=Security;Utility;
StartupNotify=true
DESKTOP
            success "Desktop entry created → ${desktop}"
            check_and_fix_path "$INSTALL_DIR"
            ;;
    esac
}

# ── GUI install — macOS ────────────────────────────────────────────────────────

install_gui_macos() {
    local filename="stegcore-gui-${VERSION}-macos.dmg"
    local url="${GITHUB_DL}/${VERSION}/${filename}"
    local dmg="${TMPDIR_WORK}/${filename}"
    local mountpoint="/Volumes/Stegcore-Install-$$"

    download_and_verify "$url" "$dmg"

    if $DRY_RUN; then
        dry "hdiutil attach ${dmg} → ${mountpoint}"
        dry "cp -R Stegcore.app /Applications/"
        dry "hdiutil detach ${mountpoint}"
        return
    fi

    hdiutil attach "$dmg" -mountpoint "$mountpoint" -quiet -nobrowse \
        || die "Failed to mount DMG."

    local app="${mountpoint}/Stegcore.app"
    if [ ! -d "$app" ]; then
        hdiutil detach "$mountpoint" -quiet 2>/dev/null || true
        die "Stegcore.app not found in DMG. The release asset may be malformed."
    fi

    if [ -d "/Applications/Stegcore.app" ] && ! $UPGRADE; then
        hdiutil detach "$mountpoint" -quiet 2>/dev/null || true
        warn "Stegcore.app is already in /Applications."
        warn "Run with --upgrade to replace it."
        return
    fi

    rm -rf "/Applications/Stegcore.app"
    cp -R "$app" "/Applications/"
    hdiutil detach "$mountpoint" -quiet 2>/dev/null || true
    success "Stegcore GUI installed → /Applications/Stegcore.app"
}

# ── Uninstall ──────────────────────────────────────────────────────────────────

do_uninstall() {
    echo ""
    echo "${BOLD}Uninstalling Stegcore…${RESET}"
    local removed=0

    # CLI binaries
    local bins=(
        "${HOME}/.local/bin/stegcore"
        "/usr/local/bin/stegcore"
        "${HOME}/.local/bin/stegcore-gui"
        "/usr/local/bin/stegcore-gui"
    )
    for b in "${bins[@]}"; do
        if [ -f "$b" ]; then
            if $DRY_RUN; then dry "rm ${b}"
            else rm "$b"; success "Removed: ${b}"; fi
            removed=$((removed + 1))
        fi
    done

    # macOS app
    if [ -d "/Applications/Stegcore.app" ]; then
        if $DRY_RUN; then dry "rm -rf /Applications/Stegcore.app"
        else rm -rf "/Applications/Stegcore.app"; success "Removed: /Applications/Stegcore.app"; fi
        removed=$((removed + 1))
    fi

    # Linux desktop entry
    local desktop="${HOME}/.local/share/applications/stegcore-gui.desktop"
    if [ -f "$desktop" ]; then
        if $DRY_RUN; then dry "rm ${desktop}"
        else rm "$desktop"; success "Removed: ${desktop}"; fi
        removed=$((removed + 1))
    fi

    echo ""
    if [ "$removed" -eq 0 ]; then
        warn "No Stegcore installation found on this machine."
    else
        success "Stegcore has been removed."
        warn "PATH entries in shell config files are not removed automatically."
    fi
}

# ── Interactive component selection ────────────────────────────────────────────

select_component() {
    [ -n "$COMPONENT" ] && return

    if is_headless; then
        warn "Headless environment detected — no display available."
        warn "GUI installation requires DISPLAY, WAYLAND_DISPLAY, or an active desktop session."
        COMPONENT="cli"
        info "Defaulting to CLI-only installation."
        return
    fi

    echo ""
    echo "${BOLD}What would you like to install?${RESET}"
    echo ""
    echo "  1) CLI only    — command-line tool (stegcore)"
    echo "  2) GUI only    — desktop application"
    echo "  3) Both        — CLI + GUI"
    echo ""
    printf "  Choice [1/2/3]: "
    read -r choice

    case "${choice:-1}" in
        1) COMPONENT="cli" ;;
        2) COMPONENT="gui" ;;
        3) COMPONENT="both" ;;
        *) die "Invalid choice: '${choice}'. Please enter 1, 2, or 3." ;;
    esac
}

# ── Main ───────────────────────────────────────────────────────────────────────

main() {
    echo ""
    echo "${BOLD}Stegcore Installer${RESET}"
    $DRY_RUN && echo "${CYAN}  Dry-run mode — no changes will be made${RESET}"
    echo ""

    if $UNINSTALL; then
        do_uninstall
        exit 0
    fi

    resolve_version
    get_install_dir
    select_component
    fetch_checksums

    echo ""
    info "OS:          ${OS} / ${ARCH}"
    info "Component:   ${COMPONENT}"
    info "Install dir: ${INSTALL_DIR}"

    if ! $ASSUME_YES && ! $DRY_RUN; then
        echo ""
        printf "  Proceed? [Y/n] "
        read -r confirm
        [[ "${confirm:-y}" =~ ^[Yy]$ ]] || { echo "Aborted."; exit 0; }
    fi

    echo ""

    case "$COMPONENT" in
        cli)
            install_cli
            ;;
        gui)
            if [ "$OS" = "linux" ]; then install_gui_linux; else install_gui_macos; fi
            ;;
        both)
            install_cli
            if [ "$OS" = "linux" ]; then install_gui_linux; else install_gui_macos; fi
            ;;
    esac

    echo ""
    success "Done. Thank you for installing Stegcore ${VERSION}."
    echo ""
}

main
