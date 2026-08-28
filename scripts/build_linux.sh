#!/usr/bin/env bash
# Build the native Linux beta artifact from a Linux desktop or WSL.
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
OUTPUT_DIR="${ROOT}/dist/linux"
RELEASE_DIR="${ROOT}/dist/release"
CLEAN=false
SKIP_TESTS=false

usage() {
  cat <<'EOF'
Usage: ./scripts/build_linux.sh [--clean] [--skip-tests] [--output DIR]

Builds WizZ Desktop for Linux. Run it on Linux or WSL after installing the
system dependencies required by Flet/Flutter. It produces a tar.gz archive and
a SHA-256 checksum under dist/release.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --clean) CLEAN=true ;;
    --skip-tests) SKIP_TESTS=true ;;
    --output)
      OUTPUT_DIR="${2:?--output requires a directory}"
      shift
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
  shift
done

if [[ "$(uname -s)" != "Linux" ]]; then
  echo "This build must run on Linux or WSL." >&2
  exit 1
fi

cd "$ROOT"
PYTHON="${PYTHON:-$ROOT/.venv/bin/python}"
if [[ ! -x "$PYTHON" ]]; then
  PYTHON="$(command -v python3)"
fi
FLET="${FLET:-$ROOT/.venv/bin/flet}"
if [[ ! -x "$FLET" ]]; then
  FLET="$(command -v flet || true)"
fi
if [[ -z "$FLET" || ! -x "$FLET" ]]; then
  echo "Flet CLI was not found. Install flet[cli] in the active environment." >&2
  exit 1
fi

# Flutter native assets resolve the linker beside the selected clang binary.
# Ubuntu splits it into the lld package; without it Flet fails much later with
# an unhelpful empty tool-name error from dart_build.
CLANG_PATH="$(readlink -f "$(command -v clang || true)")"
if [[ -z "$CLANG_PATH" || ! -x "$CLANG_PATH" ]]; then
  echo "clang was not found. Install: sudo apt install -y clang cmake ninja-build pkg-config libgtk-3-dev" >&2
  exit 1
fi
LLVM_BIN="$(dirname "$CLANG_PATH")"
if [[ ! -x "$LLVM_BIN/ld.lld" && ! -x "$LLVM_BIN/ld" ]]; then
  echo "LLVM linker was not found beside clang at $LLVM_BIN." >&2
  echo "On Ubuntu install it with: sudo apt install -y lld-14" >&2
  exit 1
fi

export PYTHONUTF8=1
export PYTHONIOENCODING=utf-8
export FLET_CLI_NO_RICH_OUTPUT=true

VERSION="$($PYTHON -c 'from app_meta import APP_VERSION; print(APP_VERSION)')"
BUILD_NUMBER="$($PYTHON -c 'from app_meta import APP_BUILD_NUMBER; print(APP_BUILD_NUMBER)')"
ARTIFACT="$($PYTHON -c 'from app_meta import APP_ARTIFACT; print(APP_ARTIFACT)')"
PYTHON_VERSION="$($PYTHON -c 'import platform; print(platform.python_version())')"
FLET_VERSION="$($PYTHON -c 'import flet; print(flet.__version__)')"

if [[ "$CLEAN" == true ]]; then
  rm -rf "$ROOT/build" "$OUTPUT_DIR"
fi

if [[ "$SKIP_TESTS" != true ]]; then
  "$PYTHON" -m compileall -q main.py app_meta.py core config ui localization tests tools
  "$PYTHON" -m pytest -q
  "$PYTHON" tools/i18n_audit.py
fi

mkdir -p "$RELEASE_DIR"
"$FLET" build linux . --output "$OUTPUT_DIR" --yes --no-rich-output

EXECUTABLE="$(find "$OUTPUT_DIR" -type f -name "$ARTIFACT" -perm -u+x -print -quit)"
if [[ -z "$EXECUTABLE" ]]; then
  echo "Build completed without finding executable $ARTIFACT." >&2
  exit 1
fi

COMMIT="$(git rev-parse --short=12 HEAD 2>/dev/null || echo no-git)"
DIRTY=false
if ! git diff --quiet 2>/dev/null; then
  DIRTY=true
fi

cat > "$OUTPUT_DIR/BUILD_INFO.json" <<EOF
{
  "product": "WizZ Desktop",
  "version": "$VERSION",
  "build_number": $BUILD_NUMBER,
  "artifact": "$ARTIFACT",
  "platform": "linux",
  "python": "$PYTHON_VERSION",
  "flet": "$FLET_VERSION",
  "commit": "$COMMIT",
  "dirty": $DIRTY
}
EOF

ARCHIVE="$RELEASE_DIR/WizZDesktop-v${VERSION}-linux-x64.tar.gz"
CHECKSUM="$ARCHIVE.sha256"
rm -f "$ARCHIVE" "$CHECKSUM"
tar -C "$OUTPUT_DIR" -czf "$ARCHIVE" .
sha256sum "$ARCHIVE" > "$CHECKSUM"

echo "Linux beta build ready: $OUTPUT_DIR"
echo "Archive: $ARCHIVE"
echo "Checksum: $CHECKSUM"
