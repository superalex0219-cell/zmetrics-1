#!/usr/bin/env bash
# Build the ZMetrics desktop client into a macOS .app bundle (+ .dmg).
#
# MUST run on macOS — PyInstaller cannot cross-compile. From a Windows checkout,
# copy/clone the repo onto a Mac (or use the CI workflow) and run this there:
#
#     cd desktop
#     ./build_macos.sh
#
# Output: desktop/dist/ZMetrics.app  and  desktop/dist/ZMetrics.dmg
set -euo pipefail

cd "$(dirname "$0")"

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "error: this script must run on macOS (PyInstaller does not cross-compile)." >&2
  echo "       use the GitHub Actions workflow (.github/workflows/desktop-macos.yml) instead." >&2
  exit 1
fi

PYTHON="${PYTHON:-python3}"
VENV_DIR="${VENV_DIR:-.venv-build}"

echo ">> creating build venv: $VENV_DIR"
"$PYTHON" -m venv "$VENV_DIR"
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

echo ">> installing app + build deps"
python -m pip install --upgrade pip
pip install -e ".[dev]"
pip install pyinstaller

echo ">> cleaning previous build"
rm -rf build dist

echo ">> running PyInstaller"
pyinstaller --noconfirm --clean zmetrics_desktop.spec

APP="dist/ZMetrics.app"
if [[ ! -d "$APP" ]]; then
  echo "error: expected $APP was not produced" >&2
  exit 1
fi

echo ">> packaging DMG"
DMG="dist/ZMetrics.dmg"
rm -f "$DMG"
hdiutil create -volname "ZMetrics" -srcfolder "$APP" -ov -format UDZO "$DMG"

echo
echo "done:"
echo "  app: $APP"
echo "  dmg: $DMG"
echo
echo "note: the bundle is unsigned. To distribute, codesign + notarize:"
echo "  codesign --deep --force --options runtime --sign \"Developer ID Application: <NAME>\" \"$APP\""
echo "  xcrun notarytool submit \"$DMG\" --keychain-profile <PROFILE> --wait"
