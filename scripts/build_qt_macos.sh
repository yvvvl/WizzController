#!/usr/bin/env bash
# Experimental, unsigned macOS .app build for smoke testing (not for release).
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
OUTPUT_DIR="$ROOT/dist/macos"
RELEASE_DIR="$ROOT/dist/release"
SKIP_TESTS=false

usage() {
  cat <<'EOF'
Usage: ./scripts/build_qt_macos.sh [--skip-tests] [--output DIR] [--release-dir DIR]

Builds an experimental, unsigned macOS .app and ZIP for smoke testing. A Mac
is required; this script does not sign or notarize the app for public release.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --skip-tests) SKIP_TESTS=true ;;
    --output) OUTPUT_DIR="${2:?--output requires a directory}"; shift ;;
    --release-dir) RELEASE_DIR="${2:?--release-dir requires a directory}"; shift ;;
    --help|-h) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage >&2; exit 2 ;;
  esac
  shift
done

[[ "$(uname -s)" == "Darwin" ]] || { echo "This build must run on macOS." >&2; exit 1; }
case "$(uname -m)" in
  arm64) ARCH="arm64" ;;
  x86_64) ARCH="x64" ;;
  *) echo "Unsupported Mac CPU architecture: $(uname -m)" >&2; exit 1 ;;
esac

cd "$ROOT"
PYTHON="${PYTHON:-$ROOT/.venv/bin/python}"
[[ -x "$PYTHON" ]] || PYTHON="$(command -v python3)"
VERSION="$("$PYTHON" -c 'from app_meta import APP_VERSION; print(APP_VERSION)')"
ARTIFACT="$("$PYTHON" -c 'from app_meta import APP_ARTIFACT; print(APP_ARTIFACT)')"
WORK_DIR="$ROOT/build/pyinstaller-macos"
APP_PATH="$OUTPUT_DIR/$ARTIFACT.app"

mkdir -p "$OUTPUT_DIR" "$WORK_DIR" "$RELEASE_DIR"
"$PYTHON" -m compileall -q app_meta.py core config qt_ui tests tools
if [[ "$SKIP_TESTS" != true ]]; then
  "$PYTHON" -m pytest -q \
    tests/test_app_paths.py \
    tests/test_release_metadata.py \
    tests/test_update_client.py \
    tests/test_qt_bridge.py
fi

"$PYTHON" -m PyInstaller --noconfirm --clean --windowed \
  --name "$ARTIFACT" \
  --osx-bundle-identifier "io.github.yvvvl.wizzdesktop" \
  --distpath "$OUTPUT_DIR" \
  --workpath "$WORK_DIR" \
  --specpath "$WORK_DIR" \
  --add-data "$ROOT/assets:assets" \
  --add-data "$ROOT/qt_ui/qml:qt_ui/qml" \
  --collect-data PySide6 \
  --collect-binaries PySide6 \
  --collect-data certifi \
  --hidden-import PySide6.QtQuickControls2 \
  --hidden-import PySide6.QtWidgets \
  "$ROOT/qt_ui/run.py"

[[ -x "$APP_PATH/Contents/MacOS/$ARTIFACT" ]] || { echo "Build completed without $APP_PATH." >&2; exit 1; }
INFO_PLIST="$APP_PATH/Contents/Info.plist"
LOCAL_NETWORK_DESCRIPTION="WizZ Desktop discovers and controls WiZ lights on your local network."
/usr/libexec/PlistBuddy -c "Set :NSLocalNetworkUsageDescription '$LOCAL_NETWORK_DESCRIPTION'" "$INFO_PLIST" 2>/dev/null \
  || /usr/libexec/PlistBuddy -c "Add :NSLocalNetworkUsageDescription string '$LOCAL_NETWORK_DESCRIPTION'" "$INFO_PLIST"
/usr/libexec/PlistBuddy -c "Set :CFBundleDisplayName 'WizZ Desktop'" "$INFO_PLIST" 2>/dev/null \
  || /usr/libexec/PlistBuddy -c "Add :CFBundleDisplayName string 'WizZ Desktop'" "$INFO_PLIST"

ZIP="$RELEASE_DIR/$ARTIFACT-v$VERSION-macos-$ARCH.zip"
rm -f -- "$ZIP" "$ZIP.sha256"
ditto -c -k --sequesterRsrc --keepParent "$APP_PATH" "$ZIP"
shasum -a 256 "$ZIP" > "$ZIP.sha256"
echo "Experimental macOS app: $APP_PATH"
echo "Smoke-test archive: $ZIP"
