"""Tests for transcription module."""

import pytest
import numpy as np
from unittest.mock import Mock, patch, MagicMock
from scribe.transcribe import Transcriber


class TestTranscriber:
    """Test transcription functionality."""

    def test_initialization(self):
        """Test Transcriber initialization."""
        transcriber = Transcriber(
            model_size="tiny.en",
            device="cpu",
            compute_type="int8",
            keep_loaded=False,
        )

        assert transcriber.model_size == "tiny.en"
        assert transcriber.device == "cpu"
        assert transcriber.compute_type == "int8"
        assert transcriber.model is None  # Not loaded yet

    def test_initialization_with_preload(self):
        """Test Transcriber initialization with preloaded model."""
        with patch('scribe.transcribe.WhisperModel') as mock_model:
            mock_model.return_value = MagicMock()

            transcriber = Transcriber(
                model_size="tiny.en",
                keep_loaded=True,
            )

            assert transcriber.model is not None
            mock_model.assert_called_once()

    @patch('scribe.transcribe.WhisperModel')
    def test_load_model(self, mock_whisper_model):
        """Test model loading."""
        mock_model_instance = MagicMock()
        mock_whisper_model.return_value = mock_model_instance

        transcriber = Transcriber(model_size="tiny.en", keep_loaded=False)
        model = transcriber._load_model()

        assert model == mock_model_instance
        mock_whisper_model.assert_called_once_with(
            "tiny.en",
            device="cpu",
            compute_type="int8",
        )

    @patch('scribe.transcribe.WhisperModel')
    def test_transcribe(self, mock_whisper_model):
        """Test audio transcription."""
        # Create mock model
        mock_model = MagicMock()
        mock_whisper_model.return_value = mock_model

        # Mock transcription segments
        mock_segment1 = MagicMock()
        mock_segment1.text = " Hello"
        mock_segment1.start = 0.0
        mock_segment1.end = 1.0

        mock_segment2 = MagicMock()
        mock_segment2.text = " world"
        mock_segment2.start = 1.0
        mock_segment2.end = 2.0

        mock_info = MagicMock()
        mock_info.language = "en"
        mock_info.language_probability = 0.99

        mock_model.transcribe.return_value = ([mock_segment1, mock_segment2], mock_info)

        # Create transcriber
        transcriber = Transcriber(model_size="tiny.en", keep_loaded=False)

        # Create test audio
        audio = np.random.randint(-1000, 1000, size=16000, dtype=np.int16)

        # Transcribe
        result = transcriber.transcribe(audio, sample_rate=16000)

        assert result == "Hello world"
        mock_model.transcribe.assert_called_once()

    @patch('scribe.transcribe.WhisperModel')
    def test_transcribe_empty(self, mock_whisper_model):
        """Test transcription with no speech detected."""
        mock_model = MagicMock()
        mock_whisper_model.return_value = mock_model

        # Mock empty transcription
        mock_info = MagicMock()
        mock_info.language = "en"
        mock_info.language_probability = 0.99

        mock_model.transcribe.return_value = ([], mock_info)

        transcriber = Transcriber(model_size="tiny.en")
        audio = np.zeros(16000, dtype=np.int16)

        result = transcriber.transcribe(audio)

        assert result == ""

    @patch('scribe.transcribe.WhisperModel')
    def test_transcribe_streaming(self, mock_whisper_model):
        """Test streaming transcription."""
        mock_model = MagicMock()
        mock_whisper_model.return_value = mock_model

        # Mock segments
        mock_segment1 = MagicMock()
        mock_segment1.text = " Hello"

        mock_segment2 = MagicMock()
        mock_segment2.text = " world"

        mock_info = MagicMock()
        mock_info.language = "en"
        mock_info.language_probability = 0.99

        mock_model.transcribe.return_value = ([mock_segment1, mock_segment2], mock_info)

        transcriber = Transcriber(model_size="tiny.en")
        audio = np.random.randint(-1000, 1000, size=16000, dtype=np.int16)

        # Collect streaming results
        results = list(transcriber.transcribe_streaming(audio))

        assert len(results) == 2
        assert results[0] == "Hello"
        assert results[1] == "world"

    def test_get_available_models(self):
        """Test getting list of available models."""
        transcriber = Transcriber()
        models = transcriber.get_available_models()

        assert "tiny.en" in models
        assert "base.en" in models
        assert "small.en" in models
        assert len(models) > 0

    @patch('scribe.transcribe.WhisperModel')
    def test_download_model(self, mock_whisper_model):
        """Test model download."""
        mock_whisper_model.return_value = MagicMock()

        transcriber = Transcriber(model_size="tiny.en")
        transcriber.download_model("base.en")

        # Should create model instance to trigger download
        assert mock_whisper_model.call_count >= 1
