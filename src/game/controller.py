"""Controls the Hearts of Iron IV game process.

Provides methods to launch HOI4, send console commands via xdotool, and
manage the game lifecycle.  Falls back gracefully when the executable is
missing so the orchestrator can still run with a manually-launched game.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import time
from pathlib import Path

logger = logging.getLogger(__name__)

# Default launch flags -- keeps the game quiet and debug-friendly.
DEFAULT_LAUNCH_FLAGS = ["-debug", "-nolog", "-nomusic", "-nosound"]

# Delay between xdotool keystrokes to let the console catch up.
_XDOTOOL_DELAY_MS = 50
_CONSOLE_SETTLE_SECS = 0.3


class GameController:
    """Manages the HOI4 process and sends console commands.

    Parameters
    ----------
    executable : Path
        Path to the HOI4 binary.
    use_xvfb : bool
        If ``True``, set ``DISPLAY=:99`` so the game runs inside a virtual
        framebuffer (headless server mode).
    """

    def __init__(self, executable: Path, use_xvfb: bool = False) -> None:
        self.executable = executable
        self.use_xvfb = use_xvfb
        self._process: subprocess.Popen | None = None  # type: ignore[type-arg]

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
        """Type *cmd* into the HOI4 debug console via xdotool.

        Sequence: press grave (backtick) to open console -> type command ->
        press Return -> press grave again to close console.

        Returns ``True`` on success, ``False`` if xdotool is unavailable.
        """
        if not shutil.which("xdotool"):
            logger.warning("xdotool not found -- cannot send console command: %s", cmd)
            return False

        env = os.environ.copy()
        if self.use_xvfb:
            env["DISPLAY"] = ":99"

        try:
            # Open the console
            subprocess.run(
                ["xdotool", "key", "grave"],
                env=env,
                check=True,
                timeout=5,
            )
            time.sleep(_CONSOLE_SETTLE_SECS)

            # Type the command
            subprocess.run(
                ["xdotool", "type", "--delay", str(_XDOTOOL_DELAY_MS), cmd],
                env=env,
                check=True,
                timeout=10,
            )
            time.sleep(_CONSOLE_SETTLE_SECS)

            # Execute
            subprocess.run(
                ["xdotool", "key", "Return"],
                env=env,
                check=True,
                timeout=5,
            )
            time.sleep(_CONSOLE_SETTLE_SECS)

            # Close the console
            subprocess.run(
                ["xdotool", "key", "grave"],
                env=env,
                check=True,
                timeout=5,
            )

            logger.debug("Sent console command: %s", cmd)
            return True
        except (subprocess.SubprocessError, OSError) as exc:
            logger.warning("Failed to send console command '%s': %s", cmd, exc)
            return False

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
