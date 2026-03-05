"""FIP Client — send, receive, and manage agent messages."""
from __future__ import annotations

import hashlib
import json
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Any, Optional

from fip.schema import SCHEMA_SQL
from fip.models import Event, Ack, Delivery
from fip.reply_parser import parse_reply_intent


class FIPClient:
    """Main interface for the Forced Injection Protocol."""

    def __init__(self, db_path: str = "fip.db", agent_id: str = "agent:default"):
        self.db_path = Path(db_path)
        self.agent_id = agent_id
        self._conn: Optional[sqlite3.Connection] = None

    def _connect(self) -> sqlite3.Connection:
        if self._conn is None:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self._conn = sqlite3.connect(str(self.db_path))
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL")
        return self._conn

    def init_db(self) -> None:
        """Create all tables and indexes."""
        conn = self._connect()
        conn.executescript(SCHEMA_SQL)
        conn.commit()

    def _mk_dedupe_key(self, event_type: str, title: str, body: str, priority: str) -> str:
        basis = f"{event_type}|{priority}|{title}|{body}".encode("utf-8")
        return hashlib.sha256(basis).hexdigest()[:24]

    def _is_duplicate(self, conn: sqlite3.Connection, dedupe_key: str, ttl: int) -> bool:
        row = conn.execute(
            "SELECT last_sent_at FROM dedupe WHERE dedupe_key=?", (dedupe_key,)
        ).fetchone()
        if not row:
            return False
        return (time.time() - float(row["last_sent_at"])) < ttl

    def _mark_sent(self, conn: sqlite3.Connection, dedupe_key: str) -> None:
        conn.execute(
            "INSERT INTO dedupe(dedupe_key,last_sent_at) VALUES (?,?) "
            "ON CONFLICT(dedupe_key) DO UPDATE SET last_sent_at=excluded.last_sent_at",
            (dedupe_key, time.time()),
        )

    def send(
        self,
        target: str,
        event_type: str,
        title: str,
        body: str,
        priority: str = "normal",
        delivery: str = "text_only",
        action_text: str = "",
        requires_ack: bool = False,
        ttl_seconds: int = 900,
        dedupe_key: str = "",
        metadata: Optional[dict] = None,
        correlation_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """Send an event to a target agent."""
        conn = self._connect()

        corr = correlation_id or f"evt-{uuid.uuid4()}"
        dk = dedupe_key or self._mk_dedupe_key(event_type, title, body, priority)

        # Check dedupe
        if self._is_duplicate(conn, dk, ttl_seconds):
            event_id = self._insert_event(conn, corr, event_type, priority, delivery,
                                          title, body, action_text, requires_ack,
                                          ttl_seconds, dk, "deduped", target, metadata)
            conn.commit()
            return {"ok": True, "deduped": True, "event_id": event_id, "correlation_id": corr}

        event_id = self._insert_event(conn, corr, event_type, priority, delivery,
                                      title, body, action_text, requires_ack,
                                      ttl_seconds, dk, "pending", target, metadata)

        # Mark sent for dedupe tracking
        self._mark_sent(conn, dk)
        conn.execute("UPDATE events SET status='sent' WHERE id=?", (event_id,))
        conn.commit()

        return {
            "ok": True,
            "deduped": False,
            "event_id": event_id,
            "correlation_id": corr,
        }

    def _insert_event(self, conn, corr, event_type, priority, delivery,
                      title, body, action_text, requires_ack,
                      ttl_seconds, dedupe_key, status, target, metadata) -> int:
        cur = conn.execute(
            """INSERT INTO events(
                correlation_id,event_type,injection_type,priority,delivery,
                source,target,title,body,action_text,requires_ack,
                ttl_seconds,dedupe_key,status,metadata_json
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (corr, event_type, "event_injection", priority, delivery,
             self.agent_id, target, title, body, action_text,
             int(requires_ack), ttl_seconds, dedupe_key, status,
             json.dumps(metadata or {})),
        )
        return int(cur.lastrowid)

    def poll(
        self,
        status: str = "sent",
        limit: int = 10,
        priority: Optional[str] = None,
    ) -> list[dict]:
        """Poll for messages targeting this agent."""
        conn = self._connect()
        query = "SELECT * FROM events WHERE target=? AND status=?"
        params: list[Any] = [self.agent_id, status]
        if priority:
            query += " AND priority=?"
            params.append(priority)
        query += " ORDER BY CASE priority WHEN 'critical' THEN 0 WHEN 'high' THEN 1 WHEN 'normal' THEN 2 ELSE 3 END, created_at ASC LIMIT ?"
        params.append(limit)
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]

    def ack(
        self,
        event_id: int,
        ack_type: str = "manual",
        ack_text: str = "Acknowledged.",
        intent: str = "ack",
    ) -> dict[str, Any]:
        """Acknowledge an event."""
        conn = self._connect()
        conn.execute(
            "INSERT INTO acks(event_id,ack_type,ack_text,source,intent) VALUES (?,?,?,?,?)",
            (event_id, ack_type, ack_text, self.agent_id, intent),
        )
        conn.execute("UPDATE events SET status='acked' WHERE id=?", (event_id,))
        conn.commit()
        return {"ok": True, "event_id": event_id, "acked": True}

    def ingest_reply(self, text: str, event_id: Optional[int] = None) -> dict[str, Any]:
        """Parse a natural language reply and apply the detected intent."""
        parsed = parse_reply_intent(text)
        if parsed.intent == "unknown":
            return {"ok": True, "applied": False, "reason": "unknown_intent", "text": parsed.normalized}

        conn = self._connect()

        if event_id is None:
            # Find most recent actionable event for this agent
            row = conn.execute(
                """SELECT * FROM events
                   WHERE target=? AND status IN ('pending','sent','partial_failure')
                   AND requires_ack=1
                   ORDER BY created_at DESC LIMIT 1""",
                (self.agent_id,),
            ).fetchone()
            if not row:
                return {"ok": True, "applied": False, "reason": "no_actionable_event"}
            event_id = int(row["id"])

        self.ack(event_id, ack_type="auto", ack_text=text, intent=parsed.intent)

        return {
            "ok": True,
            "applied": True,
            "event_id": event_id,
            "intent": parsed.intent,
            "normalized": parsed.normalized,
            "duration_seconds": parsed.duration_seconds,
        }

    def events(self, limit: int = 20, target: Optional[str] = None) -> list[dict]:
        """List recent events."""
        conn = self._connect()
        if target:
            rows = conn.execute(
                "SELECT * FROM events WHERE target=? ORDER BY id DESC LIMIT ?",
                (target, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM events ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(r) for r in rows]

    def add_template(self, template) -> int:
        """Add or update a message template."""
        conn = self._connect()
        conn.execute(
            """INSERT INTO templates(name,injection_type,priority,delivery,
               title_template,body_template,action_template,requires_ack,ttl_seconds,enabled)
               VALUES (?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(name) DO UPDATE SET
               injection_type=excluded.injection_type,priority=excluded.priority,
               delivery=excluded.delivery,title_template=excluded.title_template,
               body_template=excluded.body_template,action_template=excluded.action_template,
               requires_ack=excluded.requires_ack,ttl_seconds=excluded.ttl_seconds,
               enabled=excluded.enabled,updated_at=datetime('now')""",
            (template.name, template.injection_type, template.priority,
             template.delivery, template.title_template, template.body_template,
             template.action_template, int(template.requires_ack),
             template.ttl_seconds, int(template.enabled)),
        )
        conn.commit()
        row = conn.execute("SELECT id FROM templates WHERE name=?", (template.name,)).fetchone()
        return int(row["id"])

    def add_peer(self, agent_id: str, name: str = "", url: str = "", auth_token: str = "") -> None:
        """Register a peer agent for cross-agent messaging."""
        conn = self._connect()
        conn.execute(
            """INSERT INTO peers(agent_id,name,url,auth_token)
               VALUES (?,?,?,?)
               ON CONFLICT(agent_id) DO UPDATE SET
               name=excluded.name,url=excluded.url,
               auth_token=excluded.auth_token,active=1""",
            (agent_id, name, url, auth_token),
        )
        conn.commit()

    def peers(self) -> list[dict]:
        """List registered peer agents."""
        conn = self._connect()
        rows = conn.execute("SELECT * FROM peers WHERE active=1 ORDER BY agent_id").fetchall()
        return [dict(r) for r in rows]

    def stats(self) -> dict[str, Any]:
        """Get message queue statistics."""
        conn = self._connect()
        total = conn.execute("SELECT COUNT(*) as c FROM events").fetchone()["c"]
        pending = conn.execute("SELECT COUNT(*) as c FROM events WHERE status='pending'").fetchone()["c"]
        sent = conn.execute("SELECT COUNT(*) as c FROM events WHERE status='sent'").fetchone()["c"]
        acked = conn.execute("SELECT COUNT(*) as c FROM events WHERE status='acked'").fetchone()["c"]
        deduped = conn.execute("SELECT COUNT(*) as c FROM events WHERE status='deduped'").fetchone()["c"]
        return {
            "total": total,
            "pending": pending,
            "sent": sent,
            "acked": acked,
            "deduped": deduped,
            "agent_id": self.agent_id,
        }
