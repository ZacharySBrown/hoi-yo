"""Campaign lobby -- FastAPI router.

Provides authentication, campaign CRUD endpoints, and the lobby UI
for the cloud-hosted HOI-YO experience.
"""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel

from src.cloud.auth import (
    COOKIE_NAME,
    auth_required,
    create_token,
    verify_password,
)
from src.cloud.database import Database

logger = logging.getLogger("hoi-yo.lobby")

TEMPLATES_DIR = Path(__file__).parent / "templates"

# ─── Shared Database Instance ─────────────────────────────────────────

db = Database()

# ─── Router ───────────────────────────────────────────────────────────

router = APIRouter()


# ─── Request Models ───────────────────────────────────────────────────

class CreateCampaignRequest(BaseModel):
    personas: dict[str, str]


# ─── Public Endpoints ─────────────────────────────────────────────────

@router.get("/", response_class=HTMLResponse)
async def login_page():
    """Serve the login page."""
    html = (TEMPLATES_DIR / "login.html").read_text()
    return HTMLResponse(html)


@router.post("/auth")
async def authenticate(request: Request, password: str = Form(...)):
    """Verify password, set JWT cookie, redirect to lobby."""
    import os

    password_hash = os.environ.get("HOIYO_PASSWORD_HASH", "")
    if not password_hash:
        raise HTTPException(status_code=500, detail="Server not configured")

    if not verify_password(password, password_hash):
        # Re-render login with error
        html = (TEMPLATES_DIR / "login.html").read_text()
        html = html.replace("<!-- ERROR_PLACEHOLDER -->", '<p class="error">Invalid password</p>')
        return HTMLResponse(html, status_code=401)

    secret = os.environ.get("HOIYO_JWT_SECRET", "")
    token = create_token(secret)

    response = RedirectResponse(url="/lobby", status_code=303)
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        max_age=24 * 60 * 60,
    )
    return response


# ─── Protected Endpoints ──────────────────────────────────────────────

@router.get("/lobby", response_class=HTMLResponse)
async def lobby_page(_auth: bool = Depends(auth_required)):
    """Serve the campaign lobby page."""
    html = (TEMPLATES_DIR / "lobby.html").read_text()
    return HTMLResponse(html)


@router.post("/api/campaigns")
async def create_campaign(
    body: CreateCampaignRequest,
    _auth: bool = Depends(auth_required),
):
    """Create a new campaign with the given persona assignments."""
    campaign_id = await db.create_campaign(body.personas)
    campaign = await db.get_campaign(campaign_id)
    logger.info("Campaign %s created", campaign_id)
    return JSONResponse(campaign, status_code=201)


@router.get("/api/campaigns")
async def list_campaigns(_auth: bool = Depends(auth_required)):
    """List all campaigns, newest first."""
    campaigns = await db.list_campaigns()
    return JSONResponse(campaigns)


@router.get("/api/campaigns/{campaign_id}")
async def get_campaign(campaign_id: str, _auth: bool = Depends(auth_required)):
    """Get a single campaign's details."""
    campaign = await db.get_campaign(campaign_id)
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return JSONResponse(campaign)


@router.delete("/api/campaigns/{campaign_id}")
async def delete_campaign(campaign_id: str, _auth: bool = Depends(auth_required)):
    """Stop and delete a campaign."""
    campaign = await db.get_campaign(campaign_id)
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found")
    await db.delete_campaign(campaign_id)
    logger.info("Campaign %s deleted", campaign_id)
    return JSONResponse({"status": "deleted", "id": campaign_id})


@router.get("/logout")
async def logout():
    """Clear the session cookie and redirect to login."""
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie(COOKIE_NAME)
    return response
