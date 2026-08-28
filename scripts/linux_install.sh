#!/usr/bin/env bash
# Install one extracted WizZ Desktop Linux bundle for the current user.
set -euo pipefail

PRODUCT="WizZ Desktop"
ARTIFACT="WizZDesktop"
DESKTOP_ID="io.github.yvvvl.wizz-controller.desktop"
BUNDLE_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
INSTALL_DIR="$DATA_HOME/WizZDesktop"
APPLICATIONS_DIR="$DATA_HOME/applications"
DESKTOP_FILE="$APPLICATIONS_DIR/$DESKTOP_ID"

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  cat <<'EOF'
Usage: ./install.sh

Installs WizZ Desktop for the current user. It creates an entry in the
application menu and does not require sudo. Configuration and logs are kept
outside the installed bundle and are preserved when the app is updated.
EOF
  exit 0
fi

if [[ ! -x "$BUNDLE_DIR/$ARTIFACT" ]]; then
  echo "Cannot find executable $ARTIFACT beside this installer." >&2
  exit 1
fi

if [[ "$BUNDLE_DIR" == "$INSTALL_DIR" ]]; then
  echo "$PRODUCT is already installed at $INSTALL_DIR."
  echo "Run install.sh from a newly extracted release to update it."
  exit 0
fi

if [[ -e "$INSTALL_DIR" && ! -d "$INSTALL_DIR" ]]; then
  echo "Install path exists but is not a directory: $INSTALL_DIR" >&2
  exit 1
fi

mkdir -p "$DATA_HOME" "$APPLICATIONS_DIR"
# Replacing only this known per-user directory is safe and keeps the separate
# XDG configuration/state folders untouched.
rm -rf -- "$INSTALL_DIR"
mkdir -p "$INSTALL_DIR"
cp -a "$BUNDLE_DIR/." "$INSTALL_DIR/"
chmod +x "$INSTALL_DIR/$ARTIFACT" "$INSTALL_DIR/install.sh" "$INSTALL_DIR/uninstall.sh"

ICON_PATH="$INSTALL_DIR/assets/icon.png"
if [[ ! -f "$ICON_PATH" ]]; then
  echo "The bundled application icon is missing: $ICON_PATH" >&2
  exit 1
fi

cat > "$DESKTOP_FILE" <<EOF
[Desktop Entry]
Type=Application
Version=1.0
Name=$PRODUCT
Comment=Control local de luces WiZ
Exec=$INSTALL_DIR/$ARTIFACT
Icon=$ICON_PATH
Terminal=false
Categories=Utility;Settings;HomeAutomation;
StartupNotify=true
StartupWMClass=$ARTIFACT
EOF
chmod 644 "$DESKTOP_FILE"

if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database "$APPLICATIONS_DIR" >/dev/null 2>&1 || true
fi

echo "$PRODUCT installed. Open it from Applications or run: $INSTALL_DIR/$ARTIFACT"
echo "To remove the launcher and installed files, run: $INSTALL_DIR/uninstall.sh"
