#!/usr/bin/env python3
"""Demo of the natural language reply intent parser."""

from fip import parse_reply_intent

# Test various replies
replies = [
    "got it",
    "okay",
    "done",
    "stop reminding me",
    "cancel",
    "snooze 30 minutes",
    "remind me in 2 hours",
    "run it now",
    "do it",
    "go ahead",
    "what are you talking about",
    "I need more context",
]

for reply in replies:
    result = parse_reply_intent(reply)
    duration = f" ({result.duration_seconds}s)" if result.duration_seconds else ""
    print(f'  "{reply}" → {result.intent}{duration}')
