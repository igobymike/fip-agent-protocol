#!/usr/bin/env python3
"""FIP database initialization and helpers."""
import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS events(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  correlation_id TEXT NOT NULL UNIQUE,
  event_type TEXT NOT NULL,
  priority TEXT NOT NULL DEFAULT 'normal',
  source TEXT NOT NULL,
  target TEXT NOT NULL DEFAULT '',
  title TEXT NOT NULL,
  body TEXT NOT NULL,
  action_text TEXT,
  requires_ack INTEGER NOT NULL DEFAULT 0,
  ttl_seconds INTEGER NOT NULL DEFAULT 900,
  dedupe_key TEXT NOT NULL DEFAULT '',
  status TEXT NOT NULL DEFAULT 'pending',
  metadata_json TEXT DEFAULT '{}',
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS acks(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  event_id INTEGER NOT NULL,
  ack_type TEXT NOT NULL,
  ack_text TEXT,
  source TEXT DEFAULT '',
  intent TEXT DEFAULT 'ack',
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  FOREIGN KEY(event_id) REFERENCES events(id)
);

CREATE TABLE IF NOT EXISTS enrollments(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  agent_address TEXT UNIQUE NOT NULL,
  agent_name TEXT,
  endpoint TEXT,
  public_key TEXT,
  trust_level TEXT NOT NULL DEFAULT 'unknown',
  permissions_json TEXT DEFAULT '["send_messages"]',
  rate_limit TEXT DEFAULT '10/hour',
  direction TEXT NOT NULL DEFAULT 'inbound',
  status TEXT NOT NULL DEFAULT 'unknown',
  reason TEXT,
  message_count INTEGER DEFAULT 0,
  last_message_at TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS dedupe(
  dedupe_key TEXT UNIQUE NOT NULL,
  last_sent_at REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_events_target ON events(target, status);
CREATE INDEX IF NOT EXISTS idx_enrollments_address ON enrollments(agent_address);
"""

def init_db(db_path: str) -> None:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.commit()
    conn.close()
