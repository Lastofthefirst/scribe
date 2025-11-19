"""Audio recording and voice activity detection for Scribe."""

import logging
import time
from typing import Optional, Tuple
import numpy as np
import sounddevice as sd
import webrtcvad
from collections import deque

logger = logging.getLogger(__name__)


class AudioRecorder:
    """Records audio with voice activity detection."""

    def __init__(
        self,
        sample_rate: int = 16000,
        channels: int = 1,
        vad_aggressiveness: int = 3,
        silence_duration: float = 1.5,
        min_audio_duration: float = 0.5,
    ):
        """Initialize audio recorder.

        Args:
            sample_rate: Audio sample rate in Hz (must be 8000, 16000, 32000, or 48000 for VAD).
            channels: Number of audio channels (1 for mono).
            vad_aggressiveness: VAD aggressiveness level (0-3, higher = more aggressive).
            silence_duration: Duration of silence in seconds before stopping recording.
            min_audio_duration: Minimum audio duration in seconds to avoid accidental triggers.
        """
        self.sample_rate = sample_rate
        self.channels = channels
        self.vad_aggressiveness = vad_aggressiveness
        self.silence_duration = silence_duration
        self.min_audio_duration = min_audio_duration

        # Validate sample rate for VAD
        if sample_rate not in [8000, 16000, 32000, 48000]:
            raise ValueError(f"Sample rate must be 8000, 16000, 32000, or 48000 for VAD, got {sample_rate}")

        # Initialize VAD
        self.vad = webrtcvad.Vad(vad_aggressiveness)

        # Frame duration for VAD (10ms, 20ms, or 30ms)
        self.frame_duration_ms = 30
        self.frame_size = int(sample_rate * self.frame_duration_ms / 1000)

        # Recording state
        self.is_recording = False
        self.audio_buffer = []
        self.silence_start = None

        logger.info(f"AudioRecorder initialized: {sample_rate}Hz, {channels}ch, VAD={vad_aggressiveness}")

    def _is_speech(self, audio_frame: bytes) -> bool:
        """Check if audio frame contains speech using VAD.

        Args:
            audio_frame: Audio frame as bytes.

        Returns:
            True if speech is detected, False otherwise.
        """
        try:
            return self.vad.is_speech(audio_frame, self.sample_rate)
        except Exception as e:
            logger.debug(f"VAD error: {e}")
            return False

    def record_with_vad(self) -> Optional[np.ndarray]:
        """Record audio with voice activity detection.

        Returns:
            Numpy array of recorded audio, or None if recording was too short.
        """
        logger.info("Starting audio recording with VAD...")
        self.audio_buffer = []
        self.silence_start = None
        speech_detected = False
        recording_start = time.time()

        # Use a queue to buffer frames for VAD processing
        frame_buffer = deque(maxlen=2)  # Buffer 2 frames for smoother detection

        try:
            with sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype="int16",
                blocksize=self.frame_size,
            ) as stream:
                logger.info("Recording started (speak now)...")

                while True:
                    # Read audio frame
                    audio_chunk, overflowed = stream.read(self.frame_size)
                    if overflowed:
                        logger.warning("Audio buffer overflow detected")

                    # Add to buffer
                    self.audio_buffer.append(audio_chunk.copy())

                    # Convert to bytes for VAD
                    audio_bytes = audio_chunk.tobytes()

                    # Check for speech
                    is_speech = self._is_speech(audio_bytes)
                    frame_buffer.append(is_speech)

                    # Use majority vote from buffered frames
                    speech_in_buffer = sum(frame_buffer) > len(frame_buffer) / 2

                    if speech_in_buffer:
                        speech_detected = True
                        self.silence_start = None
                    else:
                        # Speech not detected in this frame
                        if speech_detected and self.silence_start is None:
                            # Start tracking silence
                            self.silence_start = time.time()
                        elif speech_detected and self.silence_start is not None:
                            # Check if silence duration exceeded
                            silence_elapsed = time.time() - self.silence_start
                            if silence_elapsed >= self.silence_duration:
                                logger.info(f"Silence detected for {silence_elapsed:.2f}s, stopping recording")
                                break

                # Calculate recording duration
                recording_duration = time.time() - recording_start
                logger.info(f"Recording finished: {recording_duration:.2f}s")

                # Check minimum duration
                if recording_duration < self.min_audio_duration:
                    logger.warning(f"Recording too short ({recording_duration:.2f}s < {self.min_audio_duration}s), ignoring")
                    return None

                # Concatenate audio buffer
                if self.audio_buffer:
                    audio_data = np.concatenate(self.audio_buffer, axis=0)
                    logger.info(f"Recorded {len(audio_data)} samples ({len(audio_data) / self.sample_rate:.2f}s)")
                    return audio_data
                else:
                    logger.warning("No audio data recorded")
                    return None

        except Exception as e:
            logger.error(f"Recording error: {e}")
            return None

    def record_toggle(self, stop_callback=None) -> Optional[np.ndarray]:
        """Toggle recording on/off (for manual control in noisy environments).

        Args:
            stop_callback: Optional callback function to check if recording should stop.

        Returns:
            Numpy array of recorded audio, or None if stopped early.
        """
        logger.info("Starting manual recording (call again to stop)...")
        self.audio_buffer = []
        recording_start = time.time()

        try:
            with sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype="int16",
                blocksize=self.frame_size,
            ) as stream:
                logger.info("Recording started (manual mode)...")

                while True:
                    # Read audio frame
                    audio_chunk, overflowed = stream.read(self.frame_size)
                    if overflowed:
                        logger.warning("Audio buffer overflow detected")

                    # Add to buffer
                    self.audio_buffer.append(audio_chunk.copy())

                    # Check stop callback
                    if stop_callback and stop_callback():
                        logger.info("Stop signal received")
                        break

                    # Prevent infinite recording (max 5 minutes)
                    if time.time() - recording_start > 300:
                        logger.warning("Maximum recording duration reached (5 minutes)")
                        break

                # Calculate recording duration
                recording_duration = time.time() - recording_start
                logger.info(f"Recording finished: {recording_duration:.2f}s")

                # Concatenate audio buffer
                if self.audio_buffer:
                    audio_data = np.concatenate(self.audio_buffer, axis=0)
                    logger.info(f"Recorded {len(audio_data)} samples ({len(audio_data) / self.sample_rate:.2f}s)")
                    return audio_data
                else:
                    logger.warning("No audio data recorded")
                    return None

        except Exception as e:
            logger.error(f"Recording error: {e}")
            return None

    def get_available_devices(self) -> list:
        """Get list of available audio input devices.

        Returns:
            List of device information dictionaries.
        """
        devices = sd.query_devices()
        input_devices = [d for d in devices if d["max_input_channels"] > 0]
        return input_devices

    def test_audio(self, duration: float = 3.0) -> bool:
        """Test audio recording for a fixed duration.

        Args:
            duration: Test duration in seconds.

        Returns:
            True if audio was successfully recorded, False otherwise.
        """
        logger.info(f"Testing audio recording for {duration}s...")
        try:
            recording = sd.rec(
                int(duration * self.sample_rate),
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype="int16",
            )
            sd.wait()
            logger.info(f"Audio test successful: recorded {len(recording)} samples")
            return True
        except Exception as e:
            logger.error(f"Audio test failed: {e}")
            return False
