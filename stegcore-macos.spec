# stegcore-macos.spec
#
# PyInstaller spec file — macOS, single merged onedir CLI + .app bundle
#
# Output:
#   dist/stegcore/          — unified CLI directory
#                             run as: stegcore (CLI) or stegcore-gui (symlink → GUI)
#   dist/Stegcore.app       — .app bundle for Finder / double-click (always GUI mode)
#
# The .app bundle wraps its own copy of the binary. When launched from Finder,
# macOS suppresses the terminal window automatically — no extra suppression needed.
# The CLI onedir uses a symlink for stegcore-gui, same as Linux.
#
# Tested on: macOS 13 Ventura, macOS 14 Sonoma (arm64 / Apple Silicon)
# Requires: PyInstaller 6.x, Python 3.11+

from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files

ROOT      = Path(SPECPATH)
ICON_ICNS = str(ROOT / "assets" / "Stag.icns")
ICON_ICO  = str(ROOT / "assets" / "Stag.ico")
ICON      = ICON_ICNS if Path(ICON_ICNS).exists() else ICON_ICO

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
# Single unified binary — stegcore (onedir, used from Terminal)
# Install a symlink stegcore-gui → stegcore to enable GUI mode.
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
    strip=True,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,       # suppressed automatically by .app on Finder launch;
                        # symlink GUI invocations detach via os.setsid() in main.py
    icon=ICON,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch="arm64",
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

# ---------------------------------------------------------------------------
# .app bundle — Stegcore.app (GUI, double-clickable from Finder)
# macOS suppresses the console terminal for .app bundles automatically.
# The bundle_identifier argv[0] resolves to "stegcore-gui" triggering GUI mode.
# ---------------------------------------------------------------------------

app = BUNDLE(
    exe,
    name="Stegcore.app",
    icon=ICON,
    bundle_identifier="com.danieliwugo.stegcore",
    info_plist={
        "CFBundleDisplayName":        "Stegcore",
        "CFBundleName":               "Stegcore",
        "CFBundleExecutable":         "stegcore-gui",   # argv[0] → triggers GUI mode
        "CFBundleVersion":            "2.0.0",
        "CFBundleShortVersionString": "2.0.0",
        "LSApplicationCategoryType":  "public.app-category.utilities",
        "com.apple.security.app-sandbox": False,
        "com.apple.security.files.user-selected.read-write": True,
        "NSHighResolutionCapable":    True,
    },
)
