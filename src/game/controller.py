"""Controls the Hearts of Iron IV game process.

Provides methods to launch HOI4, send console commands, and manage the
game lifecycle.  Console automation uses platform-specific input backends
(xdotool on Linux, AppleScript on macOS, pyautogui on Windows).
"""

from __future__ import annotations

import logging
import os
import subprocess
from pathlib import Path

from src.game.input_backends import InputBackend, get_input_backend

logger = logging.getLogger(__name__)

# Default launch flags -- keeps the game quiet and debug-friendly.
DEFAULT_LAUNCH_FLAGS = ["-debug", "-nolog", "-nomusic", "-nosound"]


class GameController:
    """Manages the HOI4 process and sends console commands.

    Parameters
    ----------
    executable : Path
        Path to the HOI4 binary.
    use_xvfb : bool
        If ``True``, set ``DISPLAY=:99`` so the game runs inside a virtual
        framebuffer (headless server mode).  Only relevant on Linux.
    """

    def __init__(self, executable: Path, use_xvfb: bool = False) -> None:
        self.executable = executable
        self.use_xvfb = use_xvfb
        self._process: subprocess.Popen | None = None  # type: ignore[type-arg]
        self._backend: InputBackend = get_input_backend(use_xvfb=use_xvfb)

    # ── Lifecycle ─────────────────────────────────────────────────────

    def launch(self) -> bool:
        """Start the HOI4 process.

        Returns ``True`` on success, ``False`` if the executable cannot be
        found or fails to start.  Never raises on a missing binary -- logs a
        warning instead so the orchestrator can proceed with a manually
        launched game.
        """
        if not self.executable.exists():
            logger.warning(
                "HOI4 executable not found at %s -- "
                "launch the game manually and the orchestrator will still work.",
                self.executable,
            )
            return False

        env = os.environ.copy()
        if self.use_xvfb:
            env["DISPLAY"] = ":99"
            logger.info("Using Xvfb display :99")

        cmd = [str(self.executable)] + DEFAULT_LAUNCH_FLAGS
        logger.info("Launching HOI4: %s", " ".join(cmd))

        try:
            self._process = subprocess.Popen(
                cmd,
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            logger.info("HOI4 started with PID %d", self._process.pid)
            return True
        except OSError as exc:
            logger.warning("Failed to launch HOI4: %s", exc)
            return False

    def is_running(self) -> bool:
        """Return ``True`` if the managed HOI4 process is still alive."""
        if self._process is None:
            return False
        return self._process.poll() is None

    def stop(self) -> None:
        """Terminate the HOI4 process if it is running."""
        if self._process is not None and self.is_running():
            logger.info("Terminating HOI4 (PID %d)", self._process.pid)
            self._process.terminate()
            try:
                self._process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                logger.warning("HOI4 did not exit in time -- killing")
                self._process.kill()

    # ── Console commands ──────────────────────────────────────────────

    def send_console_command(self, cmd: str) -> bool:
        """Type *cmd* into the HOI4 debug console.

        Uses the platform-specific input backend (xdotool / AppleScript /
        pyautogui) to open the console, type the command, and close it.

        Returns ``True`` on success.
        """
        return self._backend.send_console_command(cmd)

    # ── Convenience wrappers ──────────────────────────────────────────

    def enter_observer_mode(self) -> bool:
        """Switch the game to observer mode."""
        logger.info("Entering observer mode")
        return self.send_console_command("observe")

    def reload_files(self) -> bool:
        """Reload strategy files in-game."""
        logger.info("Reloading strategy files")
        return self.send_console_command("reload")

    def set_speed(self, speed: int) -> bool:
        """Set the game speed (1-5)."""
        speed = max(1, min(5, speed))
        logger.info("Setting game speed to %d", speed)
        return self.send_console_command(f"speed {speed}")
