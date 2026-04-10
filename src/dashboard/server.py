"""HOI-YO Observer Dashboard -- FastAPI server.

Serves a live WebSocket-powered dashboard showing AI agent decisions
in real time as they play Hearts of Iron IV.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from src.config import DashboardConfig
from src.interfaces import MAJOR_POWERS

logger = logging.getLogger("hoi-yo.dashboard")

STATIC_DIR = Path(__file__).parent / "static"

# ─── Pydantic Models ──────────────────────────────────────────────────

class WhisperRequest(BaseModel):
    tag: str
    message: str


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


# ─── FastAPI App ───────────────────────────────────────────────────────

app = FastAPI(title="HOI-YO Observer Dashboard", version="0.1.0")

# Mount static files (CSS, JS)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", response_class=HTMLResponse)
async def index():
    """Serve the main dashboard page."""
    index_path = STATIC_DIR / "index.html"
    return FileResponse(index_path, media_type="text/html")


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


# ─── Launcher ──────────────────────────────────────────────────────────

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
