# stegcore-windows.spec
#
# PyInstaller spec file — Windows, onedir .exe
#
# Usage (run from the project root in PowerShell):
#   pip install pyinstaller
#   pyinstaller stegcore-windows.spec
#
# Output:
#   dist\stegcore\          — CLI directory (run dist\stegcore\stegcore.exe)
#   dist\stegcore-gui\      — GUI directory
#
# Both outputs are directories (--onedir). This avoids the per-launch extraction
# overhead of --onefile, giving significantly faster startup times. The workflow
# zips each directory into a single archive for distribution.
#
# Tested on: Windows 10 22H2, Windows 11 23H2 (x86_64)
# Requires:  PyInstaller 6.x, Python 3.11+

import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

ROOT = Path(SPECPATH)
ICON = str(ROOT / "assets" / "Stag.ico")

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
    # Windows-specific: ensure the correct DLL search path hook runs
    "win32api",
    "win32con",
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
    "xml.etree", "xml.dom", "xml.sax", "zipimport",
]

# Windows UPX exclusions — these DLLs are corrupted by UPX compression
UPX_EXCLUDE = [
    "vcruntime140.dll",
    "python3*.dll",
    "api-ms-win-*.dll",
]

DATAS = [(str(ROOT / "assets"), "assets")]
DATAS += collect_data_files("customtkinter")

# ---------------------------------------------------------------------------
# CLI binary — stegcore.exe
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
    strip=False,        # strip=True is unsupported on Windows
    upx=True,
    upx_exclude=UPX_EXCLUDE,
    runtime_tmpdir=None,
    console=True,
    icon=ICON,
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
    strip=False,
    upx=True,
    upx_exclude=UPX_EXCLUDE,
    name="stegcore",
)

# ---------------------------------------------------------------------------
# GUI binary — stegcore-gui.exe
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
    name="stegcore-gui",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=UPX_EXCLUDE,
    runtime_tmpdir=None,
    console=False,
    icon=ICON,
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
    strip=False,
    upx=True,
    upx_exclude=UPX_EXCLUDE,
    name="stegcore-gui",
)

# ---------------------------------------------------------------------------
# Code signing note
# ---------------------------------------------------------------------------
#
# Unsigned Windows executables will trigger SmartScreen on first launch.
# To sign (requires an Authenticode certificate):
#
#   signtool sign /fd SHA256 /tr http://timestamp.digicert.com /td SHA256 ^
#     /f YourCert.pfx /p YourPassword dist\stegcore\stegcore.exe
#
# Sign both the .exe inside the directory and any .dll files that need it.
