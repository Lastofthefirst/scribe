# Scribe 🎤

**Fast, local speech-to-text for KDE/Debian systems**

Scribe is a lightweight, privacy-focused speech-to-text utility designed for Linux desktop environments. It runs entirely on your local machine (no cloud services), uses state-of-the-art AI models optimized for CPU performance, and provides a seamless user experience with automatic pause detection and real-time text output.

## ✨ Features

- **🚀 Fast & Efficient**: Uses Faster-Whisper with optimized models (tiny.en runs 9.67x faster than real-time on CPU)
- **🔒 Privacy-First**: 100% local processing, no data sent to cloud services, models cached locally
- **🎯 Smart Recording**: Automatic pause detection using Voice Activity Detection (VAD)
- **⚡ Streaming Mode**: Text appears in real-time as you speak with chunk-by-chunk transcription
- **⌨️ Seamless Output**: Types directly at cursor position or copies to clipboard
- **🖥️ Universal Desktop Support**: Full support for both X11 and Wayland (KDE Plasma, GNOME, etc.)
  - Auto-detects display server and installs correct tools (dotool/kdotool for Wayland, xdotool for X11)
- **🔔 User-Friendly**: Desktop notifications with smart timeouts (brief "still listening" notifications during streaming)
- **⏱️ Smart Timeouts**: Streaming mode auto-stops after 5 minutes or on long pause (configurable)
- **⚙️ Highly Configurable**: TOML-based configuration with sensible defaults
- **🧪 Well-Tested**: Comprehensive test suite following TDD principles
- **📦 Easy Installation**: One-command installation script with automatic dependency detection

## 🎯 Use Cases

- **Dictation**: Write emails, documents, or code using your voice
- **Accessibility**: Hands-free text input for users with mobility limitations
- **Productivity**: Quick note-taking and transcription during meetings
- **Convenience**: Fast text input when typing is inconvenient

## 📋 Requirements

- **OS**: Debian, Ubuntu, KDE Neon, Linux Mint, Pop!_OS, or other Debian-based distros
- **Python**: 3.8 or later
- **Audio**: Working microphone and audio input
- **Desktop**: X11 or Wayland session

## 🚀 Quick Start

Scribe comes in **two versions**: Python (mature, feature-complete) and Rust (20x faster startup, 70% less memory). Both versions have identical functionality!

### Clone the Repository

```bash
# HTTPS (recommended for most users)
git clone https://github.com/Lastofthefirst/scribe.git
cd scribe

# SSH (if you have SSH keys set up)
git clone git@github.com:Lastofthefirst/scribe.git
cd scribe
```

### Installation: Choose Your Version

#### Option 1: Python Version (Recommended for Most Users)

**One-command installation:**

```bash
./install-python.sh
source ~/.bashrc  # or restart your terminal
scribe --stream
```

**What it does:**
- ✅ Installs `uv` (ultra-fast Python package manager)
- ✅ Checks and installs all system dependencies automatically
- ✅ Installs typing tools (xdotool works on both X11 and Wayland via XWayland)
- ✅ Creates virtual environment and installs Python packages
- ✅ Downloads Whisper models (cached locally)
- ✅ Creates `~/.local/bin/scribe` launcher
- ✅ Adds to PATH automatically
- ✅ Ready to use immediately!

#### Option 2: Rust Version (For Maximum Performance)

**One-command installation:**

```bash
cd rust-scribe
./install-rust.sh
source ~/.bashrc  # or restart your terminal
scribe-rust --stream
```

**What it does:**
- ✅ Installs Rust toolchain if missing
- ✅ Checks and installs system dependencies (ALSA, pkg-config)
- ✅ Installs typing tools (xdotool)
- ✅ Builds optimized release binary with cargo
- ✅ Downloads GGML models (whisper.cpp format)
- ✅ Creates `~/.local/bin/scribe-rust` launcher
- ✅ Adds to PATH automatically
- ✅ **20-23x faster startup than Python!**

**Performance Benefits:**
- Startup: 13ms (vs 250ms Python) - **20-23x faster**
- Binary: 2.8MB (vs 115MB Python) - **97% smaller**
- Memory: ~70MB peak (vs ~250MB Python) - **70% less**

### Which Version Should I Choose?

| Feature | Python | Rust | Winner |
|---------|--------|------|--------|
| **Installation** | Very easy | Very easy | Tie ✅ |
| **Startup Time** | 250ms | 13ms | Rust ⚡ |
| **Memory Usage** | 250MB | 70MB | Rust 💾 |
| **Features** | Complete | Complete | Tie ✅ |
| **Maturity** | Stable | New | Python 🧪 |

**Recommendation:** Start with Python (more mature), switch to Rust for performance if needed.

### First Run

After installation, simply run:

```bash
# Python version
scribe --stream

# OR Rust version
scribe-rust --stream
```

1. Speak clearly into your microphone
2. Text appears in real-time as you speak!
3. Pause for 2 seconds when finished
4. Recording automatically ends

> **Installation Issues?** See [INSTALL_TROUBLESHOOTING.md](INSTALL_TROUBLESHOOTING.md) for common problems and solutions.

## 📖 Usage

### Basic Commands

```bash
# Streaming mode (RECOMMENDED - text appears as you speak!)
scribe --stream

# Standard mode (record all, then transcribe)
scribe

# Output to clipboard instead of typing
scribe --output clipboard

# Streaming mode with clipboard
scribe --stream --output clipboard

# Use a more accurate model
scribe --model base.en

# Disable notifications
scribe --no-notification --no-bell

# Test your setup
scribe test

# Download/cache a model for faster first run
scribe download

# List available models
scribe models

# Show help
scribe --help
```

### Keybinding Setup

#### KDE Plasma

1. Open **System Settings** → **Shortcuts** → **Custom Shortcuts**
2. Click **Edit** → **New** → **Global Shortcut** → **Command/URL**
3. Name it "Scribe Voice Input"
4. Set **Trigger**: Choose your preferred key (e.g., `Meta+S` or `Ctrl+Shift+S`)
5. Set **Action** (choose one):
   - **Streaming mode (recommended)**: `bash -c "export PATH=\"\$HOME/.local/bin:\$PATH\" && scribe --stream"`
   - **Standard mode**: `bash -c "export PATH=\"\$HOME/.local/bin:\$PATH\" && scribe"`
   - **Clipboard mode**: `bash -c "export PATH=\"\$HOME/.local/bin:\$PATH\" && scribe --output clipboard"`
6. Click **Apply**

> **Note**: The `bash -c` wrapper is needed to ensure PATH is set correctly when triggered by keybindings.

#### GNOME

1. Open **Settings** → **Keyboard** → **Keyboard Shortcuts**
2. Scroll to bottom and click **+** (Add Custom Shortcut)
3. Name: `Scribe Voice Input (Streaming)`
4. Command: `bash -c "export PATH=\"$HOME/.local/bin:$PATH\" && scribe --stream"`
5. Set your preferred shortcut
6. Click **Add**

> **Note**: Use `--output clipboard` instead of `--stream` if you prefer clipboard mode.

#### Other Desktop Environments

Most desktop environments support custom keybindings. Look for:
- **XFCE**: Settings → Keyboard → Application Shortcuts
- **Cinnamon**: System Settings → Keyboard → Shortcuts
- **MATE**: System → Preferences → Hardware → Keyboard Shortcuts

## ⚙️ Configuration

Configuration file: `~/.config/scribe/config.toml`

### Example Configuration

```toml
[model]
size = "tiny.en"          # Model: tiny.en, base.en, small.en
device = "cpu"            # Device: cpu or cuda
compute_type = "int8"     # int8 (fastest), float16, float32

[audio]
sample_rate = 16000       # Audio sample rate (Hz)
channels = 1              # Audio channels (1=mono)
vad_aggressiveness = 3    # VAD level: 0-3 (higher=more aggressive)
silence_duration = 1.5    # Pause detection time (seconds)
min_audio_duration = 0.5  # Minimum recording length (seconds)

[output]
mode = "type"             # Output: "type" or "clipboard"
typing_delay = 0.0        # Delay between chars (0=instant, 0.01=gradual)
auto_enter = false        # Auto-press Enter after typing

[notifications]
show_notification = true  # Show desktop notifications
play_bell = true          # Play sound when recording starts
bell_sound = "system"     # "system" or path to audio file
notification_timeout = 3000  # Timeout in milliseconds

[advanced]
keep_model_loaded = false # Keep model in RAM (faster but uses ~200MB)
log_level = "INFO"        # DEBUG, INFO, WARNING, ERROR
```

## 🎛️ Model Selection

| Model | Size | Speed | Accuracy | Best For |
|-------|------|-------|----------|----------|
| **tiny.en** | 39M | ⚡⚡⚡⚡⚡ | ⭐⭐⭐ | **Quick dictation (recommended)** |
| **base.en** | 74M | ⚡⚡⚡⚡ | ⭐⭐⭐⭐ | **Balanced (accurate + fast)** |
| **small.en** | 244M | ⚡⚡⚡ | ⭐⭐⭐⭐⭐ | Longer transcriptions |
| **medium.en** | 769M | ⚡⚡ | ⭐⭐⭐⭐⭐ | High accuracy needs |

**Recommendation**: Start with `tiny.en` for instant results. Upgrade to `base.en` if you need better accuracy.

English-specific models (`.en`) are 2-3x faster than multilingual models.

## 🧪 Testing

Run the test suite:

```bash
# Install test dependencies
pip install -e ".[dev]"

# Run all tests
pytest

# Run with coverage
pytest --cov=scribe --cov-report=html

# Run specific test file
pytest tests/test_config.py
```

Test your installation:

```bash
scribe test
```

This will verify:
- Audio recording works
- Required tools are installed
- Configuration is valid
- All components are functional

## 🔧 Troubleshooting

### No audio recorded

**Solution**: Check your microphone settings:
```bash
scribe test  # Test audio recording
```

If test fails:
- Verify microphone is connected and enabled
- Check audio input level in system settings
- Try different VAD aggressiveness (0-3) in config

### Text not appearing at cursor

**Problem**: Typing tool not found

**Solutions**:
- **X11**: Install xdotool: `sudo apt install xdotool`
- **Wayland**: Install ydotool: `sudo apt install ydotool`
- **Alternative**: Use clipboard mode: `scribe --output clipboard`

### Model download fails

**Solution**: Download manually:
```bash
scribe download --model tiny.en
```

If behind proxy, set environment variables:
```bash
export HTTP_PROXY=http://proxy:port
export HTTPS_PROXY=http://proxy:port
scribe download
```

### Slow transcription

**Solutions**:
1. Use smaller model: `--model tiny.en`
2. Enable model caching in config: `keep_model_loaded = true`
3. Use int8 compute type (default)

### Permission errors with ydotool (Wayland)

**Solution**: Add your user to input group:
```bash
sudo usermod -aG input $USER
sudo systemctl enable --now ydotool
```

Log out and back in for changes to take effect.

## 🏗️ Architecture

```
scribe/
├── cli.py           # Command-line interface & main entry point
├── config.py        # Configuration management (TOML)
├── audio.py         # Audio recording + VAD (webrtcvad)
├── transcribe.py    # Faster-Whisper integration
├── output.py        # Text output (xdotool/ydotool + clipboard)
└── notifications.py # Desktop notifications + audio alerts
```

**Core Technologies**:
- **Speech Recognition**: [Faster-Whisper](https://github.com/SYSTRAN/faster-whisper) (CTranslate2 optimized)
- **VAD**: [WebRTC VAD](https://github.com/wiseman/py-webrtcvad)
- **Audio**: [sounddevice](https://python-sounddevice.readthedocs.io/)
- **Typing**: xdotool (X11), ydotool (Wayland)

## 🤝 Contributing

Contributions are welcome! Here's how you can help:

1. **Report bugs**: Open an issue with details
2. **Suggest features**: Describe your use case
3. **Submit PRs**: Add features or fix bugs
4. **Improve docs**: Help others use Scribe

### Development Setup

```bash
# Clone repository
git clone https://github.com/Lastofthefirst/scribe.git
cd scribe

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install in development mode
pip install -e ".[dev]"

# Run tests
pytest

# Run linter
pylint scribe/
```

## 📜 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **OpenAI Whisper**: Original speech recognition model
- **Faster-Whisper**: High-performance Whisper implementation
- **SYSTRAN**: CTranslate2 inference engine
- **WebRTC**: Voice activity detection

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/Lastofthefirst/scribe/issues)
- **Discussions**: [GitHub Discussions](https://github.com/Lastofthefirst/scribe/discussions)

## 🗺️ Roadmap

- [ ] Multi-language support (auto-detection)
- [ ] Custom vocabulary/context
- [ ] Punctuation commands ("period", "comma")
- [ ] Daemon mode for persistent background service
- [ ] GUI configuration tool
- [ ] Integration with popular text editors
- [ ] Real-time streaming transcription
- [ ] Support for more desktop environments

## ⚡ Performance Tips

1. **Use English-specific models** (`.en`) for 2-3x speed boost
2. **Enable model caching** (`keep_model_loaded = true`) for instant startup
3. **Adjust VAD aggressiveness** (3 = fastest pause detection)
4. **Use int8 compute type** (default, best CPU performance)
5. **Close other heavy applications** for best performance

## 📊 Benchmarks

Tested on: Intel i7-8550U @ 1.80GHz (4 cores), 16GB RAM

| Model | Load Time | Transcription Speed | Memory Usage |
|-------|-----------|---------------------|--------------|
| tiny.en | ~1.5s | 9.67x realtime | ~180MB |
| base.en | ~2.0s | 5.2x realtime | ~250MB |
| small.en | ~3.5s | 2.1x realtime | ~600MB |

*10-second audio sample, CPU-only, int8 quantization*

---

**Made with ❤️ for the Linux community**

If you find Scribe useful, please ⭐ star the repository!
