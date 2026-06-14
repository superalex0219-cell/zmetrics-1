# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for the ZMetrics desktop client.

Cross-platform: produces a one-folder app on every OS and, on macOS, wraps it in
a proper ``ZMetrics.app`` bundle. PyInstaller does NOT cross-compile — run this on
the target OS:

    macOS:    pyinstaller zmetrics_desktop.spec      (build_macos.sh wraps this)
    Windows:  pyinstaller zmetrics_desktop.spec

The macOS run yields ``dist/ZMetrics.app``; build_macos.sh then packages a .dmg.
"""
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# `pyinstaller zmetrics_desktop.spec` runs from desktop/, so the package is alongside.
PROJECT_DIR = Path(SPECPATH)  # noqa: F821 - SPECPATH injected by PyInstaller
PKG_DIR = PROJECT_DIR / "zmetrics_desktop"

# Bundle the in-package assets (e.g. assets/rock-sample.png) preserving their layout.
datas = collect_data_files("zmetrics_desktop", includes=["assets/*"])

# keyring discovers OS backends via entry points; PyInstaller needs them named
# explicitly. macOS uses the Keychain backend.
hiddenimports = collect_submodules("keyring.backends") + [
    "keyring.backends.macOS",
]

# Optional .icns — drop one at zmetrics_desktop/assets/AppIcon.icns to brand the app.
_icns = PKG_DIR / "assets" / "AppIcon.icns"
app_icon = str(_icns) if _icns.exists() else None


a = Analysis(
    ["zmetrics_desktop/__main__.py"],
    pathex=[str(PROJECT_DIR)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=["tkinter", "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets"],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="ZMetrics",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=True,  # macOS: forward "open with" file args into sys.argv
    target_arch=None,     # honours $ARCHFLAGS / arch of the running Python
    codesign_identity=None,
    entitlements_file=None,
    icon=app_icon,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="ZMetrics",
)

# macOS .app bundle. NSCameraUsageDescription is required for UVC capture (ZED 2)
# under the macOS TCC privacy gate, otherwise cv2.VideoCapture is silently denied.
app = BUNDLE(
    coll,
    name="ZMetrics.app",
    icon=app_icon,
    bundle_identifier="com.zmetrics.desktop",
    info_plist={
        "CFBundleName": "ZMetrics",
        "CFBundleDisplayName": "ZMetrics",
        "CFBundleShortVersionString": "0.1.0",
        "CFBundleVersion": "0.1.0",
        "NSHighResolutionCapable": True,
        "LSMinimumSystemVersion": "12.0",
        "NSCameraUsageDescription": "ZMetrics captures stereo frames from the ZED 2 camera for blast fragmentation analysis.",
    },
)
