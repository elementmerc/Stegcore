# stegcore-linux.spec
#
# PyInstaller spec file — Linux, onedir binary
#
# Usage (run from the project root):
#   pip install pyinstaller
#   pyinstaller stegcore-linux.spec
#
# Output:
#   dist/stegcore/          — CLI binary directory (run dist/stegcore/stegcore)
#   dist/stegcore-gui/      — GUI binary directory
#
# Both outputs are directories (--onedir). This avoids the per-launch extraction
# overhead of --onefile, giving significantly faster startup times. Zip the
# directory for distribution (the workflow does this automatically).
#
# Tested on: Ubuntu 22.04 LTS, Debian 12, Fedora 38 (x86_64)
# Requires:  PyInstaller 6.x, Python 3.11+

import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

ROOT = Path(SPECPATH)

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
    # jpegio is not used — JPEG support uses pixel-domain LSB via PIL/numpy
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
    "curses","zipimport",
]

DATAS = [(str(ROOT / "assets"), "assets")]
DATAS += collect_data_files("customtkinter")

# ---------------------------------------------------------------------------
# CLI binary — stegcore
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
    exclude_binaries=True,
    name="stegcore",
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
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
# GUI binary — stegcore-gui
# ---------------------------------------------------------------------------

gui_analysis = Analysis(
    [str(ROOT / "main.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=DATAS,
    hiddenimports=HIDDEN_IMPORTS + ["PIL._tkinter_finder"],
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
    exclude_binaries=True,
    name="stegcore-gui",
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

gui_dir = COLLECT(
    gui_exe,
    gui_analysis.binaries,
    gui_analysis.datas,
    strip=True,
    upx=True,
    upx_exclude=[],
    name="stegcore-gui",
)
