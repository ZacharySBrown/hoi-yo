"""HOI-YO Observer Dashboard + Launcher -- FastAPI server.

Serves the launcher (game setup UI) and the live WebSocket-powered
dashboard showing AI agent decisions in real time.
"""

from __future__ import annotations

import asyncio
import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from src.config import DashboardConfig, detect_hoi4_paths, find_config, get_app_data_dir, write_config
from src.interfaces import MAJOR_POWERS
from src.personas.loader import discover_personas

logger = logging.getLogger("hoi-yo.dashboard")

STATIC_DIR = Path(__file__).parent / "static"

# ─── Pydantic Models ──────────────────────────────────────────────────

class WhisperRequest(BaseModel):
    tag: str
    message: str


class LaunchRequest(BaseModel):
    player_tag: str | None = None
    personas: dict[str, str] = {}  # tag -> persona directory path
    speed: int = 3
    popcorn: bool = False
    deep_dive: bool = False


# ─── Dashboard Server ─────────────────────────────────────────────────

class DashboardServer:
    """Manages the dashboard state and WebSocket connections."""

    def __init__(self) -> None:
        self.connections: list[WebSocket] = []
        self.decision_history: list[dict[str, Any]] = []
        self.whisper_log: list[dict[str, str]] = []
        self.game_date: str = "1936.1.1"
        self.turn_number: int = 0
        self.game_speed: int = 3
        self.paused: bool = False
        self.personas: list[dict[str, str]] = []
        self.latest_state: dict[str, Any] = {}

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self.connections.append(ws)
        logger.info("Dashboard client connected (%d total)", len(self.connections))
        # Send current state on connect
        if self.latest_state:
            await ws.send_json(self.latest_state)

    def disconnect(self, ws: WebSocket) -> None:
        if ws in self.connections:
            self.connections.remove(ws)
        logger.info("Dashboard client disconnected (%d remaining)", len(self.connections))

    async def broadcast(self, data: dict) -> None:
        """Push turn update data to all connected WebSocket clients."""
        self.latest_state = data

        # Store in history
        if "turn" in data:
            self.turn_number = data["turn"]
        if "date" in data:
            self.game_date = data["date"]

        self.decision_history.append(data)

        stale: list[WebSocket] = []
        for ws in self.connections:
            try:
                await ws.send_json(data)
            except Exception:
                stale.append(ws)

        for ws in stale:
            self.disconnect(ws)

    def set_personas(self, personas: list[dict[str, str]]) -> None:
        """Register loaded personas for the /api/personas endpoint."""
        self.personas = personas

    def get_status(self) -> dict[str, Any]:
        return {
            "date": self.game_date,
            "turn": self.turn_number,
            "speed": self.game_speed,
            "paused": self.paused,
            "connected_clients": len(self.connections),
        }

    def get_history(self) -> list[dict[str, Any]]:
        return self.decision_history


# ─── Singleton ─────────────────────────────────────────────────────────

dashboard = DashboardServer()
_game_running = False  # True once orchestrator is started
_game_process: subprocess.Popen | None = None  # HOI4 process


# ─── FastAPI App ───────────────────────────────────────────────────────

app = FastAPI(title="HOI-YO Observer Dashboard", version="0.1.0")

# Mount static files (CSS, JS)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", response_class=HTMLResponse)
async def index():
    """Serve launcher (no game running) or dashboard (game active)."""
    if _game_running:
        return FileResponse(STATIC_DIR / "index.html", media_type="text/html")
    return FileResponse(STATIC_DIR / "launcher.html", media_type="text/html")


@app.get("/launcher", response_class=HTMLResponse)
async def launcher_page():
    """Always serve the launcher page."""
    return FileResponse(STATIC_DIR / "launcher.html", media_type="text/html")


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page():
    """Always serve the dashboard page."""
    return FileResponse(STATIC_DIR / "index.html", media_type="text/html")


@app.get("/api/status")
async def api_status():
    """Return current game status."""
    return JSONResponse(dashboard.get_status())


@app.get("/api/personas")
async def api_personas():
    """Return list of loaded persona names and tags."""
    if not dashboard.personas:
        # Return default major powers if no personas loaded yet
        return JSONResponse([
            {"tag": tag, "name": tag} for tag in MAJOR_POWERS
        ])
    return JSONResponse(dashboard.personas)


@app.get("/api/history")
async def api_history():
    """Return full decision history for replay."""
    return JSONResponse(dashboard.get_history())


@app.post("/api/speed/{speed}")
async def api_set_speed(speed: int):
    """Change game speed (1-5) or 0 to pause."""
    if speed == 0:
        dashboard.paused = True
        return JSONResponse({"paused": True, "speed": dashboard.game_speed})
    if speed < 1 or speed > 5:
        return JSONResponse({"error": "Speed must be 1-5 (or 0 to pause)"}, status_code=400)
    dashboard.game_speed = speed
    dashboard.paused = False
    return JSONResponse({"paused": False, "speed": speed})


@app.post("/api/whisper")
async def api_whisper(req: WhisperRequest):
    """Send a human message (whisper) to a specific agent."""
    entry = {"tag": req.tag, "message": req.message}
    dashboard.whisper_log.append(entry)
    logger.info("Whisper to %s: %s", req.tag, req.message[:80])
    return JSONResponse({"status": "delivered", "tag": req.tag})


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    """WebSocket endpoint for live turn updates."""
    await dashboard.connect(ws)
    try:
        while True:
            # Keep connection alive; handle any client messages (e.g., pings)
            data = await ws.receive_text()
            # Client can send pings or commands; we just acknowledge
            if data == "ping":
                await ws.send_json({"type": "pong"})
    except WebSocketDisconnect:
        dashboard.disconnect(ws)
    except Exception:
        dashboard.disconnect(ws)


# ─── Launcher API ─────────────────────────────────────────────────────


@app.get("/api/setup/status")
async def api_setup_status():
    """Return setup state: API key set? HOI4 found?"""
    app_dir = get_app_data_dir()
    env_path = app_dir / ".env"
    api_key_set = False

    # Check .env in app data dir, then CWD
    for p in [env_path, Path(".env")]:
        if p.exists():
            for line in p.read_text().splitlines():
                if line.strip().startswith("ANTHROPIC_API_KEY") and "=" in line:
                    val = line.split("=", 1)[1].strip().strip("'\"")
                    if val:
                        api_key_set = True
                        break
        if api_key_set:
            break

    # Also check environment variable
    if not api_key_set and os.environ.get("ANTHROPIC_API_KEY"):
        api_key_set = True

    paths = detect_hoi4_paths()
    config_path = find_config()

    return JSONResponse({
        "api_key_set": api_key_set,
        "hoi4_found": paths["hoi4_executable"] is not None,
        "hoi4_path": str(paths["hoi4_executable"]) if paths["hoi4_executable"] else None,
        "config_found": config_path is not None,
        "config_path": str(config_path) if config_path else None,
        "game_running": _game_running,
    })


@app.post("/api/setup/save")
async def api_setup_save(body: dict):
    """Save config.toml from launcher setup."""
    hoi4_path = body.get("hoi4_path", "")
    if not hoi4_path:
        return JSONResponse({"error": "hoi4_path is required"}, status_code=400)

    exe = Path(hoi4_path)
    # Derive other paths from the executable location
    if sys.platform == "win32":
        docs_base = Path.home() / "Documents" / "Paradox Interactive" / "Hearts of Iron IV"
    elif sys.platform == "darwin":
        docs_base = Path.home() / "Documents" / "Paradox Interactive" / "Hearts of Iron IV"
    else:
        docs_base = Path.home() / "Documents" / "Paradox Interactive" / "Hearts of Iron IV"

    paths = {
        "hoi4_executable": str(exe),
        "save_dir": str(docs_base / "save games"),
        "mod_dir": str(docs_base / "mod" / "hoi_yo_bots"),
        "config_dir": str(docs_base),
    }

    config_path = Path("config.toml")
    write_config(config_path, paths)

    return JSONResponse({"status": "saved", "path": str(config_path)})


@app.get("/api/personas/available")
async def api_personas_available():
    """Return all available personas grouped by country tag."""
    personas_dir = Path("personas")
    if not personas_dir.exists():
        return JSONResponse({})
    result = discover_personas(personas_dir)
    return JSONResponse(result)


@app.post("/api/game/launch")
async def api_game_launch(req: LaunchRequest):
    """Launch HOI4 and prepare the orchestrator."""
    global _game_process

    config_path = find_config()
    if not config_path:
        return JSONResponse({"error": "No config.toml found. Run setup first."}, status_code=400)

    from src.config import load_config
    config = load_config(config_path)

    # Launch HOI4
    exe = config.game.hoi4_executable
    if exe.exists():
        launch_flags = ["-debug", "-nolog", "-nomusic", "-nosound"]
        if sys.platform == "darwin" and exe.suffix == ".app":
            _game_process = subprocess.Popen(["open", str(exe), "--args"] + launch_flags)
        else:
            _game_process = subprocess.Popen([str(exe)] + launch_flags)
        logger.info("Launched HOI4: %s", exe)
    else:
        logger.warning("HOI4 not found at %s -- user must launch manually", exe)

    return JSONResponse({
        "status": "launched",
        "player_tag": req.player_tag,
        "hoi4_found": exe.exists(),
    })


@app.post("/api/game/ready")
async def api_game_ready(body: dict):
    """User confirms they're in-game. Start the orchestrator."""
    global _game_running

    player_tag = body.get("player_tag")
    persona_overrides = body.get("personas", {})
    speed = body.get("speed", 3)
    popcorn = body.get("popcorn", False)
    deep_dive = body.get("deep_dive", False)

    config_path = find_config()
    if not config_path:
        return JSONResponse({"error": "No config.toml found"}, status_code=400)

    from src.config import load_config
    from src.personas.loader import load_all_personas

    config = load_config(config_path)
    config.game.initial_speed = speed

    # Apply persona overrides from launcher
    if persona_overrides:
        config.personas.mappings.update(persona_overrides)

    # Load personas
    personas = load_all_personas(Path("personas"), config.personas.mappings)

    # Set personas on dashboard
    dashboard.set_personas([{"tag": p.tag, "name": p.name} for p in personas])

    _game_running = True

    # Enter observer mode if spectator
    if not player_tag:
        from src.game.controller import GameController
        controller = GameController(config.game.hoi4_executable)
        await asyncio.sleep(2)  # Brief delay for game window to be ready
        controller.enter_observer_mode()

    # Start orchestrator in background
    from src.orchestrator import HoiYoOrchestrator
    orchestrator = HoiYoOrchestrator(
        config=config,
        personas=personas,
        dashboard=dashboard,
        headless=False,
        popcorn=popcorn,
        deep_dive=deep_dive,
        player_tag=player_tag.upper() if player_tag else None,
    )

    async def run_orchestrator():
        global _game_running
        try:
            await orchestrator.run()
        except Exception:
            logger.exception("Orchestrator stopped with error")
        finally:
            _game_running = False

    asyncio.create_task(run_orchestrator())

    return JSONResponse({
        "status": "started",
        "player_tag": player_tag,
        "personas": [{"tag": p.tag, "name": p.name} for p in personas],
    })


@app.post("/api/game/stop")
async def api_game_stop():
    """Stop the orchestrator and optionally HOI4."""
    global _game_running, _game_process

    _game_running = False
    if _game_process and _game_process.poll() is None:
        _game_process.terminate()
        _game_process = None

    return JSONResponse({"status": "stopped"})


# ─── Server Start ─────────────────────────────────────────────────────

def start(config: DashboardConfig | None = None) -> None:
    """Run the dashboard server with uvicorn."""
    import uvicorn

    port = config.port if config else 8080
    logger.info("Starting HOI-YO dashboard on port %d", port)
    uvicorn.run(
        "src.dashboard.server:app",
        host="0.0.0.0",
        port=port,
        log_level="info",
    )
