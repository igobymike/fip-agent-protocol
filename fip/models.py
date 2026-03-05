"""Data models for FIP events, acks, deliveries, templates, and schedules."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
import uuid
import time


@dataclass
class Event:
    event_type: str
    priority: str  # critical, high, normal, low
    delivery: str  # text_only, tts_only, text_and_tts, webhook, agent_inject
    title: str
    body: str
    source: str
    target: str
    correlation_id: str = field(default_factory=lambda: f"evt-{uuid.uuid4()}")
    injection_type: str = "event_injection"
    action_text: str = ""
    requires_ack: bool = False
    ttl_seconds: int = 900
    dedupe_key: str = ""
    status: str = "pending"
    metadata: dict = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    event_id: Optional[int] = None


@dataclass
class Delivery:
    event_id: int
    channel: str
    status: str  # sent, failed, suppressed
    detail: str = ""
    latency_ms: int = 0
    created_at: float = field(default_factory=time.time)


@dataclass
class Ack:
    event_id: int
    ack_type: str  # manual, auto, voice_auto_ingest
    ack_text: str = ""
    source: str = ""
    intent: str = "ack"  # ack, stop, snooze, run_now
    created_at: float = field(default_factory=time.time)


@dataclass
class Template:
    name: str
    injection_type: str
    priority: str
    delivery: str
    title_template: str
    body_template: str
    action_template: str = ""
    requires_ack: bool = False
    ttl_seconds: int = 900
    enabled: bool = True
    template_id: Optional[int] = None


@dataclass
class Schedule:
    name: str
    template_id: int
    run_at: str
    every_seconds: Optional[int] = None
    payload_json: str = "{}"
    max_attempts: Optional[int] = None
    requires_ack: bool = False
    quiet_hours_json: Optional[str] = None
    active: bool = True
