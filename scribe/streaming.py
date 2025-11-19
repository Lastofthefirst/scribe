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
        chunk_pause: float = 0.8,
        final_pause: float = 2.0,
    ):
        """Initialize streaming recorder.

        Args:
            audio_recorder: AudioRecorder instance.
            transcriber: Transcriber instance.
            output_handler: OutputHandler instance.
            chunk_pause: Short pause duration (seconds) to trigger chunk transcription.
            final_pause: Long pause duration (seconds) to end recording.
        """
        self.audio_recorder = audio_recorder
        self.transcriber = transcriber
        self.output_handler = output_handler
        self.chunk_pause = chunk_pause
        self.final_pause = final_pause

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
        last_chunk_time = time.time()
        recording_start = time.time()
        speech_detected = False

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

                    # Check for speech
                    audio_bytes = audio_chunk.tobytes()
                    is_speech = self._is_speech(audio_bytes)

                    if is_speech:
                        speech_detected = True
                        silence_start = None
                    else:
                        # Silence detected
                        if speech_detected and silence_start is None:
                            silence_start = time.time()

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

                                current_chunk = []
                                silence_start = None

                            # Check for final pause (end recording)
                            if silence_duration >= self.final_pause:
                                logger.info(f"Final pause detected ({silence_duration:.1f}s), ending recording")
                                break

                # Transcribe any remaining audio
                if len(current_chunk) > 0:
                    chunk_duration = len(current_chunk) * self.frame_size / self.sample_rate
                    if chunk_duration > 0.3:
                        logger.info("Transcribing final chunk...")
                        self._transcribe_and_output_chunk(current_chunk)

                recording_duration = time.time() - recording_start
                logger.info(f"Streaming recording complete: {recording_duration:.1f}s total")

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
