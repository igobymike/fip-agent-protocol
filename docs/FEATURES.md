# FIP Agent-to-Agent — Complete Feature List

**Every feature, every capability, everything this protocol enables.**

---

## 1. Core Messaging

### Send & Receive
- **Async message delivery** — send a message, it gets there when the other agent is ready. No real-time requirement.
- **Priority-ordered delivery** — critical messages jump the queue. Low-priority batches up.
- **Structured messages** — not just text blobs. Event type, title, body, action text, metadata. The receiving agent knows exactly what kind of message it is.
- **Correlation IDs** — thread messages together. "This response is for that request." Multi-turn conversations across agents.
- **TTL (Time-to-Live)** — messages expire. A "is he free tonight?" message shouldn't deliver 3 days later.
- **Fire-and-forget OR guaranteed delivery** — your choice per message. FYI = send and move on. Important = require ack.

### Message Types
- **Standard message** — general communication between agents
- **Task delegation** — assign work to another agent with a brief
- **Task completion** — report results back to the delegating agent
- **Status request** — ask an agent "what are you working on?"
- **Status report** — respond with current state
- **Alert / notification** — something happened that the other agent should know about
- **Query** — ask the other agent to look something up or compute something
- **Query response** — results from the query
- **Approval request** — ask the other agent (or its human) to approve something
- **Approval response** — yes/no/defer
- **Heartbeat / ping** — "are you alive?"
- **Broadcast** — one message to multiple enrolled agents at once
- **Relay request** — "forward this to agent X for me" (if you're not directly enrolled)

### Delivery Modes
- **Text injection** — deliver into the agent's chat session (OpenClaw native)
- **Voice (TTS)** — speak the message aloud through the agent's voice pipeline
- **Text + Voice** — both simultaneously
- **Webhook** — POST to a URL (for agents not running FIP natively)
- **Email** — fall back to email if the agent is unreachable (last resort)
- **Queue** — hold for later delivery (scheduled or when agent comes online)

---

## 2. Reliability & Delivery Guarantees

### Deduplication
- **Content-hash dedup** — identical messages within the TTL window are automatically suppressed
- **Custom dedupe keys** — manually specify what counts as "the same message"
- **Dedupe across delivery modes** — a message sent via text AND voice only fires once per mode, not twice

### Retry & Backoff
- **Exponential backoff** — failed deliveries retry at 0s, 60s, 180s, 600s intervals
- **Configurable retry policy** — set custom backoff schedules per message or per enrollment
- **Max attempts** — stop retrying after N attempts and escalate
- **Offline tolerance** — messages queue in the outbox until the target comes online

### Acknowledgments
- **Ack tracking** — know for certain whether the other agent received and processed your message
- **Ack types** — `received` (got it), `processing` (working on it), `completed` (done), `rejected` (can't/won't do this)
- **Ack timeout** — if no ack within N seconds, retry or escalate
- **Natural language acks** — the receiving agent (or human) can reply naturally: "got it", "snooze 30 min", "stop", "do it now"

### Store-and-Forward (Outbox)
- **Persistent outbox** — messages that can't be delivered immediately are stored locally
- **Automatic retry** — outbox worker retries with backoff until delivered or expired
- **Outbox monitoring** — see all pending outbound messages and their retry status
- **TTL expiration** — messages that expire before delivery are marked expired, sender notified

---

## 3. Trust & Enrollment

### Enrollment Flow
- **Discovery** — find an agent's endpoint and public key via `.well-known/fip.json` or DNS
- **Enrollment request** — send a signed request with your identity, reason, and capabilities needed
- **Human approval** — the receiving agent's human owner reviews and approves/denies
- **Mutual key exchange** — both agents store each other's public keys after approval
- **One-time setup** — enroll once, communicate forever (until revoked)

### Trust Levels
- **Unknown** — never interacted
- **Requested** — enrollment pending
- **Approved** — can send and receive messages within rate limits
- **Trusted** — elevated access: task delegation, action requests, higher rate limits
- **Admin** — full access (typically only for same-operator agents)
- **Denied** — enrollment rejected
- **Blocked** — all messages silently dropped, no response
- **Revoked** — was approved, trust withdrawn

### Permissions (Per-Enrollment)
- `send_messages` — can send standard messages
- `request_reports` — can ask for generated reports
- `delegate_tasks` — can assign work
- `request_actions` — can ask the agent to do something
- `read_status` — can query current status
- `manage_schedules` — can create/modify FIP schedules
- `relay` — can ask this agent to forward messages to other agents
- `broadcast` — can send messages to this agent as part of a broadcast
- Custom permissions — define your own per agent

### Rate Limiting
- **Per-sender limits** — each enrolled agent has a rate cap (e.g., 10/hour)
- **Global limits** — total inbound messages per hour across all senders
- **Priority override** — critical messages bypass normal rate limits
- **Rate limit headers** — senders get told their remaining quota in responses
- **Graduated limits** — trust level determines rate limit (approved: 10/hr, trusted: 100/hr)

---

## 4. Security

### Identity & Authentication
- **Ed25519 keypairs** — every agent has a cryptographic identity
- **Message signing** — every message signed with sender's private key
- **Signature verification** — receiver verifies against stored public key from enrollment
- **Nonce + timestamp** — replay attack prevention (±5 min clock skew window)
- **Key rotation** — rotate keys with signed rotation messages, old key verifies new key
- **Key pinning** — alert if an enrolled agent's key changes unexpectedly

### Transport Security
- **HTTPS only** — all federation traffic over TLS
- **Certificate pinning** — optional pinning of peer TLS certificates
- **No plaintext fallback** — if HTTPS fails, message queues, doesn't downgrade

### Privacy
- **Messages are end-to-end between agents** — no central server reads them
- **Local storage only** — each agent's SQLite stays on their machine
- **Metadata minimization** — the hub sees enrollment records, not message content
- **Quiet hours** — respect the human's sleep schedule
- **Blocking** — block any agent, their messages are silently dropped

---

## 5. Templates & Scheduling

### Message Templates
- **Define once, use everywhere** — create templates with variable placeholders
- **Variable substitution** — `{task_id}`, `{agent_name}`, `{description}`, etc.
- **Template inheritance** — defaults from template, overrides per-send
- **Template library** — share templates between agents
- **Template versioning** — update templates without breaking existing schedules

### Scheduled Messaging
- **One-shot schedules** — send a message at a specific future time
- **Recurring schedules** — send every N seconds/minutes/hours/days
- **Cron-like scheduling** — "every Monday at 9 AM"
- **Quiet hours** — suppress during sleep hours (except critical)
- **Schedule management** — pause, resume, modify, delete schedules
- **Schedule-triggered actions** — "every 20 minutes, check task status and report to coordinator"

---

## 6. Agent Collaboration Patterns

### Task Delegation
- **Delegate with a brief** — send a task with full context, spec, and requirements
- **Track task status** — delegated task stays in your outbox until acked + completed
- **Progress updates** — worker agent sends periodic progress via FIP
- **Completion report** — worker sends results back with deliverables
- **Verification** — delegating agent can verify output before marking complete
- **Re-delegation** — if worker can't do it, they can suggest or forward to another agent
- **Parallel delegation** — send the same task to multiple workers, take the best result

### Agent Swarms
- **Coordinator pattern** — one agent manages, many agents execute
- **Fan-out** — coordinator sends tasks to N workers simultaneously
- **Fan-in** — coordinator collects results from all workers
- **Worker registration** — workers announce their capabilities to the coordinator
- **Load balancing** — coordinator routes tasks to the least-busy worker
- **Failover** — if a worker goes down, coordinator re-delegates to another

### Research Networks
- **Query routing** — research agent receives a question, routes to the most relevant specialist
- **Source aggregation** — multiple research agents each search different sources, results combined
- **Confidence scoring** — each agent rates its confidence in the answer
- **Citation tracking** — every claim comes with sources
- **Caching** — if the same question was answered recently, return cached result
- **Follow-up chains** — initial answer → follow-up questions → deeper research → final report

### Monitoring & Alerting
- **Health check agents** — dedicated agents that monitor services/infrastructure
- **Alert routing** — monitor detects issue → FIP alert to coordinator → coordinator decides action
- **Escalation chains** — if first responder doesn't ack in 5 min, escalate to next agent
- **Incident correlation** — multiple alerts about the same issue are grouped
- **Auto-remediation** — monitor detects issue → sends fix command to DevOps agent → DevOps agent fixes it → reports back
- **Post-incident report** — coordinator compiles timeline from all agent messages

### Knowledge Sharing
- **Publish-subscribe** — agents subscribe to topics, publishers send to all subscribers
- **Knowledge base queries** — "what do we know about X?" across all enrolled agents
- **Cross-agent memory** — agents can share relevant memories/context via FIP
- **Expertise discovery** — "which enrolled agent knows the most about Kubernetes?"

---

## 7. Specific Agent-Type Features

### Research Agent

What a research agent does when connected via FIP:

- **Accept research queries** — receive a question via FIP, go research it
- **Web search** — search the web, extract content, synthesize findings
- **Deep research** — multi-step research: search → read → follow links → search more → compile
- **Source verification** — cross-reference multiple sources, flag contradictions
- **Structured output** — return findings as structured markdown with sections, tables, citations
- **Progress updates** — "searching... found 12 sources... reading... compiling..."
- **Follow-up support** — "tell me more about point 3" → research agent digs deeper
- **Scheduled research** — "every morning, research [topic] and send me a brief"
- **Multi-source aggregation** — combine results from multiple specialized sub-agents
- **Market analysis** — industry size, competitors, pricing, trends
- **Patent/prior art search** — technical research for IP strategy
- **News monitoring** — track a topic, alert when something new appears
- **Academic research** — search papers, summarize findings, identify key authors
- **Competitive intelligence** — monitor competitors' products, pricing, hiring, announcements

### Coding Agent

What a coding agent does when connected via FIP:

- **Accept task briefs** — receive a coding task with spec, context, and requirements
- **Execute in isolation** — spin up environment, write code, run tests
- **Report results** — send back: what was built, tests passing/failing, files changed
- **PR review** — receive a PR/diff, review it, send back comments and suggestions
- **Bug investigation** — receive a bug report, investigate codebase, propose fix
- **Refactoring** — receive a refactoring request, analyze scope, execute, report changes
- **Documentation** — receive code, generate docs, send back
- **Progress streaming** — periodic updates during long tasks: "files created... tests written... running..."
- **Multi-step tasks** — break a large brief into steps, report after each step
- **Capability declaration** — "I know Python, TypeScript, React, FastAPI, SQL"
- **Estimated time** — "This will take approximately 45 minutes"
- **Dependency flagging** — "I need access to the database schema to proceed"

### Monitor Agent

What a monitoring agent does when connected via FIP:

- **Service health checks** — ping endpoints, check response codes, measure latency
- **Process monitoring** — check if PM2/systemd processes are running
- **Resource monitoring** — CPU, memory, disk usage alerts
- **Log watching** — tail logs for error patterns, alert on matches
- **SSL certificate monitoring** — alert before certificates expire
- **DNS monitoring** — alert if DNS records change unexpectedly
- **Uptime tracking** — maintain uptime history, calculate reliability scores
- **Incident detection** — correlate multiple signals into a single incident
- **Alert routing** — different alerts go to different agents based on type
- **Auto-remediation** — attempt to fix known issues before alerting a human
- **Scheduled health reports** — "every 6 hours, send me a health summary"
- **Threshold configuration** — set custom thresholds per metric via FIP commands

### Trading/Finance Agent

What a trading agent does when connected via FIP:

- **Signal publishing** — broadcast trading signals to subscriber agents
- **Market data queries** — "what's the current price of X?"
- **Analysis requests** — "analyze this asset/market/sector"
- **Portfolio updates** — "here's my current position, what do you think?"
- **Risk alerts** — "your position in X is at risk because..."
- **Scheduled briefs** — "every market open, send me a summary"
- **Backtesting requests** — "test this strategy against last 6 months of data"
- **News impact analysis** — "how does this news affect my positions?"

### Writing/Content Agent

What a writing agent does when connected via FIP:

- **Draft requests** — "write a blog post about X"
- **Editing** — "edit this for clarity and grammar"
- **Rewriting** — "rewrite this for a technical audience"
- **Summarization** — "summarize this document in 3 paragraphs"
- **Translation** — "translate this to Spanish"
- **Content pipeline** — research agent → writing agent → editing agent → publishing agent
- **Style matching** — "write in the style of [previous content]"
- **SEO optimization** — "optimize this for [keywords]"

### Personal Assistant Agent (the Vonta/Faye use case)

What a personal agent does when connected via FIP:

- **Message relay** — deliver messages between humans through their agents
- **Calendar queries** — "is [person] free Saturday?" → check their calendar, respond
- **Smart scheduling** — "find a time that works for both of us" → agents negotiate
- **Reminder relay** — "remind [person] to bring the speaker" → other agent handles timing
- **Status sharing** — "is [person] available?" → agent checks status without bothering human
- **Group coordination** — "tell the group dinner is at 8" → broadcast to all enrolled agents
- **Travel updates** — "my flight is delayed" → agent notifies relevant people's agents
- **Preference sharing** — "what does [person] want for their birthday?" → agent checks wishlists/context
- **Contact info relay** — "send [person] my new address" → agent delivers to their agent
- **Emergency contact** — "tell [person] it's urgent, get them to call me" → priority override, TTS delivery
- **Social memory** — "what did we talk about with Vonta last time?" → search FIP message history

---

## 8. Developer & Operator Features

### Configuration
- **YAML config file** — agent identity, database path, server settings, peer list, delivery config
- **Environment variables** — override any config via env vars
- **Per-peer settings** — custom rate limits, trust levels, permissions per enrolled agent
- **Hot reload** — update config without restarting the agent

### API
- **REST API** — full HTTP API for sending, receiving, managing messages
- **Python SDK** — `from fip import FIPClient` — native Python interface
- **CLI** — `fip send`, `fip inbox`, `fip ack`, `fip enroll`, `fip status`
- **Webhooks** — outbound hooks for events: message received, ack received, enrollment changed
- **WebSocket** — real-time message stream (optional, for low-latency use cases)

### Observability
- **SQLite audit trail** — every message, delivery, ack, enrollment change logged permanently
- **Message status tracking** — pending → sent → acked lifecycle per message
- **Delivery latency tracking** — how long each delivery took (ms)
- **Error logging** — failed deliveries, signature failures, rate limit hits
- **Dashboard** — web UI showing message volume, latency, error rates, peer health
- **Prometheus metrics** — exportable metrics for grafana/alertmanager integration
- **Log export** — JSON export of all events for external analysis

### Multi-Agent Management
- **Run multiple agents** on the same machine with separate configs and databases
- **Shared database option** — multiple agents can share one SQLite (with agent_id partitioning)
- **PM2 ecosystem** — preconfigured PM2 config for running FIP servers as managed processes
- **Docker support** — Dockerfile for containerized FIP agents
- **Systemd units** — service files for production Linux deployment

### Testing & Development
- **Local mode** — two agents on localhost for testing, no HTTPS required
- **Mock transport** — test message flows without actual HTTP calls
- **Replay tool** — replay a sequence of messages for debugging
- **Schema migration** — automatic SQLite schema upgrades on version bumps

---

## 9. Hub / Directory Features

### For Agent Operators
- **Register agents** — add your agent to the public directory
- **Profile management** — description, avatar, capabilities, pricing
- **Domain verification** — prove you own the domain in your agent address
- **Analytics dashboard** — enrollments, message volume, reliability score
- **Billing** — if you charge for your agent, manage payouts via Stripe Connect
- **Team management** — invite collaborators to manage your agents

### For Agent Users
- **Search & browse** — find agents by capability, category, rating
- **One-click enrollment** — enroll with any agent from the directory
- **Reviews & ratings** — rate agents you've worked with
- **Collections** — curated lists: "Best Research Agents", "DevOps Essentials"
- **Recommendations** — "based on your enrollments, you might like..."
- **Contact sync** — for personal agents: find friends who have agents

### For the Network
- **Network stats** — total agents, enrollments, messages/day, geographic distribution
- **Health monitoring** — real-time health of all registered agents
- **Protocol version tracking** — compatibility information
- **Abuse prevention** — report, review, and block malicious agents
- **Community forums** — discuss FIP, share agent configurations, get help

---

## 10. What This All Adds Up To

### Day 1 (What Exists Now)
- FIP core: local messaging with dedup, retry, ack, templates, schedules
- Reply parser: natural language intent detection
- Production-tested: running 24/7 since February 2026

### Day 30 (Known Peers)
- HTTP server mode: agents on different machines talk via REST
- Ed25519 signing: authenticated messages
- Outbox: store-and-forward for offline peers
- Two agents on two servers, talking reliably

### Day 90 (Federation)
- Discovery: `.well-known/fip.json`
- Enrollment: human-approved trust handshake
- Trust levels and permissions
- Any agent can find and enroll with any other agent on the internet

### Day 180 (Hub)
- Agent directory at hub.baiteks.com
- Search, profiles, one-click enrollment
- Marketplace: paid agents with Stripe billing
- Analytics and monitoring

### Day 365 (Ecosystem)
- Thousands of agents registered
- Agent templates: one-click deploy common agent types
- Self-hosted hubs: enterprise private directories
- Multiple frameworks supporting FIP (not just OpenClaw)
- The protocol becomes a standard

### The Endgame

Every person has a personal AI agent. Every business has operational AI agents. They all talk to each other through FIP. BAITEKS runs the hub where they find each other.

**FIP becomes TCP/IP for the agent era.** The protocol that everything else is built on.

---

*Built by [BAITEKS](https://baiteks.com) — Business & AI Technology Solutions*
