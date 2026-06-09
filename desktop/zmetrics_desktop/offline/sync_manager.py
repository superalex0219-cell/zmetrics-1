"""SQLite-backed offline queue for write operations.

Parity with the former Flutter ``SyncManager``: pending operations live in the
``pending_uploads`` table, each with a client-generated ``idempotency_key`` (UUID v4).
The queue is drained when connectivity is available; after ``MAX_ATTEMPTS`` failures an
item is surfaced to the user as an error rather than retried forever.
"""
from __future__ import annotations

import json
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

MAX_ATTEMPTS = 5

_SCHEMA = """
CREATE TABLE IF NOT EXISTS pending_uploads (
    idempotency_key TEXT PRIMARY KEY,
    kind            TEXT NOT NULL,
    payload         TEXT NOT NULL,
    attempts        INTEGER NOT NULL DEFAULT 0,
    last_error      TEXT,
    created_at      TEXT NOT NULL
);
"""


@dataclass(frozen=True)
class PendingUpload:
    idempotency_key: str
    kind: str
    payload: dict
    attempts: int
    last_error: str | None
    created_at: str


class SyncManager:
    """Minimal durable queue. Not thread-safe; use one instance per worker thread."""

    def __init__(self, db_path: str | Path = ":memory:") -> None:
        if db_path != ":memory:":
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(db_path))
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def enqueue(self, kind: str, payload: dict) -> str:
        """Queue an operation; returns its idempotency_key (UUID v4)."""
        key = str(uuid.uuid4())
        self._conn.execute(
            "INSERT INTO pending_uploads (idempotency_key, kind, payload, created_at) "
            "VALUES (?, ?, ?, ?)",
            (key, kind, json.dumps(payload), datetime.now(timezone.utc).isoformat()),
        )
        self._conn.commit()
        return key

    def pending(self) -> list[PendingUpload]:
        """Items still eligible for sending (attempts < MAX_ATTEMPTS), oldest first."""
        rows = self._conn.execute(
            "SELECT * FROM pending_uploads WHERE attempts < ? ORDER BY created_at ASC",
            (MAX_ATTEMPTS,),
        ).fetchall()
        return [self._row_to_item(r) for r in rows]

    def failed(self) -> list[PendingUpload]:
        """Items exhausted (attempts >= MAX_ATTEMPTS) — surface these to the user."""
        rows = self._conn.execute(
            "SELECT * FROM pending_uploads WHERE attempts >= ? ORDER BY created_at ASC",
            (MAX_ATTEMPTS,),
        ).fetchall()
        return [self._row_to_item(r) for r in rows]

    def mark_failure(self, key: str, error: str) -> None:
        self._conn.execute(
            "UPDATE pending_uploads SET attempts = attempts + 1, last_error = ? "
            "WHERE idempotency_key = ?",
            (error, key),
        )
        self._conn.commit()

    def remove(self, key: str) -> None:
        """Remove an item after the server confirmed it (success)."""
        self._conn.execute(
            "DELETE FROM pending_uploads WHERE idempotency_key = ?", (key,)
        )
        self._conn.commit()

    @staticmethod
    def _row_to_item(row: sqlite3.Row) -> PendingUpload:
        return PendingUpload(
            idempotency_key=row["idempotency_key"],
            kind=row["kind"],
            payload=json.loads(row["payload"]),
            attempts=row["attempts"],
            last_error=row["last_error"],
            created_at=row["created_at"],
        )
