"""Tests for the HOI-YO Observer Dashboard."""

import pytest
from httpx import ASGITransport, AsyncClient

from src.dashboard.server import app, dashboard


@pytest.fixture(autouse=True)
def reset_dashboard():
    """Reset dashboard state before each test."""
    dashboard.decision_history.clear()
    dashboard.whisper_log.clear()
    dashboard.game_date = "1936.1.1"
    dashboard.turn_number = 0
    dashboard.game_speed = 3
    dashboard.paused = False
    dashboard.personas = []
    dashboard.latest_state = {}
    yield


@pytest.fixture
def client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.mark.asyncio
async def test_index_serves_html(client):
    """GET / should serve the dashboard index.html."""
    resp = await client.get("/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    assert "HOI-YO" in resp.text


@pytest.mark.asyncio
async def test_api_status_returns_valid_json(client):
    """GET /api/status should return current game status as JSON."""
    resp = await client.get("/api/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "date" in data
    assert "turn" in data
    assert "speed" in data
    assert "paused" in data
    assert data["date"] == "1936.1.1"
    assert data["turn"] == 0
    assert data["speed"] == 3
    assert data["paused"] is False


@pytest.mark.asyncio
async def test_api_personas_returns_defaults(client):
    """GET /api/personas should return major powers when no personas loaded."""
    resp = await client.get("/api/personas")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 6
    tags = [p["tag"] for p in data]
    assert "GER" in tags
    assert "SOV" in tags
    assert "USA" in tags


@pytest.mark.asyncio
async def test_api_personas_returns_loaded(client):
    """GET /api/personas should return loaded personas when available."""
    dashboard.set_personas([
        {"tag": "GER", "name": "Iron Chancellor"},
        {"tag": "SOV", "name": "Red Bear"},
    ])
    resp = await client.get("/api/personas")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    assert data[0]["name"] == "Iron Chancellor"


@pytest.mark.asyncio
async def test_api_whisper_accepts_and_stores(client):
    """POST /api/whisper should accept a message and store it."""
    resp = await client.post(
        "/api/whisper",
        json={"tag": "GER", "message": "Consider allying with Italy"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "delivered"
    assert data["tag"] == "GER"

    # Verify it was stored
    assert len(dashboard.whisper_log) == 1
    assert dashboard.whisper_log[0]["tag"] == "GER"
    assert dashboard.whisper_log[0]["message"] == "Consider allying with Italy"


@pytest.mark.asyncio
async def test_api_speed_valid(client):
    """POST /api/speed/{speed} should change game speed."""
    resp = await client.post("/api/speed/5")
    assert resp.status_code == 200
    data = resp.json()
    assert data["speed"] == 5
    assert data["paused"] is False
    assert dashboard.game_speed == 5


@pytest.mark.asyncio
async def test_api_speed_pause(client):
    """POST /api/speed/0 should pause the game."""
    resp = await client.post("/api/speed/0")
    assert resp.status_code == 200
    data = resp.json()
    assert data["paused"] is True


@pytest.mark.asyncio
async def test_api_speed_invalid(client):
    """POST /api/speed/9 should return 400."""
    resp = await client.post("/api/speed/9")
    assert resp.status_code == 400
    data = resp.json()
    assert "error" in data


@pytest.mark.asyncio
async def test_api_history_empty(client):
    """GET /api/history should return empty list initially."""
    resp = await client.get("/api/history")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 0


@pytest.mark.asyncio
async def test_broadcast_stores_history():
    """broadcast() should store data in decision_history."""
    await dashboard.broadcast({"turn": 1, "date": "1936.2.1", "decisions": {}})
    assert len(dashboard.decision_history) == 1
    assert dashboard.turn_number == 1
    assert dashboard.game_date == "1936.2.1"


@pytest.mark.asyncio
async def test_static_css_served(client):
    """Static CSS file should be served."""
    resp = await client.get("/static/style.css")
    assert resp.status_code == 200
    assert "text/css" in resp.headers["content-type"]


@pytest.mark.asyncio
async def test_static_js_served(client):
    """Static JS file should be served."""
    resp = await client.get("/static/app.js")
    assert resp.status_code == 200
    assert "javascript" in resp.headers["content-type"]
