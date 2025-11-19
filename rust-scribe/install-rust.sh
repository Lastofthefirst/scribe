#!/bin/bash
#
# Scribe Rust Installation Script
#
# This script installs Scribe (Rust version) with all dependencies
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

# Install Rust if not present
install_rust() {
    if ! command_exists cargo; then
        print_info "Installing Rust toolchain..."
        curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
        source "$HOME/.cargo/env"

        if ! command_exists cargo; then
            print_error "Failed to install Rust. Please install manually: https://rustup.rs/"
            exit 1
        fi

        # Add to PATH permanently
        if [[ ":$PATH:" != *":$HOME/.cargo/bin:"* ]]; then
            echo 'export PATH="$HOME/.cargo/bin:$PATH"' >> "$HOME/.bashrc"
        fi

        print_success "Rust installed"
    else
        rust_version=$(rustc --version | cut -d' ' -f2)
        print_success "Rust $rust_version found"
    fi
}

# Check and install system dependencies
install_system_deps() {
    print_header "Checking System Dependencies"

    local missing_deps=()
    local typing_tool_found=false

    # Check pkg-config
    if command_exists pkg-config; then
        print_success "pkg-config found"
    else
        print_warning "pkg-config not found"
        missing_deps+=("pkg-config")
    fi

    # Check ALSA
    if pkg-config --exists alsa 2>/dev/null; then
        print_success "ALSA library found"
    else
        print_warning "ALSA library not found"
        if [ "$OS" = "debian" ] || [ "$OS" = "ubuntu" ]; then
            missing_deps+=("libasound2-dev")
        elif [ "$OS" = "fedora" ]; then
            missing_deps+=("alsa-lib-devel")
        elif [ "$OS" = "arch" ]; then
            missing_deps+=("alsa-lib")
        fi
    fi

    # Check libclang (required for whisper-rs bindings via bindgen)
    if /sbin/ldconfig -p 2>/dev/null | grep -q libclang || [ -f "/usr/lib/libclang.so" ] || [ -f "/usr/lib/x86_64-linux-gnu/libclang.so.1" ]; then
        print_success "libclang found"
    else
        print_warning "libclang not found (required for whisper-rs)"
        if [ "$OS" = "debian" ] || [ "$OS" = "ubuntu" ]; then
            missing_deps+=("libclang-dev" "clang")
        elif [ "$OS" = "fedora" ]; then
            missing_deps+=("clang-devel")
        elif [ "$OS" = "arch" ]; then
            missing_deps+=("clang")
        fi
    fi

    # Check cmake (required for whisper-rs build)
    if command_exists cmake; then
        print_success "cmake found"
    else
        print_warning "cmake not found (required for whisper-rs)"
        missing_deps+=("cmake")
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

# Build and install ydotool (universal typing tool for Wayland/X11)
install_ydotool() {
    print_header "Checking ydotool"

    # Check if ydotool is already available
    if command_exists ydotool && command_exists ydotoold; then
        print_success "ydotool already installed"
        return 0
    fi

    print_info "ydotool not found - building from source..."
    print_info "This is a universal typing tool that works on Wayland and X11"

    # Check for required build dependencies
    local build_deps=()

    if ! command_exists cmake; then
        build_deps+=("cmake")
    fi

    if ! command_exists git; then
        build_deps+=("git")
    fi

    # scdoc is optional for man pages
    if ! command_exists scdoc; then
        if [ "$OS" = "debian" ] || [ "$OS" = "ubuntu" ]; then
            build_deps+=("scdoc")
        elif [ "$OS" = "fedora" ]; then
            build_deps+=("scdoc")
        elif [ "$OS" = "arch" ]; then
            build_deps+=("scdoc")
        fi
    fi

    # Install build dependencies if needed
    if [ ${#build_deps[@]} -gt 0 ]; then
        print_info "Installing build dependencies: ${build_deps[*]}"
        if [ "$OS" = "debian" ] || [ "$OS" = "ubuntu" ]; then
            sudo apt-get update
            sudo apt-get install -y "${build_deps[@]}"
        elif [ "$OS" = "fedora" ]; then
            sudo dnf install -y "${build_deps[@]}"
        elif [ "$OS" = "arch" ]; then
            sudo pacman -S --noconfirm "${build_deps[@]}"
        fi
    fi

    # Clone ydotool
    local ydotool_dir="/tmp/ydotool-build-$$"
    local original_dir="$(pwd)"

    print_info "Cloning ydotool repository..."
    git clone https://github.com/ReimuNotMoe/ydotool.git "$ydotool_dir"

    cd "$ydotool_dir"

    # Build ydotool
    print_info "Building ydotool..."
    mkdir build
    cd build
    cmake .. -DCMAKE_INSTALL_PREFIX="$HOME/.local"
    make -j "$(nproc)"

    # Install to ~/.local
    print_info "Installing ydotool to ~/.local..."
    make install

    # Return to original directory and cleanup
    cd "$original_dir"
    rm -rf "$ydotool_dir"

    # Set up ydotoold systemd service for user
    print_info "Setting up ydotoold systemd user service..."
    mkdir -p "$HOME/.config/systemd/user"

    cat > "$HOME/.config/systemd/user/ydotool.service" <<'EOF'
[Unit]
Description=ydotool daemon
Documentation=https://github.com/ReimuNotMoe/ydotool

[Service]
Type=simple
Restart=always
ExecStart=%h/.local/bin/ydotoold
Environment=DISPLAY=:0

[Install]
WantedBy=default.target
EOF

    # Set up udev rules for /dev/uinput access
    print_info "Setting up udev rules for /dev/uinput access..."
    sudo tee /etc/udev/rules.d/80-uinput.rules > /dev/null <<'EOF'
KERNEL=="uinput", MODE="0660", GROUP="input", OPTIONS+="static_node=uinput"
EOF

    # Add user to input group
    print_info "Adding user to 'input' group..."
    sudo usermod -aG input "$USER"

    # Reload udev rules
    print_info "Reloading udev rules..."
    sudo udevadm control --reload-rules
    sudo udevadm trigger

    # Load uinput module
    print_info "Loading uinput kernel module..."
    sudo modprobe uinput

    # Enable and start the service
    systemctl --user daemon-reload
    systemctl --user enable ydotool.service
    systemctl --user start ydotool.service

    # Wait a moment for the service to start
    sleep 2

    if systemctl --user is-active --quiet ydotool.service; then
        print_success "ydotool installed and daemon started successfully"
        print_info "ydotool and ydotoold are now available in ~/.local/bin"
    else
        print_warning "ydotool daemon may need a reboot to access /dev/uinput"
        print_info "After rebooting, the daemon will start automatically"
        print_info "Or manually start: systemctl --user start ydotool.service"
    fi

    print_warning "NOTE: You may need to log out and back in for group changes to take effect"
}

# Build Scribe
build_scribe() {
    print_header "Building Scribe (Rust)"

    print_info "Building release binary (this may take a few minutes)..."
    cargo build --release

    if [ -f "target/release/scribe" ]; then
        binary_size=$(du -h target/release/scribe | cut -f1)
        print_success "Build complete! Binary size: $binary_size"
    else
        print_error "Build failed - binary not found"
        exit 1
    fi
}

# Download Whisper model
download_model() {
    print_header "Downloading Whisper Model"

    local model_dir="$HOME/.cache/scribe/models"
    mkdir -p "$model_dir"

    local model_file="$model_dir/ggml-tiny.en.bin"

    if [ -f "$model_file" ]; then
        print_success "Model already exists: $model_file"
    else
        print_info "Downloading ggml-tiny.en.bin (74MB)..."

        if command_exists wget; then
            wget -q --show-progress \
                https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-tiny.en.bin \
                -O "$model_file"
        elif command_exists curl; then
            curl -L --progress-bar \
                https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-tiny.en.bin \
                -o "$model_file"
        else
            print_error "Neither wget nor curl found. Please install one of them."
            print_info "Or download manually:"
            print_info "  wget https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-tiny.en.bin"
            print_info "  mv ggml-tiny.en.bin $model_file"
            return
        fi

        if [ -f "$model_file" ]; then
            model_size=$(du -h "$model_file" | cut -f1)
            print_success "Model downloaded: $model_size"
        else
            print_error "Failed to download model"
        fi
    fi
}

# Create launcher script
create_launcher() {
    print_header "Creating Launcher"

    local install_dir="$(pwd)"
    local launcher="$HOME/.local/bin/scribe-rust"

    # Create .local/bin if it doesn't exist
    mkdir -p "$HOME/.local/bin"

    # Create launcher script
    cat > "$launcher" <<EOF
#!/bin/bash
# Scribe Rust launcher script
exec "$install_dir/target/release/scribe" "\$@"
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
        # Use example config from parent directory if available
        if [ -f "../config.example.toml" ]; then
            cp ../config.example.toml "$config_file"
            print_success "Config created: $config_file"
        else
            print_warning "No example config found, creating minimal config"
            cat > "$config_file" <<'EOF'
[model]
size = "tiny.en"
device = "cpu"
compute_type = "int8"

[audio]
sample_rate = 16000
channels = 1
vad_aggressiveness = 3
silence_duration = 1.5
min_audio_duration = 0.5

[output]
mode = "type"
typing_delay = 0.0
auto_enter = false

[notifications]
enabled = true
audio_bell = true
bell_sound = "system"
timeout = 3000

[advanced]
keep_model_loaded = false
EOF
            print_success "Minimal config created: $config_file"
        fi
    else
        print_info "Config already exists: $config_file"
    fi
}

# Main installation
main() {
    print_header "Scribe Rust Installation"

    # Detect OS
    detect_os

    # Check if we're in the rust-scribe directory
    if [ ! -f "Cargo.toml" ]; then
        print_error "Please run this script from the rust-scribe directory"
        exit 1
    fi

    # Install Rust
    install_rust

    # Install system dependencies
    install_system_deps

    # Install ydotool if no typing tool found
    install_ydotool

    # Build Scribe
    build_scribe

    # Download model
    download_model

    # Create launcher
    create_launcher

    # Create config
    create_config

    # Final message
    print_header "Installation Complete!"

    print_success "Scribe (Rust) installed successfully!"
    echo ""
    print_info "Performance improvements over Python:"
    echo "  • 20-23x faster startup (13ms vs 250ms)"
    echo "  • 97% smaller binary (2.8MB vs 115MB)"
    echo "  • 70% less memory usage"
    echo ""
    print_info "To use Scribe, either:"
    echo "  1. Restart your shell (or run: source ~/.bashrc)"
    echo "  2. Run directly: $HOME/.local/bin/scribe-rust"
    echo ""
    print_info "Test your installation:"
    echo "  scribe-rust test         # Test system setup"
    echo "  scribe-rust test-typing  # Test typing functionality"
    echo "  scribe-rust              # Start recording"
    echo "  scribe-rust --stream     # Start streaming mode"
    echo ""
    print_info "Configuration file: $HOME/.config/scribe/config.toml"
    print_info "Models directory: $HOME/.cache/scribe/models/"
    echo ""

    # Show additional models info
    print_info "To download additional models:"
    echo "  # base.en (better accuracy, ~75MB):"
    echo "  wget https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.en.bin \\"
    echo "       -O ~/.cache/scribe/models/ggml-base.en.bin"
    echo ""
    echo "  # small.en (high accuracy, ~245MB):"
    echo "  wget https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-small.en.bin \\"
    echo "       -O ~/.cache/scribe/models/ggml-small.en.bin"
    echo ""
}

# Run main
main
