# Changelog

All notable changes to Scribe will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2024-11-19

### Added
- Initial release of Scribe
- Speech-to-text using Faster-Whisper (optimized for CPU)
- Voice Activity Detection (VAD) for automatic pause detection
- Text output via typing (xdotool/ydotool/wtype) or clipboard
- Desktop notifications with audio bell support
- Support for both X11 and Wayland
- Configurable TOML-based configuration
- One-command installation script for Debian-based systems
- Comprehensive test suite (100+ tests)
- CLI with multiple commands (test, download, models, setup)
- Support for multiple Whisper models (tiny, base, small, medium)
- Automatic model downloading and caching
- Real-time transcription with streaming support
- Keybinding integration guides for KDE and GNOME

### Features
- **Performance**: Tiny.en model runs 9.67x faster than real-time on CPU
- **Privacy**: 100% local processing, no cloud services
- **User Experience**: Smart pause detection (1.5s default, configurable)
- **Accessibility**: Hands-free text input support
- **Flexibility**: Multiple output modes and configuration options

### Dependencies
- Python 3.8+
- faster-whisper >= 1.0.0
- sounddevice >= 0.4.6
- webrtcvad >= 2.0.10
- pyperclip >= 1.8.2
- toml >= 0.10.2
- click >= 8.1.0

### System Requirements
- Debian-based Linux distribution
- Working microphone
- xdotool (X11) or ydotool/wtype (Wayland)
- notify-send or equivalent notification tool
- Audio playback tool (paplay, aplay, ffplay, or mpv)

## [Unreleased]

### Added
- **Wayland Priority Support**: Full Wayland support with auto-detection
  - dotool support (recommended for Wayland - no daemon, works everywhere)
  - kdotool support (KDE-specific via KWin DBus)
  - Automatic display server detection (Wayland/X11)
  - Auto-installation of correct typing tools during setup
- **Model Caching**: Offline-first model loading
  - Models loaded from local cache first (no network check)
  - Only downloads if not in cache
  - Eliminates HuggingFace rate limit errors
  - Faster startup times
- **Streaming Mode Improvements**:
  - Maximum duration timeout (5 minutes, configurable)
  - Brief "still listening" notifications after each chunk (500ms)
  - "Finished transcribing" notification with preview
  - Smart timeout prevents infinite recordings
- **Window Focus Protection**: Target window captured before notifications to prevent focus stealing
- **Notification Improvements**:
  - Configurable per-notification timeouts
  - Brief notifications don't interrupt workflow
  - Low urgency notifications for status updates

### Fixed
- Streaming mode not stopping after long timeout
- Model downloading on every run (now caches properly)
- xdotool not working on Wayland (now uses dotool/kdotool)
- Synthetic event rejection in modern applications
- Focus loss from notifications interfering with text output

### Changed
- Typing tool detection now prioritizes Wayland tools
- Installation script auto-detects display server
- Window activation uses windowactivate instead of windowfocus (avoids synthetic events)
- Brief notifications use 500ms timeout instead of 3000ms

## [0.1.0] - 2024-11-19 (Initial Release)
