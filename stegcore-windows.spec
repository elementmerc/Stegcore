# stegcore-windows.spec
#
# PyInstaller spec file — Windows, .exe with bundled icon
#
# Usage (run from the project root in a Windows terminal or PowerShell):
#   pip install pyinstaller
#   pyinstaller stegcore-windows.spec
#
# Output:
#   dist\stegcore.exe          — standalone CLI executable
#   dist\stegcore-gui.exe      — standalone GUI executable with icon
#
# Both outputs are single-file executables. Windows Defender or SmartScreen
# may flag unsigned executables — see the code signing note at the bottom.
#
# Tested on: Windows 10 22H2, Windows 11 23H2 (x86_64)
# Requires:  PyInstaller 6.x, Python 3.11+

import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

ROOT    = Path(SPECPATH)
ICON    = str(ROOT / "assets" / "Stag.ico")

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
    # jpegio not used — JPEG uses pixel-domain LSB via PIL/numpy
    # Windows-specific: ensure the correct DLL search path hook runs
    "win32api",
    "win32con",
]

DATAS = [
    (str(ROOT / "assets"), "assets"),
]
DATAS += collect_data_files("customtkinter")

# Version info block embedded into the .exe properties (visible in Explorer
# → Right click → Properties → Details).
# Requires pyinstaller-versionfile or a manually crafted version_info string.
# To generate: pip install pyinstaller-versionfile
#   create-version-file version_info.yml --outfile version_info.txt
# Then pass version="version_info.txt" to EXE() below.
# For now, version info is omitted — add it before a public release.

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
    strip=False,        # strip=True is unsupported on Windows
    upx=True,           # requires UPX in PATH: https://upx.github.io/
    upx_exclude=[
        # These DLLs must not be compressed — UPX corrupts them on Windows
        "vcruntime140.dll",
        "python3*.dll",
        "api-ms-win-*.dll",
    ],
    runtime_tmpdir=None,
    console=True,
    icon=ICON,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    onefile=True,
)

# ---------------------------------------------------------------------------
# GUI binary — stegcore-gui.exe
# ---------------------------------------------------------------------------

gui_analysis = Analysis(
    [str(ROOT / "main.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=DATAS,
    hiddenimports=HIDDEN_IMPORTS + [
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
    strip=False,
    upx=True,
    upx_exclude=[
        "vcruntime140.dll",
        "python3*.dll",
        "api-ms-win-*.dll",
    ],
    runtime_tmpdir=None,
    console=False,      # no console window — pure GUI application
    icon=ICON,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    onefile=True,
)

# ---------------------------------------------------------------------------
# Code signing note
# ---------------------------------------------------------------------------
#
# Unsigned Windows executables will trigger SmartScreen on first launch.
# To sign (requires an Authenticode certificate from a CA, or a self-signed
# cert for internal distribution):
#
#   signtool sign /fd SHA256 /tr http://timestamp.digicert.com /td SHA256 ^
#     /f YourCert.pfx /p YourPassword dist\stegcore-gui.exe
#
# For open-source projects, Certum and Sectigo offer affordable OV
# certificates. A self-signed cert removes the SmartScreen warning only for
# machines that have explicitly trusted the certificate.
#
# Alternatively, submit the unsigned binary to Microsoft's MAPS service for
# reputation building after it has been downloaded enough times.
