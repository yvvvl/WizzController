#!/usr/bin/env bash
# Build the official native Qt/PySide Linux bundle. Run on native Linux only.
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
OUTPUT_DIR="$ROOT/dist/linux"
RELEASE_DIR="$ROOT/dist/release"
ARCH=""
CLEAN=false
SKIP_TESTS=false

usage() {
  cat <<'EOF'
Usage: ./scripts/build_qt_linux.sh [--clean] [--skip-tests] [--arch x64|arm64] [--output DIR]

Creates a native Qt/PySide Linux bundle, a portable tar.gz archive and SHA-256
sidecar. The archive contains install.sh for per-user installation without sudo.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --clean) CLEAN=true ;;
    --skip-tests) SKIP_TESTS=true ;;
    --arch) ARCH="${2:?--arch requires x64 or arm64}"; shift ;;
    --output) OUTPUT_DIR="${2:?--output requires a directory}"; shift ;;
    --help|-h) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage >&2; exit 2 ;;
  esac
  shift
done

[[ "$(uname -s)" == "Linux" ]] || { echo "This build must run on Linux." >&2; exit 1; }
case "$(uname -m)" in
  x86_64|amd64) HOST_ARCH="x64" ;;
  aarch64|arm64) HOST_ARCH="arm64" ;;
  *) echo "Unsupported Linux CPU architecture: $(uname -m)" >&2; exit 1 ;;
esac
ARCH="${ARCH:-$HOST_ARCH}"
[[ "$ARCH" == "$HOST_ARCH" ]] || { echo "Cross-compilation is not supported." >&2; exit 1; }

cd "$ROOT"
PYTHON="${PYTHON:-$ROOT/.venv/bin/python}"
[[ -x "$PYTHON" ]] || PYTHON="$(command -v python3)"
VERSION="$($PYTHON -c 'from app_meta import APP_VERSION; print(APP_VERSION)')"
BUILD_NUMBER="$($PYTHON -c 'from app_meta import APP_BUILD_NUMBER; print(APP_BUILD_NUMBER)')"
ARTIFACT="$($PYTHON -c 'from app_meta import APP_ARTIFACT; print(APP_ARTIFACT)')"
PACKAGE_DIR="$OUTPUT_DIR/$ARTIFACT"
WORK_DIR="$ROOT/build/pyinstaller-linux"

if [[ "$CLEAN" == true ]]; then
  rm -rf -- "$OUTPUT_DIR" "$WORK_DIR"
fi
if [[ "$SKIP_TESTS" != true ]]; then
  "$PYTHON" -m compileall -q app_meta.py core config qt_ui tests tools
  # The official bundle is Qt-only. Legacy Flet tests live in a separate
  # compatibility suite and must not pull Flet into the Linux artifact.
  "$PYTHON" -m pytest -q \
    tests/test_qt_runtime.py \
    tests/test_qt_bridge.py \
    tests/test_app_runtime_manager.py \
    tests/test_packaged_startup.py \
    tests/test_platform_linux.py \
    tests/test_update_installer.py \
    tests/test_app_paths.py \
    tests/test_release_metadata.py
fi

mkdir -p "$OUTPUT_DIR" "$WORK_DIR" "$RELEASE_DIR"
"$PYTHON" -m PyInstaller --noconfirm --clean --windowed \
  --name "$ARTIFACT" \
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

[[ -x "$PACKAGE_DIR/$ARTIFACT" ]] || { echo "Build completed without $ARTIFACT." >&2; exit 1; }
install -m 755 "$ROOT/scripts/linux_install.sh" "$PACKAGE_DIR/install.sh"
install -m 755 "$ROOT/scripts/linux_uninstall.sh" "$PACKAGE_DIR/uninstall.sh"
mkdir -p "$PACKAGE_DIR/assets"
cp "$ROOT/assets/icon.png" "$PACKAGE_DIR/assets/icon.png"
# Preserve the third-party license notice for dependencies bundled by PyInstaller.
cp "$ROOT/THIRD_PARTY_NOTICES.md" "$PACKAGE_DIR/THIRD_PARTY_NOTICES.md"
cp -R "$ROOT/licenses" "$PACKAGE_DIR/licenses"

cat > "$PACKAGE_DIR/BUILD_INFO.json" <<EOF
{
  "product": "WizZ Desktop",
  "version": "$VERSION",
  "build_number": $BUILD_NUMBER,
  "artifact": "$ARTIFACT",
  "platform": "linux",
  "architecture": "$ARCH",
  "packaging": "PyInstaller Qt",
  "installer": "install.sh"
}
EOF

ARCHIVE="$RELEASE_DIR/WizZDesktop-v${VERSION}-linux-${ARCH}.tar.gz"
CHECKSUM="$ARCHIVE.sha256"
rm -f -- "$ARCHIVE" "$CHECKSUM"
tar -C "$PACKAGE_DIR" -czf "$ARCHIVE" .
sha256sum "$ARCHIVE" > "$CHECKSUM"
echo "Qt Linux bundle: $PACKAGE_DIR"
echo "Archive: $ARCHIVE"
