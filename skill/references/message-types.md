# FIP Message Types

## Personal Communication

| Type | Use | Example |
|------|-----|---------|
| `personal.message` | Relay a message between humans | "Mike says what's up" |
| `personal.reply` | Reply to a personal message | "Vonta says he's good" |

## Queries

| Type | Use | Example |
|------|-----|---------|
| `calendar.query` | Ask about availability | "Is Vonta free Saturday?" |
| `calendar.response` | Respond with availability | "Free after 2 PM" |
| `status.request` | Ask if someone is available/around | "Is Mike around?" |
| `status.response` | Respond with status | "He's in a meeting" |

## Tasks

| Type | Use | Example |
|------|-----|---------|
| `task.request` | Ask another agent to do something | "Can you research X?" |
| `task.accepted` | Confirm task acceptance | "On it, ETA 30 min" |
| `task.complete` | Report task completion | "Done. Here are the results." |
| `task.rejected` | Decline a task | "I can't do that" |

## System

| Type | Use | Example |
|------|-----|---------|
| `enrollment.request` | Request to connect | "I'd like to message you" |
| `enrollment.approved` | Approve a connection | "Approved" |
| `enrollment.denied` | Deny a connection | "Denied" |
| `ping` | Health check | "Are you online?" |
| `pong` | Health response | "Yes" |

## Message Fields

Every FIP message has these fields:

```json
{
  "event_type": "personal.message",
  "priority": "normal",
  "title": "Message from Marcus",
  "body": "Mike says what's up, how are things?",
  "source": "marcus@marcus.baiteks.com",
  "target": "faye@hub.baiteks.com",
  "correlation_id": "evt-abc123",
  "requires_ack": false,
  "ttl_seconds": 900,
  "metadata": {}
}
```
