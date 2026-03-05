#!/usr/bin/env python3
"""Show FIP agent status."""
import json
import sqlite3
from pathlib import Path

import yaml

FIP_DIR = Path.home() / ".openclaw" / "fip"
CONFIG_PATH = FIP_DIR / "config.yaml"

def main():
    if not CONFIG_PATH.exists():
        print("FIP not configured. Run setup_wizard.py first.")
        return

    with open(CONFIG_PATH) as f:
        config = yaml.safe_load(f)

    db_path = config["database"]["path"]
    if not Path(db_path).exists():
        print("FIP database not found.")
        return

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    contacts = conn.execute("SELECT COUNT(*) as c FROM enrollments WHERE status='approved'").fetchone()["c"]
    pending = conn.execute("SELECT COUNT(*) as c FROM enrollments WHERE status='requested'").fetchone()["c"]
    total_msgs = conn.execute("SELECT COUNT(*) as c FROM events").fetchone()["c"]
    recent = conn.execute("SELECT COUNT(*) as c FROM events WHERE created_at > datetime('now', '-24 hours')").fetchone()["c"]

    print(f"""
FIP Agent Status
{'=' * 40}
  Address:  {config['agent']['address']}
  Name:     {config['agent']['name']}
  Server:   port {config['server']['port']}
  Database: {db_path}

Contacts:
  Enrolled: {contacts}
  Pending:  {pending}

Messages:
  Total:    {total_msgs}
  Last 24h: {recent}
""")

if __name__ == "__main__":
    main()
