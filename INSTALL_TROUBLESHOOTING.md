# Installation Troubleshooting

## Python 3.14+ Not Supported

If you see errors like:
```
ERROR: Cannot install scribe-stt because these package versions have conflicting dependencies.
Additionally, some packages in these conflicts have no matching distributions available for your environment:
    onnxruntime
```

**Problem**: Python 3.14 is too new - `onnxruntime` (required by faster-whisper) doesn't have pre-built wheels for Python 3.14+ yet.

**Solution**: The install script will automatically detect this and try to use Python 3.11, 3.12, or 3.13 instead.

### If Installation Script Fails

If the script can't find a compatible Python version, install Python 3.11 manually:

#### Debian/Ubuntu
```bash
sudo apt update
sudo apt install -y python3.11 python3.11-venv python3.11-dev

# Verify installation
python3.11 --version
```

Then run the install script again - it will automatically detect and use Python 3.11.

### Manual Virtual Environment with Specific Python Version

If you prefer to create the venv manually:
```bash
# Remove old venv if it exists
rm -rf ~/.local/share/scribe-venv

# Create new venv with Python 3.11
python3.11 -m venv ~/.local/share/scribe-venv
source ~/.local/share/scribe-venv/bin/activate

# Install scribe
cd scribe
pip install -e .
```

## FFmpeg Libraries Missing Error

If you see errors like:
```
Package 'libavformat', required by 'virtual:world', not found
Package 'libavcodec', required by 'virtual:world', not found
```

**Solution**: Install FFmpeg development libraries:

### Debian/Ubuntu
```bash
sudo apt update
sudo apt install -y ffmpeg libavcodec-dev libavformat-dev libavdevice-dev \
    libavutil-dev libavfilter-dev libswscale-dev libswresample-dev pkg-config
```

Then retry the installation:
```bash
./install.sh
```

Or if you already have the virtual environment:
```bash
source ~/.local/share/scribe-venv/bin/activate
pip install -e .
```

### Fedora/RHEL
```bash
sudo dnf install -y ffmpeg ffmpeg-devel pkg-config
```

### Arch/Manjaro
```bash
sudo pacman -S ffmpeg pkg-config
```

## Other Common Issues

### PortAudio Missing
```bash
sudo apt install -y portaudio19-dev python3-dev
```

### No Typing Tool (xdotool/ydotool)
```bash
# For X11
sudo apt install -y xdotool

# For Wayland
sudo apt install -y ydotool
```

### Permission Errors with ydotool
```bash
sudo usermod -aG input $USER
sudo systemctl enable --now ydotool
# Log out and back in
```

## Manual Installation

If the install script fails, you can install manually:

```bash
# 1. Install system dependencies
sudo apt install -y python3 python3-pip python3-dev python3-venv \
    portaudio19-dev ffmpeg libavcodec-dev libavformat-dev libavdevice-dev \
    libavutil-dev libavfilter-dev libswscale-dev libswresample-dev \
    pkg-config xdotool libnotify-bin pulseaudio-utils

# 2. Create virtual environment
python3 -m venv ~/.local/share/scribe-venv
source ~/.local/share/scribe-venv/bin/activate

# 3. Install Scribe
cd scribe
pip install -e .

# 4. Create launcher script
mkdir -p ~/.local/bin
cat > ~/.local/bin/scribe << 'EOF'
#!/bin/bash
source ~/.local/share/scribe-venv/bin/activate
exec scribe "$@"
EOF
chmod +x ~/.local/bin/scribe

# 5. Add to PATH (if needed)
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

## Testing Your Installation

After fixing dependencies, test with:
```bash
scribe test
```

This will verify all components are working correctly.

## Still Having Issues?

1. Check the full error message
2. Verify Python version: `python3 --version` (need 3.8+)
3. Check available disk space: `df -h`
4. Try installing in a clean environment
5. Open an issue on GitHub with the full error log
