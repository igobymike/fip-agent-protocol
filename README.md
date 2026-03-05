# FIP Agent Protocol

**Your AI talks to their AI.**

> The messaging protocol that lets personal AI agents communicate across the internet — like texting, but through your agents.

[![Built by BAITEKS](https://img.shields.io/badge/Built%20by-BAITEKS-0066cc)](https://baiteks.com)
[![License](https://img.shields.io/badge/License-MIT-green)]()
[![Python](https://img.shields.io/badge/Python-3.10+-blue)]()

---

## What Is This?

You have an AI agent. Your friend has an AI agent. **This protocol lets them talk to each other.**

```
You: "Marcus, tell Vonta what's up"

  Marcus ──→ Faye (Vonta's agent): "Mike says what's up"
  Faye ──→ Vonta: "Mike says what's up"
  Vonta: "Tell him I'm good, just got back from Dallas"
  Faye ──→ Marcus: "Vonta's good, just got back from Dallas"

Marcus: "Vonta's good, just got back from Dallas."
```

You didn't open an app. You didn't type a text. You talked to your agent, your agent talked to their agent, and the message got delivered. That's it.

---

## Why This Exists

Right now, AI agents are isolated. Your agent can talk to you. It can maybe run tasks on your machine. But it **can't reach out to your friend's agent, your coworker's agent, or anyone else's agent.**

There's no way for Marcus to message Faye. No protocol, no addressing, no trust system. Every agent is an island.

FIP Agent Protocol fixes that. It gives agents:

- **Addresses** — `marcus@marcus.baiteks.com`, `faye@vonta.example.com`
- **Discovery** — how to find another agent's endpoint on the internet
- **Enrollment** — a trust handshake (like adding a contact) before agents can communicate
- **Signed messages** — cryptographic proof that a message really came from who it claims
- **Reliable delivery** — messages persist until delivered, retry if the other agent is offline
- **Audit trail** — every message logged on both sides

---

## How It Works — The Big Picture

### 1. Each agent has an address

Like an email address, but for your AI:

```
marcus@marcus.baiteks.com
faye@vonta.example.com
scout@research.example.org
```

The domain part tells other agents where to find yours on the internet.

### 2. Agents discover each other

When Marcus wants to reach Faye, he looks up her address:

```
GET https://vonta.example.com/.well-known/fip.json

→ {
    "agents": [{
        "address": "faye@vonta.example.com",
        "endpoint": "https://vonta.example.com/fip/v1",
        "public_key": "ed25519:...",
        "enrollment": "approval_required"
    }]
  }
```

Now Marcus knows where to send messages and how to verify Faye's identity.

### 3. Enrollment — adding a contact

Before agents can talk, they need to be enrolled with each other. This is like a friend request:

```
Marcus → Faye: "Hey, I'm Marcus, Mike Birklett's agent. Mike and Vonta are friends.
                I'd like to be able to message you."

Vonta sees: "Marcus (Mike's agent) wants to connect. [Approve] [Deny]"

Vonta clicks Approve.

Now Marcus and Faye can message each other freely.
```

**Why enrollment matters:** Without it, any random agent on the internet could spam Faye with messages. Enrollment means only approved agents get through. Vonta decides who Faye talks to.

### 4. Agents exchange messages

Once enrolled, it's just messaging:

```
Marcus → Faye: "Mike wants to know if Vonta's free Saturday"
Faye checks Vonta's calendar → "He's free after 2 PM"
Faye → Marcus: "Vonta's free Saturday after 2"
Marcus → Mike: "Vonta's free after 2 on Saturday"
```

Every message is:
- **Signed** — proves it really came from Marcus (not an impersonator)
- **Persisted** — stored in SQLite on both sides (full audit trail)
- **Prioritized** — urgent messages jump the queue
- **Deduplicated** — won't deliver the same message twice
- **Retried** — if Faye is offline, Marcus keeps trying until it goes through

---

## What Agents Can Do Through FIP

### Personal Communication

The core use case — people communicating through their agents:

| What You Say | What Happens |
|-------------|-------------|
| "Tell Vonta what's up" | Marcus relays the message to Faye → Faye delivers to Vonta |
| "Is Vonta free Saturday?" | Marcus asks Faye → Faye checks calendar → responds without bothering Vonta |
| "Remind Vonta to bring the speaker" | Marcus → Faye → Faye reminds Vonta at the right time |
| "Tell him happy birthday" (at 3 AM) | Marcus → Faye → Faye holds it, delivers in the morning |
| "What did Vonta say about dinner?" | Marcus searches FIP message history, finds it instantly |
| "Tell the group dinner is at 8" | Marcus broadcasts to all enrolled agents |
| "My flight is delayed" | Marcus notifies all relevant agents, they tell their humans |

### Smart Delivery

This isn't just message relay — agents are intelligent about delivery:

- **Calendar-aware** — "Is he free?" gets answered from calendar data without interrupting the person
- **Time-zone aware** — messages deliver at appropriate times, not 3 AM
- **Priority handling** — "It's urgent, get him to call me" overrides quiet hours
- **Filtering** — unknown agents can't get through without enrollment
- **Context-aware** — Faye knows Vonta's preferences, schedule, and communication style
- **Memory** — agents remember every conversation, searchable forever

### Beyond Personal — What Else Agents Can Do

Once agents can talk to each other, everything else follows:

- **Research** — your agent asks a research agent to look something up, gets results back
- **Coding** — your agent delegates a coding task to a coding agent on another machine
- **Monitoring** — a monitor agent on your server alerts your personal agent when something breaks
- **Coordination** — multiple agents coordinate a project, each handling their piece
- **Commerce** — agents that offer services (research, writing, analysis) for a fee

But the foundation is always the same: **agents talking to agents, reliably, securely, across the internet.**

---

## The Trust Model

Trust is the hardest part of agent-to-agent communication. FIP handles it with layers:

### Enrollment (Required)
No agent can message another without enrollment approval. Period. This prevents spam, phishing, and unwanted contact.

### Trust Levels
| Level | What It Means |
|-------|--------------|
| `approved` | Can send and receive messages (default after enrollment) |
| `trusted` | Elevated access — can delegate tasks, higher message limits |
| `blocked` | All messages silently dropped |

### Message Signing
Every message is signed with Ed25519. The receiver verifies the signature against the sender's public key from enrollment. No one can impersonate another agent.

### Human Oversight
- Enrollment requires human approval
- Agents follow their owner's rules (SOUL.md, safety constraints)
- Receiving a message never auto-executes anything — the agent decides what to do
- Sensitive actions always require the human's OK

### Rate Limiting
Each enrolled agent has a message rate limit. Prevents any single sender from flooding your agent.

---

## Quick Start

### 1. Install

```bash
git clone https://github.com/igobymike/fip-agent-protocol.git
cd fip-agent-protocol
pip install -e .
```

### 2. Initialize Your Agent

```python
from fip import FIPClient

agent = FIPClient(db_path="marcus.db", agent_id="marcus@marcus.baiteks.com")
agent.init_db()
```

### 3. Send a Message

```python
result = agent.send(
    target="faye@vonta.example.com",
    event_type="personal.message",
    priority="normal",
    title="Message from Mike",
    body="Hey, Mike says what's up, how are things?"
)
```

### 4. Check for Messages

```python
messages = agent.poll()
for msg in messages:
    print(f"From {msg['source']}: {msg['body']}")
    agent.ack(msg['id'])
```

### 5. Parse Natural Language Replies

```python
from fip import parse_reply_intent

reply = parse_reply_intent("got it, thanks")
# → ReplyIntent(intent='ack', normalized='got it thanks')

reply = parse_reply_intent("snooze 30 minutes")
# → ReplyIntent(intent='snooze', duration_seconds=1800)
```

---

## Architecture

```
┌──────────────────────┐              ┌──────────────────────┐
│   Mike's Setup        │              │   Vonta's Setup       │
│                       │              │                       │
│   Mike ←→ Marcus      │    FIP       │   Faye ←→ Vonta       │
│            │          │  (HTTPS)     │    │                  │
│        FIP Client ────┼──────────────┼→ FIP Server           │
│        FIP Server ←───┼──────────────┼── FIP Client          │
│            │          │              │    │                  │
│        SQLite         │              │  SQLite               │
│   (messages, acks,    │              │  (messages, acks,     │
│    enrollments)       │              │   enrollments)        │
└──────────────────────┘              └──────────────────────┘
```

Each agent runs both a **client** (sends messages) and a **server** (receives messages). Each has its own SQLite database. No shared infrastructure. No central server.

**The agents talk directly to each other.** There's no middleman reading your messages.

---

## Protocol Features

| Feature | How It Works |
|---------|-------------|
| **Addressing** | `agent@domain.com` — like email addresses |
| **Discovery** | `.well-known/fip.json` on the agent's domain |
| **Enrollment** | Friend-request flow with human approval |
| **Signing** | Ed25519 signatures on every message |
| **Deduplication** | Content-hash prevents duplicate delivery |
| **Retry** | Exponential backoff if recipient is offline |
| **Acknowledgments** | Know for certain the message was received |
| **Reply parsing** | Natural language: "got it", "snooze 30 min", "stop" |
| **Priority** | Critical / high / normal / low with interrupt capability |
| **Quiet hours** | Don't deliver at 3 AM (except critical) |
| **Templates** | Reusable message formats with variables |
| **Schedules** | One-shot or recurring messages |
| **Audit trail** | Every message, delivery, and ack logged in SQLite |
| **Rate limiting** | Per-sender caps to prevent spam |
| **Offline delivery** | Messages queue until the recipient comes online |

---

## Documentation

| Doc | What It Covers |
|-----|---------------|
| [FEATURES.md](docs/FEATURES.md) | Complete feature list — every capability, every agent type, every collaboration pattern |
| [FEDERATION.md](docs/FEDERATION.md) | Technical protocol spec — identity, discovery, enrollment, signing, transport, security |
| [AGENT-HUB.md](docs/AGENT-HUB.md) | Agent directory and marketplace — discovery platform, business model, personal texting use case |

---

## Built On

FIP Agent Protocol is built on top of the [Forced Injection Protocol](https://github.com/igobymike/forced-injection-protocol) — a production messaging system that's been running 24/7 since February 2026. FIP handles the hard parts (persistence, dedup, retry, ack tracking, scheduling). This project adds addressing, discovery, enrollment, and cross-network transport on top.

---

## Roadmap

- [x] Core FIP (events, delivery, acks, dedup, retry, templates, schedules)
- [x] Python client library with send/poll/ack
- [x] Natural language reply parser
- [x] Protocol spec (federation, enrollment, signing)
- [ ] HTTP server mode (FastAPI endpoints)
- [ ] Ed25519 message signing
- [ ] `.well-known/fip.json` discovery
- [ ] Enrollment flow (request → approve → communicate)
- [ ] Outbox with store-and-forward
- [ ] Agent Hub directory (hub.baiteks.com)
- [ ] QR code enrollment (scan to add someone's agent)
- [ ] PyPI package (`pip install fip-protocol`)

---

## License

MIT — use it, fork it, build on it.

---

## Author

**Mike Birklett** — [baiteks.com](https://baiteks.com)
Built by [BAITEKS](https://baiteks.com) — Business & AI Technology Solutions

*Your AI should be able to talk to their AI. Now it can.*
