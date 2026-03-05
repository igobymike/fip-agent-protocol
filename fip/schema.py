"""SQLite schema for FIP database."""

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS events(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  correlation_id TEXT NOT NULL UNIQUE,
  event_type TEXT NOT NULL,
  injection_type TEXT NOT NULL,
  priority TEXT NOT NULL,
  delivery TEXT NOT NULL,
  source TEXT NOT NULL,
  target TEXT NOT NULL DEFAULT '',
  title TEXT NOT NULL,
  body TEXT NOT NULL,
  action_text TEXT,
  requires_ack INTEGER NOT NULL DEFAULT 0,
  ttl_seconds INTEGER NOT NULL,
  dedupe_key TEXT NOT NULL,
  status TEXT NOT NULL,
  metadata_json TEXT DEFAULT '{}',
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS deliveries(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  event_id INTEGER NOT NULL,
  channel TEXT NOT NULL,
  status TEXT NOT NULL,
  detail TEXT,
  latency_ms INTEGER,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  FOREIGN KEY(event_id) REFERENCES events(id)
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

CREATE TABLE IF NOT EXISTS templates(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT UNIQUE NOT NULL,
  injection_type TEXT NOT NULL,
  priority TEXT NOT NULL,
  delivery TEXT NOT NULL,
  title_template TEXT NOT NULL,
  body_template TEXT NOT NULL,
  action_template TEXT,
  requires_ack INTEGER NOT NULL DEFAULT 0,
  ttl_seconds INTEGER NOT NULL DEFAULT 900,
  enabled INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS schedules(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT UNIQUE NOT NULL,
  run_at TEXT NOT NULL,
  next_run_at TEXT,
  last_run_at TEXT,
  template_id INTEGER NOT NULL,
  payload_json TEXT,
  every_seconds INTEGER,
  max_attempts INTEGER,
  attempts INTEGER NOT NULL DEFAULT 0,
  requires_ack INTEGER NOT NULL DEFAULT 0,
  quiet_hours_json TEXT,
  active INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now')),
  FOREIGN KEY(template_id) REFERENCES templates(id)
);

CREATE TABLE IF NOT EXISTS dedupe(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  dedupe_key TEXT UNIQUE NOT NULL,
  last_sent_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS peers(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  agent_id TEXT UNIQUE NOT NULL,
  name TEXT,
  url TEXT,
  auth_token TEXT,
  last_seen_at TEXT,
  active INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_events_target_status ON events(target, status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_events_source ON events(source);
CREATE INDEX IF NOT EXISTS idx_events_priority ON events(priority, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_acks_event ON acks(event_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_schedules_active ON schedules(active, next_run_at);
CREATE INDEX IF NOT EXISTS idx_peers_agent_id ON peers(agent_id);
"""
