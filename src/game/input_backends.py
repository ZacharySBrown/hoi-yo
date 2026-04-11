"""Platform-specific input backends for HOI4 console automation.

Each backend implements the same interface for sending keystrokes to the
HOI4 debug console.  The correct backend is selected automatically based
on ``sys.platform``.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
import time
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

_KEYSTROKE_DELAY = 0.05  # seconds between typed characters
_CONSOLE_SETTLE = 0.3    # seconds to wait after opening/closing console


class InputBackend(ABC):
    """Abstract interface for sending commands to the HOI4 debug console."""

    @abstractmethod
    def send_console_command(self, cmd: str) -> bool:
        """Open console, type *cmd*, press Enter, close console.

        Returns ``True`` on success.
        """

    @abstractmethod
    def focus_game_window(self) -> bool:
        """Bring the HOI4 window to the foreground.

        Returns ``True`` if the window was found and focused.
        """


# ── Windows ──────────────────────────────────────────────────────────


class WindowsInputBackend(InputBackend):
    """Uses pyautogui + pygetwindow to send keystrokes on Windows."""

    def focus_game_window(self) -> bool:
        try:
            import pygetwindow as gw  # type: ignore[import-untyped]
        except ImportError:
            logger.warning("pygetwindow not installed -- cannot focus HOI4 window")
            return False

        windows = gw.getWindowsWithTitle("Hearts of Iron IV")
        if not windows:
            logger.warning("HOI4 window not found")
            return False

        win = windows[0]
        try:
            if win.isMinimized:
                win.restore()
            win.activate()
            time.sleep(0.3)
            return True
        except Exception as exc:
            logger.warning("Failed to focus HOI4 window: %s", exc)
            return False

    def send_console_command(self, cmd: str) -> bool:
        try:
            import pyautogui  # type: ignore[import-untyped]
        except ImportError:
            logger.warning("pyautogui not installed -- cannot send console commands on Windows")
            return False

        if not self.focus_game_window():
            logger.warning("Cannot send command without game window focus: %s", cmd)
            return False

        try:
            # Open console (grave/backtick key)
            pyautogui.press("`")
            time.sleep(_CONSOLE_SETTLE)

            # Type the command character by character
            pyautogui.typewrite(cmd, interval=_KEYSTROKE_DELAY)
            time.sleep(_CONSOLE_SETTLE)

            # Execute
            pyautogui.press("enter")
            time.sleep(_CONSOLE_SETTLE)

            # Close console
            pyautogui.press("`")

            logger.debug("Sent console command (Windows): %s", cmd)
            return True
        except Exception as exc:
            logger.warning("Failed to send console command '%s': %s", cmd, exc)
            return False


# ── macOS ────────────────────────────────────────────────────────────


class MacOSInputBackend(InputBackend):
    """Uses AppleScript via osascript to send keystrokes on macOS."""

    def focus_game_window(self) -> bool:
        script = '''
        tell application "System Events"
            set procs to (name of every process whose name contains "hoi4")
            if (count of procs) > 0 then
                tell process (item 1 of procs)
                    set frontmost to true
                end tell
                return true
            end if
        end tell
        return false
        '''
        try:
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True, text=True, timeout=5,
            )
            return result.returncode == 0
        except (subprocess.SubprocessError, OSError):
            return False

    def send_console_command(self, cmd: str) -> bool:
        # Escape any quotes in the command for AppleScript
        safe_cmd = cmd.replace('"', '\\"')
        script = f'''
        tell application "System Events"
            set procs to (name of every process whose name contains "hoi4")
            if (count of procs) = 0 then
                return false
            end if
            tell process (item 1 of procs)
                set frontmost to true
                delay 0.3
                keystroke "`"
                delay 0.3
                keystroke "{safe_cmd}"
                delay 0.2
                key code 36
                delay 0.3
                keystroke "`"
            end tell
        end tell
        '''
        try:
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True, text=True, timeout=15,
            )
            if result.returncode == 0:
                logger.debug("Sent console command (macOS): %s", cmd)
                return True
            logger.warning("AppleScript failed: %s", result.stderr.strip())
            return False
        except (subprocess.SubprocessError, OSError) as exc:
            logger.warning("Failed to send console command '%s': %s", cmd, exc)
            return False


# ── Linux ────────────────────────────────────────────────────────────


class LinuxInputBackend(InputBackend):
    """Uses xdotool to send keystrokes on Linux."""

    _XDOTOOL_DELAY_MS = 50

    def __init__(self, use_xvfb: bool = False, display: str = ":99") -> None:
        self.use_xvfb = use_xvfb
        self.display = display

    def _env(self) -> dict[str, str]:
        env = os.environ.copy()
        if self.use_xvfb:
            env["DISPLAY"] = self.display
        return env

    def focus_game_window(self) -> bool:
        if not shutil.which("xdotool"):
            return False
        try:
            result = subprocess.run(
                ["xdotool", "search", "--name", "Hearts of Iron IV"],
                capture_output=True, text=True, env=self._env(), timeout=5,
            )
            if result.returncode == 0 and result.stdout.strip():
                wid = result.stdout.strip().splitlines()[0]
                subprocess.run(
                    ["xdotool", "windowactivate", wid],
                    env=self._env(), timeout=5,
                )
                return True
            return False
        except (subprocess.SubprocessError, OSError):
            return False

    def send_console_command(self, cmd: str) -> bool:
        if not shutil.which("xdotool"):
            logger.warning("xdotool not found -- cannot send console command: %s", cmd)
            return False

        env = self._env()

        try:
            subprocess.run(
                ["xdotool", "key", "grave"],
                env=env, check=True, timeout=5,
            )
            time.sleep(_CONSOLE_SETTLE)

            subprocess.run(
                ["xdotool", "type", "--delay", str(self._XDOTOOL_DELAY_MS), cmd],
                env=env, check=True, timeout=10,
            )
            time.sleep(_CONSOLE_SETTLE)

            subprocess.run(
                ["xdotool", "key", "Return"],
                env=env, check=True, timeout=5,
            )
            time.sleep(_CONSOLE_SETTLE)

            subprocess.run(
                ["xdotool", "key", "grave"],
                env=env, check=True, timeout=5,
            )

            logger.debug("Sent console command (Linux): %s", cmd)
            return True
        except (subprocess.SubprocessError, OSError) as exc:
            logger.warning("Failed to send console command '%s': %s", cmd, exc)
            return False


# ── Factory ──────────────────────────────────────────────────────────


def get_input_backend(use_xvfb: bool = False) -> InputBackend:
    """Return the correct input backend for the current platform."""
    if sys.platform == "win32":
        return WindowsInputBackend()
    elif sys.platform == "darwin":
        return MacOSInputBackend()
    else:
        return LinuxInputBackend(use_xvfb=use_xvfb)
