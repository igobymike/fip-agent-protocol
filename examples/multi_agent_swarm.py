#!/usr/bin/env python3
"""Multi-agent task delegation with FIP.

Demonstrates a coordinator delegating tasks to multiple workers,
tracking completion, and handling results.
"""

from fip import FIPClient

# Initialize agents
coordinator = FIPClient(db_path="swarm.db", agent_id="agent:coordinator")
coordinator.init_db()

# Register peers
coordinator.add_peer("agent:worker-frontend", name="Frontend Worker", url="http://localhost:8781/fip")
coordinator.add_peer("agent:worker-backend", name="Backend Worker", url="http://localhost:8782/fip")
coordinator.add_peer("agent:worker-data", name="Data Worker", url="http://localhost:8783/fip")

# Delegate tasks
tasks = [
    ("agent:worker-frontend", "Build chat UI", "Implement the React chat interface with tiles and markdown rendering."),
    ("agent:worker-backend", "Build API endpoints", "Implement FastAPI routes: /api/chat, /api/projects, /api/health."),
    ("agent:worker-data", "Generate synthetic data", "Populate P6 database with 3,000 realistic turnaround activities."),
]

print("=== Delegating tasks ===\n")
for target, title, body in tasks:
    result = coordinator.send(
        target=target,
        event_type="task.delegate",
        priority="high",
        title=title,
        body=body,
        requires_ack=True,
        ttl_seconds=7200,
        metadata={"project": "p6-intelligence", "phase": "build"},
    )
    print(f"  → {target}: {title} (event_id={result['event_id']})")

# Simulate workers polling and completing
print("\n=== Workers processing ===\n")
for agent_id, title, _ in tasks:
    worker = FIPClient(db_path="swarm.db", agent_id=agent_id)
    messages = worker.poll()
    for msg in messages:
        print(f"  [{agent_id}] Received: {msg['title']}")
        worker.ack(msg["id"], ack_text=f"Completed: {msg['title']}")

        # Worker reports back to coordinator
        worker.send(
            target="agent:coordinator",
            event_type="task.complete",
            priority="normal",
            title=f"Done: {msg['title']}",
            body=f"Task completed successfully. Ready for review.",
        )

# Coordinator checks results
print("\n=== Coordinator inbox ===\n")
results = coordinator.poll(status="sent")
for msg in results:
    print(f"  ← {msg['source']}: {msg['title']}")
    coordinator.ack(msg["id"])

print(f"\nFinal stats: {coordinator.stats()}")
