"""Speech transcription using Faster-Whisper."""

import logging
import numpy as np
from typing import Optional, Iterator, Tuple
from faster_whisper import WhisperModel
import time

logger = logging.getLogger(__name__)


class Transcriber:
    """Transcribes audio using Faster-Whisper."""

    def __init__(
        self,
        model_size: str = "tiny.en",
        device: str = "cpu",
        compute_type: str = "int8",
        keep_loaded: bool = False,
    ):
        """Initialize transcriber.

        Args:
            model_size: Whisper model size (tiny, tiny.en, base, base.en, small, etc.).
            device: Device to use ("cpu" or "cuda").
            compute_type: Compute type ("int8", "float16", "float32").
            keep_loaded: Keep model loaded in memory for faster subsequent runs.
        """
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self.keep_loaded = keep_loaded
        self.model: Optional[WhisperModel] = None

        logger.info(f"Transcriber initialized: model={model_size}, device={device}, compute={compute_type}")

        # Preload model if requested
        if keep_loaded:
            self._load_model()

    def _load_model(self) -> WhisperModel:
        """Load Whisper model.

        Returns:
            WhisperModel instance.
        """
        if self.model is None:
            logger.info(f"Loading Whisper model: {self.model_size}")
            start_time = time.time()

            try:
                self.model = WhisperModel(
                    self.model_size,
                    device=self.device,
                    compute_type=self.compute_type,
                )

                load_time = time.time() - start_time
                logger.info(f"Model loaded in {load_time:.2f}s")

            except Exception as e:
                logger.error(f"Failed to load model: {e}")
                raise

        return self.model

    def transcribe(
        self,
        audio: np.ndarray,
        sample_rate: int = 16000,
        language: str = "en",
        beam_size: int = 5,
    ) -> str:
        """Transcribe audio to text.

        Args:
            audio: Audio data as numpy array (int16).
            sample_rate: Audio sample rate in Hz.
            language: Language code (e.g., "en" for English).
            beam_size: Beam size for decoding (higher = more accurate but slower).

        Returns:
            Transcribed text.
        """
        logger.info(f"Transcribing audio: {len(audio)} samples ({len(audio) / sample_rate:.2f}s)")
        start_time = time.time()

        try:
            # Load model if not already loaded
            model = self._load_model()

            # Ensure audio is 1D (squeeze out channel dimension if present)
            if audio.ndim > 1:
                audio = audio.squeeze()

            # Convert int16 to float32 and normalize to [-1, 1]
            audio_float = audio.astype(np.float32) / 32768.0

            # Transcribe
            segments, info = model.transcribe(
                audio_float,
                language=language,
                beam_size=beam_size,
                vad_filter=True,  # Use VAD to filter out non-speech
                vad_parameters=dict(
                    min_silence_duration_ms=500,  # Minimum silence duration
                ),
            )

            # Collect all segments
            transcription_parts = []
            for segment in segments:
                text = segment.text.strip()
                if text:
                    transcription_parts.append(text)
                    logger.debug(f"Segment [{segment.start:.2f}s - {segment.end:.2f}s]: {text}")

            # Combine segments
            transcription = " ".join(transcription_parts)

            # Log detected language and statistics
            logger.info(
                f"Detected language: {info.language} "
                f"(probability: {info.language_probability:.2f})"
            )

            transcription_time = time.time() - start_time
            audio_duration = len(audio) / sample_rate
            rtf = transcription_time / audio_duration  # Real-time factor

            logger.info(
                f"Transcription complete in {transcription_time:.2f}s "
                f"(RTF: {rtf:.2f}x, {len(transcription)} chars)"
            )

            # Unload model if not keeping it loaded
            if not self.keep_loaded:
                self._unload_model()

            return transcription.strip()

        except Exception as e:
            logger.error(f"Transcription error: {e}")
            return ""

    def transcribe_streaming(
        self,
        audio: np.ndarray,
        sample_rate: int = 16000,
        language: str = "en",
        beam_size: int = 5,
    ) -> Iterator[str]:
        """Transcribe audio to text with streaming output.

        Args:
            audio: Audio data as numpy array (int16).
            sample_rate: Audio sample rate in Hz.
            language: Language code (e.g., "en" for English).
            beam_size: Beam size for decoding.

        Yields:
            Text segments as they are transcribed.
        """
        logger.info(f"Starting streaming transcription: {len(audio)} samples")

        try:
            # Load model if not already loaded
            model = self._load_model()

            # Ensure audio is 1D (squeeze out channel dimension if present)
            if audio.ndim > 1:
                audio = audio.squeeze()

            # Convert int16 to float32 and normalize
            audio_float = audio.astype(np.float32) / 32768.0

            # Transcribe with streaming
            segments, info = model.transcribe(
                audio_float,
                language=language,
                beam_size=beam_size,
                vad_filter=True,
            )

            # Yield segments as they are generated
            for segment in segments:
                text = segment.text.strip()
                if text:
                    logger.debug(f"Streaming segment: {text}")
                    yield text

            # Unload model if not keeping it loaded
            if not self.keep_loaded:
                self._unload_model()

        except Exception as e:
            logger.error(f"Streaming transcription error: {e}")
            yield ""

    def _unload_model(self):
        """Unload model from memory."""
        if self.model is not None:
            logger.info("Unloading model from memory")
            self.model = None

    def get_available_models(self) -> list:
        """Get list of available Whisper models.

        Returns:
            List of model names.
        """
        return [
            "tiny.en",
            "tiny",
            "base.en",
            "base",
            "small.en",
            "small",
            "medium.en",
            "medium",
            "large-v1",
            "large-v2",
            "large-v3",
        ]

    def download_model(self, model_size: str = None):
        """Download and cache a Whisper model.

        Args:
            model_size: Model size to download. If None, uses current model size.
        """
        if model_size is None:
            model_size = self.model_size

        logger.info(f"Downloading model: {model_size}")
        try:
            WhisperModel(model_size, device=self.device, compute_type=self.compute_type)
            logger.info(f"Model {model_size} downloaded successfully")
        except Exception as e:
            logger.error(f"Failed to download model: {e}")
            raise

    def __del__(self):
        """Cleanup when object is destroyed."""
        self._unload_model()
