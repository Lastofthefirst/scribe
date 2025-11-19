"""Streaming speech-to-text with real-time output."""

import logging
import time
import numpy as np
from typing import Optional
import sounddevice as sd

logger = logging.getLogger(__name__)


class StreamingRecorder:
    """Records and transcribes audio in real-time chunks."""

    def __init__(
        self,
        audio_recorder,
        transcriber,
        output_handler,
        notification_handler=None,
        chunk_pause: float = 0.8,
        final_pause: float = 2.0,
        max_duration: float = 300.0,  # 5 minutes max
    ):
        """Initialize streaming recorder.

        Args:
            audio_recorder: AudioRecorder instance.
            transcriber: Transcriber instance.
            output_handler: OutputHandler instance.
            notification_handler: NotificationHandler instance (optional).
            chunk_pause: Short pause duration (seconds) to trigger chunk transcription.
            final_pause: Long pause duration (seconds) to end recording.
            max_duration: Maximum recording duration (seconds) before auto-stop.
        """
        self.audio_recorder = audio_recorder
        self.transcriber = transcriber
        self.output_handler = output_handler
        self.notification_handler = notification_handler
        self.chunk_pause = chunk_pause
        self.final_pause = final_pause
        self.max_duration = max_duration

        self.sample_rate = audio_recorder.sample_rate
        self.frame_size = audio_recorder.frame_size
        self.vad = audio_recorder.vad

        self.total_audio = []
        self.transcribed_text = []

    def record_and_transcribe_streaming(self) -> str:
        """Record audio and transcribe in real-time chunks.

        Returns:
            Complete transcribed text.
        """
        logger.info("Starting streaming recording...")

        current_chunk = []
        silence_start = None
        last_speech_time = None  # Track when speech last occurred (for final pause)
        last_chunk_time = time.time()
        recording_start = time.time()
        speech_detected = False

        # Rolling buffer for VAD debouncing (10 frames)
        from collections import deque
        vad_buffer = deque(maxlen=10)

        # Continuous silence counter
        continuous_silence_frames = 0
        SILENCE_FRAMES_THRESHOLD = 5  # Require 5 consecutive silence frames to start timer

        try:
            with sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.audio_recorder.channels,
                dtype="int16",
                blocksize=self.frame_size,
            ) as stream:
                logger.info("Streaming mode active (speak continuously)...")

                while True:
                    # Read audio frame
                    audio_chunk, overflowed = stream.read(self.frame_size)
                    if overflowed:
                        logger.warning("Audio buffer overflow")

                    current_chunk.append(audio_chunk.copy())
                    self.total_audio.append(audio_chunk.copy())

                    # Check for speech with VAD
                    audio_bytes = audio_chunk.tobytes()
                    is_speech = self._is_speech(audio_bytes)
                    vad_buffer.append(is_speech)

                    # Use majority vote from VAD buffer (debouncing)
                    if len(vad_buffer) >= 5:
                        speech_ratio = sum(vad_buffer) / len(vad_buffer)
                        is_speech_smoothed = speech_ratio > 0.5
                    else:
                        is_speech_smoothed = is_speech

                    if is_speech_smoothed:
                        # Speech detected
                        speech_detected = True
                        last_speech_time = time.time()
                        silence_start = None
                        continuous_silence_frames = 0
                    else:
                        # Silence frame detected
                        continuous_silence_frames += 1

                        # Only start silence timer after multiple consecutive silence frames
                        if speech_detected and silence_start is None and continuous_silence_frames >= SILENCE_FRAMES_THRESHOLD:
                            silence_start = time.time()
                            logger.debug(f"Silence started after {continuous_silence_frames} continuous frames")

                        if silence_start:
                            silence_duration = time.time() - silence_start

                            # Check for chunk pause (transcribe but continue recording)
                            if silence_duration >= self.chunk_pause and len(current_chunk) > 0:
                                chunk_duration = len(current_chunk) * self.frame_size / self.sample_rate

                                # Only transcribe if chunk is substantial
                                if chunk_duration > 0.5:
                                    logger.info(f"Chunk pause detected ({silence_duration:.1f}s), transcribing...")
                                    self._transcribe_and_output_chunk(current_chunk)
                                    last_chunk_time = time.time()

                                    # Show brief "still listening" notification (500ms)
                                    if self.notification_handler:
                                        self.notification_handler._show_notification(
                                            "Scribe Streaming",
                                            "Still listening...",
                                            "audio-input-microphone",
                                            urgency="low",
                                            timeout=500,  # Very brief - 0.5 seconds
                                        )

                                current_chunk = []
                                # Don't reset silence_start - keep tracking for final pause

                            # Check for final pause (end recording)
                            # Only end if we have detected speech AND have transcribed something
                            if last_speech_time is not None and silence_duration >= self.final_pause:
                                # Additional check: only end if we've transcribed at least one chunk
                                if len(self.transcribed_text) > 0:
                                    time_since_last_speech = time.time() - last_speech_time
                                    logger.info(f"Final pause detected ({time_since_last_speech:.1f}s since last speech), ending recording")
                                    break
                                else:
                                    logger.debug(f"Silence detected but no content transcribed yet, continuing...")

                    # Check for maximum duration timeout
                    elapsed_time = time.time() - recording_start
                    if elapsed_time >= self.max_duration:
                        logger.info(f"Maximum duration reached ({elapsed_time:.1f}s), ending recording")
                        break

                # Transcribe any remaining audio
                if len(current_chunk) > 0:
                    chunk_duration = len(current_chunk) * self.frame_size / self.sample_rate
                    if chunk_duration > 0.3:
                        logger.info("Transcribing final chunk...")
                        self._transcribe_and_output_chunk(current_chunk)

                recording_duration = time.time() - recording_start
                logger.info(f"Streaming recording complete: {recording_duration:.1f}s total")

                # Show "finished" notification
                if self.notification_handler:
                    total_text = " ".join(self.transcribed_text)
                    if total_text:
                        preview = total_text[:50] + "..." if len(total_text) > 50 else total_text
                        self.notification_handler._show_notification(
                            "Scribe Complete",
                            f"Transcription finished: {preview}",
                            "dialog-information",
                        )
                    else:
                        self.notification_handler._show_notification(
                            "Scribe Complete",
                            "Recording ended (no speech detected)",
                            "dialog-information",
                        )

                return " ".join(self.transcribed_text)

        except Exception as e:
            logger.error(f"Streaming recording error: {e}")
            return " ".join(self.transcribed_text)

    def _is_speech(self, audio_frame: bytes) -> bool:
        """Check if audio frame contains speech.

        Args:
            audio_frame: Audio frame as bytes.

        Returns:
            True if speech detected.
        """
        try:
            return self.vad.is_speech(audio_frame, self.sample_rate)
        except Exception:
            return False

    def _transcribe_and_output_chunk(self, chunk: list):
        """Transcribe a chunk and output it immediately.

        Args:
            chunk: List of audio frames.
        """
        try:
            # Concatenate chunk
            audio_data = np.concatenate(chunk, axis=0)

            # Ensure 1D
            if audio_data.ndim > 1:
                audio_data = audio_data.squeeze()

            # Skip if too short
            duration = len(audio_data) / self.sample_rate
            if duration < 0.3:
                logger.debug(f"Skipping short chunk: {duration:.2f}s")
                return

            # Transcribe chunk
            logger.info(f"Transcribing chunk: {len(audio_data)} samples ({duration:.2f}s)")
            text = self.transcriber.transcribe(
                audio_data,
                sample_rate=self.sample_rate,
            )

            if text and text.strip():
                # Add space if not first chunk
                if self.transcribed_text:
                    text = " " + text

                logger.info(f"Chunk transcribed: '{text.strip()}'")
                self.transcribed_text.append(text.strip())

                # Output immediately
                logger.info(f"Outputting chunk text...")
                success = self.output_handler.output(text)
                if success:
                    logger.info(f"Chunk output successful")
                else:
                    logger.error(f"Chunk output failed!")

            else:
                logger.warning("Chunk transcription produced no text")

        except Exception as e:
            logger.error(f"Chunk transcription error: {e}", exc_info=True)
