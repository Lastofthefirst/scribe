#!/usr/bin/env bash
set -euo pipefail

# ---------- helpers ----------
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
log()  { echo -e "${BLUE}[INFO]${NC} $*"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
ok()   { echo -e "${GREEN}[ OK ]${NC} $*"; }
die()  { echo -e "${RED}[ERR]${NC} $*" >&2; exit 1; }

ask(){
    read -rp "$1 [y/N] " ans
    [[ ${ans,,} == y* ]]
}

# ---------- paths ----------
BIN_DIR="$HOME/.local/bin"
LAUNCHER="$BIN_DIR/scribe-rust"
CONFIG_DIR="$HOME/.config/scribe"
CACHE_DIR="$HOME/.cache/scribe"
YD_SERVICE="$HOME/.config/systemd/user/ydotool.service"
YD_RULES="/etc/udev/rules.d/80-uinput.rules"

# ---------- steps ----------
log "Scribe-Rust uninstaller"
echo

# 1. stop / disable user service
if systemctl --user is-active -q ydotool.service 2>/dev/null; then
    log "Stopping ydotool user service..."
    systemctl --user stop ydotool.service
    systemctl --user disable ydotool.service 2>/dev/null || true
fi

# 2. remove launcher
if [[ -f $LAUNCHER ]]; then
    rm -v "$LAUNCHER" || warn "Could not delete launcher"
else
    ok "Launcher already gone"
fi

# 3. remove binary & build artefacts
if [[ -d target ]]; then
    if ask "Remove entire ./target build directory?"; then
        rm -rf ./target
    fi
else
    ok "No ./target directory found"
fi

# 4. user data
if [[ -d $CONFIG_DIR ]]; then
    ask "Delete configuration directory $CONFIG_DIR?" && rm -rfv "$CONFIG_DIR"
fi
if [[ -d $CACHE_DIR ]]; then
    ask "Delete models cache $CACHE_DIR?" && rm -rfv "$CACHE_DIR"
fi

# 5. ydotool systemd unit
if [[ -f $YD_SERVICE ]]; then
    rm -v "$YD_SERVICE"
fi
systemctl --user daemon-reload

# 6. udev rule (system-wide – needs sudo)
if [[ -f $YD_RULES ]]; then
    warn "System udev rule $YD_RULES was created by the installer."
    if ask "Remove it (requires sudo)?"; then
        sudo rm -v "$YD_RULES"
        sudo udevadm control --reload-rules
        sudo udevadm trigger
    fi
fi

# 7. ~/.local/bin in PATH
if grep -q 'export PATH.*\.local/bin' ~/.bashrc 2>/dev/null; then
    warn "The installer added ~/.local/bin to PATH in ~/.bashrc"
    warn "You may remove that line manually if no other tools need it."
fi

# 8. packages installed via package manager
warn "The installer pulled in system packages (e.g. libasound2-dev, cmake, clang, xdotool, etc.)."
warn "To remove them, run the appropriate command for your distro:"
echo "  Debian/Ubuntu:  sudo apt autoremove --purge libasound2-dev libclang-dev clang cmake xdotool pulseaudio-utils libnotify-bin"
echo "  Fedora:         sudo dnf remove alsa-lib-devel clang-devel cmake xdotool pulseaudio-utils libnotify"
echo "  Arch:           sudo pacman -Rs alsa-lib clang cmake xdotool libnotify"

log "Uninstall finished.  Scribe-Rust has been removed."
