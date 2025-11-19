# Typing Functionality Debugging Guide

## Recent Changes

The typing functionality has been significantly improved to fix focus issues:

### Key Changes:
1. **Window Capture Before Notifications**: The target window is now captured at the very start, before any notifications appear
2. **Explicit Window Focusing**: Uses `xdotool windowfocus --sync` to ensure correct window has focus
3. **Increased Wait Times**: Longer delays (1.0s) to ensure notifications have cleared
4. **Comprehensive Logging**: Detailed logs at every step to diagnose issues

## How to Test

### Test 1: Basic Typing Test
```bash
# Open a text editor (gedit, kate, or terminal)
# Focus the text editor
# Run:
scribe test-typing

# Expected: "Hello from Scribe! This is a typing test." appears in 3 seconds
```

### Test 2: Standard Mode Test
```bash
# Open a text editor
# Focus the text editor
# Run:
scribe

# Speak something like "Hello world, this is a test"
# Wait for pause detection
# Expected: Text appears in your editor after transcription
```

### Test 3: Streaming Mode Test
```bash
# Open a text editor
# Focus the text editor
# Run:
scribe --stream

# Speak several sentences with brief pauses
# Expected: Text appears gradually as you speak
```

### Test 4: With Audio File (if you have test.mp3)
```bash
# Open a text editor
# Focus the text editor
# Run:
scribe test-audio /path/to/test.mp3

# Expected: Transcribed text from audio file appears in editor
```

## Checking Logs

Enable debug logging to see detailed information:

```bash
# Set log level to DEBUG in config
mkdir -p ~/.config/scribe
cat > ~/.config/scribe/config.toml << 'EOF'
[advanced]
log_level = "DEBUG"
EOF

# Run scribe and check logs
scribe 2>&1 | tee scribe_debug.log
```

Look for these log messages:
- `Captured target window ID: XXXXX` - Window was captured successfully
- `Target window name: 'Your App Name'` - Shows which window will receive text
- `Focusing window XXXXX` - Attempting to focus target window
- `Window focused successfully` - Focus succeeded
- `Text typed successfully with xdotool` - Typing completed

## Common Issues and Solutions

### Issue 1: Window Not Captured
**Symptoms**: Logs show "No pre-captured window"
**Solution**: This is a code issue - window capture should happen automatically. Check that you're using the updated version.

### Issue 2: Wrong Window Focused
**Symptoms**: Text appears in wrong application or notification
**Logs**: Check "Target window name" in logs
**Solution**:
- Make sure the text editor is focused when you trigger the keybinding
- Close or disable notifications temporarily to test
- Try with `--no-notification` flag: `scribe --no-notification`

### Issue 3: xdotool Permission Denied
**Symptoms**: Errors about permissions or access denied
**Solution**:
```bash
# For X11, check if xdotool can access windows:
xdotool getactivewindow

# For Wayland, you may need to switch to ydotool or use X11 compatibility
```

### Issue 4: Text Types But Doesn't Appear
**Symptoms**: Logs show success but no text in editor
**Possible Causes**:
1. Application doesn't accept synthetic input events
2. Window manager blocking xdotool
3. Compositor interfering

**Solutions**:
```bash
# Test if xdotool works at all:
echo "test" | xdotool type --file -

# Try different applications:
- gedit (usually works well)
- kate (KDE default, should work)
- gnome-terminal or konsole
- Avoid: Some Electron apps, browsers may block synthetic input

# Try clipboard mode as workaround:
scribe --output clipboard
```

### Issue 5: Notifications Stealing Focus
**Symptoms**: Text appears partially or not at all
**Solution**:
```bash
# Disable notifications temporarily for testing:
scribe --no-notification --no-bell

# Or configure shorter notification timeout:
cat >> ~/.config/scribe/config.toml << 'EOF'
[notifications]
notification_timeout = 500  # 0.5 seconds instead of 3
EOF
```

## Testing Without Microphone

You can test with a pre-recorded audio file instead of live recording. First, you need an audio file:

### Create Test Audio
```python
# Create a test WAV file
python3 << 'EOF'
from scribe.test_utils import generate_test_audio, save_audio_file
import numpy as np

# Generate 3 seconds of silence (real speech would be better)
audio = generate_test_audio(duration=3.0, frequency=440)
save_audio_file(audio, "test_recording.wav")
print("Created test_recording.wav")
EOF
```

Or record your own:
```bash
# Record 5 seconds with arecord
arecord -d 5 -f cd -t wav test_recording.wav

# Then test with it
scribe test-audio test_recording.wav
```

## Advanced Debugging

### Check xdotool Window Stack
```bash
# See all windows
xdotool search --name "."

# Get current focused window
xdotool getwindowfocus getwindowname

# Test typing directly
xdotool type "test message"
```

### Monitor Window Focus Changes
```bash
# In one terminal, monitor focus changes:
while true; do
    xdotool getwindowfocus getwindowname 2>/dev/null
    sleep 0.5
done

# In another terminal, run scribe and watch focus changes
```

### Check Notification Behavior
```bash
# Send a test notification and see if it steals focus:
notify-send -t 3000 "Test" "Does this steal focus?"

# If it does, try adjusting notification settings in your desktop environment
```

## Reporting Issues

If typing still doesn't work after trying these steps, please provide:

1. **Log output** with DEBUG level enabled
2. **Desktop environment**: KDE/GNOME/etc.
3. **Display server**: X11 or Wayland
4. **Application you're trying to type into**
5. **Output of**: `xdotool getwindowfocus getwindowname`
6. **Whether clipboard mode works**: `scribe --output clipboard`

Example bug report:
```
Environment:
- KDE Plasma 5.27
- X11
- Trying to type into: Kate text editor

Logs show:
- Window captured successfully: ID=12345678, name='Kate'
- Window focused successfully
- Text typed successfully
- BUT: No text appears in Kate

Clipboard mode: Works perfectly

xdotool test: `xdotool type "test"` DOES work when run manually
```
