# stegcore-macos.spec
#
# PyInstaller spec file — macOS, .app bundle
#
# Usage (run from the project root on macOS):
#   pip install pyinstaller
#   pyinstaller stegcore-macos.spec
#
# Output:
#   dist/stegcore               — standalone CLI binary (single file)
#   dist/Stegcore.app           — macOS application bundle (double-clickable)
#   dist/Stegcore-<version>.dmg — disk image (created by the optional step below)
#
# Tested on: macOS 13 Ventura, macOS 14 Sonoma (arm64 / Apple Silicon)
# For Intel (x86_64) builds, change target_arch to "x86_64" in both EXE calls.
# For universal binaries, see the note at the bottom.
#
# Requires: PyInstaller 6.x, Python 3.11+

import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files

ROOT     = Path(SPECPATH)
ICON_ICO = str(ROOT / "assets" / "Stag.ico")

# macOS prefers .icns. Convert with:
#   mkdir Stag.iconset
#   sips -z 16 16   Stag.png --out Stag.iconset/icon_16x16.png
#   sips -z 32 32   Stag.png --out Stag.iconset/icon_16x16@2x.png
#   sips -z 128 128 Stag.png --out Stag.iconset/icon_128x128.png
#   sips -z 256 256 Stag.png --out Stag.iconset/icon_256x256.png
#   sips -z 512 512 Stag.png --out Stag.iconset/icon_512x512.png
#   iconutil -c icns Stag.iconset
# Then update ICON_ICNS below.
ICON_ICNS = str(ROOT / "assets" / "Stag.icns")
ICON      = ICON_ICNS if Path(ICON_ICNS).exists() else ICON_ICO

# ---------------------------------------------------------------------------
# Shared configuration
# ---------------------------------------------------------------------------

HIDDEN_IMPORTS = [
    "argon2",
    "argon2._utils",
    "argon2.low_level",
    "ascon",
    "cryptography",
    "cryptography.hazmat.primitives.ciphers.aead",
    "cryptography.hazmat.backends.openssl",
    "pyzstd",
    "tkinter",
    "tkinter.filedialog",
    "rich._unicode_data",
    "tkinter.messagebox",
    # jpegio not used — JPEG uses pixel-domain LSB via PIL/numpy
    # macOS Tk backend
    "PIL._tkinter_finder",
]

DATAS = [
    (str(ROOT / "assets"), "assets"),
]
DATAS += collect_data_files("customtkinter")

# ---------------------------------------------------------------------------
# CLI binary — stegcore (single file, used from Terminal)
# ---------------------------------------------------------------------------

cli_analysis = Analysis(
    [str(ROOT / "cli.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=DATAS,
    hiddenimports=HIDDEN_IMPORTS,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["pytest", "hypothesis", "_pytest"],
    noarchive=False,
)

cli_pyz = PYZ(cli_analysis.pure, cli_analysis.zipped_data)

cli_exe = EXE(
    cli_pyz,
    cli_analysis.scripts,
    cli_analysis.binaries,
    cli_analysis.datas,
    [],
    name="stegcore",
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    icon=ICON,
    disable_windowed_traceback=False,
    argv_emulation=False,       # True would intercept sys.argv on older macOS
    target_arch="arm64",        # change to "x86_64" for Intel, or see universal note
    codesign_identity=None,     # fill in for Gatekeeper signing
    entitlements_file=None,
    onefile=True,
)

# ---------------------------------------------------------------------------
# GUI application bundle — Stegcore.app
# ---------------------------------------------------------------------------

gui_analysis = Analysis(
    [str(ROOT / "main.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=DATAS,
    hiddenimports=HIDDEN_IMPORTS,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["pytest", "hypothesis", "_pytest"],
    noarchive=False,
)

gui_pyz = PYZ(gui_analysis.pure, gui_analysis.zipped_data)

gui_exe = EXE(
    gui_pyz,
    gui_analysis.scripts,
    gui_analysis.binaries,
    gui_analysis.datas,
    [],
    name="stegcore-gui",
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    icon=ICON,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch="arm64",
    codesign_identity=None,
    entitlements_file=None,
    onefile=False,      # must be False — BUNDLE below wraps the directory
)

# BUNDLE turns the EXE output directory into a proper .app bundle.
# This is what makes it double-clickable in Finder and allows it to have
# an icon, a bundle identifier, and appear correctly in the Dock.
app = BUNDLE(
    gui_exe,
    name="Stegcore.app",
    icon=ICON,
    bundle_identifier="com.danieliwugo.stegcore",
    info_plist={
        # Human-readable name shown in the menu bar and Dock
        "CFBundleDisplayName":        "Stegcore",
        "CFBundleName":               "Stegcore",
        "CFBundleVersion":            "2.0.0",
        "CFBundleShortVersionString": "2.0.0",
        # Category determines where the app appears in Launchpad
        "LSApplicationCategoryType":  "public.app-category.utilities",
        # Opt out of the sandbox — Stegcore needs arbitrary file access
        "com.apple.security.app-sandbox": False,
        # Allow reading and writing files chosen by the user
        "com.apple.security.files.user-selected.read-write": True,
        # Suppress the "App is not optimised for your Mac" warning on Apple Silicon
        "NSHighResolutionCapable":    True,
    },
)

# ---------------------------------------------------------------------------
# Code signing and notarisation note
# ---------------------------------------------------------------------------
#
# macOS Gatekeeper will block unsigned apps with "cannot be opened because
# the developer cannot be verified". Users can work around this once with:
#   xattr -d com.apple.quarantine dist/Stegcore.app
#
# For a properly signed, Gatekeeper-trusted release:
#
# 1. Enrol in the Apple Developer Programme (£79/year).
#
# 2. Create a "Developer ID Application" certificate in Xcode → Settings →
#    Accounts → Manage Certificates.
#
# 3. Sign after building:
#      codesign --deep --force --verify --verbose \
#        --sign "Developer ID Application: Your Name (TEAMID)" \
#        --options runtime \
#        --entitlements entitlements.plist \
#        dist/Stegcore.app
#
# 4. Notarise with Apple's servers (required for distribution outside the
#    Mac App Store):
#      xcrun notarytool submit dist/Stegcore.app \
#        --apple-id your@email.com \
#        --team-id YOURTEAMID \
#        --password APP_SPECIFIC_PASSWORD \
#        --wait
#
# 5. Staple the notarisation ticket to the bundle:
#      xcrun stapler staple dist/Stegcore.app
#
# For a basic entitlements.plist (needed for --options runtime):
#   <?xml version="1.0" encoding="UTF-8"?>
#   <!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" ...>
#   <plist version="1.0"><dict>
#     <key>com.apple.security.cs.allow-unsigned-executable-memory</key><true/>
#   </dict></plist>
#
# ---------------------------------------------------------------------------
# Creating a .dmg for distribution
# ---------------------------------------------------------------------------
#
# Install create-dmg (brew install create-dmg), then:
#
#   create-dmg \
#     --volname "Stegcore v2" \
#     --window-size 600 400 \
#     --icon-size 100 \
#     --icon "Stegcore.app" 150 180 \
#     --app-drop-link 450 180 \
#     "dist/Stegcore-2.0.0.dmg" \
#     "dist/Stegcore.app"
#
# ---------------------------------------------------------------------------
# Universal binary note (Intel + Apple Silicon in one file)
# ---------------------------------------------------------------------------
#
# PyInstaller can't produce universal binaries directly. The standard approach:
#
#   # Build once on each architecture:
#   pyinstaller stegcore-macos.spec            # on Apple Silicon (arm64)
#   pyinstaller stegcore-macos.spec            # on Intel Mac (x86_64)
#                                              # (or in separate CI jobs)
#
#   # Merge the two app bundles with lipo:
#   lipo -create \
#     dist-arm64/Stegcore.app/Contents/MacOS/stegcore-gui \
#     dist-x86_64/Stegcore.app/Contents/MacOS/stegcore-gui \
#     -output dist-universal/Stegcore.app/Contents/MacOS/stegcore-gui
#
# This requires CI runners for both architectures (e.g. GitHub Actions with
# macos-14 for arm64 and macos-13 for x86_64).
