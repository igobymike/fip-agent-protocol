# FIP — Forced Injection Protocol

**Async agent-to-agent messaging for AI systems**

> Priority-aware. Auditable. SQLite-backed. Built for autonomous AI agents that need to talk to each other.

[![Built by BAITEKS](https://img.shields.io/badge/Built%20by-BAITEKS-0066cc)](https://baiteks.com)
[![License](https://img.shields.io/badge/License-MIT-green)]()
[![Python](https://img.shields.io/badge/Python-3.10+-blue)]()

---

## What Is FIP?

FIP is a **message protocol for AI agents**. It lets autonomous agents send messages to each other — across processes, machines, and networks — with built-in priority handling, deduplication, retry logic, acknowledgment tracking, and a full audit trail.

Think of it as a **message broker designed specifically for AI agent communication**, backed by SQLite so it's zero-dependency, portable, and inspectable.

**Born from production.** FIP was built to solve a real problem: an AI operating partner (Marcus) running on a VPS needed a reliable way to deliver urgent messages, reminders, and alerts to a human operator and other agents across multiple machines. The protocol evolved from simple text injection into a full agent-to-agent communication system.

---

## Why Not Just Use HTTP / WebSockets / Message Queues?

You could. But FIP solves problems those don't:

| Problem | HTTP/WS/MQ | FIP |
|---------|-----------|-----|
| Agent is offline when message is sent | Message lost | Persisted in SQLite, delivered when agent polls |
| Same alert fires 10 times in 5 minutes | 10 duplicate messages | Deduped by content hash within TTL window |
| Critical alert during low-priority work | No priority system | 4-level priority with interrupt capability |
| "Did the other agent actually get this?" | Hope | Ack/nack tracking with retry + backoff |
| "What messages were sent last Tuesday?" | Check logs maybe | Full audit trail in SQLite — every event, delivery, ack |
| Agent needs to snooze/defer a message | Build it yourself | Built-in snooze, stop, run-now reply intents |
| Late night — don't bother the human | Build quiet hours | Quiet hours per schedule, except critical |
| Need templates for recurring alerts | Build it yourself | Template engine with variable substitution |

**FIP is opinionated about reliability.** Every message is persisted before delivery is attempted. Every delivery attempt is logged. Every ack is recorded. Nothing is fire-and-forget.

---

## Core Concepts

### Events
An event is a message. It has a type, priority, title, body, and delivery preference.

```python
{
    "event_type": "agent.task_complete",
    "priority": "high",
    "delivery": "text_and_tts",
    "title": "Build step 3 complete",
    "body": "FastAPI backend is up and passing health checks. Ready for Step 4.",
    "source": "agent:coding-worker-01",
    "target": "agent:marcus",
    "requires_ack": True,
    "ttl_seconds": 900
}
```

### Priority Levels
| Level | When to Use | Behavior |
|-------|------------|----------|
| `critical` | System failure, safety issue | Interrupts active work, bypasses quiet hours |
| `high` | Urgent operational item | Delivered immediately, respects quiet hours |
| `normal` | Standard communication | Delivered on next poll cycle |
| `low` | FYI, batched suggestions | May be batched or deferred |

### Delivery Modes
| Mode | What Happens |
|------|-------------|
| `text_only` | Injected into target agent's session as text |
| `tts_only` | Spoken aloud via TTS (if target has audio) |
| `text_and_tts` | Both — text injection + voice announcement |
| `webhook` | POST to a URL endpoint |
| `agent_inject` | Direct injection into another OpenClaw agent session |

### Deduplication
Every event gets a `dedupe_key` (auto-generated from content hash or manually specified). If the same dedupe_key was sent within the TTL window, the message is suppressed. No duplicate spam.

### Acknowledgments
Events with `requires_ack=True` track whether the recipient acknowledged the message. If no ack within the retry window, FIP re-sends with exponential backoff:

```
Attempt 1: immediate
Attempt 2: +60 seconds
Attempt 3: +180 seconds
Attempt 4: +600 seconds
Final: escalation note
```

### Reply Intents
Recipients can respond naturally, and FIP parses the intent:

| Reply | Parsed Intent | Action |
|-------|--------------|--------|
| "got it" / "ok" / "done" | `ack` | Mark acknowledged, stop retries |
| "stop" / "cancel" / "don't remind" | `stop` | Deactivate the schedule |
| "snooze 30 minutes" | `snooze` | Reschedule delivery for +30min |
| "run it now" / "do it" | `run_now` | Execute immediately |

### Templates
Define reusable message templates with variable substitution:

```python
# Template definition
{
    "name": "task_complete",
    "title_template": "Task {task_id} Complete",
    "body_template": "{agent_name} finished {task_description}. Duration: {duration}.",
    "priority": "normal",
    "delivery": "text_and_tts"
}

# Usage
fip dispatch --template task_complete \
    --var task_id=TSK-142 \
    --var agent_name="coding-worker-01" \
    --var task_description="API endpoint implementation" \
    --var duration="47 minutes"
```

### Schedules
One-shot or recurring message delivery:

```bash
# One-shot: remind at specific time
fip schedule add --name "standup-reminder" \
    --run-at "2026-03-05 14:00:00" \
    --template-id 3

# Recurring: every 20 minutes
fip schedule add-recurring --name "heartbeat-check" \
    --every-seconds 1200 \
    --template-id 5 \
    --quiet-hours '{"start": "23:00", "end": "08:00", "tz": "America/Chicago"}'
```

---

## Agent-to-Agent Communication

### The Architecture

```
┌─────────────────┐         ┌──────────────────┐
│   Agent A        │         │   Agent B         │
│   (VPS)          │         │   (OVH Server)    │
│                  │         │                   │
│  ┌────────────┐  │   FIP   │  ┌─────────────┐ │
│  │ FIP Client │──┼────────→│  │ FIP Server   │ │
│  └────────────┘  │  HTTP   │  └─────────────┘ │
│                  │         │        │          │
│  ┌────────────┐  │         │  ┌─────▼───────┐ │
│  │ FIP Server │←─┼─────────┤  │ FIP Client  │ │
│  └────────────┘  │  HTTP   │  └─────────────┘ │
│        │         │         │                   │
│  ┌─────▼──────┐  │         │  ┌─────────────┐ │
│  │  SQLite    │  │         │  │  SQLite      │ │
│  │  (events,  │  │         │  │  (events,    │ │
│  │  acks,     │  │         │  │  acks,       │ │
│  │  delivery) │  │         │  │  delivery)   │ │
│  └────────────┘  │         │  └─────────────┘ │
└─────────────────┘         └──────────────────┘
```

Each agent runs both a **FIP Server** (receives messages) and a **FIP Client** (sends messages). Every agent has its own SQLite database — no shared state, no central broker.

### How It Works

**Agent A wants to tell Agent B something:**

1. Agent A creates an event targeting Agent B
2. FIP Client serializes the event and POSTs it to Agent B's FIP Server endpoint
3. Agent B's FIP Server validates, dedupes, persists to its local SQLite
4. Agent B's FIP Server delivers the message (text injection, TTS, or both)
5. Agent B processes the message and sends an ack back to Agent A
6. Agent A's FIP Server records the ack

**If Agent B is offline:**
- Agent A's FIP Client retries with exponential backoff
- The event stays in Agent A's outbox until delivered or TTL expires
- When Agent B comes online, pending messages are delivered in priority order

### Multi-Agent Topology

```
                    ┌──────────────┐
                    │   Marcus     │
                    │   (primary)  │
                    └──────┬───────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
        ┌─────▼─────┐ ┌───▼────┐ ┌────▼─────┐
        │ Coding     │ │ Monitor│ │ Research  │
        │ Agent      │ │ Agent  │ │ Agent     │
        └───────────┘ └────────┘ └──────────┘
```

- **Marcus** delegates a coding task → FIP event to Coding Agent
- **Coding Agent** completes the task → FIP event back to Marcus with results
- **Monitor Agent** detects a service outage → FIP critical event to Marcus
- **Marcus** tells Monitor Agent to restart the service → FIP command event
- **Research Agent** finds relevant information → FIP event to Marcus with findings

All communication is **async, persistent, auditable, and priority-ordered.**

---

## Use Cases

### 1. Task Delegation
```python
# Marcus delegates a coding task
fip.send(
    target="agent:coding-worker",
    event_type="task.delegate",
    priority="normal",
    title="Build synthetic data generator",
    body="Generate 3,000 realistic turnaround activities. See spec at docs/GAMEPLAN.md Step 2.",
    requires_ack=True
)

# Coding worker reports completion
fip.send(
    target="agent:marcus",
    event_type="task.complete",
    priority="high",
    title="TSK-142 Complete",
    body="Synthetic data generator done. 3,000 activities generated. Tests passing.",
    action_text="Review output at data/synthetic_schedule.db"
)
```

### 2. Health Monitoring & Alerts
```python
# Monitor agent detects service down
fip.send(
    target="agent:marcus",
    event_type="alert.service_down",
    priority="critical",
    title="Voice server DOWN",
    body="marcus-voice not responding on port 8770. Last healthy: 3 minutes ago.",
    action_text="Investigate and restart. Do NOT restart via SSH (Session 0 limitation).",
    requires_ack=True
)
```

### 3. Scheduled Coordination
```python
# Every morning at 8 AM, research agent sends market brief
fip.schedule_recurring(
    name="morning-brief",
    every_seconds=86400,
    target="agent:marcus",
    template="daily_research_brief",
    quiet_hours={"start": "23:00", "end": "07:00", "tz": "America/Chicago"}
)
```

### 4. Human-in-the-Loop
```python
# Agent needs human approval before proceeding
fip.send(
    target="human:mike",
    event_type="approval.required",
    priority="high",
    delivery="text_and_tts",
    title="Deployment Approval Needed",
    body="P6 Intelligence v0.2 is ready to deploy to production. All tests passing.",
    action_text="Reply 'do it' to approve or 'snooze 2 hours' to defer.",
    requires_ack=True
)

# Human replies via voice: "do it now"
# FIP reply parser detects intent: run_now
# Agent receives ack with intent → proceeds with deployment
```

### 5. Cross-Machine Agent Swarm
```python
# Coordinator on VPS delegates to workers on OVH
for task in task_list:
    fip.send(
        target=f"agent:worker-{task.assigned_to}",
        event_type="task.delegate",
        priority=task.priority,
        title=f"Task {task.id}: {task.name}",
        body=task.brief,
        requires_ack=True,
        ttl_seconds=3600
    )

# Workers report back as they complete
# Coordinator tracks progress via ack stream
```

---

## Database Schema

FIP uses SQLite with WAL mode. Zero external dependencies. Portable. Inspectable with any SQLite client.

### Tables

| Table | Purpose |
|-------|---------|
| `events` | Every message ever sent or received — the core audit trail |
| `deliveries` | Every delivery attempt — channel, status, latency |
| `acks` | Every acknowledgment — type, text, timestamp |
| `templates` | Reusable message templates with variable substitution |
| `schedules` | One-shot and recurring scheduled messages |
| `rules` | Trigger rules that auto-fire events based on conditions |
| `dedupe` | Deduplication state — prevents duplicate spam |

### Event Lifecycle

```
CREATED → PENDING → SENT → ACKED
                  ↘ PARTIAL_FAILURE → RETRY → SENT
                  ↘ DEDUPED (suppressed)
```

---

## Installation

```bash
pip install fip-protocol
# or
git clone https://github.com/igobymike/fip-agent-protocol.git
cd fip-agent-protocol
pip install -e .
```

### Requirements
- Python 3.10+
- SQLite 3.35+ (included with Python)
- No other dependencies for core protocol
- Optional: `uvicorn` + `fastapi` for HTTP server mode

---

## Quick Start

### 1. Initialize the Database

```python
from fip import FIPClient

client = FIPClient(db_path="fip.db")
client.init_db()
```

### 2. Send a Message

```python
result = client.send(
    target="agent:marcus",
    event_type="greeting",
    priority="normal",
    title="Hello from Worker",
    body="I'm online and ready for tasks."
)
print(result)
# {"ok": True, "event_id": 1, "correlation_id": "evt-abc123"}
```

### 3. Check for Messages (Polling)

```python
messages = client.poll(
    agent_id="agent:marcus",
    status="pending",
    limit=10
)
for msg in messages:
    print(f"[{msg.priority}] {msg.title}: {msg.body}")
    client.ack(msg.event_id)
```

### 4. Run the HTTP Server

```bash
fip serve --port 8780 --agent-id "agent:marcus"
```

Other agents can now POST events to `http://your-host:8780/fip/events`.

### 5. CLI Usage

```bash
# Send a message
fip send --target "agent:worker-01" \
    --title "New Task" \
    --body "Build the frontend" \
    --priority high \
    --requires-ack

# Check incoming messages
fip inbox --agent-id "agent:marcus" --limit 5

# Acknowledge a message
fip ack --event-id 42

# List recent events
fip events --limit 20

# Create a template
fip template add --name "task_complete" \
    --title-template "Task {task_id} Complete" \
    --body-template "{agent} finished {description}" \
    --priority normal

# Schedule a recurring message
fip schedule add-recurring --name "health-check" \
    --every-seconds 600 \
    --template-id 1
```

---

## Configuration

```yaml
# fip.yaml
agent:
  id: "agent:marcus"
  name: "Marcus"

database:
  path: "fip.db"

server:
  port: 8780
  host: "0.0.0.0"
  auth_token: "your-secret-token"

delivery:
  text:
    method: "openclaw_inject"  # or "webhook", "stdout"
    session_key: "agent:main:main"
  tts:
    method: "voice_server"  # or "elevenlabs", "local", "none"
    url: "http://127.0.0.1:8770/inject/announce"
  webhook:
    url: "https://your-endpoint.com/fip/receive"
    headers:
      Authorization: "Bearer your-token"

peers:
  - id: "agent:coding-worker"
    url: "http://100.71.157.108:8780/fip"
    auth_token: "worker-token"
  - id: "agent:monitor"
    url: "http://localhost:8781/fip"
    auth_token: "monitor-token"
  - id: "human:mike"
    delivery: "text_and_tts"

retry:
  max_attempts: 4
  backoff: [0, 60, 180, 600]

quiet_hours:
  start: "23:00"
  end: "08:00"
  timezone: "America/Chicago"
  except: ["critical"]
```

---

## Protocol Spec

### Event Envelope (JSON)

```json
{
    "protocol": "fip/1.0",
    "event_id": "evt-550e8400-e29b-41d4-a716-446655440000",
    "event_type": "task.delegate",
    "source": "agent:marcus",
    "target": "agent:coding-worker",
    "priority": "high",
    "delivery": "text_and_tts",
    "title": "Build Step 3",
    "body": "Implement the FastAPI backend. See docs/GAMEPLAN.md for spec.",
    "action_text": "Start work and report progress.",
    "requires_ack": true,
    "ttl_seconds": 3600,
    "dedupe_key": "task-delegate-step3-20260305",
    "correlation_id": "task-step3-001",
    "created_at": "2026-03-05T04:30:00Z",
    "metadata": {
        "task_id": "TSK-142",
        "estimated_hours": 3,
        "spec_path": "docs/GAMEPLAN.md#step-3"
    }
}
```

### Ack Envelope (JSON)

```json
{
    "protocol": "fip/1.0",
    "ack_type": "received",
    "event_id": "evt-550e8400-e29b-41d4-a716-446655440000",
    "source": "agent:coding-worker",
    "target": "agent:marcus",
    "intent": "ack",
    "text": "Got it. Starting now.",
    "created_at": "2026-03-05T04:30:05Z"
}
```

### HTTP API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `POST /fip/events` | POST | Send an event to this agent |
| `GET /fip/events` | GET | List events (with filters) |
| `GET /fip/events/{id}` | GET | Get a specific event |
| `POST /fip/ack` | POST | Acknowledge an event |
| `GET /fip/health` | GET | Agent health + message queue stats |
| `POST /fip/templates` | POST | Create/update a template |
| `GET /fip/templates` | GET | List templates |
| `POST /fip/schedules` | POST | Create a schedule |
| `GET /fip/schedules` | GET | List schedules |

---

## OpenClaw Integration

FIP was built for [OpenClaw](https://github.com/openclaw/openclaw) agents. Native integration:

### Inject into Agent Session
```python
# FIP delivers a message directly into an OpenClaw agent's chat session
delivery_config = {
    "method": "openclaw_inject",
    "session_key": "agent:main:main",
    "label": "fip-delivery"
}
```

### Voice Delivery
```python
# FIP speaks through the agent's TTS pipeline
delivery_config = {
    "method": "voice_server",
    "url": "http://127.0.0.1:8770/inject/announce"
}
```

### Heartbeat Integration
Agents can check for pending FIP messages during their heartbeat cycle:

```python
# In HEARTBEAT.md workflow
pending = fip.poll(agent_id="agent:marcus", status="pending")
if pending:
    for msg in pending:
        process(msg)
        fip.ack(msg.event_id)
```

---

## Origin Story

FIP started as a hack. Marcus — an AI operating partner running on a VPS — needed to deliver backup reminders to his human operator. A simple `openclaw system event` injection worked, but there was no deduplication (the same reminder fired 10 times), no acknowledgment tracking (did the human see it?), no retry logic (what if the session was disconnected?), and no audit trail (what was sent when?).

So we built a protocol. SQLite for persistence. Templates for recurring messages. Dedupe for sanity. Acks for confirmation. Retry with backoff for reliability. Priority levels for triage. Quiet hours for sleep.

Then we realized: **if one agent can reliably message a human, agents can reliably message each other.** Same protocol, same guarantees, different targets. Add addressable routing, peer discovery, and HTTP transport — and you have a full agent-to-agent communication system.

FIP is now the messaging backbone for a multi-agent system spanning a VPS, a dedicated server, and a Windows laptop. It handles task delegation, health alerts, status reports, and human-in-the-loop approvals — all async, all auditable, all persistent.

---

## Roadmap

- [x] Core protocol (events, deliveries, acks, dedupe)
- [x] Template engine with variable substitution
- [x] Scheduler (one-shot + recurring)
- [x] Reply intent parser (ack, stop, snooze, run_now)
- [x] OpenClaw session injection delivery
- [x] Voice server TTS delivery
- [ ] HTTP server mode (FastAPI)
- [ ] Peer discovery and registration
- [ ] Outbox pattern (store-and-forward for offline peers)
- [ ] Webhook delivery mode
- [ ] End-to-end encryption (agent-to-agent)
- [ ] Web dashboard for event inspection
- [ ] PyPI package (`pip install fip-protocol`)

---

## License

MIT — use it, fork it, build on it.

---

## Author

**Mike Birklett** — [baiteks.com](https://baiteks.com)
Built by [BAITEKS](https://baiteks.com) — Business & AI Technology Solutions

*Born from production. Built for agents.*
