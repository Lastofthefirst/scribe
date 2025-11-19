#!/bin/bash
# Scribe Installation Script
# Painless installation for KDE/Debian systems

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

print_header "Scribe Installation"
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

# Check for supported distributions
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

# Check Python 3.8+
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
    PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
    PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

    if [ "$PYTHON_MAJOR" -ge 3 ] && [ "$PYTHON_MINOR" -ge 8 ]; then
        print_success "Python $PYTHON_VERSION found"
    else
        print_error "Python 3.8+ required, found $PYTHON_VERSION"
        DEPS_TO_INSTALL+=("python3")
    fi
else
    print_error "Python 3 not found"
    DEPS_TO_INSTALL+=("python3")
fi

# Check pip
if command -v pip3 &> /dev/null; then
    print_success "pip3 found"
else
    print_warning "pip3 not found"
    DEPS_TO_INSTALL+=("python3-pip")
fi

# Check pkg-config (needed for library detection)
if command -v pkg-config &> /dev/null; then
    print_success "pkg-config found"
else
    print_warning "pkg-config not found"
    DEPS_TO_INSTALL+=("pkg-config")
fi

# Check portaudio (required for sounddevice)
if command -v pkg-config &> /dev/null && pkg-config --exists portaudio-2.0; then
    print_success "PortAudio library found"
else
    print_warning "PortAudio library not found"
    case "$PKG_MANAGER" in
        apt)
            DEPS_TO_INSTALL+=("portaudio19-dev" "python3-dev")
            ;;
        dnf)
            DEPS_TO_INSTALL+=("portaudio-devel" "python3-devel")
            ;;
        pacman)
            DEPS_TO_INSTALL+=("portaudio" "python")
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

    # Detect display server
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
    # pulseaudio-utils includes paplay
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

# Step 2: Install Python package
print_header "Step 2: Installing Scribe"
echo ""

# Create virtual environment (optional but recommended)
read -p "Install in virtual environment? (recommended) [Y/n] " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Nn]$ ]]; then
    print_info "Creating virtual environment..."

    if ! command -v python3 -m venv &> /dev/null; then
        print_warning "venv module not found, installing..."
        case "$PKG_MANAGER" in
            apt)
                sudo apt install -y python3-venv
                ;;
            dnf)
                sudo dnf install -y python3-virtualenv
                ;;
            pacman)
                # venv included in python package
                ;;
        esac
    fi

    VENV_DIR="$HOME/.local/share/scribe-venv"
    python3 -m venv "$VENV_DIR"
    source "$VENV_DIR/bin/activate"
    print_success "Virtual environment created at $VENV_DIR"

    USE_VENV=true
else
    USE_VENV=false
fi

# Upgrade pip
print_info "Upgrading pip..."
python3 -m pip install --upgrade pip

# Install scribe
print_info "Installing Scribe and Python dependencies..."
print_info "This may take a few minutes (downloading ML models)..."
echo ""

pip3 install -e .

print_success "Scribe installed successfully"
echo ""

# Step 3: Create wrapper script if using venv
if [ "$USE_VENV" = true ]; then
    print_header "Step 3: Creating Launcher Script"
    echo ""

    WRAPPER_SCRIPT="$HOME/.local/bin/scribe"
    mkdir -p "$HOME/.local/bin"

    cat > "$WRAPPER_SCRIPT" << EOF
#!/bin/bash
# Scribe launcher script (auto-generated)
source "$VENV_DIR/bin/activate"
exec python3 -m scribe.cli "\$@"
EOF

    chmod +x "$WRAPPER_SCRIPT"
    print_success "Launcher script created at $WRAPPER_SCRIPT"

    # Check if ~/.local/bin is in PATH
    if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
        print_warning "~/.local/bin is not in PATH"
        print_info "Add this line to your ~/.bashrc or ~/.zshrc:"
        echo ""
        echo "    export PATH=\"\$HOME/.local/bin:\$PATH\""
        echo ""
    fi
fi

# Step 4: Setup configuration
print_header "Step 4: Configuration Setup"
echo ""

# Run setup command
if [ "$USE_VENV" = true ]; then
    source "$VENV_DIR/bin/activate"
fi

scribe setup

echo ""

# Step 5: Download default model
print_header "Step 5: Download Speech Model"
echo ""

read -p "Download default model (tiny.en, ~39MB)? [Y/n] " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Nn]$ ]]; then
    print_info "Downloading model... (this may take a minute)"
    scribe download
    print_success "Model downloaded"
else
    print_info "Skipping model download (will download on first run)"
fi

echo ""

# Step 6: Final instructions
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
echo "  Example: $HOME/.config/scribe/config.example.toml"
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

print_success "Happy transcribing! 🎤"
