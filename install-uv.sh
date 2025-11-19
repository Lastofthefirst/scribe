#!/bin/bash
#
# Scribe Python Installation Script
#
# This script installs Scribe (Python version) with all dependencies using uv
#

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print functions
print_header() {
    echo ""
    echo "================================================"
    echo -e "${BLUE}$1${NC}"
    echo "================================================"
    echo ""
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

# Detect OS
detect_os() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS=$ID
        VER=$VERSION_ID
        print_info "Detected: $PRETTY_NAME"
    else
        print_error "Cannot detect OS"
        exit 1
    fi
}

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Install uv if not present
install_uv() {
    if ! command_exists uv; then
        print_info "Installing uv (Python package manager)..."
        curl -LsSf https://astral.sh/uv/install.sh | sh
        # Source the env to make uv available
        export PATH="$HOME/.local/bin:$PATH"
        if ! command_exists uv; then
            print_error "Failed to install uv. Please install manually: https://docs.astral.sh/uv/getting-started/installation/"
            exit 1
        fi
        print_success "uv installed"
    else
        print_success "uv found"
    fi
}

# Check and install system dependencies
install_system_deps() {
    print_header "Checking System Dependencies"

    local missing_deps=()
    local typing_tool_found=false

    # Check Python 3
    if command_exists python3; then
        python_version=$(python3 --version | cut -d' ' -f2)
        print_success "Python $python_version found"
    else
        print_error "Python 3 not found"
        missing_deps+=("python3")
    fi

    # Check pkg-config
    if command_exists pkg-config; then
        print_success "pkg-config found"
    else
        print_warning "pkg-config not found"
        missing_deps+=("pkg-config")
    fi

    # Check PortAudio
    if pkg-config --exists portaudio-2.0 2>/dev/null; then
        print_success "PortAudio library found"
    else
        print_warning "PortAudio library not found"
        missing_deps+=("portaudio19-dev")
    fi

    # Check FFmpeg
    if pkg-config --exists libavcodec 2>/dev/null; then
        print_success "FFmpeg libraries found"
    else
        print_warning "FFmpeg libraries not found"
        missing_deps+=("ffmpeg" "libavcodec-dev" "libavformat-dev" "libavdevice-dev" "libavutil-dev" "libavfilter-dev" "libswscale-dev" "libswresample-dev")
    fi

    # Check for typing tools
    if command_exists dotool; then
        print_success "dotool found (Wayland typing tool)"
        typing_tool_found=true
    elif command_exists kdotool; then
        print_success "kdotool found (KDE typing tool)"
        typing_tool_found=true
    elif command_exists xdotool; then
        print_success "xdotool found (X11/XWayland typing tool)"
        typing_tool_found=true
    elif command_exists ydotool; then
        print_success "ydotool found (Universal typing tool)"
        typing_tool_found=true
    elif command_exists wtype; then
        print_success "wtype found (Wayland typing tool)"
        typing_tool_found=true
    else
        print_warning "No typing tool found"
        # xdotool works on both X11 and Wayland (via XWayland)
        print_info "Will install xdotool (works on X11 and Wayland via XWayland)"
        missing_deps+=("xdotool")
    fi

    # Check notification tools
    if command_exists notify-send; then
        print_success "notify-send found"
    elif command_exists kdialog; then
        print_success "kdialog found"
    elif command_exists zenity; then
        print_success "zenity found"
    else
        print_warning "No notification tool found - will install libnotify"
        missing_deps+=("libnotify-bin")
    fi

    # Check audio playback
    if command_exists paplay; then
        print_success "paplay found (audio playback)"
    elif command_exists aplay; then
        print_success "aplay found (audio playback)"
    elif command_exists mpv; then
        print_success "mpv found (audio playback)"
    else
        print_warning "No audio playback tool found - will install pulseaudio-utils"
        missing_deps+=("pulseaudio-utils")
    fi

    # Install missing dependencies
    if [ ${#missing_deps[@]} -gt 0 ]; then
        print_info "Installing missing system dependencies..."
        print_info "Packages: ${missing_deps[*]}"

        if [ "$OS" = "debian" ] || [ "$OS" = "ubuntu" ]; then
            sudo apt-get update
            sudo apt-get install -y "${missing_deps[@]}"
            print_success "System dependencies installed"
        elif [ "$OS" = "fedora" ]; then
            sudo dnf install -y "${missing_deps[@]}"
            print_success "System dependencies installed"
        elif [ "$OS" = "arch" ]; then
            sudo pacman -S --noconfirm "${missing_deps[@]}"
            print_success "System dependencies installed"
        else
            print_error "Unsupported OS: $OS"
            print_info "Please install these packages manually: ${missing_deps[*]}"
            exit 1
        fi
    fi
}

# Create Python virtual environment and install dependencies
install_python_deps() {
    print_header "Installing Python Dependencies"

    # Create venv with uv
    print_info "Creating virtual environment with uv..."
    uv venv .venv

    # Activate venv
    source .venv/bin/activate

    # Install dependencies with uv (much faster than pip)
    print_info "Installing Python packages with uv..."
    uv pip install -e .

    print_success "Python dependencies installed"
}

# Download Whisper model
download_model() {
    print_header "Downloading Whisper Model"

    local model_dir="$HOME/.cache/whisper"
    mkdir -p "$model_dir"

    print_info "Model will be downloaded on first run"
    print_info "Location: $model_dir"
    print_success "Model directory created"
}

# Create launcher script
create_launcher() {
    print_header "Creating Launcher"

    local install_dir="$(pwd)"
    local launcher="$HOME/.local/bin/scribe"

    # Create .local/bin if it doesn't exist
    mkdir -p "$HOME/.local/bin"

    # Create launcher script
    cat > "$launcher" <<EOF
#!/bin/bash
# Scribe launcher script
source "$install_dir/.venv/bin/activate"
exec scribe "\$@"
EOF

    chmod +x "$launcher"

    # Add to PATH if not already there
    if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
        echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.bashrc"
        export PATH="$HOME/.local/bin:$PATH"
        print_warning "Added $HOME/.local/bin to PATH in ~/.bashrc"
        print_warning "Run: source ~/.bashrc  (or restart your shell)"
    fi

    print_success "Launcher created: $launcher"
}

# Create config file
create_config() {
    print_header "Creating Configuration"

    local config_dir="$HOME/.config/scribe"
    local config_file="$config_dir/config.toml"

    mkdir -p "$config_dir"

    if [ ! -f "$config_file" ]; then
        cp config.example.toml "$config_file"
        print_success "Config created: $config_file"
    else
        print_info "Config already exists: $config_file"
    fi
}

# Main installation
main() {
    print_header "Scribe Python Installation"

    # Detect OS
    detect_os

    # Check if we're in the scribe directory
    if [ ! -f "pyproject.toml" ]; then
        print_error "Please run this script from the scribe directory"
        exit 1
    fi

    # Install uv
    install_uv

    # Install system dependencies
    install_system_deps

    # Install Python dependencies
    install_python_deps

    # Download model
    download_model

    # Create launcher
    create_launcher

    # Create config
    create_config

    # Final message
    print_header "Installation Complete!"

    print_success "Scribe (Python) installed successfully!"
    echo ""
    print_info "To use Scribe, either:"
    echo "  1. Restart your shell (or run: source ~/.bashrc)"
    echo "  2. Run directly: $HOME/.local/bin/scribe"
    echo ""
    print_info "Test your installation:"
    echo "  scribe test         # Test system setup"
    echo "  scribe test-typing  # Test typing functionality"
    echo "  scribe              # Start recording"
    echo "  scribe --stream     # Start streaming mode"
    echo ""
    print_info "Configuration file: $HOME/.config/scribe/config.toml"
    echo ""

    # Activate venv for current session
    source .venv/bin/activate
    print_success "Virtual environment activated for this session"
}

# Run main
main
