#!/bin/bash
# Scribe Installation Script (UV-based)
# Modern, fast installation using UV package manager

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print functions
print_header() {
    echo -e "${BLUE}================================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}================================================${NC}"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   print_error "Do not run this script as root (without sudo)"
   echo "The script will ask for sudo password when needed."
   exit 1
fi

print_header "Scribe Installation (UV)"
echo ""

# Detect distribution
if [ -f /etc/os-release ]; then
    . /etc/os-release
    DISTRO=$ID
    VERSION=$VERSION_ID
else
    print_error "Cannot detect Linux distribution"
    exit 1
fi

print_info "Detected: $PRETTY_NAME"
echo ""

# Detect package manager
case "$DISTRO" in
    debian|ubuntu|linuxmint|pop|kde-neon)
        PKG_MANAGER="apt"
        ;;
    fedora|rhel|centos|rocky|almalinux)
        PKG_MANAGER="dnf"
        ;;
    arch|manjaro|endeavouros)
        PKG_MANAGER="pacman"
        ;;
    *)
        print_warning "Unsupported distribution: $DISTRO"
        print_info "Installation will continue but may require manual dependency installation"
        PKG_MANAGER="unknown"
        ;;
esac

# Step 1: Check and install system dependencies
print_header "Step 1: System Dependencies"
echo ""

DEPS_TO_INSTALL=()

# Check for UV
if command -v uv &> /dev/null; then
    UV_VERSION=$(uv --version | awk '{print $2}')
    print_success "UV $UV_VERSION found"
else
    print_warning "UV not found - will install"
    INSTALL_UV=true
fi

# Check pkg-config (needed for library detection)
if command -v pkg-config &> /dev/null; then
    print_success "pkg-config found"
else
    print_warning "pkg-config not found"
    DEPS_TO_INSTALL+=("pkg-config")
fi

# Check PortAudio (required for sounddevice)
if command -v pkg-config &> /dev/null && pkg-config --exists portaudio-2.0; then
    print_success "PortAudio library found"
else
    print_warning "PortAudio library not found"
    case "$PKG_MANAGER" in
        apt)
            DEPS_TO_INSTALL+=("portaudio19-dev")
            ;;
        dnf)
            DEPS_TO_INSTALL+=("portaudio-devel")
            ;;
        pacman)
            DEPS_TO_INSTALL+=("portaudio")
            ;;
    esac
fi

# Check FFmpeg libraries (required for av/PyAV package)
if command -v pkg-config &> /dev/null && pkg-config --exists libavformat libavcodec; then
    print_success "FFmpeg libraries found"
else
    print_warning "FFmpeg libraries not found"
    case "$PKG_MANAGER" in
        apt)
            DEPS_TO_INSTALL+=("ffmpeg" "libavcodec-dev" "libavformat-dev" "libavdevice-dev" "libavutil-dev" "libavfilter-dev" "libswscale-dev" "libswresample-dev")
            ;;
        dnf)
            DEPS_TO_INSTALL+=("ffmpeg" "ffmpeg-devel")
            ;;
        pacman)
            DEPS_TO_INSTALL+=("ffmpeg")
            ;;
    esac
fi

# Check for typing tool (xdotool for X11, ydotool for Wayland)
TYPING_TOOL_FOUND=false
if command -v xdotool &> /dev/null; then
    print_success "xdotool found (X11 support)"
    TYPING_TOOL_FOUND=true
fi

if command -v ydotool &> /dev/null; then
    print_success "ydotool found (Wayland support)"
    TYPING_TOOL_FOUND=true
fi

if command -v wtype &> /dev/null; then
    print_success "wtype found (Wayland support)"
    TYPING_TOOL_FOUND=true
fi

if [ "$TYPING_TOOL_FOUND" = false ]; then
    print_warning "No typing tool found (xdotool/ydotool/wtype)"
    if [ "$XDG_SESSION_TYPE" = "wayland" ]; then
        print_info "Wayland detected, will install ydotool"
        case "$PKG_MANAGER" in
            apt)
                DEPS_TO_INSTALL+=("ydotool")
                ;;
            dnf)
                DEPS_TO_INSTALL+=("ydotool")
                ;;
            pacman)
                DEPS_TO_INSTALL+=("ydotool")
                ;;
        esac
    else
        print_info "X11 detected, will install xdotool"
        DEPS_TO_INSTALL+=("xdotool")
    fi
fi

# Check for notification tool
NOTIFY_TOOL_FOUND=false
for tool in notify-send kdialog zenity; do
    if command -v $tool &> /dev/null; then
        print_success "$tool found"
        NOTIFY_TOOL_FOUND=true
        break
    fi
done

if [ "$NOTIFY_TOOL_FOUND" = false ]; then
    print_warning "No notification tool found"
    DEPS_TO_INSTALL+=("libnotify-bin")
fi

# Check for audio playback tool
AUDIO_TOOL_FOUND=false
for tool in paplay aplay ffplay mpv; do
    if command -v $tool &> /dev/null; then
        print_success "$tool found (audio playback)"
        AUDIO_TOOL_FOUND=true
        break
    fi
done

if [ "$AUDIO_TOOL_FOUND" = false ]; then
    print_warning "No audio playback tool found"
    case "$PKG_MANAGER" in
        apt)
            DEPS_TO_INSTALL+=("pulseaudio-utils")
            ;;
        dnf)
            DEPS_TO_INSTALL+=("pulseaudio-utils")
            ;;
        pacman)
            DEPS_TO_INSTALL+=("libpulse")
            ;;
    esac
fi

# Install missing dependencies
if [ ${#DEPS_TO_INSTALL[@]} -gt 0 ]; then
    echo ""
    print_info "Installing missing dependencies: ${DEPS_TO_INSTALL[*]}"

    case "$PKG_MANAGER" in
        apt)
            sudo apt update
            sudo apt install -y "${DEPS_TO_INSTALL[@]}"
            ;;
        dnf)
            sudo dnf install -y "${DEPS_TO_INSTALL[@]}"
            ;;
        pacman)
            sudo pacman -S --noconfirm "${DEPS_TO_INSTALL[@]}"
            ;;
        *)
            print_error "Cannot auto-install dependencies on this distribution"
            print_info "Please manually install: ${DEPS_TO_INSTALL[*]}"
            exit 1
            ;;
    esac

    print_success "System dependencies installed"
else
    print_success "All system dependencies satisfied"
fi

echo ""

# Step 2: Install UV if needed
if [ "$INSTALL_UV" = true ]; then
    print_header "Step 2: Installing UV"
    echo ""

    print_info "Downloading and installing UV package manager..."
    curl -LsSf https://astral.sh/uv/install.sh | sh

    # Add UV to PATH for this session
    export PATH="$HOME/.local/bin:$PATH"

    if command -v uv &> /dev/null; then
        UV_VERSION=$(uv --version | awk '{print $2}')
        print_success "UV $UV_VERSION installed successfully"
    else
        print_error "UV installation failed"
        exit 1
    fi

    echo ""
fi

# Step 3: Install Scribe with UV
print_header "Step 3: Installing Scribe"
echo ""

print_info "UV will automatically:"
print_info "  • Download the correct Python version (3.11-3.13)"
print_info "  • Create an optimized virtual environment"
print_info "  • Install all dependencies (this may take a few minutes)"
echo ""

# UV will handle everything: Python version, venv, dependencies, and generate lockfile
uv sync

print_success "Scribe installed successfully"
echo ""

# Step 4: Create launcher script
print_header "Step 4: Creating Launcher"
echo ""

LAUNCHER_SCRIPT="$HOME/.local/bin/scribe"
mkdir -p "$HOME/.local/bin"

cat > "$LAUNCHER_SCRIPT" << 'EOF'
#!/bin/bash
# Scribe launcher script (UV-based)
SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)"
PROJECT_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"

# Find the scribe project directory
if [ -f "$PROJECT_DIR/pyproject.toml" ] && grep -q "scribe-stt" "$PROJECT_DIR/pyproject.toml"; then
    cd "$PROJECT_DIR"
    exec uv run scribe "$@"
else
    # Search for scribe installation
    for dir in ~/ridvan/projects/scribe ~/.local/share/scribe ~/scribe; do
        if [ -f "$dir/pyproject.toml" ] && grep -q "scribe-stt" "$dir/pyproject.toml"; then
            cd "$dir"
            exec uv run scribe "$@"
        fi
    done

    echo "Error: Could not find scribe installation" >&2
    exit 1
fi
EOF

chmod +x "$LAUNCHER_SCRIPT"
print_success "Launcher script created at $LAUNCHER_SCRIPT"

# Check if ~/.local/bin is in PATH
if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
    echo ""
    print_warning "~/.local/bin is not in PATH"
    print_info "Add this line to your ~/.bashrc or ~/.zshrc:"
    echo ""
    echo "    export PATH=\"\$HOME/.local/bin:\$PATH\""
    echo ""
    print_info "Then run: source ~/.bashrc (or restart your terminal)"
fi

echo ""

# Step 5: Setup configuration
print_header "Step 5: Configuration Setup"
echo ""

uv run scribe setup

echo ""

# Step 6: Download default model
print_header "Step 6: Download Speech Model"
echo ""

read -p "Download default model (tiny.en, ~39MB)? [Y/n] " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Nn]$ ]]; then
    print_info "Downloading model... (this may take a minute)"
    uv run scribe download
    print_success "Model downloaded"
else
    print_info "Skipping model download (will download on first run)"
fi

echo ""

# Final instructions
print_header "Installation Complete!"
echo ""

print_success "Scribe is now installed and ready to use!"
echo ""
print_info "Quick Start:"
echo "  1. Run 'scribe' to start recording with voice detection"
echo "  2. Speak clearly, and Scribe will transcribe when you pause"
echo "  3. Text will be typed at your cursor position"
echo ""
print_info "Useful Commands:"
echo "  scribe test           - Test your setup"
echo "  scribe --help         - Show all options"
echo "  scribe models         - List available models"
echo "  scribe --output clipboard  - Copy to clipboard instead of typing"
echo ""
print_info "Configuration:"
echo "  Edit: ~/.config/scribe/config.toml"
echo ""
print_info "Keybinding Setup (KDE):"
echo "  1. System Settings → Shortcuts → Custom Shortcuts"
echo "  2. Add new command: 'scribe'"
echo "  3. Set your preferred hotkey (e.g., Meta+S)"
echo ""
print_info "Keybinding Setup (GNOME):"
echo "  1. Settings → Keyboard → Custom Shortcuts"
echo "  2. Add new shortcut with command: 'scribe'"
echo "  3. Set your preferred hotkey"
echo ""

# Check if PATH update needed
if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
    print_warning "Don't forget to add ~/.local/bin to your PATH!"
    echo "  Run: echo 'export PATH=\"\$HOME/.local/bin:\$PATH\"' >> ~/.bashrc"
    echo "  Then: source ~/.bashrc"
    echo ""
fi

print_success "Happy transcribing! 🎤"
