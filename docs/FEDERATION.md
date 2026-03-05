# FIP Federation Protocol — Complete Specification

**Version:** 0.1.0-draft
**Author:** Mike Birklett / BAITEKS
**Date:** 2026-03-05
**Status:** Design

> How autonomous AI agents discover, trust, and communicate with each other across the internet.

---

## Table of Contents

1. [Overview](#1-overview)
2. [Agent Identity](#2-agent-identity)
3. [Discovery](#3-discovery)
4. [Enrollment — The Trust Handshake](#4-enrollment--the-trust-handshake)
5. [Trust Levels & Permissions](#5-trust-levels--permissions)
6. [Message Signing & Authentication](#6-message-signing--authentication)
7. [Transport Layer](#7-transport-layer)
8. [The Complete Flow — Step by Step](#8-the-complete-flow--step-by-step)
9. [Safeguards & Security Model](#9-safeguards--security-model)
10. [Multi-Agent Topologies](#10-multi-agent-topologies)
11. [Failure Modes & Recovery](#11-failure-modes--recovery)
12. [Protocol Envelopes](#12-protocol-envelopes)
13. [Implementation Roadmap](#13-implementation-roadmap)

---

## 1. Overview

### What This Is

A federated messaging protocol that lets any OpenClaw agent communicate with any other OpenClaw agent — across processes, machines, networks, and the open internet — with strong identity, enrollment-based trust, cryptographic authentication, and a complete audit trail.

### Why It Matters

Right now, AI agents are islands. Your agent can talk to you. It can maybe spawn sub-agents on the same machine. But it can't reach out to another person's agent, collaborate on a task, share findings, or coordinate work.

FIP Federation changes that. It's the protocol layer that makes **agent-to-agent collaboration across the internet** possible — with the same reliability guarantees (priority, dedup, retry, ack) that FIP already provides locally.

### The Analogy

Think about how email works:
- Every person has an address (`mike@baiteks.com`)
- The domain tells you where to deliver (`baiteks.com` → look up MX record → find mail server)
- Servers authenticate each other (DKIM, SPF, DMARC)
- You can email anyone, but spam filters and block lists protect you

FIP Federation follows the same pattern, but for AI agents:
- Every agent has an address (`marcus@marcus.baiteks.com`)
- The domain provides a discovery endpoint (`.well-known/fip.json`)
- Agents authenticate messages with Ed25519 signatures
- Enrollment (like a friend request) controls who can talk to whom

### Design Principles

1. **Trust is explicit.** No agent can message another without enrollment approval.
2. **Messages are data, not code.** Receiving a FIP message never auto-executes anything.
3. **The receiving agent's rules govern.** Your SOUL.md, your safety rules, your decisions.
4. **Everything is auditable.** Both sides log every message, every delivery, every ack.
5. **Humans stay in the loop.** Enrollment requires human approval. Sensitive actions require human approval.
6. **Offline-resilient.** Messages persist until delivered. No real-time requirement.
7. **Zero central authority.** No central server, no registry, no single point of failure.

---

## 2. Agent Identity

### Address Format

Every agent has a globally unique address:

```
{agent_name}@{domain}
```

**Examples:**
```
marcus@marcus.baiteks.com
research-bot@lab.baiteks.com
scheduler@kuraray-tools.com
monitor@ops.example.org
```

**Rules:**
- `agent_name`: lowercase alphanumeric + hyphens, 1-64 characters
- `domain`: valid DNS domain that the agent's operator controls
- The combination is globally unique (like email)

### Identity Keypair

Every agent generates an Ed25519 keypair on first initialization:

```
~/.fip/identity/
├── agent.pub    — Ed25519 public key (shared with peers)
├── agent.key    — Ed25519 private key (NEVER shared, NEVER leaves the machine)
└── agent.json   — Agent metadata (name, address, capabilities)
```

**`agent.json`:**
```json
{
    "address": "marcus@marcus.baiteks.com",
    "name": "Marcus",
    "description": "Strategic Operating Partner — infrastructure, ops, coding",
    "public_key": "ed25519:base64encodedpublickey...",
    "capabilities": ["task_delegation", "health_alerts", "status_reports", "research"],
    "fip_version": "1.0",
    "created_at": "2026-03-05T05:00:00Z"
}
```

### Why Ed25519?

- Fast: signing and verification in microseconds
- Small: 32-byte keys, 64-byte signatures
- Secure: no known practical attacks
- Standard: supported by every modern crypto library
- Same algorithm used by SSH, Signal, and WireGuard

---

## 3. Discovery

### How Agent A Finds Agent B

When Agent A wants to message `scheduler@kuraray-tools.com`, it needs to find the FIP endpoint. Two discovery methods:

### Method 1: Well-Known Endpoint (Primary)

Agent A makes an HTTPS request to the domain:

```
GET https://kuraray-tools.com/.well-known/fip.json
```

**Response:**
```json
{
    "fip_version": "1.0",
    "agents": [
        {
            "address": "scheduler@kuraray-tools.com",
            "name": "Kuraray Scheduler Bot",
            "endpoint": "https://kuraray-tools.com/fip/v1",
            "public_key": "ed25519:base64...",
            "capabilities": ["schedule_query", "report_generation"],
            "enrollment": "approval_required",
            "rate_limit": "10/hour"
        }
    ]
}
```

**This tells Agent A:**
- Where to send messages (`endpoint`)
- How to verify responses (`public_key`)
- What the agent can do (`capabilities`)
- Whether enrollment is needed (`enrollment`)
- How fast it can send (`rate_limit`)

### Method 2: DNS TXT Record (Fallback)

If the well-known endpoint isn't available, check DNS:

```
TXT _fip.kuraray-tools.com → "v=fip1 endpoint=https://kuraray-tools.com/fip/v1 key=ed25519:base64..."
```

### Discovery Caching

- Discovery results are cached for 24 hours (configurable)
- Public keys are pinned on first discovery (TOFU — Trust On First Use)
- Key changes require re-enrollment (prevents impersonation)

---

## 4. Enrollment — The Trust Handshake

### Why Enrollment Exists

Without enrollment, any agent on the internet could spam your agent with messages, phishing attempts, or social engineering attacks. Enrollment is the **permission layer** — it ensures only approved agents can communicate.

### The Enrollment Flow

```
Agent A                                        Agent B
  │                                               │
  │  1. DISCOVER                                  │
  │  GET /.well-known/fip.json ──────────────────→│
  │  ←──────────────────────── fip.json response  │
  │                                               │
  │  2. ENROLLMENT REQUEST                        │
  │  POST /fip/v1/enroll ────────────────────────→│
  │  {                                            │
  │    "from": "marcus@marcus.baiteks.com",       │
  │    "to": "scheduler@kuraray-tools.com",       │
  │    "public_key": "ed25519:base64...",         │
  │    "reason": "Task coordination for P6",      │
  │    "requested_trust": "approved",             │
  │    "capabilities_needed": ["task_delegation"],│
  │    "signature": "ed25519sig..."               │
  │  }                                            │
  │                                               │
  │  ←────────── 202 Accepted (pending review)    │
  │                                               │
  │         ┌─────────────────────────────┐       │
  │         │  Agent B's human owner      │       │
  │         │  reviews the enrollment     │       │
  │         │  request and approves or    │       │
  │         │  denies it.                 │       │
  │         └─────────────────────────────┘       │
  │                                               │
  │  3. ENROLLMENT RESPONSE                       │
  │  ←──────────────────── POST /fip/v1/enrolled  │
  │  {                                            │
  │    "from": "scheduler@kuraray-tools.com",     │
  │    "to": "marcus@marcus.baiteks.com",         │
  │    "status": "approved",                      │
  │    "trust_level": "approved",                 │
  │    "permissions": ["send_messages",           │
  │                     "request_reports"],        │
  │    "rate_limit": "10/hour",                   │
  │    "public_key": "ed25519:base64...",         │
  │    "signature": "ed25519sig..."               │
  │  }                                            │
  │                                               │
  │  4. NOW THEY CAN COMMUNICATE                  │
  │  POST /fip/v1/events ────────────────────────→│
  │  ←──────────────────── POST /fip/v1/events    │
```

### Enrollment States

```
UNKNOWN → REQUESTED → APPROVED → (optional) TRUSTED
                    ↘ DENIED
                    ↘ BLOCKED

APPROVED → REVOKED (trust withdrawn)
```

| State | Can Send Messages? | Can Receive Messages? |
|-------|-------------------|----------------------|
| `unknown` | ❌ | ❌ |
| `requested` | ❌ (pending approval) | ❌ |
| `approved` | ✅ (within rate limits) | ✅ |
| `trusted` | ✅ (higher limits, more permissions) | ✅ |
| `denied` | ❌ | ❌ |
| `blocked` | ❌ (all messages silently dropped) | ❌ |
| `revoked` | ❌ (was approved, trust withdrawn) | ❌ |

### Enrollment Storage

Both sides store enrollment records in their local SQLite:

```sql
CREATE TABLE IF NOT EXISTS enrollments(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_address TEXT UNIQUE NOT NULL,  -- e.g. "marcus@marcus.baiteks.com"
    agent_name TEXT,
    endpoint TEXT,
    public_key TEXT NOT NULL,
    trust_level TEXT NOT NULL DEFAULT 'unknown',
    permissions_json TEXT DEFAULT '[]',
    rate_limit TEXT DEFAULT '10/hour',
    reason TEXT,
    direction TEXT NOT NULL,  -- 'inbound' (they want to talk to us) or 'outbound' (we want to talk to them)
    status TEXT NOT NULL DEFAULT 'unknown',
    requested_at TEXT,
    approved_at TEXT,
    denied_at TEXT,
    revoked_at TEXT,
    last_message_at TEXT,
    message_count INTEGER DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);
```

### Auto-Enrollment (Optional)

Some agents may want to accept messages from anyone (like a public API):

```json
{
    "enrollment": "open",
    "auto_trust_level": "approved",
    "rate_limit": "5/hour"
}
```

This is useful for:
- Public information services
- Community agents that answer questions
- Monitoring endpoints that accept health reports

---

## 5. Trust Levels & Permissions

### Trust Levels

| Level | Description | Typical Use |
|-------|-------------|-------------|
| `approved` | Basic messaging allowed | General communication, status queries |
| `trusted` | Extended access, higher rate limits | Task delegation, command execution |
| `admin` | Full access, can manage enrollments | Operator's own agents on same domain |

### Permission Types

Permissions are granted per-enrollment and control what the sender can do:

| Permission | Description |
|-----------|-------------|
| `send_messages` | Can send standard messages (always granted with approved+) |
| `request_reports` | Can request generated reports |
| `delegate_tasks` | Can assign tasks to this agent |
| `request_actions` | Can request the agent perform actions |
| `read_status` | Can query the agent's current status |
| `manage_schedules` | Can create/modify FIP schedules on this agent |
| `relay` | Can ask this agent to relay messages to other agents |

**Important:** Having a permission doesn't mean the action happens automatically. The receiving agent's SOUL.md, safety rules, and human-in-the-loop requirements still apply. Permissions just determine whether the *request* is accepted for processing.

### Rate Limiting

Every enrollment has a rate limit:

```
"rate_limit": "10/hour"     — 10 messages per hour
"rate_limit": "100/day"     — 100 messages per day
"rate_limit": "1/minute"    — 1 message per minute (burst protection)
```

Rate limits are enforced by the **receiving** agent. Exceeding the limit returns `429 Too Many Requests`.

---

## 6. Message Signing & Authentication

### Why Signing?

Without signatures, any server could impersonate Agent A and send messages to Agent B. Signing proves that a message genuinely came from the claimed sender.

### How It Works

Every FIP message is signed with the sender's Ed25519 private key:

```
1. Sender constructs the message JSON
2. Sender creates a canonical byte string of the message (sorted keys, no whitespace)
3. Sender signs the canonical bytes with their Ed25519 private key
4. Signature is included in the message header
5. Receiver verifies the signature using the sender's public key (from enrollment)
```

### Signature Header

```json
{
    "fip_version": "1.0",
    "from": "marcus@marcus.baiteks.com",
    "to": "scheduler@kuraray-tools.com",
    "timestamp": "2026-03-05T05:00:00Z",
    "nonce": "randomnonce123",
    "signature": "ed25519:base64signature...",
    "body": {
        "event_type": "task.delegate",
        "priority": "high",
        "title": "Generate weekly report",
        "body": "..."
    }
}
```

### Verification Steps (Receiver Side)

1. **Check enrollment:** Is `marcus@marcus.baiteks.com` enrolled and approved? If not → reject.
2. **Check rate limit:** Has this sender exceeded their rate limit? If yes → 429.
3. **Check timestamp:** Is the message within the clock skew window (±5 minutes)? If not → reject (prevents replay attacks).
4. **Check nonce:** Has this nonce been seen before? If yes → reject (prevents replay attacks).
5. **Verify signature:** Reconstruct canonical bytes, verify Ed25519 signature against stored public key. If invalid → reject.
6. **Check permissions:** Does this sender have permission for this event type? If not → reject.
7. **Accept and process.**

### Key Rotation

If an agent needs to rotate its keypair:

1. Agent generates a new keypair
2. Agent signs a "key rotation" message with the OLD key, containing the NEW public key
3. Agent updates its `.well-known/fip.json` with the new key
4. Peers verify the rotation message with the old key, then update their stored key
5. Old key is kept for 30 days for in-flight message verification

---

## 7. Transport Layer

### HTTP Transport (Primary)

All FIP federation traffic moves over HTTPS. Endpoints:

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/.well-known/fip.json` | GET | None | Agent discovery |
| `/fip/v1/enroll` | POST | Signed | Request enrollment |
| `/fip/v1/enrolled` | POST | Signed | Enrollment response (approve/deny) |
| `/fip/v1/events` | POST | Signed | Send a message |
| `/fip/v1/ack` | POST | Signed | Acknowledge a message |
| `/fip/v1/health` | GET | Optional | Agent health + queue stats |
| `/fip/v1/revoke` | POST | Signed | Revoke enrollment |

### Request Format

```http
POST /fip/v1/events HTTP/1.1
Host: kuraray-tools.com
Content-Type: application/json
X-FIP-From: marcus@marcus.baiteks.com
X-FIP-Timestamp: 2026-03-05T05:00:00Z
X-FIP-Nonce: abc123def456
X-FIP-Signature: ed25519:base64signature...

{
    "event_type": "task.delegate",
    "priority": "high",
    "title": "Generate weekly report",
    "body": "Please generate the weekly turnaround progress report for the Reactor Area.",
    "requires_ack": true,
    "ttl_seconds": 3600,
    "correlation_id": "evt-550e8400-e29b-41d4-a716-446655440000",
    "metadata": {
        "project": "vinyl-plant-2026-ta",
        "wbs_section": "reactor"
    }
}
```

### Response Format

```http
HTTP/1.1 202 Accepted
Content-Type: application/json

{
    "ok": true,
    "event_id": "remote-42",
    "correlation_id": "evt-550e8400-e29b-41d4-a716-446655440000",
    "status": "received"
}
```

### Error Responses

| Code | Meaning |
|------|---------|
| `200` | Success (for acks, health) |
| `202` | Accepted (for events — async processing) |
| `400` | Bad request (malformed message) |
| `401` | Signature verification failed |
| `403` | Not enrolled or insufficient permissions |
| `404` | Agent not found at this endpoint |
| `429` | Rate limit exceeded |
| `503` | Agent temporarily unavailable |

### Outbox Pattern (Store-and-Forward)

When Agent A sends a message but Agent B is offline:

1. Agent A stores the message in its local `outbox` table with status `queued`
2. Agent A retries delivery with exponential backoff:
   - Attempt 1: immediate
   - Attempt 2: +30 seconds
   - Attempt 3: +2 minutes
   - Attempt 4: +10 minutes
   - Attempt 5: +1 hour
   - Then: every hour until TTL expires
3. When Agent B comes online and delivery succeeds → status = `delivered`
4. If TTL expires before delivery → status = `expired`, sender notified

```sql
CREATE TABLE IF NOT EXISTS outbox(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_json TEXT NOT NULL,
    target_address TEXT NOT NULL,
    target_endpoint TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'queued',  -- queued, delivering, delivered, failed, expired
    attempts INTEGER DEFAULT 0,
    max_attempts INTEGER DEFAULT 10,
    next_attempt_at TEXT,
    last_attempt_at TEXT,
    last_error TEXT,
    ttl_expires_at TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
```

---

## 8. The Complete Flow — Step by Step

Here's the full story of how two agents go from strangers to collaborators:

### Scenario: Marcus wants to ask a Research Agent for help

**Setup:**
- Marcus runs at `marcus@marcus.baiteks.com` on Mike's VPS
- Research Agent runs at `scout@research.example.org` on someone else's server
- They have never communicated before

---

**Step 1: Marcus discovers the Research Agent**

Marcus's operator (Mike) tells Marcus: "There's a research agent at research.example.org that can help with market analysis."

Marcus fetches the discovery document:
```
GET https://research.example.org/.well-known/fip.json
```

Response:
```json
{
    "fip_version": "1.0",
    "agents": [{
        "address": "scout@research.example.org",
        "name": "Scout — Research Intelligence",
        "endpoint": "https://research.example.org/fip/v1",
        "public_key": "ed25519:K7xB2m9...",
        "capabilities": ["web_research", "market_analysis", "report_generation"],
        "enrollment": "approval_required",
        "rate_limit": "20/hour"
    }]
}
```

Marcus stores this in his `enrollments` table with status `unknown`.

---

**Step 2: Marcus sends an enrollment request**

```
POST https://research.example.org/fip/v1/enroll
```

```json
{
    "from": "marcus@marcus.baiteks.com",
    "to": "scout@research.example.org",
    "public_key": "ed25519:Qm3xF8a...",
    "reason": "Market analysis collaboration for industrial AI products. I need help researching the P6 scheduling software market.",
    "requested_trust": "approved",
    "capabilities_needed": ["web_research", "market_analysis"],
    "agent_info": {
        "name": "Marcus",
        "description": "Strategic Operating Partner — infrastructure, ops, industrial AI",
        "operator": "Mike Birklett / BAITEKS",
        "website": "https://baiteks.com"
    },
    "signature": "ed25519:sig..."
}
```

Scout's FIP server:
1. Validates the signature (confirms Marcus controls the claimed key)
2. Stores the enrollment request with status `requested`
3. Notifies Scout's human operator: "New enrollment request from marcus@marcus.baiteks.com"
4. Returns `202 Accepted`

---

**Step 3: Scout's operator reviews and approves**

Scout's operator sees the request in their dashboard (or via FIP alert to their own session):

```
🔔 ENROLLMENT REQUEST
From: marcus@marcus.baiteks.com (Marcus)
Operator: Mike Birklett / BAITEKS (baiteks.com)
Reason: Market analysis collaboration for industrial AI products
Capabilities requested: web_research, market_analysis
Trust level requested: approved

[Approve] [Deny] [Block]
```

Operator clicks **Approve** with permissions: `send_messages`, `request_reports`.

---

**Step 4: Scout sends enrollment approval back to Marcus**

```
POST https://marcus.baiteks.com/fip/v1/enrolled
```

```json
{
    "from": "scout@research.example.org",
    "to": "marcus@marcus.baiteks.com",
    "status": "approved",
    "trust_level": "approved",
    "permissions": ["send_messages", "request_reports"],
    "rate_limit": "20/hour",
    "public_key": "ed25519:K7xB2m9...",
    "message": "Welcome! Happy to help with market research. Send me a query anytime.",
    "signature": "ed25519:sig..."
}
```

Marcus verifies the signature, updates the enrollment to `approved`, and stores Scout's public key.

**Both agents now have each other's public keys and trust records.**

---

**Step 5: Marcus sends a research request**

```
POST https://research.example.org/fip/v1/events
X-FIP-From: marcus@marcus.baiteks.com
X-FIP-Signature: ed25519:sig...
```

```json
{
    "event_type": "research.request",
    "priority": "normal",
    "title": "P6 scheduling market analysis",
    "body": "Research the Primavera P6 scheduling software market. I need: (1) How many industrial plants use P6 in North America, (2) Average turnaround budget by industry segment, (3) Existing AI/chatbot competitors in the P6 space, (4) Market size estimate for conversational P6 tools.",
    "requires_ack": true,
    "ttl_seconds": 86400,
    "correlation_id": "research-p6-market-001"
}
```

Scout's FIP server:
1. Checks enrollment: `marcus@marcus.baiteks.com` → approved ✅
2. Checks rate limit: within 20/hour ✅
3. Verifies signature ✅
4. Checks permissions: `send_messages` ✅
5. Delivers to Scout's session
6. Returns `202 Accepted`

---

**Step 6: Scout processes and responds**

Scout does the research (web search, analysis, etc.) and sends the results back:

```
POST https://marcus.baiteks.com/fip/v1/events
X-FIP-From: scout@research.example.org
X-FIP-Signature: ed25519:sig...
```

```json
{
    "event_type": "research.result",
    "priority": "normal",
    "title": "P6 Market Analysis — Complete",
    "body": "## P6 Scheduling Market Analysis\n\n### Market Size\n- ~1,400 P6-based turnarounds/year in North America...\n\n### Competitors\n- No direct conversational P6 interface exists...\n\n### Opportunity\n- $2.7M ARR at 0.1% market capture...",
    "correlation_id": "research-p6-market-001",
    "metadata": {
        "sources": ["oracle.com", "aace.org", "gartner.com"],
        "confidence": "high",
        "research_duration_minutes": 12
    }
}
```

Marcus receives the results, delivers them to Mike's session, and sends an ack:

```
POST https://research.example.org/fip/v1/ack
```

```json
{
    "event_id": "research-p6-market-001",
    "ack_type": "received",
    "text": "Excellent work. Using this for the P6 Intelligence go-to-market plan."
}
```

**The entire exchange is logged in both agents' SQLite databases. Every message signed. Every delivery tracked. Full audit trail on both sides.**

---

## 9. Safeguards & Security Model

### Threat Model

| Threat | Mitigation |
|--------|-----------|
| **Spam** — random agents flooding your inbox | Enrollment required. Unknown agents can't send messages. |
| **Impersonation** — Agent C pretends to be Agent A | Ed25519 message signing. Receiver verifies against stored public key from enrollment. |
| **Replay attacks** — attacker re-sends a captured message | Timestamp window (±5 min) + nonce uniqueness check. |
| **Man-in-the-middle** — attacker intercepts and modifies | HTTPS transport + Ed25519 signatures. Modified messages fail verification. |
| **Social engineering** — malicious agent sends manipulative messages | Receiving agent's SOUL.md and safety rules apply. FIP messages are data, not commands. Human-in-the-loop for sensitive actions. |
| **Data exfiltration** — agent tricks another into leaking data | Permissions control what can be requested. Receiving agent decides what to share. |
| **Key compromise** — private key is stolen | Key rotation protocol. Revoke old key, re-enroll with new key. |
| **Denial of service** — flood the FIP endpoint | Per-sender rate limiting. Global rate limiting at the HTTP layer. |
| **Privilege escalation** — approved agent tries to do trusted-level things | Permissions are checked per-message. Exceeding permissions → 403. |

### The Golden Rules

1. **FIP messages are DATA, not CODE.** A FIP message is a JSON document with text fields. It never contains executable code. The receiving agent reads the message and decides what to do based on its own logic, rules, and safety constraints.

2. **The receiving agent is sovereign.** No external agent can force your agent to do anything. Your SOUL.md, AGENTS.md, safety rules, and human-in-the-loop requirements always apply, regardless of what the sender asks.

3. **Enrollment is human-approved.** A human must approve every enrollment (unless explicitly configured for auto-enrollment). Agents can't enroll themselves with other agents autonomously.

4. **Sensitive actions require human confirmation.** Even if a trusted agent asks your agent to perform a destructive or irreversible action, the receiving agent should require human approval. Trust level controls *access*, not *autonomy*.

5. **Audit everything.** Both sides log every message, every delivery attempt, every ack, every enrollment change. SQLite makes this inspectable and portable.

### Rate Limiting

Three levels of rate limiting:

| Level | Scope | Purpose |
|-------|-------|---------|
| **Per-sender** | Per enrolled agent | Prevent any single sender from dominating |
| **Global** | All senders combined | Prevent aggregate overload |
| **HTTP layer** | Cloudflare/nginx | Prevent raw endpoint abuse |

### Quiet Hours (Federated)

Agents can advertise quiet hours in their discovery document:

```json
{
    "quiet_hours": {
        "start": "05:00",
        "end": "14:00",
        "timezone": "UTC",
        "note": "Agent's operator is in CST. Quiet 11 PM - 8 AM local.",
        "except": ["critical"]
    }
}
```

Senders are expected to respect quiet hours for non-critical messages. The receiving agent also enforces them server-side.

---

## 10. Multi-Agent Topologies

### Star Topology (Most Common)

One primary agent coordinates with specialists:

```
                    ┌──────────────┐
                    │   Marcus     │
                    │   (primary)  │
                    └──────┬───────┘
                           │
          ┌────────────────┼─────────────────┐
          │                │                 │
    ┌─────▼─────┐   ┌─────▼──────┐   ┌─────▼──────┐
    │ Research   │   │ Coding     │   │ Monitor    │
    │ Agent      │   │ Agent      │   │ Agent      │
    └───────────┘   └────────────┘   └────────────┘
```

### Mesh Topology (Advanced)

Multiple agents communicate freely:

```
    ┌─────────┐     ┌─────────┐
    │ Agent A  │←───→│ Agent B  │
    └────┬────┘     └────┬────┘
         │               │
         └───────┬───────┘
                 │
           ┌─────▼─────┐
           │  Agent C   │
           └───────────┘
```

Each pair has its own enrollment. Agent A being enrolled with Agent B doesn't grant any access to Agent C.

### Hub Topology (Enterprise)

A central hub agent routes messages:

```
    ┌─────────┐                    ┌─────────┐
    │ Agent 1  │──→ ┌────────┐ ←──│ Agent 4  │
    └─────────┘    │  Hub   │    └─────────┘
    ┌─────────┐    │ Agent  │    ┌─────────┐
    │ Agent 2  │──→ │(relay) │ ←──│ Agent 5  │
    └─────────┘    └────────┘    └─────────┘
    ┌─────────┐        ↑
    │ Agent 3  │────────┘
    └─────────┘
```

The hub agent has `relay` permission and forwards messages between agents that aren't directly enrolled with each other.

---

## 11. Failure Modes & Recovery

| Failure | Detection | Recovery |
|---------|-----------|----------|
| Target agent offline | HTTP connection refused / timeout | Outbox queues message, retries with backoff |
| Target endpoint moved | 404 or DNS change | Re-discover via `.well-known/fip.json` |
| Key compromised | Agent detects unauthorized messages | Rotate key, notify all enrolled peers, re-sign enrollments |
| Enrollment revoked | 403 on message send | Re-request enrollment or accept the revocation |
| Message TTL expired | Outbox check | Mark as expired, notify sender agent |
| Disk full (SQLite) | Write fails | Alert operator, pause incoming messages |
| Clock skew too large | Timestamp validation fails | NTP sync, configurable skew window |

---

## 12. Protocol Envelopes

### Full Event Envelope (Federated)

```json
{
    "protocol": "fip/1.0",
    "type": "event",
    "from": "marcus@marcus.baiteks.com",
    "to": "scout@research.example.org",
    "timestamp": "2026-03-05T05:00:00Z",
    "nonce": "n-8f14e45f-ceea-367f-a27f-c0c29a2bf4a2",
    "signature": "ed25519:base64...",
    "body": {
        "correlation_id": "evt-550e8400-e29b-41d4-a716-446655440000",
        "event_type": "research.request",
        "priority": "normal",
        "delivery": "text_only",
        "title": "P6 market analysis",
        "body": "Research the P6 scheduling market...",
        "action_text": "Run analysis and return findings.",
        "requires_ack": true,
        "ttl_seconds": 86400,
        "dedupe_key": "research-p6-20260305",
        "metadata": {
            "project": "p6-intelligence",
            "urgency": "this week"
        }
    }
}
```

### Enrollment Request Envelope

```json
{
    "protocol": "fip/1.0",
    "type": "enrollment_request",
    "from": "marcus@marcus.baiteks.com",
    "to": "scout@research.example.org",
    "timestamp": "2026-03-05T05:00:00Z",
    "nonce": "n-enrollment-001",
    "signature": "ed25519:base64...",
    "body": {
        "public_key": "ed25519:Qm3xF8a...",
        "reason": "Market research collaboration",
        "requested_trust": "approved",
        "capabilities_needed": ["web_research", "market_analysis"],
        "agent_info": {
            "name": "Marcus",
            "description": "Strategic Operating Partner",
            "operator": "Mike Birklett / BAITEKS",
            "website": "https://baiteks.com"
        }
    }
}
```

### Ack Envelope

```json
{
    "protocol": "fip/1.0",
    "type": "ack",
    "from": "scout@research.example.org",
    "to": "marcus@marcus.baiteks.com",
    "timestamp": "2026-03-05T05:12:00Z",
    "nonce": "n-ack-001",
    "signature": "ed25519:base64...",
    "body": {
        "event_id": "evt-550e8400-e29b-41d4-a716-446655440000",
        "ack_type": "received",
        "intent": "ack",
        "text": "Starting research now. ETA: 15 minutes."
    }
}
```

---

## 13. Implementation Roadmap

### Phase 1 — Local Agent Messaging (COMPLETE ✅)
- FIP core: events, deliveries, acks, dedupe, retry
- Templates and schedules
- Reply parser
- SQLite persistence
- OpenClaw session injection
- Voice TTS delivery

### Phase 2 — Known Peer Communication (NEXT)
- HTTP server mode (FastAPI `/fip/v1/*` endpoints)
- Peer registration with pre-shared keys
- Outbox with store-and-forward
- Message signing (Ed25519)
- Cross-machine messaging between own agents

### Phase 3 — Federated Discovery & Enrollment
- `.well-known/fip.json` endpoint
- Enrollment request/approval flow
- Trust levels and permissions
- Rate limiting (per-sender + global)
- Human-in-the-loop enrollment approval UI

### Phase 4 — Production Hardening
- Key rotation protocol
- Nonce tracking (replay prevention)
- Clock skew handling
- Quiet hours (federated)
- Monitoring and alerting for federation health

### Phase 5 — Ecosystem
- PyPI package (`pip install fip-protocol`)
- OpenClaw native integration (built-in FIP support)
- Web dashboard for enrollment management
- Reference implementation for non-Python agents
- Spec published as an open standard

---

## Appendix A: Why Not Existing Protocols?

| Protocol | Why Not FIP? |
|----------|-------------|
| **HTTP APIs** | No built-in dedup, retry, ack tracking, priority, audit trail. You'd build FIP on top of HTTP anyway. |
| **MQTT** | Designed for IoT telemetry, not agent conversations. No enrollment, no signing, no audit. |
| **AMQP / RabbitMQ** | Heavy infrastructure. Requires a central broker. FIP is decentralized. |
| **ActivityPub** | Designed for social media (posts, follows). Wrong abstraction for task delegation and operational messaging. |
| **Matrix** | Full chat protocol with rooms, E2EE, etc. Massive overhead for agent-to-agent messaging. |
| **gRPC** | Great for service-to-service RPC. Not designed for async, persistent, priority-based messaging. |
| **Email (SMTP)** | Closest analogy, but: no structured data, no priority handling, no ack tracking, spam is unsolved. |

FIP is purpose-built for the specific needs of autonomous AI agent communication. It borrows ideas from email (federated, domain-based addressing), HTTPS (transport security), and message queues (persistence, retry) — but combines them into something designed specifically for this use case.

---

*This document is a living specification. Version history tracked in git.*

*Built by [BAITEKS](https://baiteks.com) — Business & AI Technology Solutions*
