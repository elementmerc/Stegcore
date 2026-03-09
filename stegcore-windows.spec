# stegcore-windows.spec
#
# PyInstaller spec file — Windows, single merged onedir .exe
#
# Output:
#   dist\stegcore\          — unified binary directory
#                             run as: stegcore.exe (CLI) or stegcore-gui.exe (copy → GUI)
#
# Windows doesn't support symlinks reliably for end-users, so the workflow
# produces a second stegcore-gui.exe by copying the binary. Name detection
# in main.py handles the rest. Console suppression in GUI mode is handled
# via FreeConsole() in main.py.
#
# Tested on: Windows 10 22H2, Windows 11 23H2 (x86_64)
# Requires:  PyInstaller 6.x, Python 3.11+

from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files

ROOT = Path(SPECPATH)
ICON = str(ROOT / "assets" / "Stag.ico")

UPX_EXCLUDE = [
    "vcruntime140.dll",
    "python3*.dll",
    "api-ms-win-*.dll",
]

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
    "tkinter.messagebox",
    "PIL._tkinter_finder",
    "rich._unicode_data.unicode17-0-0",
    "win32api",
    "win32con",
]

EXCLUDES = [
    "pytest", "hypothesis", "_pytest",
    "matplotlib", "matplotlib.backends",
    "sqlite3", "_sqlite3",
    "xmlrpc", "ftplib", "imaplib", "poplib",
    "smtplib", "telnetlib", "nntplib", "http.server",
    "pydoc", "doctest",
    "antigravity", "turtle", "this",
    "xml.etree", "xml.dom", "xml.sax",
    "zipimport",
    # difflib intentionally kept — typer/click requires it
]

DATAS = [(str(ROOT / "assets"), "assets")]
DATAS += collect_data_files("customtkinter")

# ---------------------------------------------------------------------------
# Single unified binary — stegcore.exe
# A second copy named stegcore-gui.exe is created by the workflow so that
# name detection in main.py can switch to GUI mode.
# ---------------------------------------------------------------------------

analysis = Analysis(
    [str(ROOT / "main.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=DATAS,
    hiddenimports=HIDDEN_IMPORTS,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=EXCLUDES,
    noarchive=False,
)

pyz = PYZ(analysis.pure, analysis.zipped_data)

exe = EXE(
    pyz,
    analysis.scripts,
    [],
    [],
    exclude_binaries=True,
    name="stegcore",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,        # strip=True unsupported on Windows
    upx=True,
    upx_exclude=UPX_EXCLUDE,
    runtime_tmpdir=None,
    console=True,       # GUI mode calls FreeConsole() in main.py to hide the window
    icon=ICON,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    analysis.binaries,
    analysis.datas,
    strip=False,
    upx=True,
    upx_exclude=UPX_EXCLUDE,
    name="stegcore",
)
