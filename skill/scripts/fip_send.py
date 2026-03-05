#!/usr/bin/env python3
"""Send a FIP message to another agent."""
import argparse
import hashlib
import json
import sqlite3
import uuid
from pathlib import Path

import yaml

FIP_DIR = Path.home() / ".openclaw" / "fip"
CONFIG_PATH = FIP_DIR / "config.yaml"

def load_config():
    if not CONFIG_PATH.exists():
        print("Error: FIP not configured. Run setup_wizard.py first.")
        raise SystemExit(1)
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)

def main():
    parser = argparse.ArgumentParser(description="Send a FIP message")
    parser.add_argument("--to", required=True, help="Recipient agent address")
    parser.add_argument("--type", default="personal.message", help="Message type")
    parser.add_argument("--body", required=True, help="Message body")
    parser.add_argument("--title", default="", help="Message title")
    parser.add_argument("--priority", default="normal", choices=["critical", "high", "normal", "low"])
    parser.add_argument("--correlation", default="", help="Correlation ID for threading")
    parser.add_argument("--requires-ack", action="store_true")
    args = parser.parse_args()

    config = load_config()
    db_path = config["database"]["path"]
    source = config["agent"]["address"]

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    correlation_id = args.correlation or f"evt-{uuid.uuid4()}"
    title = args.title or f"Message from {config['agent']['name']}"
    dedupe_key = hashlib.sha256(f"{args.type}|{args.to}|{args.body}".encode()).hexdigest()[:24]

    conn.execute(
        """INSERT INTO events(correlation_id, event_type, priority, source, target,
           title, body, requires_ack, ttl_seconds, dedupe_key, status)
           VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        (correlation_id, args.type, args.priority, source, args.to,
         title, args.body, int(args.requires_ack), 900, dedupe_key, "queued")
    )
    conn.commit()

    # TODO: HTTP delivery to target endpoint (resolve via discovery)
    # For now: print confirmation
    print(json.dumps({
        "ok": True,
        "correlation_id": correlation_id,
        "from": source,
        "to": args.to,
        "type": args.type,
        "status": "queued"
    }, indent=2))

if __name__ == "__main__":
    main()
