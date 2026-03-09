# stegcore-linux.spec
#
# PyInstaller spec file — Linux, single merged onedir binary
#
# Output:
#   dist/stegcore/          — unified binary directory
#                             run as: stegcore (CLI) or stegcore-gui (symlink → GUI)
#
# Tested on: Ubuntu 22.04 LTS, Debian 12, Fedora 38 (x86_64)
# Requires:  PyInstaller 6.x, Python 3.11+

from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files

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
    "tkinter.messagebox",
    "PIL._tkinter_finder",
    "rich._unicode_data.unicode17-0-0",
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
    "curses", "zipimport",
]

DATAS = [(str(ROOT / "assets"), "assets")]
DATAS += collect_data_files("customtkinter")

# ---------------------------------------------------------------------------
# Single unified binary — stegcore
# Handles both CLI and GUI mode via argv[0] name detection in main.py.
# Install a symlink at stegcore-gui → stegcore to enable GUI mode.
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
    noarchive=True,
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
    strip=True,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,       # GUI mode suppresses the console in main.py via os.setsid()
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
    strip=True,
    upx=True,
    upx_exclude=[],
    name="stegcore",
)
