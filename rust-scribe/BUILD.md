# Building Scribe Rust

## System Requirements

### Linux

The following system libraries are required for audio recording:

#### Debian/Ubuntu
```bash
sudo apt-get install libasound2-dev pkg-config
```

#### Fedora/RHEL
```bash
sudo dnf install alsa-lib-devel pkg-config
```

#### Arch Linux
```bash
sudo pacman -S alsa-lib pkg-config
```

### Build

Once dependencies are installed:

```bash
cd rust-scribe
cargo build --release
```

The binary will be in `target/release/scribe`.

## Model Installation

Whisper models must be downloaded manually:

1. Create model directory:
   ```bash
   mkdir -p ~/.cache/scribe/models
   ```

2. Download a model from [whisper.cpp releases](https://huggingface.co/ggerganov/whisper.cpp/tree/main):
   ```bash
   # For tiny.en (recommended for CPU):
   wget https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-tiny.en.bin \
        -O ~/.cache/scribe/models/ggml-tiny.en.bin

   # For base.en (better accuracy):
   wget https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.en.bin \
        -O ~/.cache/scribe/models/ggml-base.en.bin
   ```

3. Update your config to use the model:
   ```toml
   [model]
   size = "tiny.en"  # or "base.en", etc.
   ```

## Testing

```bash
# Test system setup
./target/release/scribe test

# Test typing
./target/release/scribe test-typing

# Run standard mode
./target/release/scribe

# Run streaming mode
./target/release/scribe --stream
```

## Known Issues

### Container Environments

The build requires ALSA development libraries which may not be available in container environments. This is expected - build on your actual system instead.

### Model Format

Rust version uses whisper.cpp (GGML format) instead of faster-whisper (CTranslate2 format). You'll need to download GGML models separately. The models are compatible and performance is similar or better.
