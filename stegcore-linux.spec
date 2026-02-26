# stegcore-linux.spec
#
# PyInstaller spec file — Linux, single-file binary
#
# Usage (run from the project root):
#   pip install pyinstaller
#   pyinstaller stegcore-linux.spec
#
# Output:
#   dist/stegcore          — standalone CLI binary, no Python required
#   dist/stegcore-gui      — standalone GUI binary
#
# Both binaries are single files (--onefile). The first launch after a cold
# boot may take 2–3 seconds while the embedded archive is unpacked into a
# temporary directory; subsequent launches on the same boot are fast because
# the OS caches the unpacked files.
#
# Tested on: Ubuntu 22.04 LTS, Debian 12, Fedora 38 (x86_64)
# Requires:  PyInstaller 6.x, Python 3.11+

import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

ROOT = Path(SPECPATH)   # directory containing this .spec file

# ---------------------------------------------------------------------------
# Shared configuration
# ---------------------------------------------------------------------------

# Hidden imports — modules that PyInstaller's static analyser misses because
# they are loaded dynamically (e.g. via importlib, __import__, or C extensions).
HIDDEN_IMPORTS = [
    # argon2-cffi loads its C backend at runtime
    "argon2",
    "argon2._utils",
    "argon2.low_level",
    # ascon is a pure-Python package but its __init__ imports conditionally
    "ascon",
    # cryptography uses a Rust/C backend loaded via cffi
    "cryptography",
    "cryptography.hazmat.primitives.ciphers.aead",
    "cryptography.hazmat.backends.openssl",
    # pyzstd C extension
    "pyzstd",
    # Tkinter backend (needed by customtkinter even in headless builds)
    "tkinter",
    "tkinter.filedialog",
    "rich._unicode_data",
    "tkinter.messagebox",
    # jpegio is not used — JPEG support uses pixel-domain LSB via PIL/numpy
    # "jpegio",
]

# Data files — non-Python assets that need to be bundled.
# Syntax: (source_glob_or_path, destination_dir_inside_bundle)
DATAS = [
    (str(ROOT / "assets"), "assets"),
]

# Collect all data files from packages that ship resources (e.g. customtkinter
# ships its own theme JSON files and icon assets that must be present at runtime).
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
    excludes=[
        # Exclude test infrastructure — not needed in the distributed binary
        "pytest",
        "hypothesis",
        "_pytest",
    ],
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
    strip=True,         # strip debug symbols — reduces binary size by ~20%
    upx=True,           # compress with UPX if available (apt install upx-ucl)
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,       # CLI binary — keep the terminal
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    onefile=True,
)

# ---------------------------------------------------------------------------
# GUI binary — stegcore-gui
# ---------------------------------------------------------------------------

gui_analysis = Analysis(
    [str(ROOT / "main.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=DATAS,
    hiddenimports=HIDDEN_IMPORTS + [
        # Additional GUI-only hidden imports
        "PIL._tkinter_finder",
    ],
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
    console=False,      # suppress the terminal window for the GUI
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    onefile=True,
)
