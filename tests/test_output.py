"""Tests for output handling module."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from scribe.output import OutputHandler


class TestOutputHandler:
    """Test output handling functionality."""

    def test_initialization(self):
        """Test OutputHandler initialization."""
        handler = OutputHandler(
            mode="type",
            typing_delay=0.01,
            auto_enter=True,
        )

        assert handler.mode == "type"
        assert handler.typing_delay == 0.01
        assert handler.auto_enter is True

    @patch('scribe.output.shutil.which')
    def test_detect_xdotool(self, mock_which):
        """Test detection of xdotool."""
        mock_which.side_effect = lambda x: "/usr/bin/xdotool" if x == "xdotool" else None

        handler = OutputHandler()

        assert handler.typing_tool == "xdotool"

    @patch('scribe.output.shutil.which')
    def test_detect_ydotool(self, mock_which):
        """Test detection of ydotool."""
        def which_side_effect(cmd):
            if cmd == "ydotool":
                return "/usr/bin/ydotool"
            return None

        mock_which.side_effect = which_side_effect

        handler = OutputHandler()

        assert handler.typing_tool == "ydotool"

    @patch('scribe.output.shutil.which')
    def test_no_typing_tool(self, mock_which):
        """Test when no typing tool is available."""
        mock_which.return_value = None

        handler = OutputHandler()

        assert handler.typing_tool is None

    @patch('scribe.output.pyperclip.copy')
    def test_clipboard_output(self, mock_copy):
        """Test clipboard output mode."""
        handler = OutputHandler(mode="clipboard")

        result = handler.output("Hello world")

        assert result is True
        mock_copy.assert_called_once_with("Hello world")

    @patch('scribe.output.pyperclip.copy')
    def test_clipboard_output_error(self, mock_copy):
        """Test clipboard output error handling."""
        mock_copy.side_effect = Exception("Clipboard error")

        handler = OutputHandler(mode="clipboard")

        result = handler.output("Hello world")

        assert result is False

    @patch('scribe.output.subprocess.run')
    @patch('scribe.output.shutil.which')
    @patch('scribe.output.time.sleep')
    def test_type_with_xdotool(self, mock_sleep, mock_which, mock_run):
        """Test typing with xdotool."""
        mock_which.side_effect = lambda x: "/usr/bin/xdotool" if x == "xdotool" else None
        mock_run.return_value = MagicMock(returncode=0)

        handler = OutputHandler(mode="type")

        result = handler.output("Hello")

        assert result is True
        # Should call xdotool type
        assert any("xdotool" in str(call) for call in mock_run.call_args_list)

    @patch('scribe.output.subprocess.run')
    @patch('scribe.output.shutil.which')
    @patch('scribe.output.time.sleep')
    def test_type_with_delay(self, mock_sleep, mock_which, mock_run):
        """Test typing with character delay."""
        mock_which.side_effect = lambda x: "/usr/bin/xdotool" if x == "xdotool" else None
        mock_run.return_value = MagicMock(returncode=0)

        handler = OutputHandler(mode="type", typing_delay=0.01)

        result = handler.output("Hi")

        assert result is True
        # Should have delays between characters
        assert mock_sleep.call_count >= 1

    @patch('scribe.output.subprocess.run')
    @patch('scribe.output.shutil.which')
    @patch('scribe.output.time.sleep')
    def test_type_with_auto_enter(self, mock_sleep, mock_which, mock_run):
        """Test typing with auto Enter key."""
        mock_which.side_effect = lambda x: "/usr/bin/xdotool" if x == "xdotool" else None
        mock_run.return_value = MagicMock(returncode=0)

        handler = OutputHandler(mode="type", auto_enter=True)

        result = handler.output("Hello")

        assert result is True
        # Should press Return key
        calls = [str(call) for call in mock_run.call_args_list]
        assert any("Return" in call or "key" in call for call in calls)

    @patch('scribe.output.pyperclip.paste')
    def test_get_clipboard_content(self, mock_paste):
        """Test getting clipboard content."""
        mock_paste.return_value = "Clipboard text"

        handler = OutputHandler()
        content = handler.get_clipboard_content()

        assert content == "Clipboard text"
        mock_paste.assert_called_once()

    def test_output_empty_text(self):
        """Test output with empty text."""
        handler = OutputHandler()

        result = handler.output("")

        assert result is False

    @patch('scribe.output.shutil.which')
    @patch('scribe.output.pyperclip.copy')
    def test_fallback_to_clipboard(self, mock_copy, mock_which):
        """Test fallback to clipboard when no typing tool available."""
        mock_which.return_value = None  # No typing tool

        handler = OutputHandler(mode="type")

        result = handler.output("Hello")

        # Should fall back to clipboard
        mock_copy.assert_called_once_with("Hello")
