"""
control_db.py — persistence for the AITZAZ AI command center runtime.

Keeps system configuration, audit logs, detected live moments, and the
publishing queue in SQLite alongside the legacy project/clip tables.
"""

from __future__ import annotations

import json
import uuid
from typing import Any, Optional

import database  # type: ignore


DEFAULT_CONFIG: dict[str, Any] = {
    "stumps_team_id": __import__("os").environ.get("STUMPS_TEAM_ID", "-OiyGifAxdcSXcSbbE5m"),
    "publish_mode": "approval",
    "auto_publish_minimum": 85,
    "pre_roll_seconds": 10,
    "post_roll_seconds": 15,
    "youtube_privacy_status": "private",
}


async def init_control_db() -> None:
    conn = await database._get_connection()
    try:
        await conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS system_config (
                key TEXT PRIMARY KEY,
                value TEXT
            );

            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                actor TEXT NOT NULL,
                success INTEGER NOT NULL DEFAULT 1,
                details TEXT,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS moments (
                id TEXT PRIMARY KEY,
                event_id TEXT UNIQUE,
                match_id TEXT,
                event_type TEXT NOT NULL,
                player TEXT,
                bowler TEXT,
                over_text TEXT,
                score_text TEXT,
                viral_score INTEGER,
                confidence REAL,
                fingerprint TEXT UNIQUE,
                timestamp TEXT,
                event_json TEXT,
                clip_path TEXT,
                captioned_path TEXT,
                title TEXT,
                description TEXT,
                hashtags TEXT,
                status TEXT NOT NULL DEFAULT 'detected',
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS publishing_jobs (
                id TEXT PRIMARY KEY,
                moment_id TEXT NOT NULL,
                platform TEXT NOT NULL,
                status TEXT NOT NULL,
                approval_required INTEGER NOT NULL DEFAULT 0,
                metadata_json TEXT,
                external_id TEXT,
                error_message TEXT,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(moment_id, platform),
                FOREIGN KEY (moment_id) REFERENCES moments(id)
            );
            """
        )
        await conn.commit()

        for key, value in DEFAULT_CONFIG.items():
            await conn.execute(
                "INSERT OR IGNORE INTO system_config (key, value) VALUES (?, ?)",
                (key, json.dumps(value) if not isinstance(value, str) else value),
            )
        await conn.commit()
    finally:
        await conn.close()


async def set_config(key: str, value: Any) -> None:
    conn = await database._get_connection()
    try:
        stored = json.dumps(value) if not isinstance(value, str) else value
        await conn.execute(
            "INSERT INTO system_config (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, stored),
        )
        await conn.commit()
    finally:
        await conn.close()


async def get_config(key: str, default: Any = None) -> Any:
    conn = await database._get_connection()
    try:
        cursor = await conn.execute("SELECT value FROM system_config WHERE key = ?", (key,))
        row = await cursor.fetchone()
        if not row:
            return DEFAULT_CONFIG.get(key, default)
        value = row[0]
        if value is None:
            return DEFAULT_CONFIG.get(key, default)
        try:
            return json.loads(value)
        except Exception:
            return value
    finally:
        await conn.close()


async def get_all_config() -> dict[str, Any]:
    conn = await database._get_connection()
    try:
        cursor = await conn.execute("SELECT key, value FROM system_config")
        rows = await cursor.fetchall()
        result = dict(DEFAULT_CONFIG)
        for row in rows:
            value = row["value"]
            try:
                result[row["key"]] = json.loads(value) if value is not None else None
            except Exception:
                result[row["key"]] = value
        return result
    finally:
        await conn.close()


async def add_audit_log(event_type: str, actor: str, success: bool, details: str) -> None:
    conn = await database._get_connection()
    try:
        await conn.execute(
            "INSERT INTO audit_logs (event_type, actor, success, details) VALUES (?, ?, ?, ?)",
            (event_type, actor, int(bool(success)), details),
        )
        await conn.commit()
    finally:
        await conn.close()


async def list_audit_logs(limit: int = 50) -> list[dict[str, Any]]:
    conn = await database._get_connection()
    try:
        cursor = await conn.execute(
            "SELECT * FROM audit_logs ORDER BY created_at DESC, id DESC LIMIT ?",
            (limit,),
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]
    finally:
        await conn.close()


async def insert_moment(moment: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    """Insert a detected moment. Duplicate fingerprints are ignored."""
    conn = await database._get_connection()
    try:
        record = {
            "id": moment.get("id") or str(uuid.uuid4()),
            "event_id": moment.get("event_id"),
            "match_id": moment.get("match_id"),
            "event_type": moment["event_type"],
            "player": moment.get("player"),
            "bowler": moment.get("bowler"),
            "over_text": moment.get("over_text"),
            "score_text": moment.get("score_text"),
            "viral_score": moment.get("viral_score"),
            "confidence": moment.get("confidence"),
            "fingerprint": moment.get("fingerprint"),
            "timestamp": moment.get("timestamp"),
            "event_json": json.dumps(moment.get("event_json") or {}),
            "clip_path": moment.get("clip_path"),
            "captioned_path": moment.get("captioned_path"),
            "title": moment.get("title"),
            "description": moment.get("description"),
            "hashtags": json.dumps(moment.get("hashtags") or []),
            "status": moment.get("status", "detected"),
        }
        await conn.execute(
            """
            INSERT INTO moments (
                id, event_id, match_id, event_type, player, bowler, over_text, score_text,
                viral_score, confidence, fingerprint, timestamp, event_json, clip_path,
                captioned_path, title, description, hashtags, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record["id"], record["event_id"], record["match_id"], record["event_type"],
                record["player"], record["bowler"], record["over_text"], record["score_text"],
                record["viral_score"], record["confidence"], record["fingerprint"], record["timestamp"],
                record["event_json"], record["clip_path"], record["captioned_path"], record["title"],
                record["description"], record["hashtags"], record["status"],
            ),
        )
        await conn.commit()
        return True, record
    except Exception:
        # Fetch existing duplicate if present.
        if moment.get("fingerprint"):
            cursor = await conn.execute(
                "SELECT * FROM moments WHERE fingerprint = ?",
                (moment["fingerprint"],),
            )
            row = await cursor.fetchone()
            if row:
                data = dict(row)
                data["hashtags"] = json.loads(data.get("hashtags") or "[]")
                data["event_json"] = json.loads(data.get("event_json") or "{}")
                return False, data
        raise
    finally:
        await conn.close()


async def update_moment(moment_id: str, **fields: Any) -> None:
    if not fields:
        return
    allowed = {
        "clip_path", "captioned_path", "title", "description", "hashtags", "status", "viral_score"
    }
    pairs = []
    values: list[Any] = []
    for key, value in fields.items():
        if key not in allowed:
            continue
        if key == "hashtags":
            value = json.dumps(value or [])
        pairs.append(f"{key} = ?")
        values.append(value)
    if not pairs:
        return
    values.append(moment_id)
    conn = await database._get_connection()
    try:
        await conn.execute(f"UPDATE moments SET {', '.join(pairs)} WHERE id = ?", values)
        await conn.commit()
    finally:
        await conn.close()


async def list_moments(limit: int = 25) -> list[dict[str, Any]]:
    conn = await database._get_connection()
    try:
        cursor = await conn.execute(
            "SELECT * FROM moments ORDER BY created_at DESC LIMIT ?",
            (limit,),
        )
        rows = await cursor.fetchall()
        result = []
        for row in rows:
            item = dict(row)
            item["hashtags"] = json.loads(item.get("hashtags") or "[]")
            item["event_json"] = json.loads(item.get("event_json") or "{}")
            result.append(item)
        return result
    finally:
        await conn.close()


async def upsert_publishing_job(
    moment_id: str,
    platform: str,
    status: str,
    approval_required: bool,
    metadata: Optional[dict[str, Any]] = None,
    external_id: Optional[str] = None,
    error_message: Optional[str] = None,
) -> dict[str, Any]:
    conn = await database._get_connection()
    try:
        job_id = str(uuid.uuid4())
        metadata_json = json.dumps(metadata or {})
        await conn.execute(
            """
            INSERT INTO publishing_jobs (
                id, moment_id, platform, status, approval_required, metadata_json,
                external_id, error_message, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(moment_id, platform) DO UPDATE SET
                status = excluded.status,
                approval_required = excluded.approval_required,
                metadata_json = excluded.metadata_json,
                external_id = COALESCE(excluded.external_id, publishing_jobs.external_id),
                error_message = excluded.error_message,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                job_id,
                moment_id,
                platform,
                status,
                int(bool(approval_required)),
                metadata_json,
                external_id,
                error_message,
            ),
        )
        await conn.commit()
        cursor = await conn.execute(
            "SELECT * FROM publishing_jobs WHERE moment_id = ? AND platform = ?",
            (moment_id, platform),
        )
        row = await cursor.fetchone()
        return _row_to_job(dict(row)) if row else {}
    finally:
        await conn.close()


async def update_publishing_job(job_id: str, **fields: Any) -> None:
    if not fields:
        return
    allowed = {"status", "approval_required", "metadata_json", "external_id", "error_message"}
    pairs = []
    values: list[Any] = []
    for key, value in fields.items():
        if key not in allowed:
            continue
        if key == "approval_required":
            value = int(bool(value))
        if key == "metadata_json" and isinstance(value, dict):
            value = json.dumps(value)
        pairs.append(f"{key} = ?")
        values.append(value)
    if not pairs:
        return
    values.append(job_id)
    conn = await database._get_connection()
    try:
        await conn.execute(
            f"UPDATE publishing_jobs SET {', '.join(pairs)}, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            values,
        )
        await conn.commit()
    finally:
        await conn.close()


async def get_publishing_job(job_id: str) -> Optional[dict[str, Any]]:
    conn = await database._get_connection()
    try:
        cursor = await conn.execute("SELECT * FROM publishing_jobs WHERE id = ?", (job_id,))
        row = await cursor.fetchone()
        return _row_to_job(dict(row)) if row else None
    finally:
        await conn.close()


async def list_publishing_jobs(limit: int = 50) -> list[dict[str, Any]]:
    conn = await database._get_connection()
    try:
        cursor = await conn.execute(
            """
            SELECT j.*, m.event_type, m.player, m.viral_score, m.title, m.clip_path, m.captioned_path
            FROM publishing_jobs j
            JOIN moments m ON m.id = j.moment_id
            ORDER BY j.updated_at DESC, j.created_at DESC
            LIMIT ?
            """,
            (limit,),
        )
        rows = await cursor.fetchall()
        return [_row_to_job(dict(r)) for r in rows]
    finally:
        await conn.close()


def _row_to_job(row: dict[str, Any]) -> dict[str, Any]:
    row["approval_required"] = bool(row.get("approval_required"))
    row["metadata"] = json.loads(row.get("metadata_json") or "{}")
    row.pop("metadata_json", None)
    return row
