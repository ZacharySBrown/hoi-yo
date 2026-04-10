"""SQLite campaign store backed by aiosqlite.

Stores campaign metadata, persona assignments, and runtime state
for cloud-hosted HOI-YO sessions.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

import aiosqlite

_CREATE_TABLE = """\
CREATE TABLE IF NOT EXISTS campaigns (
    id TEXT PRIMARY KEY,
    status TEXT DEFAULT 'starting',
    created_at TEXT,
    ended_at TEXT,
    turn_count INTEGER DEFAULT 0,
    game_date TEXT,
    total_cost REAL DEFAULT 0.0,
    personas TEXT,
    config TEXT
);
"""


class Database:
    """Async SQLite wrapper for campaign persistence."""

    def __init__(self) -> None:
        self._db_path: str | None = None
        self._db: aiosqlite.Connection | None = None

    # ── Lifecycle ─────────────────────────────────────────────────────

    async def init(self, db_path: str) -> None:
        """Open (or create) the database and ensure tables exist."""
        self._db_path = db_path
        self._db = await aiosqlite.connect(db_path)
        self._db.row_factory = aiosqlite.Row
        await self._db.execute(_CREATE_TABLE)
        await self._db.commit()

    async def close(self) -> None:
        """Close the database connection."""
        if self._db:
            await self._db.close()
            self._db = None

    # ── Helpers ───────────────────────────────────────────────────────

    def _row_to_dict(self, row: aiosqlite.Row) -> dict:
        """Convert a Row to a plain dict, deserializing JSON columns."""
        d = dict(row)
        for key in ("personas", "config"):
            if d.get(key):
                try:
                    d[key] = json.loads(d[key])
                except (json.JSONDecodeError, TypeError):
                    pass
        return d

    # ── CRUD ──────────────────────────────────────────────────────────

    async def create_campaign(self, personas: dict) -> str:
        """Insert a new campaign and return its UUID."""
        campaign_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        await self._db.execute(
            "INSERT INTO campaigns (id, status, created_at, personas) VALUES (?, ?, ?, ?)",
            (campaign_id, "starting", now, json.dumps(personas)),
        )
        await self._db.commit()
        return campaign_id

    async def get_campaign(self, campaign_id: str) -> dict | None:
        """Fetch a single campaign by id, or None if not found."""
        cursor = await self._db.execute(
            "SELECT * FROM campaigns WHERE id = ?", (campaign_id,)
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        return self._row_to_dict(row)

    async def list_campaigns(self) -> list[dict]:
        """Return all campaigns, newest first."""
        cursor = await self._db.execute(
            "SELECT * FROM campaigns ORDER BY created_at DESC"
        )
        rows = await cursor.fetchall()
        return [self._row_to_dict(r) for r in rows]

    async def update_campaign(self, campaign_id: str, **kwargs) -> None:
        """Update arbitrary columns on a campaign row.

        JSON-serialisable values for ``personas`` and ``config`` are
        automatically encoded.
        """
        if not kwargs:
            return
        # Auto-serialise dict/list values for JSON columns
        for key in ("personas", "config"):
            if key in kwargs and not isinstance(kwargs[key], str):
                kwargs[key] = json.dumps(kwargs[key])

        set_clause = ", ".join(f"{k} = ?" for k in kwargs)
        values = list(kwargs.values()) + [campaign_id]
        await self._db.execute(
            f"UPDATE campaigns SET {set_clause} WHERE id = ?",  # noqa: S608
            values,
        )
        await self._db.commit()

    async def delete_campaign(self, campaign_id: str) -> None:
        """Delete a campaign row."""
        await self._db.execute("DELETE FROM campaigns WHERE id = ?", (campaign_id,))
        await self._db.commit()
