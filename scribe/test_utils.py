"""Test utilities for Scribe - includes audio file testing."""

import numpy as np
import wave
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def generate_test_audio(duration: float = 3.0, frequency: int = 440, sample_rate: int = 16000) -> np.ndarray:
    """Generate a test audio tone.

    Args:
        duration: Duration in seconds.
        frequency: Tone frequency in Hz.
        sample_rate: Sample rate in Hz.

    Returns:
        Audio data as int16 numpy array.
    """
    t = np.linspace(0, duration, int(sample_rate * duration))
    audio = np.sin(2 * np.pi * frequency * t)
    # Scale to int16 range
    audio_int16 = (audio * 32767).astype(np.int16)
    return audio_int16


def load_audio_file(file_path: str, target_sample_rate: int = 16000) -> np.ndarray:
    """Load audio from WAV file.

    Args:
        file_path: Path to WAV file.
        target_sample_rate: Target sample rate (will resample if different).

    Returns:
        Audio data as int16 numpy array (1D).
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Audio file not found: {file_path}")

    with wave.open(str(path), 'rb') as wf:
        sample_rate = wf.getframerate()
        n_channels = wf.getnchannels()
        n_frames = wf.getnframes()
        audio_data = wf.readframes(n_frames)

        # Convert to numpy array
        if wf.getsampwidth() == 2:  # 16-bit
            audio = np.frombuffer(audio_data, dtype=np.int16)
        else:
            raise ValueError("Only 16-bit WAV files are supported")

        # Handle stereo
        if n_channels == 2:
            audio = audio.reshape(-1, 2)
            audio = audio.mean(axis=1).astype(np.int16)  # Convert to mono

        # Resample if needed (simple linear interpolation)
        if sample_rate != target_sample_rate:
            logger.info(f"Resampling from {sample_rate}Hz to {target_sample_rate}Hz")
            duration = len(audio) / sample_rate
            new_length = int(duration * target_sample_rate)
            indices = np.linspace(0, len(audio) - 1, new_length)
            audio = np.interp(indices, np.arange(len(audio)), audio).astype(np.int16)

        return audio


def save_audio_file(audio: np.ndarray, file_path: str, sample_rate: int = 16000):
    """Save audio to WAV file.

    Args:
        audio: Audio data as int16 numpy array.
        file_path: Output file path.
        sample_rate: Sample rate in Hz.
    """
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    # Ensure 1D
    if audio.ndim > 1:
        audio = audio.squeeze()

    with wave.open(str(path), 'wb') as wf:
        wf.setnchannels(1)  # Mono
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(sample_rate)
        wf.writeframes(audio.tobytes())

    logger.info(f"Audio saved to {file_path}")
