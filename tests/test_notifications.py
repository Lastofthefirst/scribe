"""Tests for notifications module."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
from scribe.notifications import NotificationHandler


class TestNotificationHandler:
    """Test notification handling functionality."""

    def test_initialization(self):
        """Test NotificationHandler initialization."""
        handler = NotificationHandler(
            show_notification=True,
            play_bell=True,
            bell_sound="system",
        )

        assert handler.show_notification is True
        assert handler.play_bell is True
        assert handler.bell_sound == "system"

    @patch('scribe.notifications.shutil.which')
    def test_detect_notify_send(self, mock_which):
        """Test detection of notify-send."""
        mock_which.side_effect = lambda x: "/usr/bin/notify-send" if x == "notify-send" else None

        handler = NotificationHandler()

        assert handler.notify_tool == "notify-send"

    @patch('scribe.notifications.shutil.which')
    def test_detect_kdialog(self, mock_which):
        """Test detection of kdialog."""
        def which_side_effect(cmd):
            if cmd == "kdialog":
                return "/usr/bin/kdialog"
            return None

        mock_which.side_effect = which_side_effect

        handler = NotificationHandler()

        assert handler.notify_tool == "kdialog"

    @patch('scribe.notifications.shutil.which')
    def test_detect_paplay(self, mock_which):
        """Test detection of paplay for audio."""
        def which_side_effect(cmd):
            if cmd == "paplay":
                return "/usr/bin/paplay"
            return None

        mock_which.side_effect = which_side_effect

        handler = NotificationHandler()

        assert handler.audio_tool == "paplay"

    @patch('scribe.notifications.subprocess.run')
    @patch('scribe.notifications.shutil.which')
    def test_show_notification_with_notify_send(self, mock_which, mock_run):
        """Test showing notification with notify-send."""
        mock_which.side_effect = lambda x: "/usr/bin/notify-send" if x == "notify-send" else None
        mock_run.return_value = MagicMock(returncode=0)

        handler = NotificationHandler(show_notification=True)

        result = handler._show_notification(
            "Test Title",
            "Test Message",
            "dialog-information",
        )

        assert result is True
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert "notify-send" in call_args
        assert "Test Title" in call_args
        assert "Test Message" in call_args

    @patch('scribe.notifications.subprocess.run')
    @patch('scribe.notifications.shutil.which')
    def test_notify_recording_started(self, mock_which, mock_run):
        """Test recording started notification."""
        mock_which.side_effect = lambda x: "/usr/bin/notify-send" if x == "notify-send" else None
        mock_run.return_value = MagicMock(returncode=0)

        handler = NotificationHandler(show_notification=True, play_bell=False)

        handler.notify_recording_started()

        # Should have called notification
        assert mock_run.called

    @patch('scribe.notifications.subprocess.run')
    @patch('scribe.notifications.shutil.which')
    def test_notify_error(self, mock_which, mock_run):
        """Test error notification."""
        mock_which.side_effect = lambda x: "/usr/bin/notify-send" if x == "notify-send" else None
        mock_run.return_value = MagicMock(returncode=0)

        handler = NotificationHandler(show_notification=True)

        handler.notify_error("Test error message")

        # Should have called notification with critical urgency
        call_args = str(mock_run.call_args)
        assert "critical" in call_args or "Test error message" in call_args

    def test_get_system_bell_sound(self):
        """Test getting system bell sound."""
        handler = NotificationHandler()

        with patch('pathlib.Path.exists') as mock_exists:
            mock_exists.side_effect = lambda: True

            sound = handler._get_system_bell_sound()

            # Should return a Path object or None
            assert sound is None or isinstance(sound, Path)

    @patch('scribe.notifications.subprocess.Popen')
    @patch('scribe.notifications.shutil.which')
    def test_play_bell_with_paplay(self, mock_which, mock_popen):
        """Test playing bell with paplay."""
        def which_side_effect(cmd):
            if cmd == "paplay":
                return "/usr/bin/paplay"
            return None

        mock_which.side_effect = which_side_effect
        mock_popen.return_value = MagicMock()

        handler = NotificationHandler(play_bell=True, bell_sound="system")

        with patch.object(handler, '_get_system_bell_sound') as mock_get_sound:
            mock_get_sound.return_value = Path("/usr/share/sounds/bell.ogg")

            result = handler._play_bell()

            # Should have tried to play sound
            assert result is True or mock_popen.called

    @patch('builtins.print')
    @patch('scribe.notifications.shutil.which')
    def test_play_bell_fallback(self, mock_which, mock_print):
        """Test bell fallback to terminal bell."""
        mock_which.return_value = None  # No audio tools

        handler = NotificationHandler(play_bell=True)

        result = handler._play_bell()

        # Should fall back to terminal bell
        assert mock_print.called

    def test_notification_disabled(self):
        """Test that notifications are skipped when disabled."""
        handler = NotificationHandler(show_notification=False)

        with patch.object(handler, '_show_notification') as mock_show:
            handler.notify_recording_started()

            # Should not call _show_notification
            mock_show.assert_not_called()

    def test_bell_disabled(self):
        """Test that bell is skipped when disabled."""
        handler = NotificationHandler(play_bell=False)

        with patch.object(handler, '_play_bell') as mock_play:
            handler.notify_recording_started()

            # Should not call _play_bell
            mock_play.assert_not_called()
