"""Tests for the HOI-YO cloud authentication, database, and lobby."""

from __future__ import annotations

import os
import tempfile

import pytest
from httpx import ASGITransport, AsyncClient

from src.cloud.auth import (
    COOKIE_NAME,
    create_token,
    hash_password,
    verify_password,
    verify_token,
)
from src.cloud.database import Database


# =====================================================================
# Password hashing
# =====================================================================


class TestPasswordHashing:
    def test_hash_returns_bcrypt_string(self):
        h = hash_password("warroom42")
        assert h.startswith("$2")
        assert len(h) > 50

    def test_verify_correct_password(self):
        h = hash_password("s3cret")
        assert verify_password("s3cret", h) is True

    def test_verify_wrong_password(self):
        h = hash_password("s3cret")
        assert verify_password("wrong", h) is False

    def test_different_hashes_for_same_password(self):
        h1 = hash_password("same")
        h2 = hash_password("same")
        assert h1 != h2  # different salts
        assert verify_password("same", h1) is True
        assert verify_password("same", h2) is True


# =====================================================================
# JWT tokens
# =====================================================================


class TestJWT:
    SECRET = "test-secret-key-abc"

    def test_create_returns_string(self):
        token = create_token(self.SECRET)
        assert isinstance(token, str)
        assert len(token) > 20

    def test_verify_valid_token(self):
        token = create_token(self.SECRET)
        assert verify_token(token, self.SECRET) is True

    def test_verify_wrong_secret(self):
        token = create_token(self.SECRET)
        assert verify_token(token, "wrong-secret") is False

    def test_verify_garbage_token(self):
        assert verify_token("not.a.jwt", self.SECRET) is False

    def test_verify_empty_token(self):
        assert verify_token("", self.SECRET) is False


# =====================================================================
# Database CRUD
# =====================================================================


@pytest.fixture
async def db():
    """Provide a fresh in-memory database for each test."""
    database = Database()
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    await database.init(db_path)
    yield database
    await database.close()
    os.unlink(db_path)


class TestDatabase:
    @pytest.mark.asyncio
    async def test_create_campaign_returns_uuid(self, db):
        cid = await db.create_campaign({"GER": "personas/germany"})
        assert isinstance(cid, str)
        assert len(cid) == 36  # UUID format

    @pytest.mark.asyncio
    async def test_get_campaign(self, db):
        cid = await db.create_campaign({"GER": "personas/germany", "SOV": "personas/soviet_union"})
        campaign = await db.get_campaign(cid)
        assert campaign is not None
        assert campaign["id"] == cid
        assert campaign["status"] == "starting"
        assert campaign["personas"]["GER"] == "personas/germany"
        assert campaign["turn_count"] == 0

    @pytest.mark.asyncio
    async def test_get_campaign_not_found(self, db):
        result = await db.get_campaign("nonexistent-id")
        assert result is None

    @pytest.mark.asyncio
    async def test_list_campaigns_empty(self, db):
        campaigns = await db.list_campaigns()
        assert campaigns == []

    @pytest.mark.asyncio
    async def test_list_campaigns_newest_first(self, db):
        id1 = await db.create_campaign({"GER": "g1"})
        id2 = await db.create_campaign({"GER": "g2"})
        campaigns = await db.list_campaigns()
        assert len(campaigns) == 2
        # newest first (id2 was created after id1)
        assert campaigns[0]["id"] == id2
        assert campaigns[1]["id"] == id1

    @pytest.mark.asyncio
    async def test_update_campaign(self, db):
        cid = await db.create_campaign({"GER": "personas/germany"})
        await db.update_campaign(cid, status="running", turn_count=5, game_date="1937.1.1")
        campaign = await db.get_campaign(cid)
        assert campaign["status"] == "running"
        assert campaign["turn_count"] == 5
        assert campaign["game_date"] == "1937.1.1"

    @pytest.mark.asyncio
    async def test_update_campaign_cost(self, db):
        cid = await db.create_campaign({"GER": "personas/germany"})
        await db.update_campaign(cid, total_cost=1.23)
        campaign = await db.get_campaign(cid)
        assert campaign["total_cost"] == pytest.approx(1.23)

    @pytest.mark.asyncio
    async def test_delete_campaign(self, db):
        cid = await db.create_campaign({"GER": "personas/germany"})
        await db.delete_campaign(cid)
        result = await db.get_campaign(cid)
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_is_noop(self, db):
        # Should not raise
        await db.delete_campaign("does-not-exist")


# =====================================================================
# Auth dependency
# =====================================================================


class TestAuthRequired:
    """Test the auth_required FastAPI dependency via the lobby router."""

    @pytest.fixture(autouse=True)
    def setup_env(self, monkeypatch):
        self.password = "testpass123"
        self.pw_hash = hash_password(self.password)
        self.secret = "test-jwt-secret-xyz"
        monkeypatch.setenv("HOIYO_PASSWORD_HASH", self.pw_hash)
        monkeypatch.setenv("HOIYO_JWT_SECRET", self.secret)

    @pytest.fixture
    def client(self):
        # Import here so env vars are set first
        from src.cloud.lobby import router
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router)
        transport = ASGITransport(app=app)
        return AsyncClient(transport=transport, base_url="http://test")

    @pytest.mark.asyncio
    async def test_lobby_rejects_without_cookie(self, client):
        resp = await client.get("/lobby", follow_redirects=False)
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_lobby_rejects_bad_cookie(self, client):
        resp = await client.get(
            "/lobby",
            cookies={COOKIE_NAME: "garbage-token"},
            follow_redirects=False,
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_lobby_accepts_valid_cookie(self, client):
        token = create_token(self.secret)
        resp = await client.get(
            "/lobby",
            cookies={COOKIE_NAME: token},
            follow_redirects=False,
        )
        assert resp.status_code == 200
        assert "HOI-YO" in resp.text

    @pytest.mark.asyncio
    async def test_campaigns_rejects_without_auth(self, client):
        resp = await client.get("/api/campaigns", follow_redirects=False)
        assert resp.status_code == 401


# =====================================================================
# Lobby endpoints
# =====================================================================


class TestLobbyEndpoints:
    """Integration tests for the lobby router using a real temp database."""

    @pytest.fixture(autouse=True)
    def setup_env(self, monkeypatch):
        self.password = "warroom"
        self.pw_hash = hash_password(self.password)
        self.secret = "lobby-test-secret"
        monkeypatch.setenv("HOIYO_PASSWORD_HASH", self.pw_hash)
        monkeypatch.setenv("HOIYO_JWT_SECRET", self.secret)

    @pytest.fixture
    async def client(self):
        from src.cloud.lobby import db, router
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router)

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        await db.init(db_path)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            yield c

        await db.close()
        os.unlink(db_path)

    def _auth_cookies(self):
        token = create_token(self.secret)
        return {COOKIE_NAME: token}

    @pytest.mark.asyncio
    async def test_login_page_serves_html(self, client):
        resp = await client.get("/")
        assert resp.status_code == 200
        assert "War Room" in resp.text

    @pytest.mark.asyncio
    async def test_auth_wrong_password(self, client):
        resp = await client.post(
            "/auth",
            data={"password": "wrong"},
            follow_redirects=False,
        )
        assert resp.status_code == 401
        assert "Invalid password" in resp.text

    @pytest.mark.asyncio
    async def test_auth_correct_password_sets_cookie(self, client):
        resp = await client.post(
            "/auth",
            data={"password": self.password},
            follow_redirects=False,
        )
        assert resp.status_code == 303
        assert resp.headers.get("location") == "/lobby"
        assert COOKIE_NAME in resp.cookies

    @pytest.mark.asyncio
    async def test_create_campaign(self, client):
        resp = await client.post(
            "/api/campaigns",
            json={"personas": {"GER": "personas/germany", "SOV": "personas/soviet_union"}},
            cookies=self._auth_cookies(),
        )
        assert resp.status_code == 201
        data = resp.json()
        assert "id" in data
        assert data["status"] == "starting"
        assert data["personas"]["GER"] == "personas/germany"

    @pytest.mark.asyncio
    async def test_list_campaigns(self, client):
        # Create two campaigns
        await client.post(
            "/api/campaigns",
            json={"personas": {"GER": "personas/germany"}},
            cookies=self._auth_cookies(),
        )
        await client.post(
            "/api/campaigns",
            json={"personas": {"SOV": "personas/soviet_union"}},
            cookies=self._auth_cookies(),
        )

        resp = await client.get("/api/campaigns", cookies=self._auth_cookies())
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2

    @pytest.mark.asyncio
    async def test_get_campaign_by_id(self, client):
        create_resp = await client.post(
            "/api/campaigns",
            json={"personas": {"GER": "personas/germany"}},
            cookies=self._auth_cookies(),
        )
        cid = create_resp.json()["id"]

        resp = await client.get(f"/api/campaigns/{cid}", cookies=self._auth_cookies())
        assert resp.status_code == 200
        assert resp.json()["id"] == cid

    @pytest.mark.asyncio
    async def test_get_campaign_not_found(self, client):
        resp = await client.get(
            "/api/campaigns/nonexistent",
            cookies=self._auth_cookies(),
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_campaign(self, client):
        create_resp = await client.post(
            "/api/campaigns",
            json={"personas": {"GER": "personas/germany"}},
            cookies=self._auth_cookies(),
        )
        cid = create_resp.json()["id"]

        resp = await client.delete(f"/api/campaigns/{cid}", cookies=self._auth_cookies())
        assert resp.status_code == 200
        assert resp.json()["status"] == "deleted"

        # Confirm gone
        resp = await client.get(f"/api/campaigns/{cid}", cookies=self._auth_cookies())
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_campaign_not_found(self, client):
        resp = await client.delete(
            "/api/campaigns/nonexistent",
            cookies=self._auth_cookies(),
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_logout_clears_cookie(self, client):
        resp = await client.get("/logout", follow_redirects=False)
        assert resp.status_code == 303
        assert resp.headers.get("location") == "/"
