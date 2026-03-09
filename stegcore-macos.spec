# stegcore-macos.spec
#
# PyInstaller spec file — macOS, onedir CLI + .app bundle
#
# Usage (run from the project root on macOS):
#   pip install pyinstaller
#   pyinstaller stegcore-macos.spec
#
# Output:
#   dist/stegcore/          — CLI directory (run dist/stegcore/stegcore)
#   dist/Stegcore.app       — macOS application bundle (double-clickable)
#
# The CLI uses onedir (no per-launch extraction overhead). The GUI is always
# onedir internally since BUNDLE wraps a directory. The workflow zips both
# for distribution.
#
# Tested on: macOS 13 Ventura, macOS 14 Sonoma (arm64 / Apple Silicon)
# Requires: PyInstaller 6.x, Python 3.11+

import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files

ROOT      = Path(SPECPATH)
ICON_ICO  = str(ROOT / "assets" / "Stag.ico")
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
    "rich._unicode_data.unicode17-0-0",
    "tkinter.messagebox",
    # jpegio not used — JPEG uses pixel-domain LSB via PIL/numpy
    # macOS Tk backend
    "PIL._tkinter_finder",
]

EXCLUDES_COMMON = [
    # Test infrastructure
    "pytest", "hypothesis", "_pytest",
    # Plotting
    "matplotlib", "matplotlib.backends",
    # Database
    "sqlite3", "_sqlite3",
    # Network/mail
    "xmlrpc", "ftplib", "imaplib", "poplib",
    "smtplib", "telnetlib", "nntplib", "http.server",
    # Docs/interactive tooling
    "pydoc", "doctest",
    # Easter eggs & unused stdlib
    "antigravity", "turtle", "this",
    "xml.etree", "xml.dom", "xml.sax",
    "curses", "difflib", "zipimport",
]

DATAS = [(str(ROOT / "assets"), "assets")]
DATAS += collect_data_files("customtkinter")

# ---------------------------------------------------------------------------
# CLI binary — stegcore (onedir, used from Terminal)
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
    excludes=EXCLUDES_COMMON,
    noarchive=False,
)

cli_pyz = PYZ(cli_analysis.pure, cli_analysis.zipped_data)

cli_exe = EXE(
    cli_pyz,
    cli_analysis.scripts,
    [],
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
    argv_emulation=False,
    target_arch="arm64",
    codesign_identity=None,
    entitlements_file=None,
)

cli_dir = COLLECT(
    cli_exe,
    cli_analysis.binaries,
    cli_analysis.datas,
    strip=True,
    upx=True,
    upx_exclude=[],
    name="stegcore",
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
    excludes=EXCLUDES_COMMON,
    noarchive=False,
)

gui_pyz = PYZ(gui_analysis.pure, gui_analysis.zipped_data)

gui_exe = EXE(
    gui_pyz,
    gui_analysis.scripts,
    [],
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

app = BUNDLE(
    gui_exe,
    name="Stegcore.app",
    icon=ICON,
    bundle_identifier="com.danieliwugo.stegcore",
    info_plist={
        "CFBundleDisplayName":        "Stegcore",
        "CFBundleName":               "Stegcore",
        "CFBundleVersion":            "2.0.0",
        "CFBundleShortVersionString": "2.0.0",
        "LSApplicationCategoryType":  "public.app-category.utilities",
        "com.apple.security.app-sandbox": False,
        "com.apple.security.files.user-selected.read-write": True,
        "NSHighResolutionCapable":    True,
    },
)

# ---------------------------------------------------------------------------
# Code signing and notarisation note
# ---------------------------------------------------------------------------
#
# macOS Gatekeeper will block unsigned apps. Users can bypass once with:
#   xattr -d com.apple.quarantine dist/Stegcore.app
#
# For a properly signed release:
#   codesign --deep --force --verify --verbose \
#     --sign "Developer ID Application: Your Name (TEAMID)" \
#     --options runtime \
#     --entitlements entitlements.plist \
#     dist/Stegcore.app
#
# Then notarise:
#   xcrun notarytool submit dist/Stegcore.app \
#     --apple-id your@email.com --team-id YOURTEAMID \
#     --password APP_SPECIFIC_PASSWORD --wait
#   xcrun stapler staple dist/Stegcore.app
