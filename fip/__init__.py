"""FIP — Forced Injection Protocol for agent-to-agent messaging."""
from fip.client import FIPClient
from fip.models import Event, Ack, Delivery, Template, Schedule
from fip.reply_parser import parse_reply_intent, ReplyIntent

__version__ = "0.1.0"
__all__ = ["FIPClient", "Event", "Ack", "Delivery", "Template", "Schedule", "parse_reply_intent", "ReplyIntent"]
