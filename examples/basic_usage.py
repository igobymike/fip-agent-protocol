#!/usr/bin/env python3
"""Basic FIP usage — send messages between two agents."""

from fip import FIPClient

# === Agent A (the coordinator) ===

coordinator = FIPClient(db_path="coordinator.db", agent_id="agent:coordinator")
coordinator.init_db()

# Send a task to a worker agent
result = coordinator.send(
    target="agent:worker-01",
    event_type="task.delegate",
    priority="high",
    title="Build the API",
    body="Implement FastAPI backend with /health and /chat endpoints. See spec in docs/.",
    action_text="Start work and report when done.",
    requires_ack=True,
    ttl_seconds=3600,
)
print(f"Sent: {result}")
# {"ok": True, "event_id": 1, "correlation_id": "evt-abc...", "deduped": False}


# === Agent B (the worker) ===

worker = FIPClient(db_path="coordinator.db", agent_id="agent:worker-01")
# In production, this would be a separate DB on a separate machine.
# Using same DB here for demo simplicity.

# Poll for incoming messages
messages = worker.poll()
for msg in messages:
    print(f"\n[{msg['priority'].upper()}] {msg['title']}")
    print(f"  From: {msg['source']}")
    print(f"  Body: {msg['body']}")
    print(f"  Action: {msg['action_text']}")

    # Acknowledge the message
    worker.ack(msg["id"], ack_text="Starting work now.")

# Check stats
print(f"\nCoordinator stats: {coordinator.stats()}")
print(f"Worker stats: {worker.stats()}")
