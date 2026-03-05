#!/usr/bin/env python3
"""Manage FIP enrollments (contacts)."""
import argparse
import json
import sqlite3
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

def get_db():
    config = load_config()
    conn = sqlite3.connect(config["database"]["path"])
    conn.row_factory = sqlite3.Row
    return conn

def cmd_list(args):
    conn = get_db()
    rows = conn.execute(
        "SELECT agent_address, agent_name, trust_level, status, direction, message_count, last_message_at "
        "FROM enrollments ORDER BY status, agent_address"
    ).fetchall()
    if not rows:
        print("No contacts yet.")
        return
    for r in rows:
        status_icon = {"approved": "✅", "trusted": "⭐", "requested": "⏳", "blocked": "🚫", "denied": "❌"}.get(r["status"], "❓")
        direction = "→" if r["direction"] == "outbound" else "←"
        print(f"  {status_icon} {direction} {r['agent_address']} ({r['agent_name'] or '?'}) — {r['status']} | msgs: {r['message_count']}")

def cmd_request(args):
    conn = get_db()
    conn.execute(
        """INSERT INTO enrollments(agent_address, agent_name, direction, status, reason, updated_at)
           VALUES (?, ?, 'outbound', 'requested', ?, datetime('now'))
           ON CONFLICT(agent_address) DO UPDATE SET status='requested', reason=excluded.reason, updated_at=datetime('now')""",
        (args.address, args.address.split("@")[0], args.reason)
    )
    conn.commit()
    print(json.dumps({"ok": True, "action": "enrollment_requested", "address": args.address}))

def cmd_approve(args):
    conn = get_db()
    conn.execute(
        "UPDATE enrollments SET status='approved', trust_level='approved', updated_at=datetime('now') WHERE agent_address=?",
        (args.address,)
    )
    conn.commit()
    print(json.dumps({"ok": True, "action": "approved", "address": args.address}))

def cmd_deny(args):
    conn = get_db()
    conn.execute(
        "UPDATE enrollments SET status='denied', updated_at=datetime('now') WHERE agent_address=?",
        (args.address,)
    )
    conn.commit()
    print(json.dumps({"ok": True, "action": "denied", "address": args.address}))

def cmd_block(args):
    conn = get_db()
    conn.execute(
        "UPDATE enrollments SET status='blocked', trust_level='blocked', updated_at=datetime('now') WHERE agent_address=?",
        (args.address,)
    )
    conn.commit()
    print(json.dumps({"ok": True, "action": "blocked", "address": args.address}))

def cmd_remove(args):
    conn = get_db()
    conn.execute("DELETE FROM enrollments WHERE agent_address=?", (args.address,))
    conn.commit()
    print(json.dumps({"ok": True, "action": "removed", "address": args.address}))

def main():
    parser = argparse.ArgumentParser(description="Manage FIP contacts")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list")

    p_req = sub.add_parser("request")
    p_req.add_argument("address", help="Agent address to request enrollment with")
    p_req.add_argument("--reason", default="", help="Reason for enrollment")

    p_app = sub.add_parser("approve")
    p_app.add_argument("address")

    p_deny = sub.add_parser("deny")
    p_deny.add_argument("address")

    p_block = sub.add_parser("block")
    p_block.add_argument("address")

    p_rm = sub.add_parser("remove")
    p_rm.add_argument("address")

    args = parser.parse_args()
    {"list": cmd_list, "request": cmd_request, "approve": cmd_approve,
     "deny": cmd_deny, "block": cmd_block, "remove": cmd_remove}[args.command](args)

if __name__ == "__main__":
    main()
