#!/usr/bin/env bash
# Remove the WizZ Desktop launcher and installed bundle for the current user.
set -euo pipefail

PRODUCT="WizZ Desktop"
DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
INSTALL_DIR="$DATA_HOME/WizZDesktop"
APPLICATIONS_DIR="$DATA_HOME/applications"
DESKTOP_FILE="$APPLICATIONS_DIR/io.github.yvvvl.wizz-controller.desktop"

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  cat <<'EOF'
Usage: ./uninstall.sh

Removes the current user's WizZ Desktop launcher and installed application
files. It deliberately keeps your WiZ configuration, favourites and logs.
EOF
  exit 0
fi

rm -f -- "$DESKTOP_FILE"
if [[ -d "$INSTALL_DIR" ]]; then
  rm -rf -- "$INSTALL_DIR"
fi

if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database "$APPLICATIONS_DIR" >/dev/null 2>&1 || true
fi

echo "$PRODUCT was removed. Your configuration and logs were kept."
