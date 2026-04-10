#!/usr/bin/env python3
"""auto_shutdown.py -- Shut down the server if nobody is watching.

Checks the hoi-yo dashboard for connected clients. If zero clients have
been connected for 30 consecutive minutes (6 checks at 5-minute intervals),
kills HOI4 and shuts down the machine.

Designed to run as a systemd timer every 5 minutes:
    [Timer]
    OnBootSec=10min
    OnUnitActiveSec=5min
"""

import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from urllib.request import urlopen, URLError

STATE_FILE = Path("/var/lib/hoi-yo/autoshutdown-state.json")
DASHBOARD_URL = "http://localhost:8080/api/status"
IDLE_THRESHOLD_SECONDS = 30 * 60  # 30 minutes
LOG_PREFIX = "[auto_shutdown]"


def log(msg: str) -> None:
    print(f"{LOG_PREFIX} {time.strftime('%H:%M:%S')} {msg}", flush=True)


def get_connected_clients() -> int | None:
    """Query the dashboard for the current connected client count."""
    try:
        with urlopen(DASHBOARD_URL, timeout=5) as resp:
            data = json.loads(resp.read())
            return data.get("connected_clients", 0)
    except (URLError, OSError, json.JSONDecodeError, KeyError) as exc:
        log(f"WARNING: Could not reach dashboard: {exc}")
        return None


def load_state() -> dict:
    """Load persisted state from disk."""
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return {"idle_since": None}


def save_state(state: dict) -> None:
    """Persist state to disk."""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state))


def kill_hoi4() -> None:
    """Find and kill any running HOI4 process."""
    try:
        result = subprocess.run(
            ["pgrep", "-f", "hoi4"],
            capture_output=True,
            text=True,
        )
        pids = result.stdout.strip().split("\n")
        for pid_str in pids:
            pid_str = pid_str.strip()
            if pid_str:
                pid = int(pid_str)
                log(f"Killing HOI4 process {pid}")
                os.kill(pid, signal.SIGTERM)
    except (ValueError, ProcessLookupError, OSError) as exc:
        log(f"WARNING: Error killing HOI4: {exc}")


def shutdown_machine() -> None:
    """Shut down the machine."""
    log("SHUTTING DOWN machine.")
    subprocess.run(["sudo", "shutdown", "-h", "now"], check=False)


def main() -> None:
    now = time.time()
    clients = get_connected_clients()
    state = load_state()

    if clients is None:
        # Dashboard unreachable -- don't shut down, could be starting up.
        log("Dashboard unreachable, skipping check.")
        save_state(state)
        return

    log(f"Connected clients: {clients}")

    if clients > 0:
        # Someone is watching -- reset idle timer.
        state["idle_since"] = None
        save_state(state)
        log("Active viewers present, idle timer reset.")
        return

    # Zero clients.
    if state["idle_since"] is None:
        state["idle_since"] = now
        save_state(state)
        log("No viewers. Starting idle timer.")
        return

    idle_seconds = now - state["idle_since"]
    idle_minutes = idle_seconds / 60

    log(f"Idle for {idle_minutes:.1f} minutes (threshold: {IDLE_THRESHOLD_SECONDS / 60:.0f} min).")

    if idle_seconds >= IDLE_THRESHOLD_SECONDS:
        log(f"Idle threshold reached ({idle_minutes:.0f} min). Initiating shutdown.")
        kill_hoi4()
        time.sleep(5)  # Let HOI4 save
        shutdown_machine()
    else:
        save_state(state)
        remaining = (IDLE_THRESHOLD_SECONDS - idle_seconds) / 60
        log(f"Shutdown in ~{remaining:.0f} minutes if no viewers connect.")


if __name__ == "__main__":
    main()
