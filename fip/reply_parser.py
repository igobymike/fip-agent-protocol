"""Natural language reply intent parser for FIP acknowledgements.

Parses human or agent replies into structured intents:
- ack: message received and understood
- stop: deactivate the schedule / stop reminding
- snooze: defer for N minutes/hours
- run_now: execute the action immediately
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class ReplyIntent:
    intent: str  # ack, stop, snooze, run_now, unknown
    normalized: str
    duration_seconds: Optional[int] = None


def _normalize(text: str) -> str:
    s = text.strip().lower()
    s = s.replace("\u2019", "'")
    s = re.sub(r"[^a-z0-9\s']+", " ", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def _parse_duration(normalized: str) -> Optional[int]:
    m = re.search(
        r"(?:snooze|remind\s+me\s+in)\s+(\d+)\s*(m|min|mins|minute|minutes|h|hr|hrs|hour|hours)\b",
        normalized,
    )
    if not m:
        return None
    value = int(m.group(1))
    unit = m.group(2)
    return value * 3600 if unit.startswith("h") else value * 60


def parse_reply_intent(text: str) -> ReplyIntent:
    """Parse a natural language reply into a structured intent."""
    normalized = _normalize(text)

    # Check snooze first (has duration)
    seconds = _parse_duration(normalized)
    if seconds:
        return ReplyIntent(intent="snooze", normalized=normalized, duration_seconds=seconds)

    # Run now
    if re.search(r"\b(run it|run now|do it now|do it|execute|go ahead)\b", normalized):
        return ReplyIntent(intent="run_now", normalized=normalized)

    # Stop
    if re.search(r"\b(stop|stop it|don't remind|cancel|shut up|enough)\b", normalized):
        return ReplyIntent(intent="stop", normalized=normalized)

    # Ack
    if re.search(r"\b(heard it|got it|okay|ok|yes|done|i did|acknowledged|roger|copy|received)\b", normalized):
        return ReplyIntent(intent="ack", normalized=normalized)

    return ReplyIntent(intent="unknown", normalized=normalized)
