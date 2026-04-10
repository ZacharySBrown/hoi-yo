"""Campaign runner -- manages HOI4 + orchestrator as a subprocess.

Only one campaign can run at a time. Starting a new one stops the old one.
"""

from __future__ import annotations

import asyncio
import logging
import os
import signal
import subprocess
import sys
from pathlib import Path

logger = logging.getLogger("hoi-yo.campaign")


class CampaignRunner:
    """Manages the lifecycle of a HOI4 campaign + orchestrator process."""

    def __init__(self, hoi4_binary: Path, save_dir: Path, mod_dir: Path, config_dir: Path):
        self.hoi4_binary = hoi4_binary
        self.save_dir = save_dir
        self.mod_dir = mod_dir
        self.config_dir = config_dir
        self._process: subprocess.Popen | None = None
        self._xvfb_process: subprocess.Popen | None = None
        self._campaign_id: str | None = None

    @property
    def is_running(self) -> bool:
        return self._process is not None and self._process.poll() is None

    @property
    def current_campaign_id(self) -> str | None:
        return self._campaign_id if self.is_running else None

    async def start(
        self,
        campaign_id: str,
        personas: dict[str, str],
        api_key: str,
        config_path: Path,
        speed: int = 4,
        display: int = 99,
    ) -> bool:
        """Start a new campaign.

        1. Stop any existing campaign
        2. Start Xvfb (if not on macOS)
        3. Launch HOI4 in headless observer mode
        4. Start the orchestrator subprocess

        Returns True if started successfully.
        """
        # Stop existing campaign if any
        if self.is_running:
            logger.info("Stopping existing campaign %s", self._campaign_id)
            await self.stop()

        self._campaign_id = campaign_id
        logger.info("Starting campaign %s", campaign_id)

        # Determine if we need Xvfb (Linux only)
        use_xvfb = sys.platform == "linux"

        if use_xvfb:
            logger.info("Starting Xvfb on display :%d", display)
            self._xvfb_process = subprocess.Popen(
                ["Xvfb", f":{display}", "-screen", "0", "1920x1080x24"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            os.environ["DISPLAY"] = f":{display}"
            await asyncio.sleep(1)  # Wait for Xvfb to start

        # Build persona overrides for CLI
        persona_args = []
        for tag, path in personas.items():
            persona_args.extend(["--persona", f"{tag}={path}"])

        # Build the orchestrator command
        cmd = [
            sys.executable, "-m", "src.cli",
            "--config", str(config_path),
            "run",
            "--headless" if use_xvfb else "--local",
            "--speed", str(speed),
            *persona_args,
        ]

        env = os.environ.copy()
        env["ANTHROPIC_API_KEY"] = api_key
        env["HOIYO_CAMPAIGN_ID"] = campaign_id

        logger.info("Launching orchestrator: %s", " ".join(cmd[:6]) + "...")

        try:
            self._process = subprocess.Popen(
                cmd,
                env=env,
                cwd=str(Path(__file__).parent.parent.parent),  # project root
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )
            logger.info("Orchestrator started (PID %d)", self._process.pid)
            return True
        except Exception:
            logger.exception("Failed to start orchestrator")
            self._campaign_id = None
            return False

    async def stop(self) -> None:
        """Stop the current campaign gracefully."""
        if self._process and self._process.poll() is None:
            logger.info("Stopping orchestrator (PID %d)", self._process.pid)
            # Send SIGTERM for graceful shutdown
            self._process.send_signal(signal.SIGTERM)
            try:
                self._process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                logger.warning("Orchestrator didn't stop in 15s, killing")
                self._process.kill()
                self._process.wait(timeout=5)

        if self._xvfb_process and self._xvfb_process.poll() is None:
            self._xvfb_process.terminate()
            try:
                self._xvfb_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._xvfb_process.kill()

        self._process = None
        self._xvfb_process = None
        self._campaign_id = None
        logger.info("Campaign stopped")

    def get_output_lines(self, max_lines: int = 50) -> list[str]:
        """Read recent output from the orchestrator process."""
        if not self._process or not self._process.stdout:
            return []
        # Non-blocking read of available output
        lines = []
        try:
            while len(lines) < max_lines:
                line = self._process.stdout.readline()
                if not line:
                    break
                lines.append(line.decode("utf-8", errors="replace").rstrip())
        except Exception:
            pass
        return lines
