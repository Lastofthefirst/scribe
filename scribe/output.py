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

        logger.info(f"OutputHandler initialized: mode={mode}, tool={self.typing_tool}")

    def _detect_typing_tool(self) -> Optional[str]:
        """Detect available typing tool (xdotool, ydotool, or wtype).

        Returns:
            Name of available tool, or None if none found.
        """
        # Try xdotool (X11)
        if shutil.which("xdotool"):
            logger.debug("Found xdotool (X11)")
            return "xdotool"

        # Try ydotool (Wayland)
        if shutil.which("ydotool"):
            logger.debug("Found ydotool (Wayland)")
            return "ydotool"

        # Try wtype (Wayland)
        if shutil.which("wtype"):
            logger.debug("Found wtype (Wayland)")
            return "wtype"

        logger.warning("No typing tool found (xdotool/ydotool/wtype)")
        return None

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
            if self.typing_tool == "xdotool":
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
            # Small delay to ensure focus is correct
            time.sleep(0.1)

            if self.typing_delay > 0:
                # Type with delay (gradual appearance)
                for char in text:
                    subprocess.run(
                        ["xdotool", "type", "--", char],
                        check=True,
                        capture_output=True,
                    )
                    time.sleep(self.typing_delay)
            else:
                # Type all at once
                subprocess.run(
                    ["xdotool", "type", "--", text],
                    check=True,
                    capture_output=True,
                )

            # Press Enter if requested
            if self.auto_enter:
                subprocess.run(
                    ["xdotool", "key", "Return"],
                    check=True,
                    capture_output=True,
                )

            logger.info(f"Text typed successfully with xdotool ({len(text)} chars)")
            return True

        except subprocess.CalledProcessError as e:
            logger.error(f"xdotool error: {e.stderr.decode()}")
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
