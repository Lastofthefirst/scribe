"""Text output handling for Scribe (typing and clipboard)."""

import logging
import subprocess
import time
import shutil
from typing import Optional
import pyperclip

logger = logging.getLogger(__name__)


class OutputHandler:
    """Handles text output via typing or clipboard."""

    def __init__(
        self,
        mode: str = "type",
        typing_delay: float = 0.0,
        auto_enter: bool = False,
    ):
        """Initialize output handler.

        Args:
            mode: Output mode ("type" or "clipboard").
            typing_delay: Delay between characters when typing (seconds).
            auto_enter: Automatically press Enter after typing.
        """
        self.mode = mode
        self.typing_delay = typing_delay
        self.auto_enter = auto_enter

        # Detect available typing tools
        self.typing_tool = self._detect_typing_tool()

        # Window ID for typing (captured before notifications)
        self.target_window_id = None
        self.target_window_name = None

        logger.info(f"OutputHandler initialized: mode={mode}, tool={self.typing_tool}")

    def _detect_typing_tool(self) -> Optional[str]:
        """Detect available typing tool based on display server.

        Priority order:
        - Wayland: dotool > kdotool > ydotool > wtype
        - X11: xdotool

        Returns:
            Name of available tool, or None if none found.
        """
        import os

        # Detect display server
        session_type = os.environ.get("XDG_SESSION_TYPE", "").lower()
        wayland_display = os.environ.get("WAYLAND_DISPLAY", "")

        is_wayland = session_type == "wayland" or wayland_display
        is_x11 = session_type == "x11" or os.environ.get("DISPLAY", "")

        logger.debug(f"Display server detection: XDG_SESSION_TYPE={session_type}, is_wayland={is_wayland}, is_x11={is_x11}")

        if is_wayland:
            # Wayland tools (in priority order)

            # dotool: Best for Wayland, no daemon needed, works everywhere
            if shutil.which("dotool"):
                logger.info("Found dotool (Wayland - recommended)")
                return "dotool"

            # kdotool: KDE-specific, uses KWin DBus
            if shutil.which("kdotool"):
                logger.info("Found kdotool (Wayland/KDE)")
                return "kdotool"

            # ydotool: Universal but requires daemon
            if shutil.which("ydotool"):
                logger.info("Found ydotool (Wayland)")
                return "ydotool"

            # wtype: Only works with wlroots (sway), NOT KDE/GNOME
            if shutil.which("wtype"):
                logger.warning("Found wtype (only works with wlroots compositors like sway, NOT KDE/GNOME)")
                return "wtype"

            # Fallback to xdotool on Wayland (works via XWayland)
            if shutil.which("xdotool"):
                logger.info("Found xdotool (works on Wayland via XWayland)")
                return "xdotool"

            logger.warning("No typing tool found for Wayland")
            return None

        elif is_x11:
            # X11 tool
            if shutil.which("xdotool"):
                logger.info("Found xdotool (X11)")
                return "xdotool"

            logger.warning("No X11 typing tool found (xdotool recommended)")
            return None

        else:
            # Unknown/fallback - try all
            logger.warning("Could not detect display server type, trying all tools...")

            for tool in ["dotool", "kdotool", "xdotool", "ydotool", "wtype"]:
                if shutil.which(tool):
                    logger.info(f"Found {tool} (fallback detection)")
                    return tool

            logger.error("No typing tool found")
            return None

    def capture_target_window(self):
        """Capture the currently focused window for later typing.

        This should be called BEFORE any notifications are shown,
        to ensure we capture the window where the user wants text typed.
        """
        if self.typing_tool != "xdotool":
            # Only xdotool supports explicit window targeting
            logger.debug("Window capture only supported for xdotool")
            return

        try:
            # Get window with keyboard focus
            result = subprocess.run(
                ["xdotool", "getwindowfocus"],
                capture_output=True,
                text=True,
                timeout=1,
            )
            if result.returncode == 0:
                self.target_window_id = result.stdout.strip()
                logger.info(f"Captured target window ID: {self.target_window_id}")

                # Get window name for logging
                result = subprocess.run(
                    ["xdotool", "getwindowname", self.target_window_id],
                    capture_output=True,
                    text=True,
                    timeout=1,
                )
                if result.returncode == 0:
                    self.target_window_name = result.stdout.strip()
                    logger.info(f"Target window name: '{self.target_window_name}'")
            else:
                logger.warning(f"Failed to capture window: {result.stderr}")
        except Exception as e:
            logger.warning(f"Error capturing target window: {e}")

    def output(self, text: str) -> bool:
        """Output text using configured mode.

        Args:
            text: Text to output.

        Returns:
            True if successful, False otherwise.
        """
        if not text:
            logger.warning("Empty text provided, nothing to output")
            return False

        if self.mode == "clipboard":
            return self._to_clipboard(text)
        elif self.mode == "type":
            return self._type_text(text)
        else:
            logger.error(f"Unknown output mode: {self.mode}")
            return False

    def _to_clipboard(self, text: str) -> bool:
        """Copy text to clipboard.

        Args:
            text: Text to copy.

        Returns:
            True if successful, False otherwise.
        """
        try:
            pyperclip.copy(text)
            logger.info(f"Text copied to clipboard ({len(text)} chars)")
            return True
        except Exception as e:
            logger.error(f"Failed to copy to clipboard: {e}")
            return False

    def _type_text(self, text: str) -> bool:
        """Type text at cursor position.

        Args:
            text: Text to type.

        Returns:
            True if successful, False otherwise.
        """
        if not self.typing_tool:
            logger.error("No typing tool available, falling back to clipboard")
            return self._to_clipboard(text)

        try:
            if self.typing_tool == "dotool":
                return self._type_with_dotool(text)
            elif self.typing_tool == "kdotool":
                return self._type_with_kdotool(text)
            elif self.typing_tool == "xdotool":
                return self._type_with_xdotool(text)
            elif self.typing_tool == "ydotool":
                return self._type_with_ydotool(text)
            elif self.typing_tool == "wtype":
                return self._type_with_wtype(text)
            else:
                logger.error(f"Unknown typing tool: {self.typing_tool}")
                return False

        except Exception as e:
            logger.error(f"Failed to type text: {e}")
            return False

    def _type_with_xdotool(self, text: str) -> bool:
        """Type text using xdotool (X11).

        Args:
            text: Text to type.

        Returns:
            True if successful, False otherwise.
        """
        try:
            logger.info(f"Attempting to type {len(text)} characters with xdotool")
            logger.debug(f"Text to type: '{text[:50]}...'")

            # Use the pre-captured target window if available
            if self.target_window_id:
                logger.info(f"Using pre-captured window: ID={self.target_window_id}, name='{self.target_window_name}'")
                window_id = self.target_window_id
            else:
                # Fallback: try to detect window now (less reliable)
                logger.warning("No pre-captured window, attempting to detect current window")
                try:
                    result = subprocess.run(
                        ["xdotool", "getwindowfocus"],
                        capture_output=True,
                        text=True,
                        timeout=1,
                    )
                    if result.returncode == 0:
                        window_id = result.stdout.strip()
                        logger.debug(f"Detected window ID: {window_id}")
                    else:
                        logger.error("Could not detect any window for typing")
                        return False
                except Exception as e:
                    logger.error(f"Error detecting window: {e}")
                    return False

            # Wait for notifications to clear (reduced from 1.0s for faster typing)
            logger.debug("Waiting 0.6s for notifications to clear...")
            time.sleep(0.6)

            # Activate the target window (not just focus - this sends real events)
            # windowactivate switches desktops if needed and avoids synthetic event rejection
            try:
                logger.info(f"Activating window {window_id}")
                result = subprocess.run(
                    ["xdotool", "windowactivate", "--sync", window_id],
                    capture_output=True,
                    text=True,
                    timeout=2,
                )
                if result.returncode != 0:
                    logger.error(f"Could not activate window: {result.stderr}")
                    return False
                else:
                    logger.info("Window activated successfully")
                    # Longer delay to ensure window is ready to receive input
                    time.sleep(0.5)
            except Exception as e:
                logger.error(f"Error activating window: {e}")
                return False

            if self.typing_delay > 0:
                # Type with delay (gradual appearance)
                logger.debug(f"Typing with delay: {self.typing_delay}s per character")
                for i, char in enumerate(text):
                    result = subprocess.run(
                        ["xdotool", "type", "--clearmodifiers", "--", char],
                        capture_output=True,
                        text=True,
                    )
                    if result.returncode != 0:
                        logger.error(f"xdotool failed at char {i}: {result.stderr}")
                        return False
                    time.sleep(self.typing_delay)
            else:
                # Type all at once with clearmodifiers to avoid stuck keys
                logger.debug("Typing all text at once")
                result = subprocess.run(
                    ["xdotool", "type", "--clearmodifiers", "--", text],
                    capture_output=True,
                    text=True,
                )

                if result.returncode != 0:
                    logger.error(f"xdotool failed: {result.stderr}")
                    return False

                if result.stderr:
                    logger.warning(f"xdotool stderr: {result.stderr}")

            # Press Enter if requested
            if self.auto_enter:
                logger.debug("Pressing Enter key")
                result = subprocess.run(
                    ["xdotool", "key", "Return"],
                    capture_output=True,
                    text=True,
                )
                if result.returncode != 0:
                    logger.error(f"xdotool Enter failed: {result.stderr}")
                    return False

            logger.info(f"Text typed successfully with xdotool ({len(text)} chars)")
            return True

        except subprocess.CalledProcessError as e:
            logger.error(f"xdotool error: {e.stderr.decode() if e.stderr else str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error in xdotool typing: {e}", exc_info=True)
            return False

    def _type_with_dotool(self, text: str) -> bool:
        """Type text using dotool (Wayland).

        dotool reads commands from stdin and simulates input using uinput.
        Works on Wayland, X11, and even TTYs. No daemon needed.

        Args:
            text: Text to type.

        Returns:
            True if successful, False otherwise.
        """
        try:
            logger.info(f"Attempting to type {len(text)} characters with dotool")
            logger.debug(f"Text to type: '{text[:50]}...'")

            # Wait for notifications to clear (reduced from 1.0s for faster typing)
            logger.debug("Waiting 0.6s for notifications to clear...")
            time.sleep(0.6)

            if self.typing_delay > 0:
                # Type with delay (gradual appearance)
                logger.debug(f"Typing with delay: {self.typing_delay}s per character")
                for char in text:
                    # dotool reads from stdin: "type X" for each character
                    result = subprocess.run(
                        ["dotool"],
                        input=f"type {char}",
                        capture_output=True,
                        text=True,
                    )
                    if result.returncode != 0:
                        logger.error(f"dotool failed: {result.stderr}")
                        return False
                    time.sleep(self.typing_delay)
            else:
                # Type all at once - dotool command: "type text here"
                logger.debug("Typing all text at once")
                result = subprocess.run(
                    ["dotool"],
                    input=f"type {text}",
                    capture_output=True,
                    text=True,
                )

                if result.returncode != 0:
                    logger.error(f"dotool failed: {result.stderr}")
                    return False

                if result.stderr:
                    logger.warning(f"dotool stderr: {result.stderr}")

            # Press Enter if requested
            if self.auto_enter:
                logger.debug("Pressing Enter key")
                result = subprocess.run(
                    ["dotool"],
                    input="key enter",
                    capture_output=True,
                    text=True,
                )
                if result.returncode != 0:
                    logger.error(f"dotool Enter failed: {result.stderr}")
                    return False

            logger.info(f"Text typed successfully with dotool ({len(text)} chars)")
            return True

        except subprocess.CalledProcessError as e:
            logger.error(f"dotool error: {e.stderr.decode() if e.stderr else str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error in dotool typing: {e}", exc_info=True)
            return False

    def _type_with_kdotool(self, text: str) -> bool:
        """Type text using kdotool (Wayland/KDE).

        kdotool uses KWin's DBus interface for window management and typing.
        Works only on KDE Plasma (both X11 and Wayland).

        Args:
            text: Text to type.

        Returns:
            True if successful, False otherwise.
        """
        try:
            logger.info(f"Attempting to type {len(text)} characters with kdotool")
            logger.debug(f"Text to type: '{text[:50]}...'")

            # Wait for notifications to clear (reduced from 1.0s for faster typing)
            logger.debug("Waiting 0.6s for notifications to clear...")
            time.sleep(0.6)

            if self.typing_delay > 0:
                # Type with delay (gradual appearance)
                logger.debug(f"Typing with delay: {self.typing_delay}s per character")
                for char in text:
                    result = subprocess.run(
                        ["kdotool", "type", char],
                        capture_output=True,
                        text=True,
                    )
                    if result.returncode != 0:
                        logger.error(f"kdotool failed: {result.stderr}")
                        return False
                    time.sleep(self.typing_delay)
            else:
                # Type all at once
                logger.debug("Typing all text at once")
                result = subprocess.run(
                    ["kdotool", "type", text],
                    capture_output=True,
                    text=True,
                )

                if result.returncode != 0:
                    logger.error(f"kdotool failed: {result.stderr}")
                    return False

                if result.stderr:
                    logger.warning(f"kdotool stderr: {result.stderr}")

            # Press Enter if requested
            if self.auto_enter:
                logger.debug("Pressing Enter key")
                result = subprocess.run(
                    ["kdotool", "key", "Return"],
                    capture_output=True,
                    text=True,
                )
                if result.returncode != 0:
                    logger.error(f"kdotool Enter failed: {result.stderr}")
                    return False

            logger.info(f"Text typed successfully with kdotool ({len(text)} chars)")
            return True

        except subprocess.CalledProcessError as e:
            logger.error(f"kdotool error: {e.stderr.decode() if e.stderr else str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error in kdotool typing: {e}", exc_info=True)
            return False

    def _type_with_ydotool(self, text: str) -> bool:
        """Type text using ydotool (Wayland).

        Args:
            text: Text to type.

        Returns:
            True if successful, False otherwise.
        """
        try:
            # Small delay to ensure focus is correct
            time.sleep(0.1)

            if self.typing_delay > 0:
                # Type with delay (gradual appearance)
                for char in text:
                    subprocess.run(
                        ["ydotool", "type", char],
                        check=True,
                        capture_output=True,
                    )
                    time.sleep(self.typing_delay)
            else:
                # Type all at once
                subprocess.run(
                    ["ydotool", "type", text],
                    check=True,
                    capture_output=True,
                )

            # Press Enter if requested
            if self.auto_enter:
                subprocess.run(
                    ["ydotool", "key", "28:1", "28:0"],  # Enter key
                    check=True,
                    capture_output=True,
                )

            logger.info(f"Text typed successfully with ydotool ({len(text)} chars)")
            return True

        except subprocess.CalledProcessError as e:
            logger.error(f"ydotool error: {e.stderr.decode()}")
            return False

    def _type_with_wtype(self, text: str) -> bool:
        """Type text using wtype (Wayland).

        Args:
            text: Text to type.

        Returns:
            True if successful, False otherwise.
        """
        try:
            # Small delay to ensure focus is correct
            time.sleep(0.1)

            if self.typing_delay > 0:
                # Type with delay (gradual appearance)
                for char in text:
                    subprocess.run(
                        ["wtype", char],
                        check=True,
                        capture_output=True,
                    )
                    time.sleep(self.typing_delay)
            else:
                # Type all at once
                subprocess.run(
                    ["wtype", text],
                    check=True,
                    capture_output=True,
                )

            # Press Enter if requested
            if self.auto_enter:
                subprocess.run(
                    ["wtype", "-k", "Return"],
                    check=True,
                    capture_output=True,
                )

            logger.info(f"Text typed successfully with wtype ({len(text)} chars)")
            return True

        except subprocess.CalledProcessError as e:
            logger.error(f"wtype error: {e.stderr.decode()}")
            return False

    def type_gradually(self, text: str, delay: float = 0.01) -> bool:
        """Type text with gradual appearance effect.

        Args:
            text: Text to type.
            delay: Delay between characters (seconds).

        Returns:
            True if successful, False otherwise.
        """
        original_delay = self.typing_delay
        self.typing_delay = delay
        result = self._type_text(text)
        self.typing_delay = original_delay
        return result

    def get_clipboard_content(self) -> str:
        """Get current clipboard content.

        Returns:
            Clipboard text, or empty string if error.
        """
        try:
            return pyperclip.paste()
        except Exception as e:
            logger.error(f"Failed to get clipboard content: {e}")
            return ""
