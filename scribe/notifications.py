"""Notification and sound handling for Scribe."""

import logging
import subprocess
import shutil
from typing import Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class NotificationHandler:
    """Handles desktop notifications and audio alerts."""

    def __init__(
        self,
        show_notification: bool = True,
        play_bell: bool = True,
        bell_sound: str = "system",
        notification_timeout: int = 3000,
    ):
        """Initialize notification handler.

        Args:
            show_notification: Whether to show desktop notifications.
            play_bell: Whether to play bell sound.
            bell_sound: Bell sound to play ("system" or path to audio file).
            notification_timeout: Notification timeout in milliseconds.
        """
        self.show_notification = show_notification
        self.play_bell = play_bell
        self.bell_sound = bell_sound
        self.notification_timeout = notification_timeout

        # Detect available tools
        self.notify_tool = self._detect_notify_tool()
        self.audio_tool = self._detect_audio_tool()

        logger.info(
            f"NotificationHandler initialized: "
            f"notify={self.notify_tool}, audio={self.audio_tool}"
        )

    def _detect_notify_tool(self) -> Optional[str]:
        """Detect available notification tool.

        Returns:
            Name of available tool, or None if none found.
        """
        # Try notify-send (most common on Linux)
        if shutil.which("notify-send"):
            return "notify-send"

        # Try kdialog (KDE)
        if shutil.which("kdialog"):
            return "kdialog"

        # Try zenity (GNOME)
        if shutil.which("zenity"):
            return "zenity"

        logger.warning("No notification tool found")
        return None

    def _detect_audio_tool(self) -> Optional[str]:
        """Detect available audio playback tool.

        Returns:
            Name of available tool, or None if none found.
        """
        # Try paplay (PulseAudio)
        if shutil.which("paplay"):
            return "paplay"

        # Try aplay (ALSA)
        if shutil.which("aplay"):
            return "aplay"

        # Try ffplay (FFmpeg)
        if shutil.which("ffplay"):
            return "ffplay"

        # Try mpv
        if shutil.which("mpv"):
            return "mpv"

        logger.warning("No audio playback tool found")
        return None

    def notify_recording_started(self):
        """Show notification and play bell when recording starts."""
        if self.show_notification:
            self._show_notification(
                "Scribe Recording",
                "Listening... (speak now)",
                "audio-input-microphone",
            )

        if self.play_bell:
            self._play_bell()

    def notify_recording_stopped(self):
        """Show notification when recording stops."""
        if self.show_notification:
            self._show_notification(
                "Scribe Processing",
                "Processing audio...",
                "audio-input-microphone",
            )

    def notify_transcription_complete(self, text: str):
        """Show notification when transcription is complete.

        Args:
            text: Transcribed text (will be truncated if too long).
        """
        if self.show_notification:
            # Truncate text for notification
            preview = text[:100] + "..." if len(text) > 100 else text
            self._show_notification(
                "Scribe Complete",
                f"Transcribed: {preview}",
                "dialog-information",
            )

    def notify_error(self, error_message: str):
        """Show error notification.

        Args:
            error_message: Error message to display.
        """
        if self.show_notification:
            self._show_notification(
                "Scribe Error",
                error_message,
                "dialog-error",
                urgency="critical",
            )

    def _show_notification(
        self,
        title: str,
        message: str,
        icon: str = "dialog-information",
        urgency: str = "normal",
    ) -> bool:
        """Show desktop notification.

        Args:
            title: Notification title.
            message: Notification message.
            icon: Icon name or path.
            urgency: Urgency level ("low", "normal", "critical").

        Returns:
            True if successful, False otherwise.
        """
        if not self.notify_tool:
            logger.debug("No notification tool available, skipping notification")
            return False

        try:
            if self.notify_tool == "notify-send":
                return self._notify_with_notify_send(title, message, icon, urgency)
            elif self.notify_tool == "kdialog":
                return self._notify_with_kdialog(title, message, icon)
            elif self.notify_tool == "zenity":
                return self._notify_with_zenity(title, message, icon)
            else:
                logger.warning(f"Unknown notification tool: {self.notify_tool}")
                return False

        except Exception as e:
            logger.error(f"Failed to show notification: {e}")
            return False

    def _notify_with_notify_send(
        self,
        title: str,
        message: str,
        icon: str,
        urgency: str,
    ) -> bool:
        """Show notification using notify-send.

        Args:
            title: Notification title.
            message: Notification message.
            icon: Icon name.
            urgency: Urgency level.

        Returns:
            True if successful, False otherwise.
        """
        cmd = [
            "notify-send",
            "-a", "Scribe",
            "-i", icon,
            "-u", urgency,
            "-t", str(self.notification_timeout),
            title,
            message,
        ]

        try:
            subprocess.run(cmd, check=True, capture_output=True)
            logger.debug(f"Notification shown: {title}")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"notify-send error: {e.stderr.decode()}")
            return False

    def _notify_with_kdialog(self, title: str, message: str, icon: str) -> bool:
        """Show notification using kdialog (KDE).

        Args:
            title: Notification title.
            message: Notification message.
            icon: Icon name.

        Returns:
            True if successful, False otherwise.
        """
        cmd = [
            "kdialog",
            "--passivepopup", message,
            str(self.notification_timeout // 1000),
            "--title", title,
            "--icon", icon,
        ]

        try:
            subprocess.run(cmd, check=True, capture_output=True)
            logger.debug(f"KDE notification shown: {title}")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"kdialog error: {e.stderr.decode()}")
            return False

    def _notify_with_zenity(self, title: str, message: str, icon: str) -> bool:
        """Show notification using zenity (GNOME).

        Args:
            title: Notification title.
            message: Notification message.
            icon: Icon name.

        Returns:
            True if successful, False otherwise.
        """
        cmd = [
            "zenity",
            "--notification",
            "--text", f"{title}\n{message}",
            "--timeout", str(self.notification_timeout // 1000),
        ]

        try:
            subprocess.run(cmd, check=True, capture_output=True)
            logger.debug(f"Zenity notification shown: {title}")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"zenity error: {e.stderr.decode()}")
            return False

    def _play_bell(self) -> bool:
        """Play bell sound.

        Returns:
            True if successful, False otherwise.
        """
        if not self.audio_tool:
            logger.debug("No audio tool available, using system beep")
            # Fallback to terminal bell
            print("\a", end="", flush=True)
            return True

        try:
            # Determine sound file
            if self.bell_sound == "system":
                sound_file = self._get_system_bell_sound()
            else:
                sound_file = Path(self.bell_sound)

            if not sound_file or not sound_file.exists():
                logger.warning(f"Bell sound not found: {sound_file}, using terminal bell")
                print("\a", end="", flush=True)
                return True

            # Play sound
            if self.audio_tool == "paplay":
                return self._play_with_paplay(sound_file)
            elif self.audio_tool == "aplay":
                return self._play_with_aplay(sound_file)
            elif self.audio_tool == "ffplay":
                return self._play_with_ffplay(sound_file)
            elif self.audio_tool == "mpv":
                return self._play_with_mpv(sound_file)

        except Exception as e:
            logger.error(f"Failed to play bell: {e}")
            print("\a", end="", flush=True)  # Fallback to terminal bell
            return False

    def _get_system_bell_sound(self) -> Optional[Path]:
        """Get system bell sound file.

        Returns:
            Path to system bell sound, or None if not found.
        """
        # Common system sound locations
        sound_paths = [
            "/usr/share/sounds/freedesktop/stereo/bell.oga",
            "/usr/share/sounds/freedesktop/stereo/message.oga",
            "/usr/share/sounds/ubuntu/stereo/bell.ogg",
            "/usr/share/sounds/sound-icons/trumpet-12.wav",
            "/usr/share/sounds/KDE-Im-Message-In.ogg",
        ]

        for path in sound_paths:
            p = Path(path)
            if p.exists():
                return p

        return None

    def _play_with_paplay(self, sound_file: Path) -> bool:
        """Play sound with paplay (PulseAudio).

        Args:
            sound_file: Path to sound file.

        Returns:
            True if successful, False otherwise.
        """
        try:
            subprocess.Popen(
                ["paplay", str(sound_file)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return True
        except Exception as e:
            logger.error(f"paplay error: {e}")
            return False

    def _play_with_aplay(self, sound_file: Path) -> bool:
        """Play sound with aplay (ALSA).

        Args:
            sound_file: Path to sound file.

        Returns:
            True if successful, False otherwise.
        """
        try:
            subprocess.Popen(
                ["aplay", "-q", str(sound_file)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return True
        except Exception as e:
            logger.error(f"aplay error: {e}")
            return False

    def _play_with_ffplay(self, sound_file: Path) -> bool:
        """Play sound with ffplay (FFmpeg).

        Args:
            sound_file: Path to sound file.

        Returns:
            True if successful, False otherwise.
        """
        try:
            subprocess.Popen(
                ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", str(sound_file)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return True
        except Exception as e:
            logger.error(f"ffplay error: {e}")
            return False

    def _play_with_mpv(self, sound_file: Path) -> bool:
        """Play sound with mpv.

        Args:
            sound_file: Path to sound file.

        Returns:
            True if successful, False otherwise.
        """
        try:
            subprocess.Popen(
                ["mpv", "--no-video", "--really-quiet", str(sound_file)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return True
        except Exception as e:
            logger.error(f"mpv error: {e}")
            return False
